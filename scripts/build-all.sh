#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
./scripts/build-site.sh
./scripts/build-pdf.sh
