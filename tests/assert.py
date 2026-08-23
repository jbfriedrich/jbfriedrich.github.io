import re, sys, pathlib
html = pathlib.Path("public_test/index.html").read_text(encoding="utf-8")

# The theme-token assertions check the compiled, minified CSS actually shipped
# to visitors, not the authored source: testing the source would pass even if
# the build pipeline dropped the theme entirely. Tailwind's minifier does
# normalise whitespace/quoting (`prefers-color-scheme: dark` loses its space,
# `data-theme="dark"` loses its quotes), so the assertions below match the
# minified forms, not the brief's literal source-level strings.
_css_href = re.search(r'<link rel="stylesheet" href="([^"]+)">', html).group(1)
css_out = (pathlib.Path("public_test") / _css_href.lstrip("/")).read_text(encoding="utf-8")

fails = []

def want(needle, why, haystack=None):
    hay = html if haystack is None else haystack
    if needle not in hay:
        fails.append(f"MISSING {why}: {needle!r}")

def reject(needle, why, haystack=None):
    hay = html if haystack is None else haystack
    if needle in hay:
        fails.append(f"UNEXPECTED {why}: {needle!r}")

def tile_body(source_key):
    """Full markup of one <section class="tile" data-source="key">...</section>.
    Sections never nest, so matching up to </section> (rather than the first
    </div>, which would only reach the end of the FIRST item/book element) is
    what actually isolates one tile's contents."""
    m = re.search(r'data-source="%s"[^>]*>(.*?)</section>' % re.escape(source_key), html, re.S)
    return m.group(1) if m else ""

# --- the live channels layout ---
want('class="tile tile--posts"', "posts tile")
want('class="tile tile--books tile--full"', "books tile full width")
want("undertow.blog/notes/", "every tile shows its source path")
want("hello@friedrich.uk", "email in footer")
want("© 2026", "copyright in footer")

want("data-source=\"posts\" data-ok=\"true\"",   "posts fetched")
want("data-source=\"gone\" data-ok=\"false\"",    "404 handled")
want("data-source=\"down\" data-ok=\"false\"",    "refused handled")
want("data-source=\"garbage\" data-ok=\"false\"", "malformed handled")

want("Clicks Power Keyboard", "notes title rendered")
want("https://jason.re/notes/20260817163702/", "notes url rendered")
want("17 Aug 2026", "notes date parsed and formatted")
want("hardware", "notes tag rendered")
want("Absolutes and Vigilance", "posts title rendered")

# Position-sensitive: bind each URL to the exact anchor it must render in, not
# merely to its presence anywhere on the page. "standard-reader.app" is a
# substring of BOTH the outbound url and the jason.re permalink (it's a path
# segment of the latter), so a bare substring check can't tell a swapped
# rel="alternate"/rel="related" mapping from a correct one. The two anchors
# also carry different classes (item__t vs item__note), so a swap would land
# each href on the wrong element as well as the wrong text.
want(
    '<a class="item__t" href="https://standard-reader.app/a/did:plc:5w4eqcxzw5jv5qfnmzxcakfy/3msz2el2hxk2x">'
    'Emilia: The Internet was never real</a>',
    "link outbound target is the href of the title anchor",
)
want(
    '<a class="item__note" href="https://jason.re/links/standard-reader.app/20260817163706/">my note</a>',
    "link permalink is the href of the secondary \"my note\" anchor",
)
want('class="item__host">standard-reader.app<', "link host rendered in its own element")

want("Day 5/5", "asides item rendered")
want("https://asides.blog/22073a08a58555c8/", "asides url")
want("I really can", "mastodon summary used as title fallback")

masto_body = tile_body("mastodon")
reject("asides.blog/22073a08a58555c8/", "mastodon cross-post leaked", haystack=masto_body)
if masto_body.count('<div class="item"') != 3:
    fails.append("mastodon should render exactly 3 items after filtering")

# Final whole-branch review must-fix 1: plainify returns template.HTML,
# which renders raw; substr strips that type, so an already-escaped
# "&amp;#39;" was escaped a second time to "&amp;amp;#39;". No doubled
# entity of any kind should reach the page.
want("I really can&#39;t decide", "apostrophe single-escaped, not doubled")
reject("&amp;amp;", "no entity is ever double-escaped anywhere on the page")
reject("&amp;#39;", "the literal &#39; text is never shown to a reader")
reject("&amp;quot;", "no doubled quote entity anywhere on the page")

# Final whole-branch review must-fix 2: truncation must cut on a word
# boundary and mark that it cut, not stop mid-word with no indicator.
want("I always liked Brent…", "mastodon title fallback truncates on a word boundary, not mid-word")
reject("I always liked Br<", "truncation must not land mid-word")
reject("not sure what I t<", "truncation must not land mid-word")

want("Making It So", "book title")
want("Patrick Stewart", "author whitespace collapsed")
reject("Patrick   Stewart", "author still has doubled spaces")
reject("utm_medium=api", "utm tracking not stripped")
want('data-rating="4"', "rating parsed")

# Task 6 asserted the raw i.gr-assets.com URL reached the template; Task 10
# self-hosts covers instead, so that assertion is rewritten rather than
# dropped: the property worth keeping is that a cover URL is actually
# extracted from the feed and rendered, now via the local republished path.
reject('src="https://i.gr-assets.com', "cover still hot-linked")
want('src="/images/covers/', "cover self-hosted")

