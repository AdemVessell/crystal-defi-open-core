# CrystalDefi Public Technical Report

Status: reviewer-facing draft.

## Abstract

CrystalDefi is an open-source research and tooling prototype for structural
divergence monitoring in Ethereum-adjacent transaction trees. It uses compact
Crystal structural roots to localize suspicious tree differences, while relying
on standard hash/Merkle anchors for adversarial binding.

The core design rule is:

```text
Crystal localizes; hash/Merkle anchors prove.
```

## Problem

Ethereum already has strong cryptographic commitments. The remaining tooling
problem explored here is narrower:

```text
When two transaction-tree views disagree, can a cheap structural signal help
route the expensive proof work to the local path where the disagreement occurs?
```

Crystal roots are useful as a structural signal because the non-associative fold
changes when tree shape changes. They are not secure commitments by themselves.

## Architecture

The current prototype has four layers:

```text
SDK: builds Crystal roots, hash/Merkle anchors, witnesses, and challenge payloads.
Solidity verifier: verifies compact component-table folds and localized Merkle paths.
Watcher: emits anchored packages and local divergence payloads.
Research harnesses: measure collisions and same-query proof payload sizes.
```

The challenge path is:

```text
sequencer/sidecar posts Crystal root + Merkle root
challenger submits same-path Crystal witness + Merkle proof
contract verifies the Merkle proof reaches the posted Merkle root
contract verifies the Crystal witness recomputes a conflicting Crystal root
contract records PendingMismatch and marks the anchored tree Challenged
after the response window, resolver marks ResolvedMismatch and Invalidated
```

## Current Evidence

Reproducible evidence files:

```text
research/results/adversarial_grinding_latest.json
research/results/adversarial_grinding_latest.md
research/results/structural_baselines_latest.json
research/results/structural_baselines_latest.md
research/results/proof_payload_baselines_latest.json
research/results/proof_payload_baselines_latest.md
demo/results/devnet_observatory_latest.json
demo/results/devnet_observatory_latest.md
```

Current local findings:

```text
Foundry suite: 67 tests passed
component table equivalence: 512 bytes reconstruct 524288 full-table bytes
Crystal same-multiset collisions found at 5 and 6 leaves
domain-separated Merkle detected all tested structural variants through 6 leaves
V1 challenge path excludes full-tree calldata
expanded V1 byte baseline covers 4 through 512 leaves
512-leaf V1 local path baseline: 420 bytes
current internal-node demo proof: 84 bytes
challenge submit calldata: 324 bytes
challenge submit gas on local Anvil: 358047
challenge resolve calldata: 36 bytes
challenge resolve gas on local Anvil: 74891
```

Current devnet lifecycle:

```text
AnchoredTreeStatus: Active(1) -> Challenged(2) -> Invalidated(4)
AnchoredTreeStatus: Active(1) -> Finalized(3)
ChallengeStatus: PendingMismatch(1) -> ResolvedMismatch(2)
```

## Commands

Run the evidence gate:

```bash
forge test -vv
python3 research/adversarial_grinding_harness.py
python3 research/baseline_structural_harness.py
python3 research/proof_payload_baseline_harness.py
python3 research/component_table_equivalence.py
python3 scripts/devnet_observatory_demo.py
python3 scripts/grant_readiness_check.py
python3 scripts/export_open_core.py --force
```

Run the open-core gate:

```bash
cd ../crystal-defi-open-core
forge test -vv
python3 scripts/devnet_observatory_demo.py
python3 scripts/grant_readiness_check.py
run the BUSL marker scan against the exported tree
```

The BUSL scan should produce no matches.

## Negative Results

The adversarial harness found Crystal collisions under the tested same-multiset
adversary:

```text
5 leaves: 1680 candidates, 110 Crystal collisions
6 leaves: 30240 candidates, 3538 Crystal collisions
```

Consequence:

```text
Unanchored Crystal roots must not be used as adversarial commitments.
```

This negative result is part of the value of the project. It sharply bounds the
claim and motivates the hash/Merkle anchored architecture.

## Non-Claims

This prototype does not currently prove:

```text
Merkle replacement
standalone cryptographic commitment security
production fraud-proof soundness
second-preimage resistance
production slashing or bonding
consensus, finality, or data availability
gas superiority against Merkle/SSZ proof verifiers
```

## Roadmap

Near-term grant-facing work:

```text
publish the open-core package
publish this report and reviewer packet
verify ESP route through Wishlist or Office Hours
keep all claims tied to reproducible evidence
```

Near-term science work:

```text
finish counterproof semantics
define same-leaf or same-transaction identity
expand same-query benchmark depth
separate malformed challenge rejection from valid respondent defense
```

Near-term protocol work:

```text
freeze challenge-game state machine spec
define depth and leaf policy
prepare testnet checklist
defer economic consequences until the proof game is sound
```
