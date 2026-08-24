"""Assertions for the channels build.

The suite runs against the live feeds, so it cannot assert on specific posts:
anything named here would age out of the feed within days. It asserts structure
and invariants instead — the things that stay true whatever was published.

Reads the build output from the directory given as the first argument.
"""
import pathlib
import re
import sys

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


REAL = ["posts", "links", "notes", "asides", "mastodon", "books"]
BROKEN = ["gone", "down", "garbage"]

# every source reaches the page, working or not
for key in REAL + BROKEN:
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
    check('class="item"' not in tile(key), f"broken source {key!r} rendered items")

# counts are honoured
for key in REAL:
    n = tile(key).count('class="item"') + tile(key).count('class="book"')
    check(n <= 3, f"source {key!r} rendered {n} items, config says count: 3")
    check(n > 0, f"source {key!r} resolved but rendered no items")

# asides are cross-posted to Mastodon; without the filter the same item appears
# in two adjacent tiles
check("asides.blog" not in tile("mastodon"), "a cross-posted aside leaked into the mastodon tile")
# and the filter must run BEFORE the count cut, or a busy day empties the tile
check(tile("mastodon").count('class="item"') == 3,
      "mastodon rendered fewer than 3 items: excludes are being applied after the count cut")

# link posts surface both urls and must not swap them
links = tile("links")
check('class="item__note"' in links, "link cards are missing the permalink ('my note') link")
check('class="item__host"' in links, "link cards are missing the outbound host")

# The card must point its title at the OUTBOUND article and its note at the
# author's own page. Asserting only that the two differ is useless: swapping them
# still leaves two different values. `host` is derived from the outbound url, so
# requiring the displayed host to match the title's href catches a swap.
cards = re.findall(
    r'class="item__t" href="([^"]+)".*?class="item__host">([^<]+)<.*?class="item__note" href="([^"]+)"',
    links, re.S)
check(len(cards) > 0, "no link card matched the expected title/host/note structure")
for title_href, shown_host, note_href in cards:
    from urllib.parse import urlparse
    check(urlparse(title_href).netloc == shown_host,
          f"link card title points at {urlparse(title_href).netloc!r} "
          f"but displays host {shown_host!r} — url and permalink look swapped")
    check(title_href != note_href, "a link card points its title and its note at the same url")

# books carry what only books have
books = tile("books")
check('class="book__cover"' in books, "book cards are missing covers")
check("i.gr-assets.com" not in books, "book covers are hot-linked instead of self-hosted")
check('src="/images/covers/' in books, "book covers are not served from this site")
check('data-rating="' in books, "book cards are missing ratings")

# page furniture
check('rel="me"' in html, "rel=me is missing (mastodon verification)")
check("fediverse:creator" in html, "fediverse:creator meta is missing")
check("hello@friedrich.uk" in html, "the contact address is missing")
m = re.search(r"(\d+)/(\d+) sources", html)
check(m is not None, "the hero source count is missing")
if m:
    good, total = int(m.group(1)), int(m.group(2))
    check(good == len(REAL) and total == len(REAL) + len(BROKEN),
          f"hero claims {good}/{total} sources, expected {len(REAL)}/{len(REAL) + len(BROKEN)}")

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

for f in fails:
    print("FAIL:", f)
print("FAILURES:", len(fails))
sys.exit(1 if fails else 0)
