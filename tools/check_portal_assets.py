#!/usr/bin/env python3
"""Check that the portal pages embedded in src/AWM_html_gz.h match data/.

Each <NAME>_HTML_GZ array in the header is decompressed and compared with
data/<name>.html. Line endings are normalised first, so a header generated
from a CRLF checkout still matches an LF source file.

Exits non-zero when a page is missing or out of date. Regenerate the header
with the AyresNet GZIP Asset Compiler after editing anything in data/.
"""

import gzip
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEADER = ROOT / "src" / "AWM_html_gz.h"
DATA_DIR = ROOT / "data"

ARRAY_RE = re.compile(r"(\w+)_HTML_GZ\[\]\s*PROGMEM\s*=\s*\{(.*?)\};", re.S)
BYTE_RE = re.compile(r"0x([0-9A-Fa-f]{2})")


def normalise(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def main() -> int:
    arrays = ARRAY_RE.findall(HEADER.read_text(encoding="utf-8"))
    if not arrays:
        print(f"FAIL  no *_HTML_GZ arrays found in {HEADER.name}")
        return 1

    failures = 0
    for name, body in arrays:
        source = DATA_DIR / f"{name.lower()}.html"
        embedded = gzip.decompress(bytes(int(b, 16) for b in BYTE_RE.findall(body)))

        if not source.is_file():
            print(f"FAIL  {name}: {source.relative_to(ROOT)} does not exist")
            failures += 1
        elif normalise(embedded) != normalise(source.read_bytes()):
            print(f"FAIL  {name}: embedded copy differs from {source.relative_to(ROOT)}")
            failures += 1
        else:
            print(f"OK    {name}: matches {source.relative_to(ROOT)}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
