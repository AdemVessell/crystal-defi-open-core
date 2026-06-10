# Local Crystal Witness V1

Status: draft V1 witness format.

## Purpose

Recompute a posted Crystal root from a localized subtree root plus sibling
Crystal roots along the path to the global tree root.

This is a compact Crystal recomputation witness. It is not, by itself, a
cryptographic membership proof. Production use must pair it with a
domain-separated Merkle/SSZ/native-chain proof for the same localized path.

## Encoding

Solidity witness bytes:

```text
target root:       8 bytes
step count:        1 byte
repeated step:
  sibling side:    0x00 when sibling is right/current is left
                   0x01 when sibling is left/current is right
  sibling root:    8 bytes
```

Example for `root.L` in `((10,20),(30,40))`:

```text
target root: 038956ba36c62f1b
step count:  01
side:        00
sibling:     179566aa16d21b27
encoded:     0x038956ba36c62f1b0100179566aa16d21b27
length:      18 bytes
```

The compact verifier recomputes:

```text
fold(target_root, sibling_root) -> global Crystal root
```

## SDK Commands

```bash
python3 sdk/crystal_committer.py witness \
  --tree '((10,20),(30,40))' \
  --path root.L

python3 sdk/crystal_committer.py challenge-v1 \
  --claimed-tree '((10,20),(30,40))' \
  --observed-tree '(10,(20,(30,40)))'
```

The `challenge-v1` payload contains:

```text
payload_version: crystal-defi-challenge-v1-draft
localization
local_crystal_witnesses
local_merkle_proofs with Solidity proof bytes
claimed_commitment without full-tree calldata
observed_commitment without full-tree calldata
full_tree_calldata_included: false
```

## Contract Surface

`CrystalComponentVerifier` verifies the local Crystal and Merkle paths:

```text
commitAnchoredTree(bytes32 blockHash, uint256 treeIndex, bytes32 crystalRoot, bytes32 merkleRoot)
commitAnchoredTreeWithWindow(
  bytes32 blockHash,
  uint256 treeIndex,
  bytes32 crystalRoot,
  bytes32 merkleRoot,
  uint64 challengeWindowSeconds
)
finalizeAnchoredTree(bytes32 blockHash, uint256 treeIndex)
verifyCrystalPath(bytes witnessData, bytes32 expectedRoot)
verifyMerklePath(bytes32 targetHash, bytes proofData, bytes32 expectedMerkleRoot)
verifyLeafMerklePath(uint8 leafValue, bytes proofData, bytes32 expectedMerkleRoot)
verifyLocalizedPath(
  bytes crystalWitnessData,
  bytes32 expectedCrystalRoot,
  bytes32 targetMerkleHash,
  bytes merkleProofData,
  bytes32 expectedMerkleRoot
)
verifyLocalizedPathBinding(bytes crystalWitnessData, bytes merkleProofData)
submitCrystalPathConsistencyChallenge(bytes32 blockHash, uint256 treeIndex, bytes witnessData)
submitAnchoredLocalizedChallenge(
  bytes32 blockHash,
  uint256 treeIndex,
  bytes crystalWitnessData,
  bytes32 targetMerkleHash,
  bytes merkleProofData
)
resolveAnchoredLocalizedChallenge(bytes32 challengeId)
```

Current tests cover:

```text
single-step claimed witness
single-step observed witness
two-step witness
internal-node Merkle path
leaf Merkle path
combined localized Crystal and Merkle path verification
same localized path-depth and path-side binding
anchored per-tree commitment storage
anchored challenge-window opening
anchored commitment finalization after deadline
anchored localized challenge pending state
anchored commitment challenged state
anchored localized challenge resolution after response deadline
anchored commitment invalidation after resolved challenge
Merkle-anchor mismatch rejection
mismatch challenge marking
matching-root challenge rejection
trailing witness-data rejection
trailing Merkle-proof-data rejection
```

## Current Demo Evidence

```bash
python3 scripts/devnet_observatory_demo.py
```

Latest evidence:

```text
demo/results/devnet_observatory_latest.json
demo/results/devnet_observatory_latest.md
```

Current example:

```text
claimed_witness_encoded: 0x038956ba36c62f1b0100179566aa16d21b27
claimed_witness_encoded_length: 18
claimed_merkle_proof_encoded: 0x0100bbfe0762ecf04769e499b88b12ef2549fa065e6d0608eb154f66ca62e251ba80
claimed_merkle_proof_encoded_length: 34
localized_v1_proof_bytes: 84
challenge_tx_calldata_bytes: 324
challenge_gas_used: 358047
resolve_tx_calldata_bytes: 36
resolve_gas_used: 74891
localized_path_bound: true
posted_merkle_root: 0xee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e
anchored_status_after_commit_output: 1
anchored_status_after_submit_output: 2
anchored_status_after_resolve_output: 4
anchored_challenge_pending_record_output: 1
anchored_challenge_resolved_record_output: 2
full_tree_calldata_included: false
```

## Boundary

This V1 witness removes full-tree calldata from the Crystal recomputation path,
binds the expected Merkle root to a posted per-tree anchor, requires the Crystal
witness and Merkle proof to carry the same local path encoding, opens an
explicit challenge window, records a pending mismatch challenge, and invalidates
the bad anchored commitment only after the response window is advanced and the
challenge is resolved. It does not yet complete a production challenge game.

Remaining gates:

```text
same-transaction or same-leaf identity beyond local path encoding
sound counterproof semantics
gas and byte comparison against same-query Merkle/SSZ baselines
production finality and economic-consequence integration
```
