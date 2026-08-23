#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m http.server 8099 --directory tests/fixtures >/dev/null 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null || true' EXIT
for _ in $(seq 1 40); do
  curl -sf -o /dev/null http://127.0.0.1:8099/posts.xml && break || sleep 0.1
done
rm -rf public_test
if ! PATH="$PWD/bin:$PATH" hugo --environment test --destination public_test --quiet; then
  echo "FATAL: hugo build failed (test environment) — a failing source must never fail the build" >&2
  exit 1
fi
python3 tests/assert.py

rm -rf public_signal
# verified: HUGO_PARAMS_<KEY> overrides params without touching config files
PATH="$PWD/bin:$PATH" HUGO_PARAMS_PRESET=signal hugo --environment test \
  --destination public_signal --quiet
python3 tests/assert_signal.py
