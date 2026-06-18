#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
./scripts/build-all.sh
PDF=$(python3 - <<'PY'
import yaml
from pathlib import Path
cfg = yaml.safe_load(Path('pdf/config.yml').read_text(encoding='utf-8'))
print(cfg.get('output', 'build/architecture-document.pdf'))
PY
)
HTML=$(python3 - <<'PY'
import yaml
from pathlib import Path
cfg = yaml.safe_load(Path('pdf/config.yml').read_text(encoding='utf-8'))
print(cfg.get('output_html', 'build/architecture-document.html'))
PY
)
test -s "$PDF"
test -s "$HTML"
test -s site/index.html
for image in docs/assets/images/*.png; do test -s "$image"; done
pdfinfo "$PDF" | sed -n '1,20p'
echo "Verification passed: $PDF, $HTML, site/index.html and generated diagrams"
