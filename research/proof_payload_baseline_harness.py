#!/usr/bin/env python3
"""Proof-payload size baselines for Crystal DeFi.

This is a sizing harness, not a security proof. It compares minimal binary
payload surfaces for common proof families so Crystal claims stay attached to
the same query class.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sdk"))

from crystal_committer import CrystalCommitter, leaf, node  # noqa: E402


def balanced_tree(values: list[int]):
    if len(values) == 1:
        return leaf(values[0])
    mid = len(values) // 2
    return node(balanced_tree(values[:mid]), balanced_tree(values[mid:]))


def ceil_log2(value: int) -> int:
    return 0 if value <= 1 else math.ceil(math.log2(value))


def crystal_anchor_package_bytes(committer: CrystalCommitter, leaf_count: int) -> int:
    tree = balanced_tree([i % 256 for i in range(leaf_count)])
    encoded = committer.encode_for_chain(tree)
    # Minimal binary package:
    # 8B Crystal root + 32B anchor + 32B table commitment + encoded tree.
    return 8 + 32 + 32 + len(encoded)


def merkle_membership_bytes(leaf_count: int) -> int:
    depth = ceil_log2(leaf_count)
    # 32B root + 1B uint8 leaf + 4B generalized index + 32B siblings.
    return 32 + 1 + 4 + 32 * depth


def ssz_generalized_index_proof_bytes(leaf_count: int) -> int:
    depth = ceil_log2(leaf_count)
    # Same minimal surface as Merkle membership for this uint8 leaf model.
    # Real SSZ containers may add type/schema context outside this proof.
    return 32 + 1 + 8 + 32 * depth


def sparse_merkle_uint8_key_bytes() -> int:
    # 256-key universe, depth 8. Includes root, key, value, and siblings.
    return 32 + 1 + 1 + 32 * 8


def anchored_v1_crystal_witness_bytes(leaf_count: int) -> int:
    depth = ceil_log2(leaf_count)
    # 8B local Crystal root + 1B step count + per-step side byte and 8B sibling root.
    return 8 + 1 + depth * (1 + 8)


def anchored_v1_merkle_proof_bytes(leaf_count: int) -> int:
    depth = ceil_log2(leaf_count)
    # 1B step count + per-step side byte and 32B sibling hash.
    return 1 + depth * (1 + 32)


def anchored_v1_local_path_bytes(leaf_count: int) -> int:
    # Solidity challenge arguments include the Crystal witness, a 32B target
    # Merkle hash, and the Merkle proof bytes. Posted roots are committed
    # separately by the sequencer/sidecar.
    return (
        anchored_v1_crystal_witness_bytes(leaf_count)
        + 32
        + anchored_v1_merkle_proof_bytes(leaf_count)
    )


def full_tree_calldata_bytes(committer: CrystalCommitter, leaf_count: int) -> int:
    tree = balanced_tree([i % 256 for i in range(leaf_count)])
    return len(committer.encode_for_chain(tree))


def run(counts: list[int]) -> dict:
    committer = CrystalCommitter()
    rows = []
    for leaf_count in counts:
        rows.append(
            {
                "leaf_count": leaf_count,
                "tree_depth": ceil_log2(leaf_count),
                "full_tree_calldata_bytes": full_tree_calldata_bytes(committer, leaf_count),
                "crystal_anchor_package_bytes": crystal_anchor_package_bytes(committer, leaf_count),
                "domain_merkle_membership_bytes": merkle_membership_bytes(leaf_count),
                "ssz_generalized_index_proof_bytes": ssz_generalized_index_proof_bytes(leaf_count),
                "sparse_merkle_uint8_key_bytes": sparse_merkle_uint8_key_bytes(),
                "anchored_v1_crystal_witness_bytes": anchored_v1_crystal_witness_bytes(leaf_count),
                "anchored_v1_merkle_proof_bytes": anchored_v1_merkle_proof_bytes(leaf_count),
                "anchored_v1_local_path_bytes": anchored_v1_local_path_bytes(leaf_count),
            }
        )
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "boundary": (
            "V0 Crystal package includes the full encoded tree. Anchored V1 removes "
            "full-tree calldata from the challenge path and measures the local Crystal "
            "witness plus same-path Merkle proof. Merkle/SSZ/sparse rows are "
            "membership/update proof surfaces, not full-tree witnesses."
        ),
        "rows": rows,
    }


def write_markdown(result: dict, path: Path) -> None:
    lines = [
        "# Crystal DeFi Proof Payload Baselines",
        "",
        f"Generated: `{result['generated_at']}`",
        "",
        "## Boundary",
        "",
        result["boundary"],
        "",
        "| Leaves | Depth | V0 Crystal package | Tree calldata | Anchored V1 local path | V1 Crystal witness | V1 Merkle proof | Merkle membership | SSZ proof | Sparse Merkle uint8 |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["rows"]:
        lines.append(
            "| `{leaf_count}` | `{tree_depth}` | `{crystal_anchor_package_bytes}` | "
            "`{full_tree_calldata_bytes}` | `{anchored_v1_local_path_bytes}` | "
            "`{anchored_v1_crystal_witness_bytes}` | `{anchored_v1_merkle_proof_bytes}` | "
            "`{domain_merkle_membership_bytes}` | `{ssz_generalized_index_proof_bytes}` | "
            "`{sparse_merkle_uint8_key_bytes}` |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- V0 Crystal package is a full-tree anchored witness and should not be compared to compact membership proofs as if it were minimal.",
            "- Anchored V1 removes full-tree calldata from the challenge path and measures only the local Crystal witness plus same-path Merkle proof.",
            "- V1 is not a Merkle replacement. The Merkle/SSZ/sparse-Merkle rows remain the binding proof-size baselines.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare proof payload byte surfaces.")
    parser.add_argument("--leaf-counts", default="4,8,16,32,64,128,256,512")
    parser.add_argument("--output-dir", default="research/results")
    args = parser.parse_args()

    counts = [int(part.strip()) for part in args.leaf_counts.split(",") if part.strip()]
    result = run(counts)

    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "proof_payload_baselines_latest.json"
    md_path = output_dir / "proof_payload_baselines_latest.md"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_markdown(result, md_path)
    print(json.dumps({"json": str(json_path), "markdown": str(md_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
