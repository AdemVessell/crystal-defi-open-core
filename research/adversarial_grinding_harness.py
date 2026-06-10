#!/usr/bin/env python3
"""Adversarial collision and structural-divergence harness for Crystal DeFi.

This is a scientific gate, not a marketing benchmark. It measures whether
same-leaf-multiset tree variants can be found that collide with a committed
Crystal root, and compares that behavior with standard SHA-256 structural
digests at the same 8-byte width and at full 32-byte anchor width.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sdk"))

from crystal_committer import CrystalCommitter, CrystalLeaf, CrystalNode, CrystalTree, get_leaves, leaf, node  # noqa: E402


Shape = object


def all_shapes(leaf_count: int, memo: dict[int, list[Shape]] | None = None) -> list[Shape]:
    """Return every ordered full-binary-tree shape for leaf_count leaves."""
    if memo is None:
        memo = {}
    if leaf_count in memo:
        return memo[leaf_count]
    if leaf_count == 1:
        memo[leaf_count] = ["L"]
        return memo[leaf_count]

    result: list[Shape] = []
    for left_count in range(1, leaf_count):
        right_count = leaf_count - left_count
        for left_shape in all_shapes(left_count, memo):
            for right_shape in all_shapes(right_count, memo):
                result.append((left_shape, right_shape))
    memo[leaf_count] = result
    return result


def instantiate_shape(shape: Shape, values: Iterable[int]) -> CrystalTree:
    """Fill a shape with leaf values in left-to-right order."""
    iterator = iter(values)

    def build(current: Shape) -> CrystalTree:
        if current == "L":
            return leaf(next(iterator))
        left_shape, right_shape = current
        return node(build(left_shape), build(right_shape))

    return build(shape)


def tree_expr(tree: CrystalTree) -> str:
    if isinstance(tree, CrystalLeaf):
        return str(tree.state)
    assert isinstance(tree, CrystalNode)
    return f"({tree_expr(tree.left)},{tree_expr(tree.right)})"


def canonical_tree_bytes(tree: CrystalTree) -> bytes:
    """Canonical structural bytes for hash-baseline comparisons."""
    if isinstance(tree, CrystalLeaf):
        return bytes([0, tree.state])
    assert isinstance(tree, CrystalNode)
    return bytes([1]) + canonical_tree_bytes(tree.left) + canonical_tree_bytes(tree.right)


def sha256_truncated_8(tree: CrystalTree) -> bytes:
    return hashlib.sha256(canonical_tree_bytes(tree)).digest()[:8]


def sha256_full(tree: CrystalTree) -> bytes:
    return hashlib.sha256(canonical_tree_bytes(tree)).digest()


def random_tree_from_values(rng: random.Random, values: list[int]) -> CrystalTree:
    """Generate a random ordered binary tree containing exactly values."""
    shuffled = list(values)
    rng.shuffle(shuffled)

    def build(items: list[int]) -> CrystalTree:
        if len(items) == 1:
            return leaf(items[0])
        split = rng.randrange(1, len(items))
        return node(build(items[:split]), build(items[split:]))

    return build(shuffled)


@dataclass
class CollisionStats:
    candidates: int
    crystal_unique_roots: int
    crystal_collision_count: int
    sha8_unique_roots: int
    sha8_collision_count: int
    first_crystal_collision: dict | None
    first_sha8_collision: dict | None


def exhaustive_same_multiset(committer: CrystalCommitter, leaf_count: int) -> CollisionStats:
    """Enumerate all ordered shapes and leaf permutations for one multiset."""
    values = list(range(1, leaf_count + 1))
    crystal_seen: dict[tuple[int, ...], str] = {}
    sha8_seen: dict[str, str] = {}
    first_crystal_collision = None
    first_sha8_collision = None
    candidates = 0

    for shape in all_shapes(leaf_count):
        for perm in itertools.permutations(values):
            tree = instantiate_shape(shape, perm)
            expr = tree_expr(tree)
            candidates += 1

            crystal_root, _ = committer.commit(tree)
            prior = crystal_seen.setdefault(crystal_root, expr)
            if prior != expr and first_crystal_collision is None:
                first_crystal_collision = {
                    "root": list(crystal_root),
                    "tree_a": prior,
                    "tree_b": expr,
                }

            sha8 = sha256_truncated_8(tree).hex()
            prior_sha = sha8_seen.setdefault(sha8, expr)
            if prior_sha != expr and first_sha8_collision is None:
                first_sha8_collision = {
                    "digest8": sha8,
                    "tree_a": prior_sha,
                    "tree_b": expr,
                }

    return CollisionStats(
        candidates=candidates,
        crystal_unique_roots=len(crystal_seen),
        crystal_collision_count=candidates - len(crystal_seen),
        sha8_unique_roots=len(sha8_seen),
        sha8_collision_count=candidates - len(sha8_seen),
        first_crystal_collision=first_crystal_collision,
        first_sha8_collision=first_sha8_collision,
    )


def grinding_campaign(
    committer: CrystalCommitter,
    rng: random.Random,
    leaf_count: int,
    max_attempts: int,
) -> dict:
    values = rng.sample(range(1, 256), leaf_count)
    target = random_tree_from_values(rng, values)
    target_expr = tree_expr(target)
    target_crystal, _ = committer.commit(target)
    target_sha8 = sha256_truncated_8(target)
    target_sha256 = sha256_full(target)

    for attempt in range(1, max_attempts + 1):
        candidate = random_tree_from_values(rng, values)
        candidate_expr = tree_expr(candidate)
        if candidate_expr == target_expr:
            continue

        candidate_crystal, _ = committer.commit(candidate)
        if candidate_crystal == target_crystal:
            return {
                "hit": True,
                "hit_kind": "crystal",
                "attempts": attempt,
                "leaf_count": leaf_count,
                "target_tree": target_expr,
                "candidate_tree": candidate_expr,
                "root": list(target_crystal),
                "same_sorted_leaves": sorted(get_leaves(target)) == sorted(get_leaves(candidate)),
            }

        if sha256_truncated_8(candidate) == target_sha8:
            return {
                "hit": True,
                "hit_kind": "sha256_truncated_8",
                "attempts": attempt,
                "leaf_count": leaf_count,
                "target_tree": target_expr,
                "candidate_tree": candidate_expr,
                "digest8": target_sha8.hex(),
                "same_sorted_leaves": sorted(get_leaves(target)) == sorted(get_leaves(candidate)),
            }

        if sha256_full(candidate) == target_sha256:
            return {
                "hit": True,
                "hit_kind": "sha256_full",
                "attempts": attempt,
                "leaf_count": leaf_count,
                "target_tree": target_expr,
                "candidate_tree": candidate_expr,
                "digest": target_sha256.hex(),
                "same_sorted_leaves": sorted(get_leaves(target)) == sorted(get_leaves(candidate)),
            }

    return {
        "hit": False,
        "attempts": max_attempts,
        "leaf_count": leaf_count,
        "target_tree": target_expr,
        "root": list(target_crystal),
        "sha256_truncated_8": target_sha8.hex(),
        "sha256_full": target_sha256.hex(),
    }


def write_markdown(result: dict, path: Path) -> None:
    lines = [
        "# Crystal DeFi Adversarial Grinding Harness",
        "",
        f"Generated: `{result['generated_at']}`",
        f"Seed: `{result['seed']}`",
        "",
        "## Verdict",
        "",
        result["verdict"],
        "",
        "## Exhaustive Same-Multiset Enumeration",
        "",
        "| Leaves | Candidates | Crystal unique | Crystal collisions | SHA-8 unique | SHA-8 collisions |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["exhaustive"]:
        lines.append(
            "| `{leaf_count}` | `{candidates}` | `{crystal_unique_roots}` | "
            "`{crystal_collision_count}` | `{sha8_unique_roots}` | `{sha8_collision_count}` |".format(**row)
        )

    lines.extend(["", "## Random Grinding Campaigns", ""])
    hit_rows = [row for row in result["grinding_campaigns"] if row["hit"]]
    if hit_rows:
        lines.append(f"- Hits found: `{len(hit_rows)}`")
        for hit in hit_rows[:5]:
            lines.append(
                f"- `{hit['hit_kind']}` collision after `{hit['attempts']}` attempts "
                f"with `{hit['leaf_count']}` leaves."
            )
    else:
        attempts = [row["attempts"] for row in result["grinding_campaigns"]]
        lines.append(f"- Hits found: `0` across `{sum(attempts)}` candidate attempts.")

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- A no-hit run is not a proof of cryptographic soundness.",
            "- A Crystal collision is a hard demotion for unanchored security claims.",
            "- SHA-256 full digest is treated as the anchor baseline, not as a Crystal competitor.",
            "- Crystal should be framed as a structural divergence monitor unless this harness and later formal analysis justify stronger language.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def summarize_verdict(exhaustive_rows: list[dict], grinding_rows: list[dict]) -> str:
    crystal_exhaustive_hits = sum(row["crystal_collision_count"] for row in exhaustive_rows)
    crystal_random_hits = [row for row in grinding_rows if row["hit"] and row["hit_kind"] == "crystal"]
    sha_random_hits = [row for row in grinding_rows if row["hit"] and row["hit_kind"].startswith("sha256")]

    if crystal_exhaustive_hits or crystal_random_hits:
        return (
            "Crystal collisions were found under the tested same-multiset adversary. "
            "Do not use unanchored Crystal roots as adversarial commitments; frame Crystal as a localization/checking layer."
        )
    if sha_random_hits:
        return (
            "No Crystal collision was found, but a hash-baseline collision appeared. "
            "Inspect the harness and environment before drawing conclusions."
        )
    return (
        "No Crystal or SHA baseline collision was found within this bounded run. "
        "This supports structural-divergence monitoring language, not cryptographic commitment language."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Crystal DeFi adversarial collision/grinding checks.")
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--exhaustive-leaves", type=int, default=6)
    parser.add_argument("--grind-leaves", type=int, default=8)
    parser.add_argument("--campaigns", type=int, default=12)
    parser.add_argument("--max-attempts", type=int, default=50000)
    parser.add_argument("--output-dir", default="research/results")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    committer = CrystalCommitter()
    started = time.time()

    exhaustive_rows: list[dict] = []
    for leaf_count in range(2, args.exhaustive_leaves + 1):
        stats = exhaustive_same_multiset(committer, leaf_count)
        exhaustive_rows.append(
            {
                "leaf_count": leaf_count,
                "candidates": stats.candidates,
                "crystal_unique_roots": stats.crystal_unique_roots,
                "crystal_collision_count": stats.crystal_collision_count,
                "sha8_unique_roots": stats.sha8_unique_roots,
                "sha8_collision_count": stats.sha8_collision_count,
                "first_crystal_collision": stats.first_crystal_collision,
                "first_sha8_collision": stats.first_sha8_collision,
            }
        )

    grinding_rows = [
        grinding_campaign(committer, rng, args.grind_leaves, args.max_attempts)
        for _ in range(args.campaigns)
    ]

    no_hit_attempts = [row["attempts"] for row in grinding_rows if not row["hit"]]
    result = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seed": args.seed,
        "parameters": {
            "exhaustive_leaves": args.exhaustive_leaves,
            "grind_leaves": args.grind_leaves,
            "campaigns": args.campaigns,
            "max_attempts": args.max_attempts,
        },
        "elapsed_seconds": round(time.time() - started, 3),
        "verdict": summarize_verdict(exhaustive_rows, grinding_rows),
        "exhaustive": exhaustive_rows,
        "grinding_campaigns": grinding_rows,
        "no_hit_attempts_mean": statistics.mean(no_hit_attempts) if no_hit_attempts else None,
    }

    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "adversarial_grinding_latest.json"
    md_path = output_dir / "adversarial_grinding_latest.md"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_markdown(result, md_path)
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "verdict": result["verdict"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
