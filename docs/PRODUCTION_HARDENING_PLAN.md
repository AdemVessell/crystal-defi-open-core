# Crystal DeFi Production Hardening Plan

Status: active hardening plan after the first adversarial collision gate.

## Plain Goal

Build Crystal DeFi as a structural divergence and localization layer for
transaction trees, not as an unanchored cryptographic commitment scheme.

The production rule is:

```text
Crystal localizes; hash anchors prove.
```

## Gate 1 - Adversarial Root Behavior

Current result:

```text
research/results/adversarial_grinding_latest.md
research/results/structural_baselines_latest.md
research/results/proof_payload_baselines_latest.md
```

Observed:

```text
5 leaves: 1680 same-multiset candidates, 110 Crystal collisions
6 leaves: 30240 same-multiset candidates, 3538 Crystal collisions
SHA-256 truncated to 8 bytes: 0 collisions in the same exhaustive runs
Random grinding: 0 hits across 600000 candidate attempts
Domain-separated Merkle: 0 collisions through 6 leaves in the baseline harness
Ordered flat digest: detects leaf order but not tree shape
Sorted Merkle/set commitments: intentionally discard order and tree shape
V0 Crystal anchor package still ships full tree calldata
Draft V1 removes full-tree calldata for localized Crystal and Merkle path verification
```

Consequence:

```text
Unanchored Crystal roots are not adversarial commitments.
```

Surviving role:

```text
cheap structural signal
local divergence detector
proof-routing hint
compact observer agreement surface
```

Next measurements:

```text
exhaustive leaves 7 if runtime is acceptable
repeat with randomized leaf values and repeated seeds
measure collision families by shape class
measure collision rate by head count: 1, 2, 4, 8, 16, 32
measure anchor construction: Crystal root + SHA-256 tree digest
```

## Gate 2 - Baselines

Crystal must be compared against baselines that answer the same question.

Required baselines:

```text
domain-separated Merkle tree
RFC-6962-style leaf/node prefix hash tree
SSZ-style merkleization where applicable
sparse Merkle tree for membership/update proofs
BLAKE3 or SHA-256 canonical tree digest
sorted Merkle set commitment, explicitly labeled as order-discarding
flat hash/list digest, explicitly labeled as structurally weak
```

The correct comparison is not a Uniswap swap. The useful comparison is a
same-query proof verifier:

```text
Can this proof detect or localize the same structural disagreement?
How many bytes cross the wire?
How much gas verifies the same claim?
What adversary is covered?
```

## Gate 3 - Contract Hardening

The current Solidity contracts are prototypes. The compact verifier now has:

```text
512-byte component-table initialization
strict full-consumption checks for tree calldata
per-tree root commitments
consistency challenges bound to the posted root being challenged
local Crystal path-witness verification
path-witness consistency challenges without full-tree calldata
localized Merkle path verification
combined localized Crystal and Merkle path verification
same localized path-depth and path-side binding
anchored per-tree Merkle-root commitments
anchored challenge-window opening
anchored commitment finalization
anchored commitment challenged state
anchored localized challenge pending state
anchored localized challenge response timeout
anchored localized challenge resolution after response deadline
anchored commitment invalidation
non-fraud challenge naming
no slashing or economic penalty
```

Before live use, the lane still needs:

```text
explicit leaf-byte bounds checks
maximum tree size/depth policy
same-leaf or same-transaction identity beyond local path encoding
sound counterproof semantics and production finality lifecycle
broader gas measurements across deeper local paths and same-query Merkle/SSZ baselines
```

The current full-table storage shape is also not production-grade:

```text
8 heads * 256 * 256 bytes = 524288 bytes of table data
```

The Python table generator is actually component-decomposed:

```text
8 heads * 4 components * 16 entries
```

So the production verifier should store compact component tables and compute
the 8-bit fold result from four 2-bit component lookups. That is the right next
contract direction.

Measured equivalence check:

```bash
python3 research/component_table_equivalence.py
```

Current result:

```text
ok: true
component bytes: 512
full table bytes: 524288
```

## Gate 4 - Anchor Construction

Minimum production commitment package:

```text
crystal_root_8b
tree_anchor_sha256_32b or chain-native Merkle root
domain_separator
tree_encoding_version
leaf_mapping_version
table_or_component_table_commitment
```

Crystal is allowed to decide where to inspect. The anchor decides whether a
claim is cryptographically bound.

Current SDK command:

