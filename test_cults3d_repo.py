#
# partcad-repo-cults3d, 2026
#
# Licensed under Apache License, Version 2.0.
#
"""Tests of the Cults3D plugin, with Cults3D answered from a table.

Every question is a POST to the one GraphQL endpoint, so the table is by the
query's operation and what it was asked about. The answers have the shape
Cults3D's own query examples show, with values made up; the API's refusal is
the one it gave this plugin's author, word for word. Nothing here touches the
network.
"""

import base64
import importlib.util
import json
import os
import re
import runpy
import urllib.parse

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN = os.path.join(_HERE, "cults3d_repo.py")
_SPEC = importlib.util.spec_from_file_location("cults3d_repo_under_test", _PLUGIN)
plugin = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(plugin)
rm = plugin.rm

API = "https://cults3d.com/graphql"
LOGIN = "pc login //pub/collection/cults3d:cults3d_repo"
NICK = "ann"
KEY = "k3yK3yk3yK3yk3yK3yk3yK3y"
CDN = "https://files.cults3d.com/uploaders/1/blueprint-file-en/"

CREATIONS = {
    "cable-clip": {
        "name": "Cable clip",
        "url": "https://cults3d.com/en/3d-model/various/cable-clip",
        "creator": {"nick": "ann"},
        "license": {"name": "Creative Commons - Attribution"},
        "price": {"cents": 0},
    },
    "benchy-boat": {
        "name": "Benchy boat",
        "url": "https://cults3d.com/en/3d-model/game/benchy-boat",
        "creator": {"nick": "bob"},
        "license": {"name": "Cults - Private Use"},
        "price": {"cents": 420},
    },
    # The account's own, as Cults3D spells its creator's nick there.
    "parts-box": {
        "name": "Parts box",
        "url": "https://cults3d.com/en/3d-model/tool/parts-box",
        "creator": {"nick": "Ann"},
        "license": None,
        "price": {"cents": 150},
    },
}
BLUEPRINTS = {
    "cable-clip": ["a1/clip.stl", "a2/clip.step", "a3/base%20plate.3mf", "a4/all.zip"],
    "parts-box": ["b1/box.zip", "b2/render.jpg"],
}


def _basic(nick, key):
    return "Basic " + base64.b64encode(("%s:%s" % (nick, key)).encode()).decode()


class Wire:
    """Cults3D: the API by operation and the slug or the words it was asked, and the files by address.

    It takes one nick and key, and turns away any other pair as the API does.
    A file's address is signed afresh every time the API is asked for it.
    """

    def __init__(self):
        self.asked = []
        self.errors = {}
        self.signed = 0

    def operations(self, name):
        return [data for url, _, data in self.asked if url == API and _operation(data) == name]

    def __call__(self, url, headers=None, data=None, method=None, timeout=60):
        self.asked.append((url, dict(headers or {}), data))
        if url == API:
            if (headers or {}).get("Authorization") != _basic(NICK, KEY):
                return rm.Response(
                    401,
                    {"Content-Type": "text/html; charset=utf-8", "WWW-Authenticate": 'Basic realm="Application"'},
                    b"HTTP Basic: Access denied.",
                    url,
                )
            return rm.Response(200, {"Content-Type": "application/json"}, _json(self.graphql(data)), url)
        parts = urllib.parse.urlsplit(url)
        if url.startswith(CDN) and parts.query == "sig=%d" % self.signed:
            return rm.Response(200, {}, ("bytes of " + parts.path.rsplit("/", 1)[-1]).encode(), url)
        return rm.Response(403, {}, b"<Error><Code>AccessDenied</Code></Error>", url)

    def graphql(self, data):
        operation, variables = _operation(data), data.get("variables") or {}
        slug = variables.get("slug")
        if slug in self.errors:
            return self.errors[slug]
        if operation == "Creation":
            return {"data": {"creation": CREATIONS.get(slug)}}
        if operation == "Blueprints":
            if slug not in BLUEPRINTS:
                return {"data": {"creation": None}, "errors": [{"message": "Not authorized"}]}
            self.signed += 1
            return {
                "data": {
                    "creation": {
                        "blueprints": [{"fileUrl": "%s%s?sig=%d" % (CDN, p, self.signed)} for p in BLUEPRINTS[slug]]
                    }
                }
            }
        if operation == "Search":
            words = variables["query"].lower()
            found = [c for c in CREATIONS.values() if any(w in c["name"].lower() for w in words.split())]
            return {"data": {"creationsSearchBatch": {"total": len(found), "results": found[: variables["limit"]]}}}
        if operation == "Whoami":
            return {"data": {"myself": {"user": {"nick": NICK}}}}
        return {"errors": [{"message": "Field '%s' doesn't exist" % operation}]}


