#!/usr/bin/env python3
"""Check the translation tables of the portal pages in data/.

Each page carries its text in a <script type="application/json" id="i18n">
block with one table per language, plus a shared helper block between
/* i18n-core:begin */ and /* i18n-core:end */. This script checks that:

- every language has the same keys as English and a non-empty _name;
- every key the page uses is defined, and every defined key is used;
- {placeholders} match across languages;
- erase_all_confirm_word differs between languages;
- the i18n-core block is identical in every page.

Exits non-zero and lists the problems when something is wrong.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PAGES = [ROOT / "data" / name for name in ("index.html", "success.html", "error.html")]

TABLE_RE = re.compile(r'<script type="application/json" id="i18n">(.*?)</script>', re.S)
ATTR_RE = re.compile(r'data-i18n(?:-html|-placeholder|-title|-aria-label)?="([a-z0-9_]+)"')
CALL_RE = re.compile(r"\b(?:t|setStatus|setEraseMsg|i18nError)\(\s*'([a-z0-9_]+)'")
CORE_RE = re.compile(r"/\* i18n-core:begin \*/.*?/\* i18n-core:end \*/", re.S)
PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")
CONFIRM_KEY = "erase_all_confirm_word"
META_KEYS = {"_name"}


def check_page(path: Path) -> list:
    name = path.name
    text = path.read_text(encoding="utf-8")
    match = TABLE_RE.search(text)
    if not match:
        return [f'{name}: no i18n table (<script type="application/json" id="i18n">)']
    try:
        tables = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        return [f"{name}: i18n table is not valid JSON ({exc})"]
    if "en" not in tables:
        return [f"{name}: no 'en' table (English is the fallback)"]

    problems = []
    reference = set(tables["en"])
    for lang, table in tables.items():
        if not str(table.get("_name", "")).strip():
            problems.append(f"{name}: '{lang}' has no _name")
        for key in sorted(reference - set(table)):
            problems.append(f"{name}: '{lang}' is missing key '{key}'")
        for key in sorted(set(table) - reference):
            problems.append(f"{name}: '{lang}' has key '{key}' that 'en' does not")

    defined = reference - META_KEYS
    used = set(ATTR_RE.findall(text)) | set(CALL_RE.findall(text))
    for key in sorted(used - defined):
        problems.append(f"{name}: key '{key}' is used but not defined")
    for key in sorted(defined - used):
        problems.append(f"{name}: key '{key}' is defined but never used")

    for key in sorted(defined):
        want = set(PLACEHOLDER_RE.findall(str(tables["en"][key])))
        for lang, table in tables.items():
            if key not in table:
                continue
            got = set(PLACEHOLDER_RE.findall(str(table[key])))
            if got != want:
                problems.append(
                    f"{name}: '{key}' placeholders differ in '{lang}': {sorted(got)} vs en {sorted(want)}"
                )

    if CONFIRM_KEY in defined:
        words = [str(table.get(CONFIRM_KEY, "")).strip().upper() for table in tables.values()]
        if not all(words):
            problems.append(f"{name}: '{CONFIRM_KEY}' is empty in some language")
        elif len(set(words)) != len(words):
            problems.append(f"{name}: '{CONFIRM_KEY}' must differ between languages")
    return problems


def check_core(paths) -> list:
    problems = []
    first = None
    for path in paths:
        match = CORE_RE.search(path.read_text(encoding="utf-8"))
        if not match:
            problems.append(f"{path.name}: no i18n-core block")
            continue
        block = match.group(0).replace("\r\n", "\n")
        if first is None:
            first = (path.name, block)
        elif block != first[1]:
            problems.append(f"{path.name}: i18n-core block differs from {first[0]}")
    return problems


def main(argv=None) -> int:
    paths = [Path(arg) for arg in argv] if argv else DEFAULT_PAGES
    problems = []
    for path in paths:
        problems += check_page(path)
    problems += check_core(paths)
    for problem in problems:
        print(f"FAIL  {problem}")
    if not problems:
        print(f"OK    {len(paths)} page(s): translations complete and consistent")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
