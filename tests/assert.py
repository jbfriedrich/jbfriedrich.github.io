"""Assertions for the channels build.

The suite runs against the live feeds, so it cannot assert on specific posts:
anything named here would age out of the feed within days. It asserts structure
and invariants instead — the things that stay true whatever was published.

Reads the build output from the directory given as the first argument.
"""
import pathlib
import re
import sys
import urllib.request
from html import unescape
from urllib.parse import urlparse

BUILD = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "public_test")
html = (BUILD / "index.html").read_text(encoding="utf-8")

fails: list[str] = []


def check(ok, what):
    if not ok:
        fails.append(what)


def tile(key):
    """The markup of one source's tile, or '' if that tile is absent."""
    m = re.search(rf'data-source="{key}".*?(?=data-source="|</main>)', html, re.S)
    return m.group() if m else ""


def ok_flag(key):
    m = re.search(rf'data-source="{key}" data-ok="(\w+)"', html)
    return m.group(1) if m else None


REAL = ["posts", "links", "notes", "asides", "mastodon", "reading", "books"]

# A "currently reading" shelf is empty between books. That is a working source
# with nothing to show, not a broken one, so it is held to resolving and to
# honouring its count -- but not to having items.
MAY_BE_EMPTY = {"reading"}
BROKEN = ["gone", "down", "garbage"]
# Resolves, parses, and has no items to show. A different state from BROKEN, and
# the tile has to say so differently.
EMPTY = ["empty"]

# every source reaches the page, working or not
for key in REAL + BROKEN + EMPTY:
    check(ok_flag(key) is not None, f"source {key!r} is missing from the page entirely")

# the live feeds resolve. A failure here is a real outage or a broken feed, not a
# flaky test: these are the same fetches the deployed site makes every hour.
for key in REAL:
    check(ok_flag(key) == "true", f"live source {key!r} did not resolve (data-ok=false)")

# a broken source costs one tile, never the build. run.sh checks the exit code;
# this checks the tile still renders, empty.
for key in BROKEN:
    check(ok_flag(key) == "false", f"deliberately broken source {key!r} reported ok")
    check(tile(key) != "", f"broken source {key!r} did not render a tile")
    check("data-item" not in tile(key), f"broken source {key!r} rendered items")

# counts are honoured. The expected numbers come from the overlay the build
# actually used -- hard-coding a 3 here silently passes when someone raises a
# count in config and the template ignores it.
CONFIG = pathlib.Path(__file__).with_name("hugo.test.yaml").read_text(encoding="utf-8")
counts = {k: int(n) for k, n in re.findall(
    r"- key: (\w+)\n(?:.*\n)*?      count: (\d+)\n", CONFIG)}
check(set(counts) >= set(REAL), f"could not read counts for {sorted(set(REAL) - set(counts))}")

for key in REAL:
    # data-item-title / data-book-cover must not be counted as cards, hence
    # the delimiter: an attribute name ends at a space or the closing bracket.
    n = (len(re.findall(r"data-item[ >]", tile(key)))
         + len(re.findall(r"data-book[ >]", tile(key))))
    check(n <= counts.get(key, 0),
          f"source {key!r} rendered {n} items, config says count: {counts.get(key)}")
    if key not in MAY_BE_EMPTY:
        check(n > 0, f"source {key!r} resolved but rendered no items")

# asides are cross-posted to Mastodon; without the filter the same item appears
# in two adjacent tiles.
#
# Asserting that "asides.blog" is absent from the tile's markup does NOT test
# this. The tile renders a truncated body, so a cross-post whose link sits past
# the cut renders no "asides.blog" anywhere and the leak goes unnoticed -- which
# is exactly the bug that shipped. The item has to be traced back to the feed
# entry it came from and THAT judged, whole.
MASTO_FEED = re.search(r"- key: mastodon\n(?:.*\n)*?      feed: \"([^\"]+)\"", CONFIG).group(1)
MASTO_EXCLUDES = re.findall(
    r"[\"']([^\"']+)[\"']",
    re.search(r"- key: mastodon\n(?:.*\n)*?      excludes: \[([^\]]*)\]", CONFIG).group(1))

req = urllib.request.Request(MASTO_FEED, headers={"Accept-Encoding": "identity"})
feed = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")

# the same shape normalise.html produces: tags stripped, entities resolved and
# NOT truncated. Hugo's plainify inserts a newline at block boundaries where a
# regex strip does not, so both sides are compared with whitespace removed.
def flat(s):
    return re.sub(r"\s+", "", unescape(re.sub(r"<[^>]+>", "", unescape(s))))


bodies = [flat(m.group(1)) for it in re.findall(r"<item>(.*?)</item>", feed, re.S)
          if (m := re.search(r"<description>(.*?)</description>", it, re.S))]

rendered = [flat(t).rstrip("\u2026")
            for t in re.findall(r"data-item-title[^>]*>(.*?)</a>", tile("mastodon"), re.S)]
