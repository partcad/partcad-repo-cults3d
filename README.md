# Cults3D for PartCAD

Serves Cults3D's creations as PartCAD parts, published as
`//pub/collection/cults3d/models`.

**Your own creations are parts; everyone else's are found.** Cults3D's API
gives a creation's files to its creator only - "The API will not give you
access to the 3D files for other users", in Cults3D's own words, on its API
page. So the creations of the account you log in with are parts, a part per
file, and a search names everyone else's too, with where to get them, as what
it found and cannot serve.

**Every question needs a key.** Cults3D's API answers nobody anonymously, so
the plugin asks for nothing until it has your Cults3D nick and an API key:

```shell
pc login //pub/collection/cults3d:cults3d_repo
pc search parts -P //pub/collection/cults3d/models -k "cable clip"
pc inspect "//pub/collection/cults3d/models:<your creation's slug>"
```

Without them, every name and every search is answered with that `pc login`
line, and nothing is asked of Cults3D (see "Credentials").

**Nothing is listed.** A model site's catalog is not something to enumerate, so
`pc list parts` of this package is empty, as is `pc list packages`.

**No geometry is vendored.** Every file is fetched from Cults3D the first time a
part is built, and kept by PartCAD from then on.

**Nothing here is manufacturable.** The package says `manufacturable: false`,
and so does the plugin of what it serves: an upload to a model site says
nothing about whether, or how, it is made to be made.

Requires PartCAD 0.9.20 or newer, the first release with the toolkit the plugin
is written with (`plugin_models`). 0.9.3 was the first release with `pc login`, which is how
the plugin gets the key every question needs. Searching its own catalog
(`searchKinds`) and resolving a parametrized name itself (`instanceKinds`) are
described under "Repositories" in PartCAD's documentation.

## Names

A creation is a part per file of it that PartCAD reads, and the name says
which. A creation is named by its slug, the last part of its address,
`cults3d.com/en/3d-model/<category>/<slug>`:

| Name | Is |
| --- | --- |
| `cable-clip` | the creation's best file |
| `cable-clip;format=stl` | its best STL |
| `cable-clip;file=<name>` | one of its files, by name |

