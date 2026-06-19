#!/usr/bin/env python3
"""Build one PDF from Markdown pages in mkdocs.yml without LaTeX.

Pipeline:
  Markdown -> Pandoc standalone HTML -> WeasyPrint PDF

The MkDocs navigation is the source of truth for page ordering. The script
converts MkDocs admonitions, rewrites local links/images, concatenates pages,
and generates a print-focused HTML file and PDF.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, NoReturn

import yaml

PROJECT = Path(__file__).resolve().parents[1]
DOCS = PROJECT / "docs"
MKDOCS = PROJECT / "mkdocs.yml"
CONFIG = PROJECT / "pdf" / "config.yml"
BASE_CSS = PROJECT / "pdf" / "print.css"
HTML_TEMPLATE = PROJECT / "pdf" / "template.html"
MERMAID_DIR = PROJECT / "build" / "mermaid"
PLANTUML_DIR = PROJECT / "build" / "plantuml"
PUPPETEER_CONFIG = PROJECT / "pdf" / "puppeteer.json"


class _Loader(yaml.SafeLoader):
    """SafeLoader that ignores MkDocs plugin tags such as !!python/name:."""


def _ignore_python_tag(loader: yaml.Loader, tag_suffix: str, node: yaml.Node) -> None:
    return None


# MkDocs configs can carry "!!python/name:..." tags (e.g. the mermaid2 superfences
# fence). They are irrelevant to the PDF build, so drop them instead of executing
# or rejecting them, keeping the loader safe.
_Loader.add_multi_constructor("tag:yaml.org,2002:python/name:", _ignore_python_tag)
_Loader.add_multi_constructor("tag:yaml.org,2002:python/module:", _ignore_python_tag)


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(2)


def read_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=_Loader)
    except (OSError, yaml.YAMLError) as exc:
        fail(f"cannot read {path}: {exc}")
    if not isinstance(data, dict):
        fail(f"{path} must contain a YAML mapping")
    return data


def flatten_nav(
    items: Any, parents: tuple[str, ...] = ()
) -> Iterable[tuple[tuple[str, ...], str, str]]:
    """Yield (section path, page title, Markdown path) in MkDocs nav order."""
    if not isinstance(items, list):
        fail("mkdocs.yml nav must be a list")
    for item in items:
        if isinstance(item, str):
            yield parents, Path(item).stem, item
            continue
        if not isinstance(item, dict) or len(item) != 1:
            fail(f"unsupported nav item: {item!r}")
        title, value = next(iter(item.items()))
        if isinstance(value, str):
            yield parents, str(title), value
        elif isinstance(value, list):
            yield from flatten_nav(value, parents + (str(title),))
        else:
            fail(f"unsupported nav value for {title!r}: {value!r}")


def slug_for_file(relative_path: str) -> str:
    slug = Path(relative_path).with_suffix("").as_posix().lower()
    slug = re.sub(r"[^a-z0-9/_-]+", "-", slug)
    return "doc-" + slug.replace("/", "-").strip("-")


def demote_headings(text: str, levels: int = 1) -> str:
    output: list[str] = []
    in_fence = False
    fence = ""
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if not in_fence:
                in_fence, fence = True, marker
            elif marker == fence:
                in_fence = False
            output.append(line)
            continue
        if not in_fence:
            match = re.match(r"^(#{1,6})(\s+.*)$", line)
            if match:
                hashes, rest = match.groups()
                line = "#" * min(6, len(hashes) + levels) + rest
        output.append(line)
    return "\n".join(output) + "\n"


def convert_admonitions(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    labels = {
        "note": "NOTE",
        "warning": "WARNING",
        "tip": "TIP",
        "info": "INFO",
        "danger": "DANGER",
        "important": "IMPORTANT",
    }
    i = 0
    while i < len(lines):
        match = re.match(r'^!!!\s+([\w-]+)(?:\s+"([^"]+)")?\s*$', lines[i])
        if not match:
            out.append(lines[i])
            i += 1
            continue
        kind, title = match.groups()
        label = labels.get(kind, kind.upper())
        out.extend([f"> **{label}{': ' + title if title else ''}**", ">"])
        i += 1
        while i < len(lines):
            line = lines[i]
            if line.startswith("    "):
                out.append("> " + line[4:])
                i += 1
            elif line.startswith("\t"):
                out.append("> " + line[1:])
                i += 1
            elif not line.strip() and i + 1 < len(lines) and (
                lines[i + 1].startswith("    ") or lines[i + 1].startswith("\t")
            ):
                out.append(">")
                i += 1
            else:
                break
    return "\n".join(out) + "\n"


def add_document_anchor(text: str, anchor: str) -> str:
    lines = text.splitlines()
    in_fence = False
    fence = ""
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if not in_fence:
                in_fence, fence = True, marker
            elif marker == fence:
                in_fence = False
            continue
        if not in_fence and re.match(r"^#{1,6}\s+", line):
            lines[index] = f"{line} {{#{anchor}}}"
            break
    return "\n".join(lines) + "\n"


def rewrite_images(text: str, source_file: Path) -> str:
    source_dir = source_file.parent

    def replace(match: re.Match[str]) -> str:
        alt, target = match.group(1), match.group(2)
        if re.match(r"^[a-z]+://", target) or target.startswith("#"):
            return match.group(0)
        absolute = (source_dir / target).resolve()
        try:
            relative = absolute.relative_to(PROJECT.resolve()).as_posix()
        except ValueError:
            return match.group(0)
        return f"![{alt}]({relative})"

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace, text)


def rewrite_doc_links(text: str, source_file: Path, anchors: dict[Path, str]) -> str:
    source_dir = source_file.parent

    def replace(match: re.Match[str]) -> str:
        label, target = match.group(1), match.group(2)
        if target.startswith(("http://", "https://", "mailto:", "#")):
            return match.group(0)
        path_part, _, _fragment = target.partition("#")
        if not path_part.endswith(".md"):
            return match.group(0)
        absolute = (source_dir / path_part).resolve()
        anchor = anchors.get(absolute)
        return f"[{label}](#{anchor})" if anchor else label

    return re.sub(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)", replace, text)


def make_combined(
    entries: list[tuple[tuple[str, ...], str, str]], config: dict[str, Any]
) -> Path:
    excluded = {str(value) for value in config.get("exclude", [])}
    entries = [entry for entry in entries if entry[2] not in excluded]
    anchors = {(DOCS / path).resolve(): slug_for_file(path) for _, _, path in entries}

    output = PROJECT / str(config.get("combined_markdown", "build/arc42-combined.md"))
    output.parent.mkdir(parents=True, exist_ok=True)
    parts = ["<!-- Generated file. Edit docs/*.md, not this file. -->\n"]
    previous_groups: tuple[str, ...] = ()
    first_page = True

    for parents, _page_title, relative in entries:
        common = 0
        for left, right in zip(previous_groups, parents):
            if left != right:
                break
            common += 1

        if not first_page:
            parts.append('<div class="page-break"></div>\n')

        for level, group in enumerate(parents[common:], start=common + 1):
            parts.append(f"{'#' * level} {group}\n")

        source = DOCS / relative
        if not source.is_file():
            fail(f"missing Markdown file from mkdocs nav: {source}")
        text = source.read_text(encoding="utf-8")
        text = convert_admonitions(text)
        text = rewrite_images(text, source)
        text = rewrite_doc_links(text, source, anchors)
        text = demote_headings(text, len(parents))
        text = add_document_anchor(text, anchors[source.resolve()])
        parts.append(text)
        previous_groups = parents
        first_page = False

    output.write_text("\n".join(parts), encoding="utf-8")
    return output


def css_string(value: Any) -> str:
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def make_override_css(config: dict[str, Any]) -> Path:
    output = PROJECT / "build" / "pdf-overrides.css"
    output.parent.mkdir(parents=True, exist_ok=True)
    paper = str(config.get("paper_size", "A4"))
    css = f"""
