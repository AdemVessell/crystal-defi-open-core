# CrystalDefi 4-Week Parallel Execution Plan

Status: active execution control document.

## Summary

Run three lanes in parallel for four weeks:

```text
Grant Lane: package the reviewer-facing public artifact.
Science Lane: specify the adversarial model and counterproof semantics.
Protocol Lane: specify the challenge game and testnet readiness path.
```

The shared claim boundary is:

```text
Crystal localizes; hash/Merkle anchors prove.
```

No lane may claim that an unanchored Crystal root is a cryptographic
commitment, a Merkle replacement, a production fraud proof, or gas-superior to
Merkle/SSZ proofs without matching evidence.

## Current Baseline

Already present:

```text
Apache-2.0 open-core export
compact component-table verifier
anchored per-tree Crystal and Merkle commitments
same-local-path Crystal witness and Merkle proof binding
challenge window
pending localized challenge state
response-deadline resolution
local Anvil devnet evidence
grant-readiness gate
```

Current unresolved gates:

```text
sound counterproof semantics
same-leaf or same-transaction identity beyond local path encoding
broader same-query gas and byte comparisons
production finality and economic consequences
public testnet readiness
independent security review
```

## Week 1 - Grant Lane

Deliver:

```text
docs/PUBLIC_TECHNICAL_REPORT.md
docs/REVIEWER_PACKET.md
fresh source evidence
fresh open-core export evidence
ESP route note
```

Acceptance:

```text
the report cites concrete result files
the reviewer packet gives exact commands
the ESP packet says Wishlist or Office Hours unless a specific RFP fit is confirmed
the DeFi risk-intelligence RFP is not forced as a fit
```

## Week 2 - Science Lane

Deliver:

```text
docs/COUNTERPROOF_SEMANTICS_V0.md
expanded proof payload baselines through 512 leaves
explicit challenger proof boundary
explicit unresolved counterproof boundary
```

Acceptance:

```text
fake respondent counterproofs are rejected in writing
valid defense types are named but not overclaimed as implemented
the benchmark result includes 4,8,16,32,64,128,256,512 leaves
```

## Week 3 - Protocol Lane

Deliver:

```text
docs/CHALLENGE_GAME_STATE_MACHINE_V0.md
docs/TESTNET_READINESS_CHECKLIST.md
tree/depth/leaf policy draft
watcher expectations
economic consequence options
```

Acceptance:

```text
state transitions are documented exactly as the contract exposes them
invalid/malformed proof behavior is specified
Sepolia deployment is explicitly blocked until credentials and funding are provided
economic consequences remain future choices, not implemented claims
```

## Week 4 - Integration Lane

Deliver:

```text
final reviewer packet refresh
final public report refresh
source validation
open-core validation
Office Hours / project feedback prep note
```

Acceptance:

```text
forge tests pass in source and open core
Python compile passes in source and open core
devnet demos pass in source and open core
grant-readiness gates pass in source and open core
open-core boundary scan reports ok: true
cache/out/__pycache__ artifacts are removed after validation
```

## Validation Commands

Source lane:

```bash
forge test -vv
python3 -m py_compile sdk/crystal_committer.py watcher/crystal_watcher.py research/*.py scripts/*.py
python3 research/proof_payload_baseline_harness.py
python3 scripts/devnet_observatory_demo.py
python3 scripts/grant_readiness_check.py
```

Open-core lane:

```bash
python3 scripts/export_open_core.py --force
cd ../crystal-defi-open-core
forge test -vv
python3 -m py_compile sdk/crystal_committer.py watcher/crystal_watcher.py research/*.py scripts/*.py
python3 scripts/devnet_observatory_demo.py
python3 scripts/grant_readiness_check.py
run `python3 scripts/check_open_core_boundary.py` against the exported tree
```

The boundary scan is expected to report `ok: true`.

## ESP Route

As of the current ESP pages checked on 2026-06-11:

```text
open rounds: none active
best route: Wishlist or Office Hours / Project Feedback
possible adjacent Wishlist: Glamsterdam preparation, only if framed as monitoring/data-driven research
not a direct fit: Neutral DeFi Risk Intelligence Aggregator RFP
```

Use these URLs in reviewer-facing material:

```text
https://esp.ethereum.foundation/applicants
https://esp.ethereum.foundation/applicants/open-rounds
https://esp.ethereum.foundation/applicants/wishlist
https://esp.ethereum.foundation/applicants/rfp
https://esp.ethereum.foundation/applicants/office-hours/apply
```

## Stop Conditions

Stop and revise before submission if any public artifact says or implies:

```text
Crystal replaces Merkle proofs.
Crystal roots are adversarial commitments without hash/Merkle/native anchors.
The current challenge game is production fraud-proof sound.
The system has production slashing or bonding.
The current benchmarks prove gas superiority.
The DeFi risk-intelligence RFP is a direct fit without a product pivot.
```
