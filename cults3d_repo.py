#
# partcad-repo-cults3d, 2026
#
# Licensed under Apache License, Version 2.0.
#
"""A PartCAD 'basic' repository plugin that serves Cults3D creations as parts.

Published as ``//pub/collection/cults3d/models``. Nothing is listed: a part is
asked for by the creation's slug (the last part of
cults3d.com/<language>/3d-model/<category>/<slug>), and is one file of it.

    cable-clip                     the creation's best file (see remote_models.FORMATS)
    cable-clip;format=stl          its best STL
    cable-clip;file=clip.step      one of its files, by name

Everything is asked of Cults3D's GraphQL API, which takes HTTP Basic: the
account's nick and an API key made at https://cults3d.com/en/api/keys. There is
no anonymous way in, so without them every question is answered with how to
set them up ('pc login //pub/collection/cults3d:cults3d_repo').

And the API gives a creation's files to its creator only: "The API will not
give you access to the 3D files for other users", in Cults3D's own words. So
the creations of the account the key belongs to are parts, a part per file,
and everyone else's are found - a search names them, with where to get them -
and are not parts.

PartCAD runs this script once per key (via runpy) with the key in
``request["key"]``; the answer goes in ``output``. What the keys mean, and
everything else that is the same for every model site, is in remote_models.py.
"""

import base64
import importlib.util
import os
import re
import sys
import urllib.parse

# When this plugin's answers stopped meaning what they meant before. PartCAD
# keys everything it caches of this package on it, so raise it with any change
# to what is answered - here or in remote_models.py.
#
# v1: the creations of the signed-in account as parts, one per file; the rest
# found by search and not served.
# v2: a part's 'source' parameter, and the plugin's 'formats' and 'source' preferences;
#     'login' says what to do with nobody at the screen.
CACHE_VERSION = 2


def _shared():
    """remote_models.py, beside this script, under a name of this plugin's own."""
    name = "_partcad_cults3d_remote_models"
    if name not in sys.modules:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "remote_models.py")
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


rm = _shared()

WEB = "https://cults3d.com"
API = WEB + "/graphql"
KEYS_PAGE = WEB + "/en/api/keys"
PACKAGE = "//pub/collection/cults3d"
LOGIN = "pc login %s:cults3d_repo" % PACKAGE

# What a slug is. Cults3D makes them out of a creation's name, in lower case.
_SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,200}$", re.IGNORECASE)

# What the login's two values have to look like to be taken (see 'login_spec').
# A nick: no spaces, and not an e-mail address - the API wants the name the
# account is known by, and an address is the usual mistake. A leading '@' is
# allowed, and dropped. A key: a run of token characters, long enough not to be
# a placeholder, and not a masked '••••' either.
NICK_PATTERN = r"^@?[^\s:@/]{1,64}$"
KEY_PATTERN = r"^[A-Za-z0-9+/=_.-]{16,}$"

# The queries. Only fields Cults3D's own examples use, since a field the
# schema does not have fails the whole query, not just itself. Each is named,
# so that what was asked is plain in the site's logs as well as here.
CREATION = """
query Creation($slug: String!) {
  creation(slug: $slug) {
    name(locale: EN)
    url(locale: EN)
    creator { nick }
    license { name(locale: EN) }
    price(currency: EUR) { cents }
  }
}
"""

# Asked only of the signed-in account's own creations, the ones the API gives
# files of; and apart from the details above, so that what it answers about
# anyone else's cannot take the details down with it.
BLUEPRINTS = """
query Blueprints($slug: String!) {
  creation(slug: $slug) {
    blueprints { fileUrl }
  }
}
"""

SEARCH = """
query Search($query: String!, $limit: Int!) {
  creationsSearchBatch(query: $query, limit: $limit) {
    total
    results {
      name(locale: EN)
      url(locale: EN)
      creator { nick }
      license { name(locale: EN) }
      price(currency: EUR) { cents }
    }
  }
}
"""

WHOAMI = """
query Whoami {
  myself { user { nick } }
}
"""


def _slug_of(url):
    """The slug in a creation's address: its last path segment, whatever the language and category."""
    path = urllib.parse.urlsplit(url or "").path.rstrip("/")
    return urllib.parse.unquote(path.rsplit("/", 1)[-1]) if "/" in path else ""


def _name_of(url):
    """A file's name, out of the address the API gives for it."""
    return urllib.parse.unquote(urllib.parse.urlsplit(url or "").path.rstrip("/").rsplit("/", 1)[-1])


def _price(value):
    """'free', '4.20 EUR', or None when the API did not say."""
    cents = (value or {}).get("cents") if isinstance(value, dict) else None
    if not isinstance(cents, (int, float)):
        return None
    return "free" if cents == 0 else "%.2f EUR" % (cents / 100.0)


