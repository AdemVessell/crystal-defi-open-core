#!/usr/bin/env python3
"""Baseline structural-commitment harness for Crystal DeFi.

This compares Crystal roots against boring commitments on the same exhaustive
same-multiset tree set:

- Domain-separated Merkle tree: commits to leaf values, order, and tree shape.
- Ordered flat digest: commits to ordered leaves, but discards tree shape.
- Sorted multiset digest: commits to multiset only; discards order and shape.
- Sorted Merkle set digest: commits to sorted leaves; discards order and shape.

The purpose is to keep denominator claims honest. Crystal should not be compared
to a swap; it should be compared to proof systems answering the same question.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sdk"))
sys.path.insert(0, str(ROOT / "research"))

from adversarial_grinding_harness import all_shapes, instantiate_shape, tree_expr  # noqa: E402
from crystal_committer import CrystalCommitter, CrystalLeaf, CrystalNode, CrystalTree, get_leaves  # noqa: E402


def h(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def domain_merkle_root(tree: CrystalTree) -> bytes:
    if isinstance(tree, CrystalLeaf):
        return h(b"\x00" + bytes([tree.state]))
    assert isinstance(tree, CrystalNode)
    return h(b"\x01" + domain_merkle_root(tree.left) + domain_merkle_root(tree.right))


def ordered_flat_digest(tree: CrystalTree) -> bytes:
    return h(b"ordered-flat:v1\x00" + bytes(get_leaves(tree)))


def sorted_multiset_digest(tree: CrystalTree) -> bytes:
    return h(b"sorted-multiset:v1\x00" + bytes(sorted(get_leaves(tree))))


def sorted_merkle_set_digest(tree: CrystalTree) -> bytes:
    leaves = [h(b"\x00" + bytes([value])) for value in sorted(get_leaves(tree))]
    if not leaves:
        return h(b"empty")
    level = leaves
    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else level[i]
            next_level.append(h(b"\x01" + left + right))
        level = next_level
    return level[0]


def summarize_commitment(name: str, roots: dict[str, str], candidate_count: int) -> dict:
    unique = len(roots)
    return {
        "name": name,
        "unique_roots": unique,
        "collisions": candidate_count - unique,
        "detects_all_structural_variants": unique == candidate_count,
    }


def evaluate_leaf_count(committer: CrystalCommitter, leaf_count: int) -> dict:
    values = list(range(1, leaf_count + 1))
    seen = {
        "crystal_8_byte": {},
        "domain_merkle_sha256": {},
        "ordered_flat_sha256": {},
        "sorted_multiset_sha256": {},
        "sorted_merkle_set_sha256": {},
    }
    candidate_count = 0
    first_collision: dict[str, dict | None] = {name: None for name in seen}

    for shape in all_shapes(leaf_count):
        for perm in itertools.permutations(values):
            tree = instantiate_shape(shape, perm)
            expr = tree_expr(tree)
            candidate_count += 1
            roots = {
                "crystal_8_byte": bytes(committer.commit(tree)[0]).hex(),
                "domain_merkle_sha256": domain_merkle_root(tree).hex(),
                "ordered_flat_sha256": ordered_flat_digest(tree).hex(),
                "sorted_multiset_sha256": sorted_multiset_digest(tree).hex(),
                "sorted_merkle_set_sha256": sorted_merkle_set_digest(tree).hex(),
            }
            for name, root in roots.items():
                prior = seen[name].setdefault(root, expr)
                if prior != expr and first_collision[name] is None:
                    first_collision[name] = {
                        "root": root,
                        "tree_a": prior,
                        "tree_b": expr,
                    }

    summaries = [
        summarize_commitment(name, roots, candidate_count)
        for name, roots in seen.items()
    ]
    return {
        "leaf_count": leaf_count,
        "candidates": candidate_count,
        "commitments": summaries,
        "first_collision": first_collision,
    }


def write_markdown(result: dict, path: Path) -> None:
    lines = [
        "# Crystal DeFi Structural Baseline Harness",
        "",
        f"Generated: `{result['generated_at']}`",
        "",
        "## Summary",
        "",
        "This harness compares Crystal to same-query structural baselines. Domain-separated Merkle commits to shape and order; sorted baselines intentionally discard them.",
        "",
    ]
    for row in result["rows"]:
        lines.extend(
            [
                f"## Leaves {row['leaf_count']}",
                "",
                f"Candidates: `{row['candidates']}`",
                "",
                "| Commitment | Unique roots | Collisions | Detects all variants |",
                "|---|---:|---:|---|",
            ]
        )
        for item in row["commitments"]:
            lines.append(
                "| `{name}` | `{unique_roots}` | `{collisions}` | `{detects_all_structural_variants}` |".format(
                    **item
                )
            )
        lines.append("")

    lines.extend(
        [
            "## Interpretation",
            "",
            "- Domain-separated Merkle is the honest cryptographic baseline for structure-sensitive commitments.",
            "- Sorted Merkle/set commitments are useful only when order and tree shape are intentionally out of scope.",
            "- Crystal's sellable role is not cryptographic uniqueness; it is a compact structural signal and localization layer that can route expensive proofs.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare Crystal against structural baselines.")
    parser.add_argument("--max-leaves", type=int, default=6)
    parser.add_argument("--output-dir", default="research/results")
    args = parser.parse_args()

    committer = CrystalCommitter()
    started = time.time()
    rows = [evaluate_leaf_count(committer, leaves) for leaves in range(2, args.max_leaves + 1)]
    result = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "parameters": {"max_leaves": args.max_leaves},
        "elapsed_seconds": round(time.time() - started, 3),
        "rows": rows,
    }

    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "structural_baselines_latest.json"
    md_path = output_dir / "structural_baselines_latest.md"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_markdown(result, md_path)
    print(json.dumps({"json": str(json_path), "markdown": str(md_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
