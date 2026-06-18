#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
./scripts/check-pdf-toolchain.sh
./scripts/build-diagrams.sh
python3 pdf/build_pdf.py "$@"
