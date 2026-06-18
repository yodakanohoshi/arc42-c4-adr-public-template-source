#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p docs/assets/images
for source in diagrams/*.dot; do
  name=$(basename "$source" .dot)
  dot -Tpng -Gdpi=150 "$source" -o "docs/assets/images/${name}.png"
  echo "Generated docs/assets/images/${name}.png"
done