```bash
python3 sdk/crystal_committer.py package --tree '((10,20),(30,40))'
python3 sdk/crystal_committer.py challenge \
  --claimed-tree '((10,20),(30,40))' \
  --observed-tree '(10,(20,(30,40)))'
python3 sdk/crystal_committer.py challenge-v1 \
  --claimed-tree '((10,20),(30,40))' \
  --observed-tree '(10,(20,(30,40)))'
python3 sdk/crystal_committer.py witness \
  --tree '((10,20),(30,40))' \
  --path root.L
```

Standalone payload spec:

```text
docs/ANCHORED_CHALLENGE_PAYLOAD_V0.md
docs/LOCAL_CRYSTAL_WITNESS_V1.md
```

Current package fields:

```text
encoding_version
leaf_mapping_version
anchor_domain
table_domain
table_format
table_commitment_sha256
crystal_root
crystal_root_hex
anchor_sha256
merkle_root_sha256
calldata
calldata_length
structure
leaves
depth
trace_lengths
```

Current challenge payload fields:

```text
payload_version
challenge_type
same_sorted_leaves
different_crystal_root
different_anchor
heads_that_differ
localization
local_merkle_proofs
local_crystal_witnesses
encoded Merkle proof bytes for Solidity verification
claimed package
observed package
boundary
```

## Gate 5 - Watcher Hardening

The watcher should produce:

```text
computed Crystal root
computed anchor digest
claimed Crystal root
claimed anchor digest
divergence class
minimal localizing witness
calldata/proof payload for the anchor verifier
```

The API should stop using `fraud` for raw Crystal divergence unless the payload
also includes a valid anchor proof.

Current watcher status:

```text
/commit and /encode return the anchored package
/compare returns structural_divergence plus both anchor digests
/challenge returns the anchored challenge payload
/challenge-v1 returns a draft local-witness payload without full-tree calldata
/witness returns a local Crystal path witness
deprecated fraud-named compatibility fields remain for now
```

## Gate 6 - External Positioning

Use this language:

```text
structural divergence monitor
cheap localization layer
observer agreement surface
hash-anchored challenge router
```

Avoid this language until proven:

```text
fraud detection
fraud proof
cryptographic verification
blockchain security
100 percent adversarial detection
gas superiority over Merkle proofs
```

## Immediate Build Order

1. Done: add `research/adversarial_grinding_harness.py`.
2. Done: add `contracts/CrystalComponentVerifier.sol` beside the full-table prototype.
3. Done: add SDK `anchor_sha256` output and compact `export-components`.
4. Done: rework watcher output around `structural_divergence` plus `anchor_sha256`.
5. Done: add `research/component_table_equivalence.py`.
6. Done: install Foundry and run the Solidity suite.
7. Done: add `research/baseline_structural_harness.py`.
8. Done: add Foundry tests for the compact component verifier and compare its roots against the SDK.
9. Done: add an anchored commitment package object to SDK/watcher outputs.
10. Done: add non-fraud ABI entry points while keeping deprecated wrappers.
11. Done: add proof-size baselines for Merkle/SSZ/sparse-Merkle payloads.
12. Done: neutralize simplified slashing in the prototype challenge path.
13. Done: add per-tree commitments and per-tree consistency challenge.
14. Done: add local Merkle proofs for the first differing path in challenge payloads.
15. Done: add an Apache-2.0 open-core export boundary for grant-facing work.
16. Done: add a local Anvil devnet demo that marks a bad posted root as challenged.
17. Done: add a conservative grant-readiness gate for tests, export, and demo evidence.
18. Done: add draft V1 local Crystal witnesses without full-tree calldata.
19. Done: add compact verifier path-witness verification and challenge entry point.
20. Done: upgrade the local devnet demo to challenge with an 18-byte path witness.
21. Done: add localized Merkle path verification and combined Crystal+Merkle verifier.
22. Done: bind Crystal and Merkle proof bytes to the same localized path encoding.
23. Done: bind expected Merkle roots to posted per-tree anchors.
24. Done: add anchored localized challenge resolution state.
25. Done: add anchored challenge windows, finalization, and invalidation states.
26. Done: add pending localized challenge state and response-deadline resolution.
27. Done: add initial anchored V1 byte baselines and local-devnet gas measurements.
28. Done: add four-week parallel execution, public report, reviewer packet, counterproof boundary, and state-machine docs.
29. Done: expand proof-payload byte baselines through 512 leaves.
30. Next: specify production-grade counterproof implementation and finality integration.
31. Next: expand gas measurements across deeper paths and same-query Merkle/SSZ baselines.
