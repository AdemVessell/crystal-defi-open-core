#!/usr/bin/env python3
"""Check the public open-core tree for excluded source/license markers."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def find_scan_root() -> Path:
    if (ROOT / "OPEN_CORE_MANIFEST.json").exists():
        return ROOT
    sibling = ROOT.parent / "crystal-defi-open-core"
    if (sibling / "OPEN_CORE_MANIFEST.json").exists():
        return sibling
    return ROOT


SCAN_ROOT = find_scan_root()

SKIP_DIRS = {
    ".git",
    "cache",
    "out",
    "__pycache__",
    "lib",
}

SOURCE_PREFIXES = (
    "contracts/",
    "script/",
    "sdk/",
    "watcher/",
    "research/",
    "test/",
)

TOP_LEVEL_FILES = {
    ".gitignore",
    "CONTRIBUTING.md",
    "LICENSE",
    "NOTICE",
    "OPEN_CORE_BOUNDARY.md",
    "OPEN_CORE_MANIFEST.json",
    "README.md",
    "SECURITY.md",
    "foundry.toml",
}

ALLOWED_MARKER_FILES = {
    "scripts/check_open_core_boundary.py",
    "scripts/export_open_core.py",
    "scripts/grant_readiness_check.py",
}

PATTERNS = {
    "busl_spdx": re.compile(r"SPDX-License-Identifier:\s*BUSL", re.IGNORECASE),
    "busl_license_line": re.compile(r"BUSL-1\.1\s*-", re.IGNORECASE),
    "business_source": re.compile(r"Business Source", re.IGNORECASE),
}


def is_skipped(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.relative_to(SCAN_ROOT).parts)


def is_candidate(rel: str) -> bool:
    if rel in TOP_LEVEL_FILES:
        return True
    if rel in ALLOWED_MARKER_FILES:
        return True
    if rel.startswith("scripts/"):
        return True
    return rel.startswith(SOURCE_PREFIXES)


def main() -> int:
    findings: list[dict[str, object]] = []
    scanned_files = 0

    for path in sorted(SCAN_ROOT.rglob("*")):
        if not path.is_file() or is_skipped(path):
            continue
        rel = path.relative_to(SCAN_ROOT).as_posix()
        if not is_candidate(rel):
            continue
        scanned_files += 1
        if rel in ALLOWED_MARKER_FILES:
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for name, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.append(
                        {
                            "path": rel,
                            "line": line_number,
                            "pattern": name,
                            "text": line.strip()[:160],
                        }
                    )

    result = {
        "ok": not findings,
        "scan_root": str(SCAN_ROOT),
        "scanned_files": scanned_files,
        "allowed_marker_files": sorted(ALLOWED_MARKER_FILES),
        "findings": findings,
    }
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
