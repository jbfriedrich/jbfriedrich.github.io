"""Assertions for a build shaped like the deploy tool's.

blogdeploy runs `hugo --gc --minify --source <clone>` from its own working
directory, which is not the project root. That is a different build from the
ones the other two suites check, and it is the one that ships.

It matters because Tailwind resolves a relative @source path against its own
process working directory, not against the stylesheet or the Hugo project. A
path that is correct when hugo runs from the project root matches nothing when
hugo is pointed at a project with --source from elsewhere. Nothing errors: the
stylesheet compiles to its theme block with no rules in it, the build exits 0,
and an unstyled page is published. That happened.

--minify is part of the shape too. Hugo's minifier drops optional attribute
quotes, so this file must not assume `attr="value"`.

Reads the build output from the directory given as the first argument.
"""
import pathlib
import re
import sys

BUILD = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "public_deploy")
html = (BUILD / "index.html").read_text(encoding="utf-8")

fails: list[str] = []


def check(ok, what):
    if not ok:
        fails.append(what)


m = re.search(r'href="?(/css/[^"\s>]+\.css)', html)
check(m is not None, "no stylesheet is linked")

if m:
    css = (BUILD / m.group(1).lstrip("/")).read_text(encoding="utf-8")

    # The load-bearing layout utilities. Without these the page has no measure,
    # no grid and no colour -- the exact shape of the failure this file exists
    # to catch.
    for util in (".mx-auto", ".max-w-7xl", ".grid-cols-6", ".bg-tile",
                 ".text-hue", ".bg-page", ".border-line"):
        check(util in css,
              f"{util} is missing from the deploy build's stylesheet: "
              "@source matched nothing from this working directory")

    # A theme-only sheet is roughly half the size of a complete one, so this
    # catches a scan that partially matched as well as one that missed entirely.
    check(len(css) > 12000,
          f"the deploy build's stylesheet is only {len(css)} bytes; "
          "a complete one is ~15K and a theme block with no rules is ~8.5K")

# The spans are safelisted with @source inline and so survive a broken scan.
# Checking them proves the file is looking at a real build, not an empty one.
check(len(re.findall(r'data-span=[\"]?\d', html)) >= 6,
      "the deploy build rendered no tiles")
check("target=" in html, "the deploy build rendered no outbound links")

for f in fails:
    print("FAIL:", f)
print("DEPLOY FAILURES:", len(fails))
sys.exit(1 if fails else 0)
