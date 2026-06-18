#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
./scripts/build-diagrams.sh
mkdocs build --strict
