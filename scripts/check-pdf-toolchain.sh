#!/usr/bin/env sh
set -eu

fail() {
  echo "PDF toolchain check failed: $*" >&2
  exit 1
}

for command in pandoc weasyprint fc-match pdfinfo dot; do
  command -v "$command" >/dev/null 2>&1 || fail "$command was not found"
done

python3 - <<'PY' || exit 1
import weasyprint
print(f"WeasyPrint: {weasyprint.__version__}")
PY

for font in "Noto Sans CJK JP" "Noto Sans Mono CJK JP"; do
  matched=$(fc-match -f '%{family}\n' "$font" | head -n 1)
  [ -n "$matched" ] || fail "$font was not found by fontconfig"
  echo "Font: $font -> $matched"
done

pandoc --version | sed -n '1,2p'
dot -V 2>&1
echo "PDF toolchain check passed (Pandoc + HTML/CSS + WeasyPrint; no LaTeX)."
