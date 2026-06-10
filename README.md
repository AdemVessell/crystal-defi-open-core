# Crystal DeFi Open Core - Structural Divergence Layer

Apache-2.0 grant-facing export of the Crystal DeFi prototype.


Non-associative algebraic folding for compact transaction-tree divergence
checks. Crystal roots are useful as a cheap structural signal and localization
surface; they are not standalone adversarial commitments.

## Current Scientific Status

The first adversarial same-multiset harness found Crystal root collisions at
5 and 6 leaves:

```text
5 leaves: 1680 candidates, 1570 unique Crystal roots, 110 collisions
6 leaves: 30240 candidates, 26702 unique Crystal roots, 3538 collisions
SHA-256 truncated to 8 bytes: 0 collisions in the same exhaustive runs
Random grinding: 0 hits across 600000 candidate attempts
```

The same-query baseline harness found that domain-separated SHA-256 Merkle roots
detected every enumerated structural variant through 6 leaves, while sorted
Merkle/set commitments intentionally collapsed all same-multiset variants.

Interpretation:

```text
Crystal should be framed as a structural divergence monitor and localization
layer. Production security must be anchored by cryptographic hashes, signatures,
Merkle/SSZ-style proofs, or native-chain commitments.
```

Run the current gate:

```bash
python3 research/adversarial_grinding_harness.py
python3 research/baseline_structural_harness.py
python3 research/proof_payload_baseline_harness.py
```

Latest output:

```text
research/results/adversarial_grinding_latest.json
research/results/adversarial_grinding_latest.md
research/results/structural_baselines_latest.json
research/results/structural_baselines_latest.md
research/results/proof_payload_baselines_latest.json
research/results/proof_payload_baselines_latest.md
```

## Supported Claim

Crystal can cheaply distinguish many same-leaf/different-structure transaction
trees and can provide a compact signal for where expensive proof work should be
spent.

## Non-Claims

This repository does not currently prove:

```text
cryptographic binding from an unanchored Crystal root
fraud-proof soundness against adversaries
second-preimage resistance
consensus, finality, or data availability
gas superiority against a domain-separated Merkle or SSZ proof verifier
production-safe slashing logic
```

## Production Design Rule

```text
Crystal localizes; hash anchors prove.
```

The intended production shape is:

```text
transaction tree
  -> Crystal structural root and witness/localization data
  -> domain-separated hash/Merkle/native-chain anchor
  -> challenge path only when Crystal or observer agreement flags divergence
```

## Project Structure

```
crystal-defi/
├── contracts/
│   ├── CrystalVerifier.sol              — full-table prototype
│   └── CrystalComponentVerifier.sol     — compact component-table prototype
├── test/
│   ├── CrystalVerifier.t.sol              — full-table compatibility tests
│   └── CrystalComponentVerifier.t.sol     — compact verifier tests
├── script/
│   └── Deploy.s.sol           — Deployment + table initialization
├── scripts/
│   ├── devnet_observatory_demo.py
│   ├── export_open_core.py
│   └── grant_readiness_check.py
├── sdk/
│   └── crystal_committer.py   — Python SDK + CLI
├── watcher/
│   └── crystal_watcher.py     — Off-chain monitoring service + REST API
├── research/
│   ├── adversarial_grinding_harness.py
│   ├── baseline_structural_harness.py
│   ├── component_table_equivalence.py
│   └── proof_payload_baseline_harness.py
├── docs/
│   ├── ANCHORED_CHALLENGE_PAYLOAD_V0.md
│   └── PRODUCTION_HARDENING_PLAN.md
└── foundry.toml               — Foundry configuration
```

## Quick Start