class Creation(rm.Model):
    """A model, and what Cults3D says of it beyond: whose it is, and what it costs."""

    def __init__(self, id, mine=False, price=None, **fields):
        super().__init__(id, **fields)
        self.mine = mine
        self.price = price


class Cults3D(rm.Site):
    NAME = "cults3d"
    TITLE = "Cults3D"
    URL = WEB
    DESC = (
        "Creations on Cults3D, by their slug: your own as parts, a part per file, and everyone's found by search. "
        "Nothing is listed; search instead."
    )
    VERSION = CACHE_VERSION
    LOGIN_INSTRUCTIONS = (
        "Cults3D's API signs in with the account's nick - the name its profile is under, not its e-mail address - and "
        "an API key, made at https://cults3d.com/en/api/keys while signed in (a read-only one is enough). It hands "
        "over the files of the account's own creations only."
    )
    CREDENTIALS = {"nick": "CULTS3D_NICK", "api_key": "CULTS3D_API_KEY"}

    def __init__(self, request=None):
        super().__init__(request)
        self.nick = rm.credential(self.request, "nick", "CULTS3D_NICK").lstrip("@")
        self.api_key = rm.credential(self.request, "api_key", "CULTS3D_API_KEY")

    def valid_id(self, model_id):
        return bool(_SLUG.match(model_id))

    # -- the API --

    @staticmethod
    def _auth(nick, api_key):
        return {"Authorization": "Basic " + base64.b64encode(("%s:%s" % (nick, api_key)).encode()).decode("ascii")}

    def graphql(self, query, variables, what, ttl=rm.DAY):
        """The 'data' of a query, asked with the user's nick and key. Raises SiteError."""
        if not (self.nick and self.api_key):
            raise rm.NeedsCredentials(
                "cults3d: %s needs a Cults3D account's nick and API key, and none was given: run '%s', "
                "or set CULTS3D_NICK and CULTS3D_API_KEY (see the README)" % (what, LOGIN)
            )
        try:
            answer = self.http.json(
                API,
                what,
                headers=self._auth(self.nick, self.api_key),
                data={"query": query, "variables": variables},
                ttl=ttl,
            )
        except rm.NeedsCredentials as e:
            raise rm.NeedsCredentials(
                "%s. Cults3D did not take the nick '%s' with the API key given for it - the key may have been "
                "deleted: run '%s'" % (e, self.nick, LOGIN)
            )
        data = answer.get("data") if isinstance(answer, dict) else None
        if not isinstance(data, dict):
            errors = answer.get("errors") if isinstance(answer, dict) else None
            said = "; ".join(str((e or {}).get("message", e)) for e in errors or [] if e) or "no data"
            raise rm.SiteError("cults3d: %s: the API answered: %s" % (what, said[:300]))
        return data

    def _details(self, slug):
        creation = self.graphql(CREATION, {"slug": slug}, "creation %s" % slug).get("creation")
        if not isinstance(creation, dict):
            raise rm.NotFound("cults3d: creation %s: not found" % slug)
        return creation

    def _creation(self, slug, details, files=None):
        nick = (details.get("creator") or {}).get("nick")
        return Creation(
            slug,
            title=details.get("name"),
            url=details.get("url") or None,
            author=nick,
            license=(details.get("license") or {}).get("name"),
            files=files,
            mine=bool(nick) and nick.lower() == self.nick.lower(),
            price=_price(details.get("price")),
        )

    def _blueprints(self, slug, ttl=rm.DAY):
        """The files of one of the account's own creations, each named by the last part of its address."""
        creation = self.graphql(BLUEPRINTS, {"slug": slug}, "the files of creation %s" % slug, ttl=ttl).get("creation")
        files, names = [], {}
        for blueprint in (creation or {}).get("blueprints") or []:
            link = (blueprint or {}).get("fileUrl")
            name = _name_of(link)
            if not link or not name:
                continue
            # A name is what a file is asked for by, so two of one name are
            # told apart by a count.
            names[name] = names.get(name, 0) + 1
            key = name if names[name] == 1 else "%s#%d" % (name, names[name])
            files.append(rm.File(key, name, link=link))
        return files

    def model(self, model_id):
        slug = model_id.lower()
        creation = self._creation(slug, self._details(slug), files=[])
        # Nobody else's files are the API's to give, so they are not asked
        # for: a request that can only be refused, against a daily allowance.
        if creation.mine:
            creation.files = self._blueprints(slug)
        return creation

    def choose(self, model, wanted_file=None, wanted_format=None, wanted_source=None):
        if not model.files and not model.mine:
            raise rm.NotFound(
                "cults3d: %s is %s's creation, and Cults3D's API gives a creation's files to its creator only. "
                "Get it from %s%s, and use the file in a package of your own"
                % (
                    model.id,
                    model.author or "someone else",
                    model.url or "Cults3D",
                    " (%s)" % model.price if model.price else "",
                )
            )
        return super().choose(model, wanted_file, wanted_format, wanted_source)

    def download(self, model, file):
        # Asked again rather than read out of the cache: the address may be a
        # signed one, good for a while.
        for fresh in self._blueprints(model.id, ttl=0):
            if fresh.id == file.id:
                # Where the API says the file is, asked with no credentials:
                # the key is for the API, and nothing else is shown it.
                return self.http.download(fresh.extra["link"], "%s of creation %s" % (file.name, model.id))
        raise rm.NotFound("cults3d: creation %s no longer has the file %s" % (model.id, file.name))

    def search(self, text, limit):
        data = self.graphql(SEARCH, {"query": text, "limit": limit}, "a search for '%s'" % text, ttl=600)
        models = []
        for hit in ((data.get("creationsSearchBatch") or {}).get("results")) or []:
            slug = _slug_of((hit or {}).get("url"))
            if not slug or not self.valid_id(slug):
                continue
            creation = self._creation(slug.lower(), hit)
            # The account's own are read in full by 'find'; nobody else's files
            # are the API's to give, so they are not asked for.
            creation.files = None if creation.mine else []
            models.append(creation)
        return models

    def unserved(self, model):
        """Every creation a search finds is worth naming, even the ones Cults3D will not hand over."""
        if getattr(model, "mine", False):
            return "it has no file PartCAD reads"
        return "Cults3D's API gives its files to its creator only; get it from Cults3D"

    def unserved_hit(self, model, reason):
        config = super().unserved_hit(model, reason)
        price = getattr(model, "price", None)
        config["desc"] = "%s, by %s%s: %s" % (
            model.title or model.id,
            model.author or "someone",
            " (%s)" % price if price else "",
            reason,
        )
        return config

    # -- logging in --

    def whoami(self, credentials):
        nick = (credentials.get("nick") or "").lstrip("@")
        api_key = credentials.get("api_key") or ""
        if not (nick and api_key):
            return None
        status, body = self.http.probe(
            API, "the account's nick", headers=self._auth(nick, api_key), data={"query": WHOAMI, "variables": {}}
        )
        if status in (401, 403):
            return None
        if status != 200:
            raise rm.SiteError("cults3d: the API could not be asked whom the key is for: HTTP %d" % status)
        # The API asks for the nick and key before it reads the query, and
        # turns away a pair it does not take with a 401: an answer at all is
        # the pair taken, whatever it says.
        data = body.get("data") if isinstance(body, dict) else None
        user = ((data or {}).get("myself") or {}).get("user") or {}
        return user.get("nick") or nick

    def login_spec(self):
        # The key page is behind the sign-in, and its markup could not be read
        # from where this was written (the site shows anything that is not a
        # browser a bot check). So the key and the nick are pasted into the
        # extension's banner rather than read off the page by a selector that
        # may not match - a key read wrongly would be a login that fails for
        # no reason the user can see. The guide's selectors are guesses, and a
        # guess that matches nothing shows nothing.
        return {
            "url": KEYS_PAGE,
            "title": "Log in to Cults3D",
            "capture": [
                {
                    "name": "nick",
                    "ask": {"label": "Your Cults3D nick: the name your profile is under, not your e-mail address"},
                    "match": NICK_PATTERN,
                },
                {
                    "name": "api_key",
                    "ask": {"label": "The API key you created for PartCAD", "secret": True},
                    "match": KEY_PATTERN,
                },
            ],
            "guide": [
                {
                    "url": WEB + "/*/api/keys*",
                    "selector": "form[action*='/api/keys'] [type=submit]",
                    "text": "Create a key for PartCAD (a read-only one is enough), then paste it and your nick "
                    "into PartCAD's banner",
                },
                {
                    "url": WEB + "/*/api/keys*",
                    "selector": "h1",
                    "text": "Create an API key here for PartCAD (a read-only one is enough), then paste it and "
                    "your nick into PartCAD's banner",
                },
            ],
        }

    def credentials_from(self, captured):
        fresh = super().credentials_from(captured)
        fresh["nick"] = fresh["nick"].lstrip("@")
        return fresh


def get(key):
    return rm.serve(Cults3D(globals().get("request")), key)


# Last, so that everything above is defined when PartCAD runs this.
if __name__ == "get":
    output = {"result": get(request["key"])}  # noqa: F821 - injected by the runtime
elif __name__ == "login":
    output = {"result": rm.login(Cults3D(globals().get("request")), globals().get("partcad_login"))}
else:
    output = {}
