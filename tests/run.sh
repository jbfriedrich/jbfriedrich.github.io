#!/usr/bin/env bash
# Build both presets against the live feeds and assert the result.
#
# The suite is deliberately online. The site's whole job is reading other
# people's feeds, so testing it against frozen copies would prove the parser
# still handles a snapshot, not that the site works. A failure here means a feed
# really is unreachable or has changed shape, which is what you want to hear.
#
# tests/hugo.test.yaml adds three sources that are meant to fail, one per failure
# mode, so the "a broken source costs one tile, never the build" guarantee is
# covered too.
set -euo pipefail
cd "$(dirname "$0")/.."

CONFIG="hugo.yaml,tests/hugo.test.yaml"
export PATH="$PWD/bin:$PATH"

command -v tailwindcss >/dev/null 2>&1 || {
  echo "tailwindcss not found; run ./scripts/get-tailwind.sh" >&2
  exit 1
}

echo "== channels =="
rm -rf public_test
if ! hugo --config "$CONFIG" --destination public_test --quiet; then
  echo "hugo exited non-zero: a failing source must never fail the build" >&2
  exit 1
fi
python3 tests/assert.py public_test

echo "== signal =="
rm -rf public_signal
if ! HUGO_PARAMS_PRESET=signal hugo --config "$CONFIG" --destination public_signal --quiet; then
  echo "hugo exited non-zero building the signal preset" >&2
  exit 1
fi
python3 tests/assert_signal.py public_signal
