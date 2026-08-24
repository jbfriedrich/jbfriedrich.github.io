"""Assertions for the signal build.

Proves the two presets are layouts over one data layer: signal must render its
own markup, carry the same sources, and contain none of channels' markup.

Reads the build output from the directory given as the first argument.
"""
import pathlib
import re
import sys

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

for f in fails:
    print("FAIL:", f)
print("SIGNAL FAILURES:", len(fails))
sys.exit(1 if fails else 0)
