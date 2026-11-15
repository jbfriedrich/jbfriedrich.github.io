# Todo

Every open task for friedrich.uk, and only here. Most important first. When an item is done,
delete it and put what is now true into its home (README, `docs/decisions.md`, config comments).

## Open

- [ ] **Replace the two Goodreads sources** (added 2026-11-15) — Goodreads discontinued its RSS
  feeds (see the jason.re post "Reading a Goodreads shelf without the RSS feeds", 2026-11-14).
  `https://www.goodreads.com/review/list_rss/145074430?shelf=read` and `?shelf=currently-reading`
  return 404, so the `reading` and `books` tiles render as unavailable: the live page reported
  `5/7 sources` on 2026-11-15. `./tests/run.sh` fails on them too — 8 assertions in the channels
  build, 7 in the signal build. Swap the `feed` of both sources in `hugo.yaml` and
  `tests/hugo.test.yaml` for whatever replaces the feed; if the replacement is not an RSS feed
  of the same shape, that is a new `kind` in `partials/normalise.html`, or a change to
  `partials/source.html` (the one file that talks to the network). Done when `./tests/run.sh`
  passes all three stages.
- [ ] **Confirm the blog tiles link to jason.re** (added 2026-11-15) — the jason.re repo's
  `baseURL` is `https://jason.re` since 2026-11-14, but on 2026-11-15 the live jason.re feeds
  still emitted `https://undertow.blog/...` permalinks, and the live hub linked to them;
  undertow.blog no longer serves HTTPS. The fix is a rebuild of the blog (jason.re /
  blogdeploy), not a change here: this site takes feeds at their word (see
  [decisions](decisions.md#feeds-are-taken-at-their-word-2026-08)). Done when
  `curl -s https://jason.re/links/index.xml | grep -c undertow.blog` prints `0` and the next
  hub build has no `undertow.blog` link.

## Waiting

- [ ] **Decide on anti-scraping for the email address** — waits for the maintainer. The footer
  is a plain `mailto:` link (`partials/footer.html`). The previous site's hidden-decoy span broke
  click-to-mail and does not stop modern harvesters, so if obfuscation is wanted it should be
  done properly.
- [ ] **Decide how to tell sources apart beyond six hues** — waits for the maintainer; blocks the
  sources under Later. Every hue pair has to clear CIELAB ΔE 25 in both themes (README, "Hue
  tokens"). Up to four more sources (Last.fm, Steam, PSN, photos) make ten hues, which likely
  cannot all clear that floor, so later sources may need a second signal — an icon or a shape —
  rather than a new colour.

## Later

- [ ] **Add a photos source** — `https://jason.re/photos/index.xml` is a live Atom feed (200 on
  2026-11-15). A config block in `hugo.yaml` and `tests/hugo.test.yaml`, a hue, and new spans so
  every mosaic row still adds up to six.
- [ ] **Add a Last.fm source** — `user.getRecentTracks`, the official free JSON API. The API key
  comes from `os.Getenv`, which must be allowlisted under `security.funcs.getenv` or it returns
  an empty string silently. The key is resolved at build time and never reaches the browser.
- [ ] **Add a Steam source** — `IPlayerService/GetRecentlyPlayedGames`, official free key, read
  the same way as Last.fm's. Steam's brand blue collides with the posts hue, so it needs a
  different one.
- [ ] **Add a PSN source** — PSN has no official API; the reverse-engineered NPSSO login expires
  about every two months and needs a manual re-login, and heavy use risks action against the
  account. It needs a stateful collector, which is a separate design. The only contract with this
  site: the collector produces the normalised item record (README, "How a feed becomes a tile").
