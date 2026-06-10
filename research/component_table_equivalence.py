#!/usr/bin/env python3
"""Check that compact component tables reconstruct the full Crystal tables."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sdk"))

from crystal_committer import N_HEADS, STATE_SIZE, build_crystal_components, build_crystal_table  # noqa: E402


def reconstruct_table_from_components(head: int) -> np.ndarray:
    components = build_crystal_components(head)
    ii, jj = np.meshgrid(np.arange(STATE_SIZE), np.arange(STATE_SIZE), indexing="ij")
    result = np.zeros((STATE_SIZE, STATE_SIZE), dtype=np.uint8)
    for k in range(4):
        ci = (ii >> (2 * k)) & 3
        cj = (jj >> (2 * k)) & 3
        result |= components[k, ci, cj].astype(np.uint8) << (2 * k)
    return result


def main() -> int:
    per_head = []
    all_match = True
    for head in range(N_HEADS):
        full = build_crystal_table(head)
        reconstructed = reconstruct_table_from_components(head)
        matches = bool(np.array_equal(full, reconstructed))
        all_match = all_match and matches
        per_head.append(
            {
                "head": head,
                "matches": matches,
                "component_bytes": int(build_crystal_components(head).reshape(-1).nbytes),
                "full_table_bytes": int(full.nbytes),
            }
        )

    output = {
        "ok": all_match,
        "n_heads": N_HEADS,
        "total_component_bytes": sum(row["component_bytes"] for row in per_head),
        "total_full_table_bytes": sum(row["full_table_bytes"] for row in per_head),
        "per_head": per_head,
    }
    print(json.dumps(output, indent=2))
    return 0 if all_match else 1


if __name__ == "__main__":
    raise SystemExit(main())