:root {{
  --pdf-paper-size: {paper};
  --pdf-mono-font: {css_string(config.get('mono_font', 'Noto Sans Mono CJK JP'))};
}}

body {{
  font-family: {css_string(config.get('main_font', 'Noto Sans CJK JP'))};
  font-size: {config.get('body_font_size', '10pt')};
}}

@page {{
  size: {paper};
  margin: {config.get('margin_top', '23mm')} {config.get('margin_right', '18mm')} {config.get('margin_bottom', '20mm')} {config.get('margin_left', '18mm')};
  @top-left {{
    content: {css_string(config.get('header_left', ''))};
    font-family: {css_string(config.get('main_font', 'Noto Sans CJK JP'))};
    font-size: 7.5pt;
    color: #52606d;
  }}
  @top-right {{
    content: {css_string(config.get('header_right', ''))};
    font-family: {css_string(config.get('main_font', 'Noto Sans CJK JP'))};
    font-size: 7.5pt;
    color: #52606d;
  }}
  @bottom-center {{
    content: counter(page) " / " counter(pages);
    font-family: {css_string(config.get('main_font', 'Noto Sans CJK JP'))};
    font-size: 7.5pt;
    color: #52606d;
  }}
}}

@page title-page {{
  size: {paper};
  margin: 0;
  @top-left {{ content: none; }}
  @top-right {{ content: none; }}
  @bottom-center {{ content: none; }}
}}
""".lstrip()
    output.write_text(css, encoding="utf-8")
    return output


def render_mermaid_blocks(combined: Path) -> int:
    """Render fenced ```mermaid blocks to PNG and replace them with images.

    WeasyPrint cannot run JavaScript, so Mermaid (including C4 diagrams) is
    rendered to images at build time with mermaid-cli (mmdc). The source ```mermaid
    blocks stay editable in docs/*.md; only the combined Markdown is rewritten.
    """
    text = combined.read_text(encoding="utf-8")
    if "```mermaid" not in text and "~~~mermaid" not in text:
        return 0

    mmdc = os.environ.get("MERMAID_CLI") or shutil.which("mmdc")
    if not mmdc:
        fail("mermaid code blocks found but mmdc (mermaid-cli) was not found in PATH")

    MERMAID_DIR.mkdir(parents=True, exist_ok=True)
    lines = text.splitlines()
    out: list[str] = []
    count = 0
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped in ("```mermaid", "~~~mermaid"):
            fence = stripped[:3]
            i += 1
            code: list[str] = []
            while i < len(lines) and lines[i].strip() != fence:
                code.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1  # skip the closing fence
            count += 1
            source = MERMAID_DIR / f"diagram-{count:03d}.mmd"
            source.write_text("\n".join(code) + "\n", encoding="utf-8")
            image = MERMAID_DIR / f"diagram-{count:03d}.png"
            command = [mmdc, "-i", str(source), "-o", str(image), "-b", "white", "-s", "2"]
            if PUPPETEER_CONFIG.is_file():
                command += ["-p", str(PUPPETEER_CONFIG)]
            run(command)
            out.append(f"![]({image.relative_to(PROJECT).as_posix()})")
            out.append("")
        else:
            out.append(lines[i])
            i += 1

    combined.write_text("\n".join(out) + "\n", encoding="utf-8")
    return count


def render_plantuml_blocks(combined: Path) -> int:
    """Render fenced ```plantuml blocks to PNG and replace them with images.

    WeasyPrint cannot run JavaScript, so PlantUML (including C4 diagrams written
    against the bundled ``<C4/...>`` standard library) is rendered to images at
    build time with the ``plantuml`` command. The source ```plantuml blocks stay
    editable in docs/*.md; only the combined Markdown is rewritten.
    """
    text = combined.read_text(encoding="utf-8")
    if "```plantuml" not in text and "~~~plantuml" not in text:
        return 0

    plantuml = os.environ.get("PLANTUML_CMD") or shutil.which("plantuml")
    if not plantuml:
        fail("plantuml code blocks found but the `plantuml` command was not found in PATH")

    PLANTUML_DIR.mkdir(parents=True, exist_ok=True)
    lines = text.splitlines()
    out: list[str] = []
    count = 0
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped in ("```plantuml", "~~~plantuml"):
            fence = stripped[:3]
            i += 1
            code: list[str] = []
            while i < len(lines) and lines[i].strip() != fence:
                code.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1  # skip the closing fence
            count += 1
            body = "\n".join(code).strip("\n")
            # plantuml-markdown wraps fenced bodies in @startuml/@enduml on the
            # site; do the same here so authors omit them in both places.
            if not body.lstrip().startswith("@start"):
                body = f"@startuml\n{body}\n@enduml"
            source = PLANTUML_DIR / f"diagram-{count:03d}.puml"
            source.write_text(body + "\n", encoding="utf-8")
            image = PLANTUML_DIR / f"diagram-{count:03d}.png"
            run([plantuml, "-tpng", "-charset", "UTF-8", "-o", str(PLANTUML_DIR), str(source)])
            out.append(f"![]({image.relative_to(PROJECT).as_posix()})")
            out.append("")
        else:
            out.append(lines[i])
            i += 1

    combined.write_text("\n".join(out) + "\n", encoding="utf-8")
    return count


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=PROJECT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--keep-html", action="store_true", default=True)
    args = parser.parse_args()

    for executable in ("pandoc", "weasyprint"):
        if not shutil.which(executable):
            fail(f"{executable} was not found in PATH")

    mkdocs = read_yaml(MKDOCS)
    config = read_yaml(CONFIG)
    entries = list(flatten_nav(mkdocs.get("nav")))
    combined = make_combined(entries, config)
    diagrams = render_mermaid_blocks(combined)
    if diagrams:
        print(f"Rendered {diagrams} Mermaid diagram(s)")
    puml = render_plantuml_blocks(combined)
    if puml:
        print(f"Rendered {puml} PlantUML diagram(s)")
    override_css = make_override_css(config)

    output_pdf = args.output or PROJECT / str(config.get("output", "build/architecture.pdf"))
    output_pdf = output_pdf.resolve()
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    output_html = PROJECT / str(config.get("output_html", "build/architecture.html"))
    output_html = output_html.resolve()
    output_html.parent.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()

    pandoc_command = [
        "pandoc",
        str(combined),
        "--from=markdown+raw_html+pipe_tables+fenced_code_blocks+link_attributes",
        "--to=html5",
        "--standalone",
        "--template",
        str(HTML_TEMPLATE),
        "--section-divs",
        "--toc",
        "--toc-depth",
        str(config.get("toc_depth", 3)),
        "--metadata",
        f"title={config.get('title', mkdocs.get('site_name', 'Architecture Document'))}",
        "--metadata",
        f"subtitle={config.get('subtitle', '')}",
        "--metadata",
        f"author={config.get('author', '')}",
        "--metadata",
        f"date={today}",
        "--metadata",
        "toc-title=目次",
        "--css",
        str(BASE_CSS.relative_to(PROJECT)),
        "--css",
        str(override_css.relative_to(PROJECT)),
        "--resource-path",
        str(PROJECT),
        "--highlight-style",
        "tango",
        "--output",
        str(output_html),
    ]
    run(pandoc_command)

    weasy_command = [
        "weasyprint",
        "--base-url",
        str(PROJECT),
        str(output_html),
        str(output_pdf),
    ]
    run(weasy_command)

    print(f"Created PDF: {output_pdf}")
    print(f"Printable HTML: {output_html}")
    print(f"Combined Markdown: {combined}")


if __name__ == "__main__":
    main()
