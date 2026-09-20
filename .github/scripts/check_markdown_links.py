"""Repository-local Markdown link checker (CI Documentation Check).

Policy (documented, deterministic):
- Checks ONLY repository-local links: `[text](./path)`, `[text](../x.md#anchor)`,
  `![alt](img.png)`, reference definitions `[id]: path`, and `#anchor` links.
- External URLs (http/https), mailto:, and data: URIs are SKIPPED — external
  hosts are flaky by nature and must never gate CI.
- Historical audit documents are checked identically (link validity only);
  their wording/scores are never touched by this script.
- Fails (exit 1) on any broken local file link or dangling #anchor.
- Stdlib only — no install step, reproducible on any runner with Python 3.11+.

Usage: python .github/scripts/check_markdown_links.py  (run from repo root)
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SKIP_DIRS = {".git", "node_modules", ".venv", "dist", "build", "__pycache__",
             ".pytest_cache", ".mypy_cache", ".ruff_cache"}

INLINE_LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
REF_DEF = re.compile(r"^\s*\[[^\]]+\]:\s*(\S+)", re.MULTILINE)
AUTOLINK = re.compile(r"<([A-Za-z][A-Za-z0-9+.-]*:[^<>\s]+)>")


def github_slug(heading: str) -> str:
    slug = heading.strip().lower()
    slug = re.sub(r"[^\w\s\-]", "", slug, flags=re.UNICODE)
    return re.sub(r"\s+", "-", slug)


def file_anchors(path: str) -> set:
    anchors = set()
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = re.match(r"#{1,6}\s+(.*)", line)
                if m:
                    anchors.add(github_slug(re.sub(r"<[^>]+>", "", m.group(1))))
                m = re.match(r'\s*<a\s+(?:name|id)=["\']([^"\']+)["\']', line)
                if m:
                    anchors.add(m.group(1).lower())
    except OSError:
        pass
    return anchors


def iter_markdown():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            if fn.endswith(".md"):
                yield os.path.join(dirpath, fn)


def extract_links(text: str):
    targets = INLINE_LINK.findall(text)
    targets += REF_DEF.findall(text)
    targets += AUTOLINK.findall(text)
    return targets


def check_link(md_path: str, target: str, errors: list) -> None:
    if re.match(r"^(https?|mailto|ftp|data|tel):", target, re.IGNORECASE):
        return  # external / non-file: policy skip
    if target.startswith("?"):
        return
    path_part, _, anchor = target.partition("#")
    if not path_part:
        if anchor and anchor.lower() not in file_anchors(md_path):
            errors.append(f"{rel(md_path)}: dangling anchor #{anchor}")
        return
    base = ROOT if path_part.startswith("/") else os.path.dirname(md_path)
    resolved = os.path.normpath(os.path.join(base, path_part.lstrip("/")))
    if not os.path.exists(resolved):
        errors.append(f"{rel(md_path)}: broken link -> {target}")
        return
    if anchor and os.path.isfile(resolved) and resolved.endswith(".md"):
        if anchor.lower() not in file_anchors(resolved):
            errors.append(f"{rel(md_path)}: dangling anchor #{anchor} -> {target}")


def rel(p: str) -> str:
    return os.path.relpath(p, ROOT)


def main() -> int:
    errors: list = []
    checked = 0
    for md in iter_markdown():
        try:
            with open(md, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as e:
            errors.append(f"{rel(md)}: unreadable ({e})")
            continue
        for target in extract_links(text):
            check_link(md, target.strip("<>"), errors)
            checked += 1
    print(f"checked {checked} links; {len(errors)} broken")
    for e in errors:
        print("BROKEN:", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
