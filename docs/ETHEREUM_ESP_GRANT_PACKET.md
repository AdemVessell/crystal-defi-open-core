# Crystal DeFi Ethereum ESP Grant Packet

Status: draft grant packet.

## Project Name

Crystal DeFi Observatory: Hash-Anchored Structural Divergence Monitoring for
Ethereum Builders

## One-Line Summary

An open-source research and tooling project that uses Crystal structural roots
to cheaply detect and localize transaction-tree divergence, while using
standard SHA/Merkle anchors for adversarial binding.

## Grant Fit

Best-fit Ethereum Foundation ESP framing:

```text
builder tooling
monitoring tooling
data-driven research
infrastructure research
security-adjacent proof and challenge tooling
```

Do not pitch this as:

```text
new blockchain
standalone fraud-proof system
Merkle replacement
production DeFi security product
token or commercial app
```

The ESP applicant guidance says supported work should strengthen Ethereum's
foundations, enable builders, and be free/open-source public goods. It also
asks proposals to provide clear methodology, timeline, and deliverables.

References:

```text
https://esp.ethereum.foundation/applicants
https://esp.ethereum.foundation/applicants/wishlist
https://esp.ethereum.foundation/applicants/open-rounds
https://esp.ethereum.foundation/applicants/rfp
https://esp.ethereum.foundation/applicants/office-hours/apply
https://blog.ethereum.org/2025/11/03/new-esp-grants
```

Current route note checked on 2026-06-11:

```text
Open rounds currently show no active rounds.
The best current route is Wishlist or ESP Office Hours / Project Feedback.
The Glamsterdam Wishlist may be adjacent if scoped as monitoring tooling,
impact-analysis tooling, or data-driven research.
The Neutral DeFi Risk Intelligence Aggregator RFP is not a direct fit unless
CrystalDefi pivots into neutral risk-feed aggregation.
```

## Critical License Gate

This open-core export is Apache-2.0.

The grant-funded core is split here as a truly open-source public-goods package. This workspace now has a reproducible
export script for that boundary:

```bash
python3 scripts/export_open_core.py --force
```

Generated package:

```text
../crystal-defi-open-core
```

Recommended split:

```text
crystal-defi-open-core/
  SPDX: Apache-2.0
  includes:
    Python SDK core
    component-table verifier
    research harnesses
    watcher/demo
    docs, public report, and reviewer packet
    vendored forge-std test dependency under its own license files

product/commercial lanes
  may remain BUSL or proprietary if kept outside the grant-funded scope
```

This generated export is the proposed resolved boundary. Do not submit until
ownership/legal approval confirms that this Apache-2.0 split is acceptable.

## Technical Thesis

Crystal is not the adversarial commitment.

The correct architecture is:

```text
transaction tree
  -> Crystal structural root
  -> Crystal localizes suspicious structure
  -> domain-separated Merkle/SHA anchor binds the tree
  -> minimal proof verifies the challenged path
  -> observer/watcher reports divergence
```

In one sentence:

```text
Crystal localizes; hash anchors prove.
```

## Current Evidence

Runnable commands:

```bash
forge test -vvv
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
python3 research/adversarial_grinding_harness.py
python3 research/baseline_structural_harness.py
python3 research/proof_payload_baseline_harness.py
python3 research/component_table_equivalence.py
python3 scripts/devnet_observatory_demo.py
python3 scripts/export_open_core.py --force
python3 scripts/grant_readiness_check.py
```

Current local results:

```text
Foundry: 67 tests passed
component table equivalence: 512 bytes reconstruct 524288 full-table bytes
adversarial harness: Crystal collisions found at 5 and 6 leaves
baseline harness: domain-separated Merkle detects all variants through 6 leaves
V0 challenge payload: localizes root.L node-type mismatch and includes local Merkle proofs
V1 draft challenge payload: excludes full-tree calldata and carries an 18-byte local Crystal witness plus a 34-byte Merkle proof for root.L
V1 byte baseline: leaf-depth local paths measure 126 bytes at 4 leaves, 336 bytes at 128 leaves, and 420 bytes at 512 leaves; the current demo's internal-node path is 84 bytes
devnet demo: compact verifier deployed, anchored tree posted, same-local-path Crystal+Merkle proof verified, localized challenge submitted as pending, response window advanced, challenge resolved, bad commitment invalidated
devnet gas/calldata: anchored challenge submit measured 324 calldata bytes and 358047 gas; resolution measured 36 calldata bytes and 74891 gas on local Anvil
open core export: Apache-2.0 sibling package generated with manifest
```

