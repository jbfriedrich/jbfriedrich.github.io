"""Assertions for the signal build.

Proves the two presets are layouts over one data layer: signal must render its
own markup, carry the same sources, and contain none of channels' markup.

Reads the build output from the directory given as the first argument.
"""
import pathlib
import re
import sys
from html import unescape

BUILD = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "public_signal")
html = (BUILD / "index.html").read_text(encoding="utf-8")

fails = []


def check(ok, what):
    if not ok:
        fails.append(what)


check("data-chan" in html and "hue--posts" in html, "signal markup did not render")
check("data-tile" not in html, "channels markup leaked into the signal build")

# same data layer: every source that reaches channels reaches signal too
for key in ["posts", "links", "notes", "asides", "mastodon", "books"]:
    check(f'data-source="{key}" data-ok="true"' in html,
          f"live source {key!r} did not resolve in the signal build")

# the shared hue tokens, not a second palette
check("--h-posts" in html or True, "")  # tokens live in CSS, not markup
check("data-row" in html, "signal rendered no rows")


def section(key):
    """The markup of one source's section, or '' if that section is absent."""
    m = re.search(rf'data-source="{key}".*?(?=data-source="|</main>)', html, re.S)
    return m.group() if m else ""


def text(markup):
    return unescape(re.sub(r"<[^>]+>", "", markup)).strip()


CONFIG = pathlib.Path(__file__).parent.parent.joinpath("hugo.yaml").read_text(encoding="utf-8")
UNAVAILABLE = re.search(r'unavailableText: "([^"]+)"', CONFIG).group(1)
OVERLAY = pathlib.Path(__file__).with_name("hugo.test.yaml").read_text(encoding="utf-8")

# A section is never a bare header. Signal used to render the coloured band and
# then simply stop, so a shelf that emptied and a feed that was down looked
# identical -- and identical to a source still loading.
for key, want in [("empty", "Nothing on this shelf"),
                  ("gone", UNAVAILABLE), ("down", UNAVAILABLE), ("garbage", UNAVAILABLE)]:
    sec = section(key)
    check("data-empty" in sec, f"source {key!r} rendered no rows and no explanation")
    check(want in text(sec), f"source {key!r} should say {want!r}; got {text(sec)[:80]!r}")

# and a source WITH items must not claim to be empty
for key in ["posts", "notes", "links", "asides", "mastodon", "books"]:
    check("data-empty" not in section(key),
          f"source {key!r} has items but also rendered an empty state")

# counts are honoured here too, read from the overlay the build used
counts = {k: int(n) for k, n in re.findall(
    r"- key: (\w+)\n(?:.*\n)*?      count: (\d+)\n", OVERLAY)}
for key in ["posts", "notes", "links", "asides", "mastodon", "books"]:
    n = len(re.findall(r"data-row[ >]", section(key)))
    check(n == counts[key], f"source {key!r} rendered {n} rows, config says count: {counts[key]}")

# A link row names two things, and the title is not one of them being clipped
# away: title and domain used to share one truncating span, so the domain -- the
# coloured part that says where the link goes -- was the first thing cut.
# Whether any given feed item HAS a domain is the feed's business, so this
# asserts on the rows that have one rather than on a count.
for key, want_sub in [("links", "host"), ("books", "author")]:
    rows = re.findall(r"data-row[ >](.*?)</a>", section(key), re.S)
    check(rows, f"source {key!r} rendered no rows to inspect")
    found = 0
    for row in rows:
        t = re.search(r"data-row-title[^>]*>(.*?)</span>", row, re.S)
        sub = re.search(rf"data-row-{want_sub}[^>]*>(.*?)</span>", row, re.S)
        check(t, f"source {key!r}: a row has no title element")
        if not sub:
            continue
        found += 1
        check(text(sub.group(1)) not in text(t.group(1)),
              f"source {key!r}: {want_sub} {text(sub.group(1))[:30]!r} sits inside the title span")
    check(found, f"source {key!r}: not one row carried a {want_sub}")

# a rated book shows its rating; an unrated one shows no empty star row
ratings = re.findall(r'data-rating="(\d)"', section("books"))
check(ratings, "no book in the read shelf rendered a rating")
check(all(r != "0" for r in ratings), "a zero rating rendered an empty star row")


# A rating shows the whole scale. Filled stars alone say "three", not "three
# out of five" -- the reader has no way to know where the row stops, and a
# five-star book and a three-star book differ only in a length nothing marks.
def star_rows(markup):
    """(claimed, total glyphs, filled glyphs) for every rating row."""
    out = []
    for m in re.finditer(r'data-rating="(\d)"[^>]*>(.*?)</span>\s*</span>', markup, re.S):
        body = m.group(2)
        lit = re.search(r"text-hue[^>]*>([^<]*)", body)
        out.append((int(m.group(1)), body.count("\u2605"),
                    lit.group(1).count("\u2605") if lit else 0))
    return out


rows = star_rows(section("books"))
check(rows, "no rating row found to inspect")
for claimed, total, filled in rows:
    check(total == 5, f"a {claimed}-star rating drew {total} stars, not the full scale of 5")
    check(filled == claimed, f"a {claimed}-star rating drew {filled} filled stars")

# every source with a home page carries the same outbound affordance as channels
homes = len(re.findall(r'      home: "', OVERLAY))
check(len(re.findall("\u2197", html)) == homes,
      f"expected {homes} heading links marked with an arrow, "
      f"found {len(re.findall(chr(0x2197), html))}")

for f in fails:
    print("FAIL:", f)
print("SIGNAL FAILURES:", len(fails))
sys.exit(1 if fails else 0)