def _operation(data):
    return re.match(r"\s*query\s+(\w+)", data["query"]).group(1)


def _json(value):
    return json.dumps(value).encode()


@pytest.fixture
def site(tmp_path, monkeypatch):
    monkeypatch.setenv("PARTCAD_CULTS3D_CACHE", str(tmp_path))
    monkeypatch.delenv("CULTS3D_NICK", raising=False)
    monkeypatch.delenv("CULTS3D_API_KEY", raising=False)

    def make(nick=NICK, api_key=KEY):
        made = plugin.Cults3D({"parameters": {"nick": nick, "api_key": api_key}})
        made.http.request = Wire()
        return made

    return make


# --- creations and their files -------------------------------------------------------


def test_a_creation_of_ones_own_is_its_best_file(site):
    config = site().get("objects/part/cable-clip")
    assert config["type"] == "step"
    assert config["desc"] == "Cable clip: clip.step"
    assert config["url"] == "https://cults3d.com/en/3d-model/various/cable-clip"
    assert config["author"] == "ann"
    assert config["license"] == "Creative Commons - Attribution"
    assert config["parameters"]["file"]["default"] == "clip.step"


def test_a_file_is_chosen_by_its_name_or_its_format(site):
    made = site()
    assert made.get("objects/part/cable-clip;file=base plate.3mf")["type"] == "3mf"
    assert made.get("objects/part/cable-clip;format=stl")["desc"] == "Cable clip: clip.stl"
    # The slug as anyone might type it is the same creation.
    assert made.get("objects/part/Cable-Clip")["desc"] == "Cable clip: clip.step"


def test_a_creation_that_is_an_archive_is_not_a_part_and_says_so(site, capsys):
    assert rm.serve(site(), "objects/part/parts-box") is None
    err = capsys.readouterr().err
    assert "has no file PartCAD reads" in err and "box.zip" in err


def test_a_download_is_from_a_fresh_address_with_no_credentials(site):
    made = site()
    config = made.get("objects/part/cable-clip;format=stl")
    assert base64.b64decode(made.get("files/" + config["path"])) == b"bytes of clip.stl"
    wire = made.http.request
    # Once to resolve the name, from the cache to find the file, and once
    # more for an address that is still good.
    assert len(wire.operations("Blueprints")) == 2
    downloads = [(url, headers) for url, headers, _ in wire.asked if url.startswith(CDN)]
    assert downloads == [(CDN + "a1/clip.stl?sig=2", {})]
    assert all(headers["Authorization"] == _basic(NICK, KEY) for url, headers, _ in wire.asked if url == API)


def test_someone_elses_creation_is_found_and_not_served(site, capsys):
    made = site()
    assert rm.serve(made, "objects/part/benchy-boat") is None
    err = capsys.readouterr().err
    assert "benchy-boat is bob's creation" in err and "to its creator only" in err
    assert "https://cults3d.com/en/3d-model/game/benchy-boat (4.20 EUR)" in err
    # Its files are not the API's to give, so they are not asked for.
    assert made.http.request.operations("Blueprints") == []


def test_an_unknown_slug_is_not_found_and_nonsense_costs_nothing(site, capsys):
    made = site()
    assert rm.serve(made, "objects/part/no-such-creation") is None
    assert "creation no-such-creation: not found" in capsys.readouterr().err
    asked = len(made.http.request.asked)
    assert rm.serve(made, "objects/part/not a slug!") is None
    assert len(made.http.request.asked) == asked


def test_an_error_the_api_answers_with_is_said(site, capsys):
    made = site()
    made.http.request.errors["cable-clip"] = {"data": None, "errors": [{"message": "Internal server error"}]}
    assert rm.serve(made, "objects/part/cable-clip") is None
    assert "creation cable-clip: the API answered: Internal server error" in capsys.readouterr().err


# --- without a key, or with one the API does not take ----------------------------------


