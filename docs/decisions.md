# Decisions

Why friedrich.uk is built the way the README describes, where the README does not already say.
Newest last. Most entries come from the hub's design spec of 2026-08-23, which lives outside this
repository.

Reasons the README already records, and which are not repeated here: the Hugo version range
([Hugo version](../README.md#hugo-version)), the online test suite ([Tests](../README.md#tests)),
absolute `@source` paths ([The @source path](../README.md#the-source-path)), and the hue palette
([Hue tokens](../README.md#hue-tokens)).

## Own design system, shared with nothing (2026-08)

The site uses its own Tailwind theme and shares no CSS or templates with the wilde theme or
tinycss that the blog uses. friedrich.uk is a different site with a different job (the
whole-person view across every source, not one blog), and sharing a design layer would turn every
change to either into a change to both. The cost is small duplication kept in step by hand: the
link-preview card image is a copy of the one the blog ships (`hugo.yaml`, `params.ogImage`).

## A failed source shows as missing, not stale (2026-08)

A source that cannot be fetched renders an "unavailable" tile until it recovers. The original
domain strategy asked for *stale beats missing*, which needs a pre-build fetcher writing each
feed to a persistent directory so a failed fetch leaves the previous copy in place. That was
dropped as complication the site does not need. Hugo's resource cache (`caches.getresource`)
covers the common case of back-to-back builds, and `partials/source.html` is the single place a
local-file fallback would go if a source ever proves unreliable.

## Feeds are taken at their word (2026-08)

The hub links to whatever URLs a feed contains and never rewrites hostnames. The design draft
proposed rewriting the blog's `jason.re` links to the domain the blog was served from at the
time, because the blog's `baseURL` and its serving domain disagreed. Rejected: a wrong URL in a
feed is a setting on the publishing site and is fixed there, not compensated for here. The
link-card test follows the same rule and
does not pin the permalink's hostname (`tests/assert.py`).

## Hues are chosen by measured distance, not brand colour (2026-08)

Every source hue has to differ from every other by at least CIELAB ΔE 25 in both themes.
Mastodon's brand periwinkle measured ΔE 14 against the posts blue in the first palette, so the
Mastodon tile does not use its brand colour: telling two adjacent tiles apart matters more than
brand recognition. Hue angle was rejected as the measure because it misleads on saturated
colours — a green and a teal 52° apart read as the same colour.

## Live feeds instead of recorded fixtures (2026-08)

The design spec planned a test suite against recorded copies of the six feeds. The suite fetches
the live feeds instead; the reasoning is in the README ([Tests](../README.md#tests)).

## Goodreads shelves come from the public widget (2026-11-18)

Goodreads switched off its RSS feeds in October 2026, so both book tiles lost their source.
The shelves are now read from Goodreads' public custom widget at build time, by Hugo, in the
same pipeline as every other source: `source.html` decodes it, a `goodreads-widget` branch in
`normalise.html` parses it. The widget, the profile page and the GraphQL API behind book pages
were found while building goodreads-nextread-random (see the jason.re post *Reading a Goodreads
shelf without the RSS feeds*, 2026-11-14).

Rejected:
- **Extending goodreads-nextread-random to serve a feed.** Its parser is sturdier and tested,
  but the public site would then depend on a self-hosted container, and that tool reads only
  one shelf.
- **A collector that writes the shelves to files before the build.** Same reasoning as
  [A failed source shows as missing, not stale](#a-failed-source-shows-as-missing-not-stale-2026-08).

Costs, accepted:
- **No dates.** The widget has none, so book items carry no date.
- **Pattern matching instead of a parser.** Goodreads can change the markup at any time. If it
  does, the tile shows "unavailable"; the build never fails.
- **Requests.** Two widget requests per hourly build, about 50 a day, plus a cover only when it
  isn't cached.
