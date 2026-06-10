# Anchored Challenge Payload V0

Status: prototype format.

## Purpose

Carry enough information to report and localize a structural disagreement while
binding both candidate trees to cryptographic anchors.

This is not yet a minimal proof payload. V0 carries full encoded trees inside
the `claimed` and `observed` packages.

## Payload Shape

```text
payload_version: crystal-defi-challenge-v0
challenge_type: structural_divergence
same_sorted_leaves: boolean
different_crystal_root: boolean
different_anchor: boolean
heads_that_differ: integer
localization:
  path: root / root.L / root.R / ...
  difference: none / leaf_value_mismatch / node_type_mismatch
local_merkle_proofs:
  claimed:
    path
    node_type
    leaf_value
    node_hash_sha256
    merkle_root_sha256
    siblings_from_node_to_root
    proof_bytes_minimal
  observed:
    path
    node_type
    leaf_value
    node_hash_sha256
    merkle_root_sha256
    siblings_from_node_to_root
    proof_bytes_minimal
claimed:
  anchored commitment package
observed:
  anchored commitment package
boundary:
  human-readable proof boundary
```

Each commitment package includes:

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

## Current Command

```bash
python3 sdk/crystal_committer.py challenge \
  --claimed-tree '((10,20),(30,40))' \
  --observed-tree '(10,(20,(30,40)))'

python3 sdk/crystal_committer.py challenge-v1 \
  --claimed-tree '((10,20),(30,40))' \
  --observed-tree '(10,(20,(30,40)))'
```

Draft V1 local-witness format:

```text
docs/LOCAL_CRYSTAL_WITNESS_V1.md
```

## Current On-Chain Demo

```bash
python3 scripts/devnet_observatory_demo.py
```

Latest evidence:

```text
demo/results/devnet_observatory_latest.json
demo/results/devnet_observatory_latest.md
research/results/proof_payload_baselines_latest.json
research/results/proof_payload_baselines_latest.md
```

The demo deploys `CrystalComponentVerifier` to Anvil, initializes compact
component tables, posts an intentionally wrong per-tree root, submits the draft
V1 local Crystal path-witness consistency challenge, and verifies that the
contract binds the Crystal witness and Merkle proof to the same local path,
records the localized mismatch as pending, advances the response window,
resolves the mismatch, and invalidates the bad anchored commitment only after
resolution.

## Current Boundary

V0 proves less than a production challenge game:

```text
It localizes a structural disagreement.
It binds both full trees to SHA-256 anchors.
It includes local Merkle proofs for the first differing path.
It still carries full encoded trees for prototype verification.
It does not slash or finalize any economic consequence.
```

## Next Format Gate

V1 draft now replaces full-tree calldata in the Crystal recomputation path with:

```text
localized Crystal witness
domain-separated Merkle or SSZ proof for the affected path
posted per-tree root
computed conflicting root
table commitment
explicit challenge-window and commitment-state transition
```

Completed in the draft:

```text
local Crystal witness
contract verification for local Crystal path recomputation
contract verification for localized Merkle path recomputation
combined localized Crystal and Merkle path verifier
same localized path-depth and path-side binding
posted per-tree Merkle anchor binding
anchored challenge-window opening
anchored commitment finalization
anchored commitment challenged state
pending localized mismatch state
response-deadline challenge resolution
anchored commitment invalidation after resolved mismatch
initial V1 byte baselines
initial local-devnet gas measurements
draft challenge-v1 SDK payload without full-tree calldata
devnet challenge using the local witness
```

Still required:

```text
sound counterproof semantics
production finality and economic-consequence integration
broader gas comparison against same-query Merkle/SSZ baselines
```