def test_without_credentials_every_question_says_how_to_log_in(site, capsys):
    made = site(nick="", api_key="")
    meta = made.get("meta")
    assert meta["manufacturable"] is False and meta["searchKinds"] == ["part"]
    assert made.get("objects/part") == {}
    for key in ("objects/part/cable-clip", "search/part?q=clip", "files/cable-clip/x/clip.stl"):
        assert rm.serve(made, key) is None
        err = capsys.readouterr().err
        assert "needs a Cults3D account's nick and API key" in err and LOGIN in err, key
    assert made.http.request.asked == []


def test_a_nick_without_a_key_is_no_credentials(site, capsys):
    assert rm.serve(site(api_key=""), "objects/part/cable-clip") is None
    assert LOGIN in capsys.readouterr().err


def test_a_key_the_api_does_not_take_says_to_log_in_again(site, capsys):
    assert rm.serve(site(api_key="d" * 24), "objects/part/cable-clip") is None
    err = capsys.readouterr().err
    assert "(HTTP 401)" in err and "did not take the nick 'ann'" in err and LOGIN in err


def test_the_environment_gives_credentials_too(site, monkeypatch):
    monkeypatch.setenv("CULTS3D_NICK", "@" + NICK)
    monkeypatch.setenv("CULTS3D_API_KEY", KEY)
    made = plugin.Cults3D({"parameters": {}})
    made.http.request = Wire()
    assert made.get("objects/part/cable-clip")["type"] == "step"


# --- search ----------------------------------------------------------------------------


def test_a_search_names_ones_own_files_then_what_else_it_found(site):
    made = site()
    hits = made.get("search/part?q=clip+boat")
    assert list(hits) == ["cable-clip;file=clip.step", "cable-clip;file=base plate.3mf", "benchy-boat"]
    assert hits["cable-clip;file=clip.step"]["type"] == "step"
    assert hits["benchy-boat"] == {
        "desc": "Benchy boat, by bob (4.20 EUR): Cults3D's API gives its files to its creator only; "
        "get it from Cults3D",
        "url": "https://cults3d.com/en/3d-model/game/benchy-boat",
    }
    (search,) = made.http.request.operations("Search")
    assert search["variables"] == {"query": "clip boat", "limit": 3 * rm.DEFAULT_LIMIT}


def test_a_search_answers_no_more_than_it_is_asked_for(site):
    made = site()
    assert list(made.get("search/part?q=clip+boat&limit=1")) == ["cable-clip;file=clip.step"]
    assert list(made.get("search/part?q=boat+box&limit=2")) == ["benchy-boat", "parts-box"]
    assert made.get("search/part?q=boat+box&limit=2")["parts-box"]["desc"] == (
        "Parts box, by Ann (1.50 EUR): it has no file PartCAD reads"
    )


def test_an_empty_search_asks_nothing(site):
    made = site()
    assert made.get("search/part?q=") == {}
    assert made.http.request.asked == []


# --- logging in ------------------------------------------------------------------------


class BrowserNeeded(BaseException):
    """What PartCAD's callback raises the first time: not an Exception, so nothing in the plugin catches it."""


class Callback:
    """PartCAD's 'partcad_login', replaying: raises the first time, returns what the browser sent after."""

    def __init__(self, results=()):
        self.results = list(results)
        self.calls = []

    def open_browser(self, **spec):
        self.calls.append(spec)
        if len(self.calls) > len(self.results):
            raise BrowserNeeded(spec)
        return self.results[len(self.calls) - 1]


def test_credentials_the_api_takes_are_kept_without_a_browser(site):
    made, callback = site(), Callback()
    assert rm.login(made, callback) == {
        "parameters": {"nick": NICK, "api_key": KEY},
        "message": "Already logged in to Cults3D as ann",
    }
    assert callback.calls == []
    (whoami,) = made.http.request.operations("Whoami")
    assert whoami["variables"] == {}


def test_stale_credentials_open_the_key_page(site):
    callback = Callback()
    with pytest.raises(BrowserNeeded):
        rm.login(site(api_key="d" * 24), callback)
    (spec,) = callback.calls
    assert spec["url"] == "https://cults3d.com/en/api/keys"
    assert spec["title"] == "Log in to Cults3D"
    captured = {item["name"]: item for item in spec["capture"]}
    assert set(captured) == {"nick", "api_key"}
    assert captured["api_key"]["ask"]["secret"] is True
    assert not captured["nick"]["ask"].get("secret")


def test_no_credentials_open_the_key_page_and_ask_nothing_first(site):
    made, callback = site(nick="", api_key=""), Callback()
    with pytest.raises(BrowserNeeded):
        rm.login(made, callback)
    assert len(callback.calls) == 1 and made.http.request.asked == []


