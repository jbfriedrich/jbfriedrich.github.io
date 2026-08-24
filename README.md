# friedrich.uk

Landing page for friedrich.uk. It aggregates content already published elsewhere —
blog posts, links, notes, status posts, Mastodon and a Goodreads shelf — and links back
to each source. Nothing is authored here.

Built with Hugo. Feeds are fetched and parsed at build time, so the published site is
static: no JavaScript fetches anything, and no visitor request reaches a third party.

## Requirements

- **Hugo 0.141–0.160.1, extended.** The range is enforced; see [Hugo version](#hugo-version).
- The Tailwind CSS standalone binary. `./scripts/get-tailwind.sh` fetches the pinned
  version into `bin/` (git-ignored). No Node, no npm, no `node_modules`.
- Python 3 for the test suite.

## Build

```
./scripts/get-tailwind.sh          # once
PATH="$PWD/bin:$PATH" hugo
```

Output lands in `public/`. For a local preview use `hugo server`.

The deployed site is built and published by `blogdeploy` on a schedule, because its
content changes when other people publish, not when this repository changes.

## Configuration

Everything lives in `hugo.yaml`. No hostname, feed URL or item count appears in a
template, so moving a domain is a config edit.

Each entry under `params.sources` describes one source:

| Key | Meaning |
|---|---|
| `key` | Identifier, used for the tile's hue and its `data-source` attribute |
| `label` | Heading shown on the tile |
| `kind` | `atom`, `rss` or `goodreads` — selects the branch in `normalise.html` |
| `feed` | Feed URL |
| `home` | Where the tile heading links |
| `count` | Items to display |
| `overfetch` | Items to read before filtering, when `excludes` would otherwise eat the count |
| `excludes` | Drop items whose URL or summary contains any of these strings |
| `hue` | Colour token for the tile |
| `full` | Render as a full-width tile |

Adding a source is a new entry plus a hue in `assets/css/main.css`.

### Presets

`params.preset` selects the layout: `channels` (tiles) or `signal` (dense rows). Both
render the same normalised data through `partials/items.html`; neither contains any
fetching or filtering logic.

### Hue tokens

The six source colours are chosen for perceptual distance, not by eye: every pair is at
least ΔE 25 apart in both light and dark themes. Two earlier choices failed that and were
replaced — green read as the same colour as teal, and Mastodon's brand periwinkle sat too
close to the blue used for posts. Any colour added later should clear the same floor.

## How a feed becomes a tile

```
partials/source.html     fetch + unmarshal, one source        -> ok, data
partials/normalise.html  four feed shapes -> one item record
partials/items.html      excludes, then overfetch, then count -> the tile's items
partials/presets/*.html  render
```

The item record is `title, url, permalink, host, date, tags, summary, image, rating`.
Presets read only that, which is why two very different layouts share one data path.

`source.html` is the seam. It is the only place that talks to the network, so replacing
build-time fetching with something else means changing one file.

## Failure handling

**A failing source costs one tile, never the build.** The site rebuilds unattended, so a
build that dies on someone else's outage would silently stop updating.

Each source is fetched and parsed inside its own `try`, and every raw XML read goes
through a coercion helper. The failures that are handled, all of which have occurred:

- **404** — `GetRemote` raises no error and returns nil, so `try` alone does not catch it
- **Connection refused** — caught by `try`
- **200 with a body that is not a feed** — the fetch succeeds and `transform.Unmarshal` fails
- **A cover image that is not an image** — the media type is checked before resizing
- **Empty, malformed or single-digit-day dates** — undated items are skipped, never given a fabricated date
- **A non-numeric rating** — coerced safely rather than passed to `int`
- **One-item feeds** — an XML element unmarshals to a map when there is one and a slice when there are several
- **Elements carrying attributes** — `<title type="text">` unmarshals to a map where a string is expected

A source that fails renders an empty tile, and the hero's `n/m sources` count reflects it.

## Tests

```
./tests/run.sh
```

Builds both presets and asserts the result. **The suite is online by design**: it fetches
the live feeds, because a site whose job is reading other people's feeds is not usefully
tested against frozen copies. A failure means a feed really is unreachable or has changed
shape — which is worth hearing about.

Assertions are structural rather than content-based, since anything named would age out
of the feed within days: counts are honoured, cross-posted asides do not appear in the
Mastodon tile, link cards point their title at the outbound article and their note at the
author's page, book covers are self-hosted, entities are decoded once.

`tests/hugo.test.yaml` is merged over `hugo.yaml` and adds three sources that are meant to
fail — one per failure mode — so the guarantee above stays covered. It also disables the
resource cache so each run performs the fetches it claims to.

## Hugo version

`hugo.yaml` pins Hugo to `0.141.0`–`0.160.1`.

The floor is `try`, which replaced `.Err` in 0.141 and which the feed partials rely on.

The ceiling is Tailwind. Hugo 0.161 dropped support for the standalone binary:
`css.TailwindCSS` now requires `@tailwindcss/cli` installed via npm as a Node script, so
Hugo can run it under `node --permission` and sandbox its filesystem access. That
hardening benefits people already running npm build tooling; this project deliberately
runs none, and adopting npm to regain a feature only needed because npm is absent would be
backwards.

`module.hugoVersion` only warns for the main project, so `partials/head.html` fails the
build outright on 0.161 or newer. Without it, a newer Hugo fails at render time with the
opaque `binary "tailwindcss" is not a Node.js script`.

## Layout

| Path | Contents |
|---|---|
| `hugo.yaml` | Site config: sources, links, preset, version pin |
| `layouts/partials/` | Fetch, normalise and render |
| `layouts/partials/presets/` | `channels.html`, `signal.html` |
| `assets/css/main.css` | Tailwind entry, design tokens, layout |
| `static/` | Favicons, avatar, `robots.txt`, the WebFinger document |
| `scripts/get-tailwind.sh` | Fetches the pinned Tailwind binary |
| `tests/` | Live test suite and its config overlay |

`static/.well-known/webfinger/index.json` makes `jason@friedrich.uk` resolve to the
Mastodon account. Serving it needs a rewrite rule, because the request has no file
extension — see the deployment Caddyfile.