### SDK
```bash
# Commit a tree
python sdk/crystal_committer.py commit --tree '((10,20),(30,40))'

# Detect structural divergence
python sdk/crystal_committer.py compare --tree-a '((10,20),(30,40))' --tree-b '(10,(20,(30,40)))'

# Export tables for contract deployment
python sdk/crystal_committer.py export-tables --output tables.json

# Export compact component tables for the component verifier
python sdk/crystal_committer.py export-components --output component_tables.json

# Emit the production-facing Crystal + anchor package
python sdk/crystal_committer.py package --tree '((10,20),(30,40))'

# Emit an anchored structural-divergence challenge payload
python sdk/crystal_committer.py challenge \
  --claimed-tree '((10,20),(30,40))' \
  --observed-tree '(10,(20,(30,40)))'

# Emit a local Crystal path witness
python sdk/crystal_committer.py witness \
  --tree '((10,20),(30,40))' \
  --path root.L

# Emit a draft V1 challenge payload without full-tree calldata
python sdk/crystal_committer.py challenge-v1 \
  --claimed-tree '((10,20),(30,40))' \
  --observed-tree '(10,(20,(30,40)))'

# Check compact tables reconstruct the full SDK tables
python research/component_table_equivalence.py
```

### Watcher Service
```bash
python watcher/crystal_watcher.py --port 8420

# POST /commit, /verify, /compare, /challenge, /challenge-v1, /witness, /verify-block, /encode
# GET  /health, /stats
```

### Smart Contract
```bash
forge install
forge test
forge script script/Deploy.s.sol --rpc-url $RPC_URL --broadcast
```

### Local Devnet Observatory Demo
```bash
python3 scripts/devnet_observatory_demo.py
```

Latest demo evidence:

```text
demo/results/devnet_observatory_latest.json
demo/results/devnet_observatory_latest.md
```

The demo starts Anvil, deploys `CrystalComponentVerifier`, initializes the
compact component tables, posts an intentionally wrong per-tree root, submits a
local Crystal path-witness consistency challenge, records it as pending, advances
the response window, resolves the challenge, and verifies that the anchored
commitment is invalidated only after resolution. The latest local run also
records the V1 local proof bytes, submit/resolve calldata bytes, and transaction
gas in the demo result files.

### Grant-Facing Open Core Export
```bash
python3 scripts/export_open_core.py --force
```

This generates a sibling Apache-2.0 package:

```text
../crystal-defi-open-core
```

Use the source lane for ongoing private/prototype work. Use the generated open
core package as the public-goods grant boundary. The export vendors
`lib/forge-std` under its own license files so the Foundry tests run in the
generated package without an extra dependency bootstrap.

Contract status: tested prototype. `CrystalVerifier.sol` is the original
full-table prototype. `CrystalComponentVerifier.sol` is the production-direction
compact component-table prototype. Foundry currently passes 67 tests. The
contract now has per-tree commitments and non-fraud challenge entry points.
Prototype slashing has been neutralized. Before live-chain use, the lane still
needs sound counterproof semantics, finality integration, and any economic
consequences specified. V0 challenge payloads still carry full-tree
calldata. Draft V1 payloads carry local Crystal witnesses and local Merkle
proofs for the first differing path without full-tree calldata. The compact
verifier now checks both the local Crystal path and Merkle path, binds the
Merkle root through an anchored per-tree commitment, requires the Crystal
witness and Merkle proof to describe the same local path, opens an explicit
challenge window, finalizes unchallenged commitments after the deadline, records
anchored localized mismatches as pending, and invalidates bad commitments only
after the response window is resolved.
Initial V1 byte baselines and local-devnet gas measurements are recorded under
`research/results/` and `demo/results/`; broader gas comparisons against
same-query Merkle/SSZ baselines remain future hardening work.

Current reviewer-facing planning and handoff artifacts:

```text
docs/CRYSTALDEFI_LONG_TERM_EXECUTION_PLAN.md
docs/PUBLIC_TECHNICAL_REPORT.md
docs/REVIEWER_PACKET.md
docs/FRESH_CLONE_VERIFICATION.md
docs/PRIOR_ART_POSITIONING_APPENDIX.md
docs/THIRD_PARTY_VERIFICATION_REQUEST.md
docs/COUNTERPROOF_SEMANTICS_V0.md
docs/CHALLENGE_GAME_STATE_MACHINE_V0.md
docs/TESTNET_READINESS_CHECKLIST.md
docs/ESP_OFFICE_HOURS_PREP.md
```

## License

Source lane: Apache-2.0.

Grant-facing open core export: Apache-2.0 via `scripts/export_open_core.py`.