def test_what_the_browser_brings_back_becomes_the_credentials(site):
    made = site(nick="", api_key="")
    result = rm.login(made, Callback([{"nick": " @ann ", "api_key": " %s\n" % KEY}]))
    assert result == {"parameters": {"nick": NICK, "api_key": KEY}, "message": "Logged in to Cults3D as ann"}
    _, headers, _ = made.http.request.asked[0]
    assert headers["Authorization"] == _basic(NICK, KEY)


def test_a_pair_the_api_does_not_take_fails_the_login(site):
    with pytest.raises(RuntimeError, match="does not take what the login captured"):
        rm.login(site(nick="", api_key=""), Callback([{"nick": "ann", "api_key": "d" * 24}]))


def test_the_login_asks_the_browser_for_what_partcad_can_ask_it(site):
    """The spec as login-protocol section 2 has it: one source per capture, 'match' beside it."""
    spec = site().login_spec()
    assert spec["url"].startswith("https://")
    sources = ("cookie", "localStorage", "sessionStorage", "dom", "redirect", "ask")
    for item in spec["capture"]:
        (source,) = [s for s in sources if s in item]
        assert item[source]["label"] and re.compile(item["match"])
    for step in spec["guide"]:
        assert step["url"].startswith("https://cults3d.com/") and step["selector"] and step["text"]


@pytest.mark.parametrize("nick", ["ann", "@ann", "Gaetan_DJ", "3d.parts-42"])
def test_a_nick_is_taken(nick):
    assert re.match(plugin.NICK_PATTERN, nick)


@pytest.mark.parametrize("nick", ["", "ann@example.com", "ann smith", "ann:key", "https://cults3d.com/en/users/ann"])
def test_what_is_not_a_nick_is_not_taken(nick):
    assert not re.match(plugin.NICK_PATTERN, nick)


@pytest.mark.parametrize("key", [KEY, "0123456789abcdef0123456789abcdef", "Zq4-x_Lm9Pw2Rt7Yv8Nk3Hd6"])
def test_a_key_is_taken(key):
    assert re.match(plugin.KEY_PATTERN, key)


@pytest.mark.parametrize("key", ["", "xxxx", "your API key", "•" * 24, "*" * 24, "Bearer " + KEY])
def test_what_is_not_a_key_is_not_taken(key):
    assert not re.match(plugin.KEY_PATTERN, key)


def test_whoami_is_the_nick_the_api_answers_for(site):
    made = site()
    assert made.whoami({"nick": "@ann", "api_key": KEY}) == "ann"
    assert made.whoami({"nick": "ann", "api_key": "d" * 24}) is None
    asked = len(made.http.request.asked)
    assert made.whoami({"nick": "ann", "api_key": ""}) is None
    assert len(made.http.request.asked) == asked


def test_whoami_does_not_take_an_api_it_cannot_ask_for_a_no(site):
    made = site()
    made.http.request = lambda url, **kw: rm.Response(502, {}, b"<html>Bad gateway</html>", url)
    with pytest.raises(rm.SiteError, match="HTTP 502"):
        made.whoami({"nick": "ann", "api_key": KEY})


# --- how PartCAD runs it ---------------------------------------------------------------


def test_partcad_runs_it_for_a_key_and_reads_the_answer_from_output():
    result = runpy.run_path(_PLUGIN, init_globals={"request": {"key": "meta", "parameters": {}}}, run_name="get")
    assert result["output"]["result"]["manufacturable"] is False


def test_partcad_runs_it_for_a_login(monkeypatch, tmp_path):
    monkeypatch.setenv("PARTCAD_CULTS3D_CACHE", str(tmp_path))
    monkeypatch.delenv("CULTS3D_NICK", raising=False)
    monkeypatch.delenv("CULTS3D_API_KEY", raising=False)
    callback = Callback()
    request = {"api": "login", "parameters": {"nick": "", "api_key": ""}, "login": {"browser": []}}
    with pytest.raises(BrowserNeeded):
        runpy.run_path(_PLUGIN, init_globals={"request": request, "partcad_login": callback}, run_name="login")
    assert callback.calls[0]["url"] == "https://cults3d.com/en/api/keys"
    with pytest.raises(RuntimeError, match="upgrade PartCAD"):
        runpy.run_path(_PLUGIN, init_globals={"request": request}, run_name="login")
