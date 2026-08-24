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
| `home` | Where the tile heading links. Optional: omit it and the heading shows no link |
| `count` | Items to display |
| `empty` | What the tile says when the source resolves with no items, overriding `params.emptyText` |
| `overfetch` | Items to read before filtering, when `excludes` would otherwise eat the count |
| `excludes` | Drop items whose URL or summary contains any of these strings |
| `span` | Tile width in columns of the six-column mosaic |
| `hue` | Colour token for the tile |
| `full` | Render the tile body as a cover grid (books) |

Adding a source is a new entry plus a hue in `assets/css/main.css`.

### Spans

The mosaic is six columns wide and each source sets its own `span`. The spans of the
sources sharing a row have to add up to six, or the row ends in an empty half — so `span`
is a layout decision made next to the source rather than derived from item counts. The
current arrangement is `2 2 2 / 3 3 / 6`: three narrow tiles, then the two text-heavy
sources that need the width, then the shelf.

Tablet widths are derived, not configured: a source of three columns or more takes the
full width, narrow ones pair up, and an odd one left over takes the full width too
(`partials/tabletspans.html`). The breakpoints are Tailwind's `md` and `lg`; below `md`
everything is one column.

`tests/assert.py` packs the spans in document order and fails if any row stops short, in
both layouts.

### Empty tiles

A tile is never a blank box. With nothing to show it says which of two things is true,
because they are different facts: the source resolved and has nothing in it
(`params.emptyText`, or the source's own `empty`), or it could not be read at all
(`params.unavailableText`). A visitor can tell an empty shelf from a feed that is down.

Testing this needs a source that is reliably empty, which a live shelf is not — it stops
being empty the moment something lands on it. The suite uses a real feed with an
`excludes` rule that filters every item away.

`kind` names the **shape of the feed**, not what the source means. Two Goodreads
shelves — read and currently-reading — are the same XML and share `kind: goodreads`;
they differ in `key`, `label` and `feed`. A new `kind` is only warranted when a feed
parses differently, because each one is another branch in `normalise.html` to keep
working.

### Presets

`params.preset` selects the layout: `channels` (tiles) or `signal` (dense rows). Both
render the same normalised data through `partials/items.html`; neither contains any
fetching or filtering logic.

## CSS

The templates are styled with Tailwind utilities. `assets/css/main.css` holds no
component rules: it declares the theme and the six source hues, and that is all.

### The @source path

Tailwind resolves a relative `@source` path against **its own process working
directory** — not against this stylesheet, and not against the Hugo project. Hugo pipes
the stylesheet in on stdin, so there is no file for Tailwind to be relative to, and the
working directory is wherever `hugo` itself was started.

Those are the same directory when you run `hugo` from the project root, and different
when the deploy tool runs `hugo --gc --minify --source <clone>` from the service's own
working directory. A relative path then matches nothing, compiles no utilities, and
**still exits 0** — publishing a page with a stylesheet that is all theme and no rules.
That shipped once.

So `main.css` is run through `ExecuteAsTemplate` and builds absolute paths from
`hugo.WorkingDir`, which is the project root however hugo was invoked. One consequence:
a Go template delimiter written literally in a comment in that file will be executed.

`tests/run.sh` builds the deploy shape from `/` and asserts the published stylesheet has
rules in it, because a build from the project root cannot catch this.

Scanning the templates rather than Hugo's `hugo_stats.json` keeps the build a single
pass. Hugo writes that file at the *end* of a build, so a build that reads it compiles
the previous run's class list, and this site is rebuilt unattended by a webhook that runs
`hugo` once.

Tile widths are assembled from config (`lg:col-span-{{ $span }}`), so no literal class
name exists for the scanner to find. `@source inline(...)` names the range instead.

`tests/assert.py` asserts that the layout's load-bearing utilities are in the compiled
sheet, and `tests/assert_deploy.py` asserts the same of the deploy-shaped build, so a
broken scan fails the suite rather than shipping.

### Theme tokens

`@theme` declares what Tailwind's own scales do not cover, which is the fluid type and
space steps — Tailwind's are fixed, and this page holds a six-column mosaic and a single
column with the same tokens. Declaring them there rather than as loose variables is what
generates `text-meta`, `gap-snug`, `p-loose` and the rest.

The semantic colours (`bg-page`, `bg-tile`, `text-ink`, `text-dim`, `border-line`) point
at tokens the `:root` blocks flip with the theme. `text-hue` and `bg-tint` cannot: a
custom property is substituted in the scope where it is **declared**, not where it is
used, so a per-source hue has nothing to resolve against at the root of the document.
They take a placeholder in `@theme` and each tile redeclares them for itself.

### Hue tokens

Every colour is a Tailwind palette variable — `var(--color-blue-600)`, not a hex value.
Tailwind v4 emits a palette variable only where it is referenced, so naming the shades in
`main.css` is what puts them in the compiled sheet; the rest of the palette costs nothing.

The six were picked for perceptual distance rather than by eye: blue, pink, emerald,
amber, violet and rose, whose closest pair is ΔE 33 apart in light and ΔE 32 in dark,
clear of the ΔE 25 floor two tiles need to read as different sources at a glance. Light
mode takes emerald and amber one shade darker than the rest (700, not 600) because at 600
they fall to 3.7:1 and 3.2:1 against white, under the 4.5:1 the domain labels and tile
headings need.

Neutrals are `zinc`, not `slate`: slate carries enough chroma (.042 at 950 against zinc's
.006) to read as blue rather than charcoal across a whole page of it.

The tint behind a tile heading is the `100` shade laid over the tile through Tailwind's
opacity modifier — `bg-tint/(--tint-alpha)`. The scale has nothing between `50` and `100`,
and `50` is barely there against a white tile while `100` reads as a filled band; the
modifier is the framework's answer to that, and it keeps the value on the palette instead
of introducing a shade that is not. `--tint-alpha` is one knob per theme: dark wants the
`950` at full strength.

Any colour added later should clear both floors. `tests/assert.py` checks that the
compiled CSS still carries Tailwind's variables, so a hand-mixed hex creeping back in
fails the suite.

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

Test hooks are `data-` attributes, not classes, so a styling change cannot quietly break
a test and a test cannot pin a class the design wants to move.

Assertions are structural rather than content-based, since anything named would age out
of the feed within days: counts are honoured, cross-posted asides do not appear in the
Mastodon tile, link cards point their title at the write-up and their domain label at the
outbound article, no mosaic row is left short, book covers are self-hosted, entities are
decoded once.

The suite builds three times: both presets from the project root, and once in the shape
blogdeploy uses — `--gc --minify --source`, started from a different working directory.
Only the third proves the stylesheet that ships has any rules in it, and `--minify`
drops optional attribute quotes, so its assertions do not assume `attr="value"`.

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