# Hostile Goodreads items: a failing item must never fail the build, and
# must not be shown with a fabricated date. Good items in the same feed
# must still render.
want("data-source=\"hostile\" data-ok=\"true\"", "hostile source fetched fine (item-level, not fetch-level, hostility)")
want("Hostile Good Control Book", "control item with a valid date/rating survives")
want("Hostile Bad Rating Book", "item with non-numeric rating survives, defaulted rather than crashing the build")
reject("Hostile No Date Book", "item with no date anywhere is skipped, not shown with a fabricated date")
reject("Hostile Bad Date Book", "item with an unparsable date is skipped, not shown with a fabricated date")

# A 200 response whose body is not an image (Goodreads serving a rate-limit /
# maintenance / error page at 200) must not crash .Resize, which is only
# valid on image resources. This item's cover URL points at malformed.xml
# served by the fixture HTTP server, a real 200 non-image response.
want("Hostile Nonimage Cover Book", "item with a non-image 200 cover response survives, rendered without an image")

hostile_body = tile_body("hostile")
if hostile_body.count('<a class="book"') != 3:
    fails.append("hostile source should render exactly the 3 datable items, skipping the 2 undatable ones")

_title_idx = hostile_body.find("Hostile Nonimage Cover Book")
_anchor_start = hostile_body.rfind('<a class="book"', 0, _title_idx)
_anchor_end = hostile_body.find("</a>", _title_idx)
nonimage_book = hostile_body[_anchor_start:_anchor_end] if _anchor_start != -1 and _anchor_end != -1 else ""
if "<img" in nonimage_book:
    fails.append("Hostile Nonimage Cover Book should render without a <img> cover, since its cover response is not an image")
if "Nonimage Author" not in nonimage_book or 'data-rating="5"' not in nonimage_book:
    fails.append("Hostile Nonimage Cover Book should still render its author and rating despite the bad cover")

# Final whole-branch review C1: Hugo's XML unmarshal returns a map for a
# single repeating element and a slice for several. A source with exactly
# one <entry>/<item> must still build and render (a new section, a purged
# Mastodon account, a one-book shelf).
want("data-source=\"one_atom\" data-ok=\"true\"", "single-entry atom source survives (C1)")
want("Lonely Only Entry", "single-entry atom item rendered (C1)")
want("data-source=\"one_rss\" data-ok=\"true\"", "single-item rss source survives (C1)")
want("Lonely Only Item", "single-item rss item rendered (C1)")
want("data-source=\"one_goodreads\" data-ok=\"true\"", "one-book shelf survives (C1)")
want("The Lonely Only Book", "one-book shelf item rendered (C1)")

# Final whole-branch review C2: an element carrying an attribute (or
# lacking one a generator normally sends) unmarshals to a map/string where
# the code assumed the other shape.
want("data-source=\"atomquirks\" data-ok=\"true\"", "atom quirks source survives (C2)")
want("Quirky Title With Type Attribute", "atom <title type=> (WordPress/Blogger) rendered as plain text (C2)")
want("Bare Content With No Type Attribute", "atom <content> with no type= rendered (C2)")
want("data-source=\"rssquirks\" data-ok=\"true\"", "rss quirks source survives (C2)")
want("Domain Category Item", "rss item with <category domain=> rendered (C2)")
want('<span>tech</span>', "rss <category domain=> tag text extracted, not the whole map (C2)")
want("Typed Title And Link Item", "rss <title type=> and attribute-bearing <link> rendered (C2)")
want("data-source=\"goodreadsquirks\" data-ok=\"true\"", "goodreads quirks source survives (C2)")
want("Quirky Title Book", "goodreads <title> with an attribute rendered (C2)")
want("Quirky Read-At And Author Book", "goodreads item rendered despite attribute-bearing <title>", )
want('<span class="book__a">Quirk Author Two</span>', "goodreads <author_name> with an attribute extracted (C2)")

# Final review gap fix: an Atom <link> or <category> with no attributes at
# all unmarshals to a bare string, not a map — the -rel/-href/-term index
# reads must degrade rather than panic the build.
want("data-source=\"bareattrs\" data-ok=\"true\"", "bare-attrs source survives (gap fix)")
want(
    '<a class="item__t" href="https://example.org/bareattrs/bare-link/">Bare Link No Href</a>',
    "attribute-less <link> falls back to its text content as href (gap fix)",
)
want("Bare Category No Term", "item with an attribute-less <category> still rendered (gap fix)")
want("<span>plain</span>", "attribute-less <category> falls back to its text content as the tag (gap fix)")

want('<link rel="me" href="https://click.ba.it/@jason">', "rel=me in head")
want('name="fediverse:creator"', "fediverse creator meta")
want("prefers-color-scheme:dark", "dark media query present in compiled CSS", css_out)
want("[data-theme=dark]", "explicit dark selector present in compiled CSS", css_out)

# The failure mode that matters: a colour token whose only definition sits
# inside a media query or [data-theme] block renders one theme's text on the
# other theme's background in the un-stamped "system" state. So confirm a
# colour token is actually defined on bare :root in the shipped CSS, not just
# somewhere in the file.
m = re.search(r':root\{([^}]*)\}', css_out)
if not m or "--h-posts:" not in m.group(1):
    fails.append("colour token --h-posts is not defined on bare :root in compiled CSS")

for f in fails:
    print(f)
print("FAILURES:", len(fails))
sys.exit(1 if fails else 0)