check(rendered, "no mastodon items rendered, so the excludes filter is untested")

for shown in rendered:
    origin = [b for b in bodies if b.startswith(shown)]
    check(origin, f"rendered mastodon item {shown[:40]!r} matches no entry in the feed")
    for b in origin:
        for pat in MASTO_EXCLUDES:
            check(flat(pat) not in b,
                  f"a cross-posted aside leaked into the mastodon tile: "
                  f"{shown[:40]!r} came from a feed entry containing {pat!r}, "
                  f"past the point the summary is truncated")

# link posts surface both urls and must not swap them
links = tile("links")
check("data-item-host" in links, "link cards are missing the outbound host")
check("my note" not in links,
      "the 'my note' link is back: the title carries the permalink now")

# A link card has two destinations and they are not interchangeable: the title
# goes to the write-up on the author's own site, the domain goes to the article
# being written about. Asserting only that the two differ is useless -- swapping
# them still leaves two different values. The displayed host is derived from the
# outbound url, so tying it to the href it labels is what catches a swap: swap
# the two and the domain label no longer matches the domain it links to.
#
# The title is only required to lead somewhere else. It cannot be pinned to the
# blog's own hostname, because the permalink comes from undertow.blog's Atom
# feed and that feed still carries an older baseURL -- which is a setting on
# that site, not something this one should second-guess or rewrite.
# Attributes after href are tolerated on purpose: target= and rel= sit on both
# of these anchors, and their order is not something a test should pin.
cards = re.findall(
    r'data-item-title[^>]*href="([^"]+)"[^>]*>'
    r'.*?data-item-host[^>]*href="([^"]+)"[^>]*>([^<]+)<',
    links, re.S)
check(len(cards) > 0, "no link card matched the expected title/host structure")
for title_href, host_href, shown_host in cards:
    check(urlparse(host_href).netloc == shown_host,
          f"link card shows host {shown_host!r} but its domain link goes to "
          f"{urlparse(host_href).netloc!r} — url and permalink look swapped")
    check(urlparse(title_href).netloc != shown_host,
          f"link card title goes to {shown_host!r}, the outbound article: "
          "the title is supposed to open the write-up")
    check(title_href != host_href, "a link card points its title and its domain at the same url")

# books carry what only books have
books = tile("books")
check("data-book-cover" in books, "book cards are missing covers")
check("i.gr-assets.com" not in books, "book covers are hot-linked instead of self-hosted")
check('src="/images/covers/' in books, "book covers are not served from this site")
check('data-rating="' in books, "book cards are missing ratings")

# A tile with nothing in it says which of the two reasons applies. Conflating
# them tells a visitor the shelf is empty when the feed is actually down.
for key in BROKEN:
    check("data-empty" in tile(key), f"broken source {key!r} rendered a blank tile")
    check("unavailable" in tile(key),
          f"broken source {key!r} claims to be empty rather than unreachable")

for key in EMPTY:
    check(ok_flag(key) == "true", f"source {key!r} should resolve; it is empty, not broken")
    check("data-item" not in tile(key), f"source {key!r} was supposed to filter every item away")
    check("Nothing on this shelf" in tile(key),
          f"source {key!r} did not fall back to its configured empty text")
    check("unavailable" not in tile(key),
          f"empty source {key!r} is being reported as unreachable")

# The mosaic is six columns wide and every tile declares its own span, so a
# config edit can leave a row short -- which is the hole this layout exists to
# avoid. Pack the spans in document order and require every row to close.
def rows_close(spans, width=6):
    acc = 0
    for i, n in enumerate(spans):
        if acc + n > width:
            return f"tile {i} (span {n}) does not fit the {width - acc} columns left in its row"
        acc += n
        if acc == width:
            acc = 0
    return "" if acc == 0 else f"the last row stops {width - acc} columns short"

desktop = [int(n) for n in re.findall(r'data-span="(\d+)"', html)]
tablet = [int(n) for n in re.findall(r'data-span-md="(\d+)"', html)]
check(len(desktop) == len(REAL) + len(BROKEN) + len(EMPTY), "not every tile declares a span")
check(len(tablet) == len(desktop), "not every tile declares a tablet span")
check(rows_close(desktop) == "", f"the desktop mosaic leaves a hole: {rows_close(desktop)}")
check(rows_close(tablet) == "", f"the tablet mosaic leaves a hole: {rows_close(tablet)}")

# Every link on this page leaves the site, and all of them open in a new tab.
# rel=noopener goes with it: modern browsers imply it for target=_blank, older
# ones hand the opened page a live window.opener reference back to this one.
outbound = re.findall(r'<a\s[^>]*href="https?://[^>]*>', html)
check(len(outbound) > 10, f"only {len(outbound)} outbound links found; the page should be full of them")
for a in outbound:
    check('target="_blank"' in a, f"outbound link does not open in a new tab: {a[:110]}")
    check("noopener" in a, f"outbound link is missing rel=noopener: {a[:110]}")

