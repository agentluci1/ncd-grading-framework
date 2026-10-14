#!/usr/bin/env python3
"""Generate the HTML views from the Markdown sources in public/grading/.

Usage: python3 build.py   (needs: pip install "markdown==3.10.2" "jsonschema>=4.19"; markdown is pinned so output is byte-stable)
The .md files are the single source of truth; never edit the .html files by hand.
"""
import os
import re
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).parent / "public" / "grading"
PAGES = [  # (markdown source, html output, title)
    ("NCD-GRADING-FRAMEWORK.md", "index.html", "NCD Grading Framework"),
    ("GRADE-DCN.md", "grade-dcn.html", "Grade DCN"),
]
INLINE_ALIGN = re.compile(r' style="text-align: ?(left|right|center);?"')
LIST_LINE = re.compile(r"^\s*(?:[-*]|\d+\.)\s")


def add_list_breaks(text):
    """python-markdown needs a blank line before a list; insert one outside code fences."""
    out, fenced, prev = [], False, ""
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        if not fenced and LIST_LINE.match(line) and prev.strip() and not LIST_LINE.match(prev):
            out.append("")
        out.append(line)
        prev = line
    return "\n".join(out) + "\n"


def render(src, title, root=None):
    body = markdown.markdown(add_list_breaks(((root or ROOT) / src).read_text(encoding="utf-8")), extensions=["tables", "fenced_code"])
    # CSP allows only self-hosted stylesheets, so turn table alignment attributes into classes.
    body = INLINE_ALIGN.sub(lambda m: f' class="align-{m.group(1)}"', body)
    nav = ('<nav><a href="NCD-GRADING-FRAMEWORK.md">Raw framework (.md)</a> | <a href="index.html">Framework</a> | '
           '<a href="grade-dcn.html">Grade DCN prompt</a> | <a href="GRADE-DCN.md">Raw DCN prompt (.md)</a></nav>')
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{title}</title><link rel="stylesheet" href="style.css"></head>'
            f'<body>{nav}<main>{body}</main></body></html>\n')


def restore(originals):
    """Best-effort restore of every original output; returns the paths that could not be restored."""
    failed = []
    for path, data in originals.items():
        try:
            path.with_suffix(".tmp").unlink(missing_ok=True)
            if data is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(data)
        except OSError:
            failed.append(str(path))
    return failed


def main(root=None):
    """Render all pages, then replace outputs; on any write failure restore every original file.

    Idempotent: re-running with unchanged sources rewrites identical bytes.
    Returns 0 on success, 1 on failure (error and any unrestored paths printed to stderr).
    """
    root = Path(root) if root else ROOT
    originals = {}
    try:
        rendered = [(root / out, render(src, title, root)) for src, out, title in PAGES]
        for path, _ in rendered:
            originals[path] = path.read_bytes() if path.exists() else None
        for path, html in rendered:
            tmp = path.with_suffix(".tmp")
            tmp.write_text(html, encoding="utf-8")
            os.replace(tmp, path)
    except (OSError, UnicodeError) as err:
        unrestored = restore(originals)
        status = f"NOT restored: {', '.join(unrestored)}" if unrestored else "outputs restored"
        print(f"build failed ({err}); {status}", file=sys.stderr)
        return 1
    for path, _ in rendered:
        print("wrote", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
