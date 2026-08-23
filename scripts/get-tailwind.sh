#!/usr/bin/env bash
set -euo pipefail
VERSION="v4.3.3"
case "$(uname -s)-$(uname -m)" in
  Darwin-arm64)  ASSET="tailwindcss-macos-arm64" ;;
  Darwin-x86_64) ASSET="tailwindcss-macos-x64" ;;
  Linux-x86_64)  ASSET="tailwindcss-linux-x64" ;;
  Linux-aarch64) ASSET="tailwindcss-linux-arm64" ;;
  *) echo "unsupported platform: $(uname -s)-$(uname -m)" >&2; exit 1 ;;
esac
mkdir -p "$(dirname "$0")/../bin"
curl -sSL --fail -o "$(dirname "$0")/../bin/tailwindcss" \
  "https://github.com/tailwindlabs/tailwindcss/releases/download/${VERSION}/${ASSET}"
chmod +x "$(dirname "$0")/../bin/tailwindcss"
"$(dirname "$0")/../bin/tailwindcss" --help | head -1
