# Crystal DeFi Structural Baseline Harness

Generated: `2026-06-10T18:12:38Z`

## Summary

This harness compares Crystal to same-query structural baselines. Domain-separated Merkle commits to shape and order; sorted baselines intentionally discard them.

## Leaves 2

Candidates: `2`

| Commitment | Unique roots | Collisions | Detects all variants |
|---|---:|---:|---|
| `crystal_8_byte` | `2` | `0` | `True` |
| `domain_merkle_sha256` | `2` | `0` | `True` |
| `ordered_flat_sha256` | `2` | `0` | `True` |
| `sorted_multiset_sha256` | `1` | `1` | `False` |
| `sorted_merkle_set_sha256` | `1` | `1` | `False` |

## Leaves 3

Candidates: `12`

| Commitment | Unique roots | Collisions | Detects all variants |
|---|---:|---:|---|
| `crystal_8_byte` | `12` | `0` | `True` |
| `domain_merkle_sha256` | `12` | `0` | `True` |
| `ordered_flat_sha256` | `6` | `6` | `False` |
| `sorted_multiset_sha256` | `1` | `11` | `False` |
| `sorted_merkle_set_sha256` | `1` | `11` | `False` |

## Leaves 4

Candidates: `120`

| Commitment | Unique roots | Collisions | Detects all variants |
|---|---:|---:|---|
| `crystal_8_byte` | `120` | `0` | `True` |
| `domain_merkle_sha256` | `120` | `0` | `True` |
| `ordered_flat_sha256` | `24` | `96` | `False` |
| `sorted_multiset_sha256` | `1` | `119` | `False` |
| `sorted_merkle_set_sha256` | `1` | `119` | `False` |

## Leaves 5

Candidates: `1680`

| Commitment | Unique roots | Collisions | Detects all variants |
|---|---:|---:|---|
| `crystal_8_byte` | `1570` | `110` | `False` |
| `domain_merkle_sha256` | `1680` | `0` | `True` |
| `ordered_flat_sha256` | `120` | `1560` | `False` |
| `sorted_multiset_sha256` | `1` | `1679` | `False` |
| `sorted_merkle_set_sha256` | `1` | `1679` | `False` |

## Leaves 6

Candidates: `30240`

| Commitment | Unique roots | Collisions | Detects all variants |
|---|---:|---:|---|
| `crystal_8_byte` | `26702` | `3538` | `False` |
| `domain_merkle_sha256` | `30240` | `0` | `True` |
| `ordered_flat_sha256` | `720` | `29520` | `False` |
| `sorted_multiset_sha256` | `1` | `30239` | `False` |
| `sorted_merkle_set_sha256` | `1` | `30239` | `False` |

## Interpretation

- Domain-separated Merkle is the honest cryptographic baseline for structure-sensitive commitments.
- Sorted Merkle/set commitments are useful only when order and tree shape are intentionally out of scope.
- Crystal's sellable role is not cryptographic uniqueness; it is a compact structural signal and localization layer that can route expensive proofs.