The slug alone, and not the category or the language before it: the slug is
what the API looks a creation up by (`creation(slug: ...)`), and the rest of
the address is presentation - the same creation is under every language, and
moves when its creator moves it to another category. A name is not case
sensitive (Cults3D's slugs are lower case).

Both may be given, and must then agree; a third, `source`, and the plugin's
own `formats` are under [Parameters](#parameters). "Best" is by format, in
this order unless `formats` says otherwise, and among files of one format the
first Cults3D lists:

| Format | Read as PartCAD part type | Extensions |
| --- | --- | --- |
| `step` | `step` | `.step`, `.stp` |
| `brep` | `brep` | `.brep`, `.brp` |
| `iges` | `iges` | `.iges`, `.igs` |
| `3mf` | `3mf` | `.3mf` |
| `stl` | `stl` | `.stl` |
| `obj` | `obj` | `.obj` |
| `glb` | `gltf` | `.glb` |
| `usd` | `usd` | `.usdz`, `.usd`, `.usdc`, `.usda` |
| `sldprt` | `sldprt` | `.sldprt` |
| `ipt` | `ipt` | `.ipt` |
| `catpart` | `catpart` | `.catpart` |
| `f3d` | `f3d` | `.f3d` |
| `fcstd` | `fcstd` | `.fcstd` |
| `sat` | `sat` | `.sat`, `.sab` |
| `pvz` | `pvz` | `.pvz` |
| `scad` | `scad` | `.scad` |

An exact boundary representation beats a mesh of it, and 3MF knows its units
where STL does not. A `.gltf` is not served, since the buffers it names beside
itself do not come with it. IGES is exact too, after STEP and BREP; OpenUSD - a
`.usdz`, a stage packed with its textures - comes after glTF; and the native
documents of CAD applications (SolidWorks, Inventor, CATIA, Fusion, FreeCAD,
ACIS, Creo View), which PartCAD reads through a converter it downloads on first
use, come after the meshes, to be taken when a model has nothing else or when
asked for. An OpenSCAD source is last, because on a model site
it is usually the customizable source of the meshes beside it. A file in any
other format - a ZIP, a picture - is not a part. A file's name is the last part
of the address the API gives for it, which is the name it was uploaded under.

A name that asks for somebody else's creation is not a part either, and says
whose it is, what it costs, and where to get it. One that asks for a file the
creation has not got says what it has.

These names are resolved by the plugin rather than by PartCAD applying the
parameters to a base part, because another file is another `path` and maybe
another `type`. `pc info` of a part shows the `file` and `format` it resolved
to, which is what to write to pin it: the best file of a creation can change
when you upload another.

## Search

`pc search parts -k <words>` asks Cults3D's own search (`creationsSearchBatch`).
Of what it finds, your own creations come first, as names of the form above -
one per file, so a hit is everything needed to fetch its geometry. Two files that
differ only in their extension (`clip.step`, `clip.stl`) are one part in two
formats, and only the better is named. Then the rest of what it found, in
Cults3D's order: each by its slug, with who made it, what it costs and its
address, as something found and not served, which PartCAD lists as such:

```text
//pub/collection/cults3d/models benchy-boat    Benchy boat, by bob (4.20 EUR): Cults3D's API gives its files to its creator only; get it from Cults3D
                                             https://cults3d.com/en/3d-model/game/benchy-boat
```

`--limit` caps the hits (20 by default). The plugin asks Cults3D for three times
as many creations, in one request, and reads the files of only your own.

A search is never cached by PartCAD; the plugin keeps what the site answered for
ten minutes.

## Credentials

The API takes HTTP Basic: your account's **nick** - the name your profile is
under, not your e-mail address - and an **API key** of that account, which you
make at <https://cults3d.com/en/api/keys>. A read-only key is enough; the plugin
only reads.

```shell
pc login //pub/collection/cults3d:cults3d_repo
```

checks the nick and key it already has, and keeps them if Cults3D still takes
them. Otherwise it opens your browser - PartCAD's own profile of it, with
PartCAD's extension - on the key page, behind Cults3D's sign-in. Sign in, make a
key, and paste the key and your nick into the extension's banner; the extension
takes a nick only without spaces, `:`, `/` or `@` (a leading `@` is dropped), and a
key only as a run of 16 or more letters, digits and `+/=_.-`, so a masked
`••••` or a placeholder is not taken for one. The plugin then asks the API whom
the pair is for (`myself { user { nick } }`), and PartCAD saves it as your own
parameters of the plugin, in your `~/.partcad/config.yaml`.

The key and the nick are pasted rather than read off the page because the
page's markup could not be seen from where this was written (see "Status"): a
key read off the wrong element would be a login that fails for no reason you
could see.

Or set them yourself, either way, never in a package:

```shell
export CULTS3D_NICK=...           # read by the plugin; see the note on Docker below
export CULTS3D_API_KEY=...
```

```yaml
# ~/.partcad/config.yaml
parameters:
  "//pub/collection/cults3d:cults3d_repo":
    nick: "..."
    api_key: "..."
```

`nick`, `api_key` are the package's, not only the plugin's: each says `shared: true`. With
PartCAD 0.10.4 or later, `pc login` keeps them under the package,
`"//pub/collection/cults3d":`, where an entry gives them to every object of the
package; an entry for the plugin, as above, still works, and wins over the
package's. An older PartCAD reads the plugin's entry only.

The pair is sent to `cults3d.com/graphql`, and to nothing else: a file is
fetched from the address the API gives for it, with no credentials.

**Without a key**, nothing is asked of Cults3D. A part, a file and a search each
say `... needs a Cults3D account's nick and API key, and none was given: run 'pc
login //pub/collection/cults3d:cults3d_repo' ...`. A key Cults3D no longer takes -
deleted, say - is the same, with the API's `HTTP 401`. PartCAD keeps none of
those answers on disk, but a PartCAD daemon that is already running remembers
them, without asking the plugin again, for as long as it runs: if a creation is
still "not found" once you have logged in, run `pc daemon stop` and ask again.

**Docker.** PartCAD runs a plugin in its Python sandbox, and the `docker` sandbox
does not carry PartCAD's environment into its container, so an environment
variable does not reach the plugin there. The repository parameters do, being
part of what PartCAD hands the plugin, and they are where `pc login` saves the
pair; use them, or `pythonSandbox: venv`.

### What Cults3D does not give

- **Somebody else's files.** Cults3D's API page says so in as many words, and
  the plugin does not ask for them: a creation that is not yours is read for its
  details only, and its files are never requested.
- **What you bought or downloaded.** The API lists your orders, with a download
  link per line, but those links are the website's and want its signed-in
  browser session - and the website admits browsers only (it answers anything
  else with Cloudflare's bot check). The plugin captures credentials and nothing
  else, does not pretend to be a browser, and does not work around a bot check;
  so those files are not served. Download them in the browser, and use the file
  in a package of your own.
- **What is inside a ZIP.** A creation uploaded as one ZIP is, to the API, one
  file called `<something>.zip`, and its members cannot be named without
  downloading it. It is not a part here; a search says so of it.

## Parameters

The plugin's parameters, declared in `partcad.yaml`, are a default for every
Cults3D part:

| Parameter | Default | What it is |
| --- | --- | --- |
| `formats` | all, in the order above | The formats to take a creation in, best first, separated by commas. A format left out is not taken - `stl,3mf` is meshes only - unless a part asks for it by its own `format` or `file`. |
| `source` | `auto` | Which of a creation's files: Cults3D has no preview meshes of its own, so `auto` and `original` are the same here and `preview` finds nothing. |
| `nick` | empty | Your account's nick, the name its profile is under. `CULTS3D_NICK` gives it too. |
| `api_key` | empty | An API key of that account, made at https://cults3d.com/en/api/keys (read-only is enough) - the only way in Cults3D's API has. `CULTS3D_API_KEY` gives it too. |

They are yours to set without touching this package - every one of them, the
credentials included, and the OAuth or API-key settings beside them:

- in your own `~/.partcad/config.yaml`, by the plugin's name, which is where
  `pc login` keeps the credentials:

  ```yaml
  parameters:
    "//pub/collection/cults3d:cults3d_repo":
      formats: stl,3mf
  ```

- or, for anything but the credentials, in a package of your own, as an enrich
  of the plugin and a package it serves - `//cults3d_meshes:<creation>` in a
  package at the root:

  ```yaml
  repositories:
    meshes_repo:
      type: enrich
      source: //pub/collection/cults3d:cults3d_repo
      with:
        formats: stl,3mf
  dependencies:
    cults3d_meshes:
      type: external
      plugin: :meshes_repo
  ```

A part's own `file`, `format` and `source` override them for that part - in its
name (`<slug>;format=stl`), or in the `with` of an enrich of the part:

```yaml
parts:
  clip:
    type: enrich
    source: //pub/collection/cults3d/models:<slug>
    with:
      format: stl
```

PartCAD keys what it caches of this package on your overrides of the plugin's
parameters, so a change to one - logging in, too - takes effect at once. An
environment variable is not seen there: after setting one, `pc update`
refreshes what was cached without it.

## Logging in with nobody at the screen

An AI agent, or a script, logs in without a browser:

```shell
pc login --agent //pub/collection/cults3d:cults3d_repo
pc login --agent --set nick=... --set api_key=... //pub/collection/cults3d:cults3d_repo
```

The first prints what a person would do in the browser instead of opening one -
where to sign in, what to copy, and the command that hands it over - and exits
with status 3. It says where the API key is made, and what the nick is. The second hands over what the person found; the
plugin checks it with Cults3D before PartCAD keeps it. `pc mcp`'s `login`
tool works the same way.

## Status

Run from a machine with no Cults3D account, so everything that needs a key is
written to Cults3D's own documentation and tested offline, against answers of
the shape that documentation shows.

Run live:

- **The API is there, and takes HTTP Basic.** `POST https://cults3d.com/graphql`
  with no credentials answers `401` with `WWW-Authenticate: Basic
  realm="Application"` and `HTTP Basic: Access denied.`; with a made-up nick and
  key, the same. That 401 is what `pc login` reads as "Cults3D does not take
  this pair".
- **The website turns away anything that is not a browser.** Every page asked
  for - the API documentation at `/en/api`, the key page, `/graphiql`, even
  `/robots.txt` - answered `403` with Cloudflare's challenge (`cf-mitigated:
  challenge`). So neither the documentation nor the key page's markup could be
  read from here; what the documentation says was read in search engines'
  excerpts of it, and the key is pasted rather than read off the page.
- **PartCAD, without a key.** `pc info //pub/collection/cults3d/models:<slug>` and
  `pc search parts -P //pub/collection/cults3d/models -k "cable clip"` both print
  the plugin's `pc login` message (the search then finds `<none>`), and `pc list
  parts` is empty. Asked again of the same daemon, `pc info` says "not found"
  without asking the plugin: the daemon remembers the first answer. PartCAD lists a hit with a `desc`, a `url` and no `type` as a
  thing found and not an object (checked with a stand-in for the plugin).

Not run, for want of a key:

- **A creation**: `creation(slug:) { name(locale: EN) url(locale: EN) creator {
  nick } license { name(locale: EN) } price(currency: EUR) { cents } }`, every
  field as Cults3D's own examples ask it. An unknown slug answers
  `creation: null`.
- **Its files**: `creation(slug:) { blueprints { fileUrl } }`, asked of your own
  creations only. Cults3D's examples read `blueprints { fileUrl }` of your own
  creations through `myself { creationsBatch }`; through `creation(slug:)` is
  how others' notes read them for one creation. Whether a `fileUrl` is a signed
  address that expires is not known, so it is asked afresh for every download.
- **Search**: `creationsSearchBatch(query:, limit:) { results { ... } }`, the
  same fields as a creation; a hit's slug is the last part of its `url`.
- **Whom a key is for**: `myself { user { nick } }`.
- **A slug in another language.** Every address is asked for in English
  (`url(locale: EN)`), and the slug taken from it. Whether `creation(slug:)`
  also takes the slug of another language's address is not known.
- **Throttling.** Cults3D's API is said to allow about 60 requests in 30 seconds
  and 500 a day. A search is one request; a creation of somebody else's, one; of
  your own, two; a download, one more to the API. A `429` is waited out and
  retried, as `Retry-After` says.

`pc login` was run against the live site in a real (headed) Chrome with
PartCAD's extension: from where it was tested, cults3d.com put Cloudflare's
"Verify you are human" in front of the API key page, which the extension's bar
asks the person to confirm, and nothing else. The key page itself, and the nick
and key pasted into the bar, were not seen live, for want of an account.

## Layout

| Path | Purpose |
| --- | --- |
| `partcad.yaml` | `//pub/collection/cults3d`; the `models` external dependency and the `cults3d_repo` repository that serves it. |
| `cults3d_repo.py` | The repository plugin: how Cults3D is asked, and how it is logged in to. |
| `test_*.py`, `conftest.py` | The tests. Nothing in them touches the network. They need PartCAD installed: the plugin imports its toolkit, `plugin_models`, from PartCAD's wrappers. |

```shell
python -m pytest
```

What every model-site plugin shares - the names, the formats, HTTP and its
cache, the keys PartCAD asks - is PartCAD's own toolkit, `plugin_models`, one
of its wrappers (PartCAD 0.9.20 and later), which the plugin imports wherever
PartCAD runs it.

When what the plugin answers changes - here, or in the `plugin_models` of a new
PartCAD - raise
`CACHE_VERSION` in `cults3d_repo.py`: PartCAD keys everything it caches of this
package on it.

## Caching

PartCAD keeps every answer the plugin gives, files included, under its own
cache, apart from a search and an answer that was no answer (no key, say),
which a running daemon remembers only until it stops (see "Credentials"). The
plugin keeps what Cults3D answered under `~/.cache/partcad-cults3d/` (or
`$PARTCAD_CULTS3D_CACHE`): a creation's details and its list of files for a day,
a search for ten minutes, and a request that came to nothing for a while too, so
that a refused or throttled run is not repeated in full by the next one - a 404
for a day, anything else for five minutes. A file's address is asked for afresh
for every download. A refusal of the key is not kept, so a new key works at
once. Delete the directory to start over.

Every request says what it is: `User-Agent: Mozilla/5.0 (compatible;
PartCAD-cults3d/<version>; +https://github.com/partcad/partcad-repo-cults3d)`.

## Licensing

The code here is Apache-2.0 (`LICENSE`). Each creation carries its own licence -
Creative Commons, or one of Cults3D's own, "Cults - Private Use" by default -
which the part states (`license`); it is the designer's, not this package's,
and it is the licence of your own creations that the parts here carry. Cults3D
explains its licences at <https://cults3d.com/en/licenses>.
