#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p docs/assets/images
for source in diagrams/*.dot; do
  [ -e "$source" ] || continue
  name=$(basename "$source" .dot)
  dot -Tpng -Gdpi=150 "$source" -o "docs/assets/images/${name}.png"
  echo "Generated docs/assets/images/${name}.png"
done

# PlantUML sources (diagrams/*.puml), including C4. Skipped when PlantUML is not
# installed so the DOT-only flow keeps working outside the Docker toolchain.
for source in diagrams/*.puml; do
  [ -e "$source" ] || continue
  if command -v plantuml >/dev/null 2>&1; then
    name=$(basename "$source" .puml)
    plantuml -tpng -charset UTF-8 -o "$(cd docs/assets/images && pwd)" "$source"
    echo "Generated docs/assets/images/${name}.png"
  else
    echo "plantuml not found: skipping $source" >&2
  fi
done