Latest demo evidence:

```text
demo/results/devnet_observatory_latest.json
demo/results/devnet_observatory_latest.md
```

## Why This Is Useful To Ethereum

Ethereum already has strong cryptographic primitives. The useful contribution
is not another hash.

The useful contribution is an observer-side structural layer:

```text
cheap divergence signal
compact table-driven structural fingerprint
localization of where two trees disagree
tooling for routing expensive proof work
empirical baselines showing exactly where Crystal helps or loses
```

Potential users:

```text
L2 and rollup researchers comparing challenge payload designs
tooling teams exploring proof routing and monitoring
client/tooling researchers studying upgrade impact on verification costs
block explorers or indexers that want structural divergence warnings
protocol researchers evaluating non-cryptographic structural signals
```

## Proposed Scope Of Work

### Milestone 1 - Open Core And Reproducible Baselines

Deliverables:

```text
open-source SDK and harness package
Foundry component verifier tests
adversarial collision report
Merkle/SSZ/sparse proof-size baseline report
public claim-boundary document
```

Success criteria:

```text
fresh checkout runs all Python harnesses and Foundry tests
all outputs are reproducible
claims are bounded to structural monitoring and localization
```

### Milestone 2 - Minimal Localizing Challenge Payload

Deliverables:

```text
draft V1 challenge payload without full-tree calldata
local Crystal witness for first differing path and contract verifier
domain-separated Merkle proof for the same path
contract verifier for localized Merkle path proof
gas and byte comparison against Merkle/SSZ baselines
```

Success criteria:

```text
contract verifies the local Crystal challenged path
contract verifies the localized Merkle path proof
challenge object binds the expected Merkle root to a posted per-tree anchor
payload size is measured against same-query baselines
no unanchored Crystal security claim is made
```

### Milestone 3 - Ethereum Devnet / Observatory Demo

Deliverables:

```text
local Ethereum devnet deployment script
watcher service that posts and checks per-tree roots
demo run with normal and divergent tree submissions
public dashboard or CLI readout
```

Success criteria:

```text
one command starts the demo
one command produces a divergence report
contract and watcher agree on the challenged path
```

### Milestone 4 - Public Report And Handoff

Deliverables:

```text
technical report
limitations and negative results section
grant closeout post
reusable public datasets/fixtures
future-work list for EF teams and ecosystem builders
```

Success criteria:

```text
all grant-funded outputs are public
all claims are evidence-backed
reviewers can reproduce the demo and baseline numbers
```

## What We Should Ask For

Ask for support to turn the current prototype into an open-source Ethereum
public-goods research/tooling artifact.

Do not ask for support to commercialize a DeFi product.

Suggested proposal title:

```text
Hash-Anchored Structural Divergence Monitoring for Ethereum Transaction Trees
```

Suggested short ask:

```text
Funding to produce an open-source SDK, Solidity verifier, watcher, baseline
harnesses, minimal challenge payload, and public report for structural
divergence monitoring in Ethereum-adjacent proof/challenge workflows.
```

## Open Risks

```text
Crystal collisions mean unanchored roots cannot be commitments.
V0 payload still carries full tree calldata.
V1 draft removes full-tree calldata for localized verification and binds the expected Merkle root to a posted per-tree anchor.
Grant-funded open core is generated as Apache-2.0, pending legal/ownership approval before submission.
The exact Wishlist/RFP fit should be confirmed through Wishlist review or Office Hours before submission.
The prototype now has same-local-path binding, active/challenged/finalized/invalidated commitment states, and pending-to-resolved localized challenge timing, but sound counterproof semantics and economic consequences are not specified yet.
```

## Submission Readiness Checklist

```text
[x] Decide open-source license split: Apache-2.0 open-core export.
[x] Create export packet for grant-funded open core.
[x] Add draft V1 local Crystal witness without full-tree calldata.
[x] Add on-chain Merkle path verification for the V1 localized proof.
[x] Bind Crystal and Merkle proof bytes to the same localized path encoding.
[x] Bind V1 expected Merkle roots to posted per-tree anchors.
[x] Add basic challenge window, finalization, and invalidation states.
[x] Add pending localized challenge timing and response-deadline resolution.
[x] Add initial V1 byte and local-devnet gas measurements.
[x] Draft sound counterproof semantics boundary.
[x] Add local devnet deployment/demo.
[x] Add clean public report.
[x] Add reviewer packet.
[ ] Confirm Wishlist route or request ESP Office Hours / Project Feedback.
[ ] Specify production economic-consequence integration.
```