# `home` is optional: a Goodreads shelf that is only ever read here has nothing
# useful to point at, and an empty one used to render href="" -- an anchor that
# reloads the page. The heading link exists exactly when home does.
homes = {}
for block in re.split(r"\n    - key: ", CONFIG)[1:]:
    hm = re.search(r'^      home: "([^"]+)"', block, re.M)
    homes[block.split("\n")[0].strip()] = hm.group(1) if hm else None

for key in REAL:
    t, home = tile(key), homes.get(key)
    # The heading link is the one carrying the outward arrow.
    heading = re.search(r'href="([^"]+)"[^>]*>[^<]*\u2197', t)
    if home is None:
        check(heading is None,
              f"source {key!r} has no home in config but its tile still links out of the heading")
        check('href=""' not in t, f"tile {key!r} rendered an empty href")
    else:
        check(heading is not None, f"source {key!r} has home {home!r} but no heading link")
        # It used to be repeated by an "All <label>" link in the tile footer
        # pointing at the identical href: the same destination twice in one card.
        n = t.count(f'href="{home}"')
        check(n == 1, f"tile {key!r} links to {home} {n} times, not once")

# page furniture
check('rel="me"' in html, "rel=me is missing (mastodon verification)")
check("fediverse:creator" in html, "fediverse:creator meta is missing")
check("hello@friedrich.uk" in html, "the contact address is missing")

# Link previews. Every one of these is invisible on the page itself, so nothing
# but a test notices when one goes missing.
for tag in ('property="og:title"', 'property="og:description"', 'property="og:url"',
            'property="og:image"', 'property="og:type"', 'property="og:site_name"',
            'name="twitter:card"', 'name="twitter:image"', 'rel="canonical"'):
    check(tag in html, f"{tag} is missing: link previews will fall back to guesswork")

og = re.search(r'property="og:image" content="([^"]+)"', html)
check(og is not None and og.group(1).startswith("https://"),
      "og:image is not an absolute URL; a scraper has no page to resolve it against")
if og:
    local = BUILD / og.group(1).split("/", 3)[-1]
    check(local.exists(), f"og:image points at {og.group(1)} which this build does not contain")

# The card type has to match the image: summary_large_image tells a consumer
# the image is a 1.91:1 banner and it crops to fit if it is not.
card = re.search(r'name="twitter:card" content="([^"]+)"', html)
check(card is not None and card.group(1) == "summary_large_image",
      "twitter:card should be 'summary_large_image' for a 1200x630 banner")
m = re.search(r"\d\d:\d\d \((\d+)/(\d+) sources\)", html)
check(m is not None, "the footer's updated/source line is missing")
# The visible label is an icon, so the only thing announcing what the number
# means is the screen-reader text. Losing it leaves a bare time and no context.
check('class="sr-only">Updated<' in html,
      "the updated line has an icon but no accessible label")
if m:
    good, total = int(m.group(1)), int(m.group(2))
    # An empty source resolved: the count is about reachability, not content.
    want_good, want_total = len(REAL) + len(EMPTY), len(REAL) + len(BROKEN) + len(EMPTY)
    check(good == want_good and total == want_total,
          f"the footer claims {good}/{total} sources, expected {want_good}/{want_total}")

# entities are decoded once, not twice
check("&amp;#" not in html, "double-escaped HTML entities in the output")

# the stylesheet is real
m = re.search(r'href="(/css/[^"]+\.css)"', html)
check(m is not None, "no stylesheet is linked")
if m:
    css = (BUILD / m.group(1).lstrip("/")).read_text(encoding="utf-8")
    check("prefers-color-scheme:dark" in css or "prefers-color-scheme: dark" in css,
          "compiled CSS has no dark-theme media query")
    check("[data-theme=dark]" in css or '[data-theme="dark"]' in css,
          "compiled CSS has no explicit dark-theme selector")
    check("--h-posts:" in css, "compiled CSS is missing the source hue tokens")
    # Tailwind only compiles a utility it has seen in a scanned file, and the
    # @source path is resolved by the Tailwind binary rather than by Hugo -- a
    # wrong one scans nothing and fails silently, leaving an unstyled page that
    # still builds cleanly. These are the layout's load-bearing utilities.
    for util in (".mx-auto", ".max-w-7xl", ".grid-cols-6", ".bg-tile"):
        check(util in css, f"{util} was not compiled: the @source scan is finding nothing")
    # The hues are Tailwind theme variables. Tailwind emits a theme variable
    # only where it is referenced, so their presence is what proves the palette
    # is the framework's and not six hand-mixed hex values.
    for token in ("--color-blue-600", "--color-zinc-900", "--color-emerald-700"):
        check(f"{token}:" in css, f"{token} is not in the compiled CSS: "
              "the palette is no longer coming from Tailwind")

for f in fails:
    print("FAIL:", f)
print("FAILURES:", len(fails))
sys.exit(1 if fails else 0)
