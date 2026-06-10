# CrystalDefi Reviewer Packet

Status: reviewer-facing command and claim packet.

## One-Sentence Claim

CrystalDefi is an open-source structural divergence monitor: Crystal localizes
tree disagreement, while hash/Merkle anchors provide adversarial binding.

## What To Review

Primary artifacts:

```text
README.md
docs/PUBLIC_TECHNICAL_REPORT.md
docs/LOCAL_CRYSTAL_WITNESS_V1.md
docs/COUNTERPROOF_SEMANTICS_V0.md
docs/CHALLENGE_GAME_STATE_MACHINE_V0.md
docs/ETHEREUM_ESP_GRANT_PACKET.md
```

Machine evidence:

```text
research/results/adversarial_grinding_latest.md
research/results/structural_baselines_latest.md
research/results/proof_payload_baselines_latest.md
demo/results/devnet_observatory_latest.md
OPEN_CORE_MANIFEST.json in the generated open-core export
```

## Exact Commands

Source lane:

```bash
forge test -vv
python3 -m py_compile sdk/crystal_committer.py watcher/crystal_watcher.py research/*.py scripts/*.py
python3 research/proof_payload_baseline_harness.py
python3 scripts/devnet_observatory_demo.py
python3 scripts/grant_readiness_check.py
python3 scripts/export_open_core.py --force
```

Open-core lane:

```bash
cd ../crystal-defi-open-core
forge test -vv
python3 -m py_compile sdk/crystal_committer.py watcher/crystal_watcher.py research/*.py scripts/*.py
python3 scripts/devnet_observatory_demo.py
python3 scripts/grant_readiness_check.py
run the BUSL marker scan against the exported tree
```

Expected result:

```text
Foundry tests pass.
Python compile passes.
Devnet demo reports ok: true.
Grant-readiness gate has no blocking items.
Open-core BUSL scan returns no matches.
```

## Current Devnet State Transitions

The local Anvil demo verifies:

```text
anchored status after commit: 1
anchored status after submit: 2
anchored status after resolve: 4
challenge record after submit: 1
challenge record after resolve: 2
localized_path_bound: true
challenge_invalidated: true
```

Meaning:

```text
Active -> Challenged -> Invalidated
PendingMismatch -> ResolvedMismatch
```

The challenge does not invalidate immediately. Invalidation happens only after
the response window is advanced and the pending localized mismatch is resolved.

## Grant-Facing Boundary

Grant-funded scope should be the Apache-2.0 open-core export:

```text
../crystal-defi-open-core
```

Included:

```text
SDK
Solidity verifier prototypes
Foundry tests
watcher service
research harnesses
devnet demo
docs and public report
```

Excluded:

```text
commercial token product
production DeFi security product
slashing or bonding mechanism
closed-source CrystalDefi extensions
CrystalSocial or unrelated side projects
```

## ESP Route

Current route:

```text
Wishlist or Office Hours / Project Feedback first.
```

Reason:

```text
Open rounds currently show none active.
The DeFi risk-intelligence RFP is not a direct fit unless the project pivots
into neutral risk-feed aggregation.
The Glamsterdam Wishlist is potentially adjacent only if the project is framed
as monitoring tooling, impact analysis tooling, or data-driven research.
```

References:

```text
https://esp.ethereum.foundation/applicants
https://esp.ethereum.foundation/applicants/open-rounds
https://esp.ethereum.foundation/applicants/wishlist
https://esp.ethereum.foundation/applicants/rfp
https://esp.ethereum.foundation/applicants/office-hours/apply
```

## Non-Claims

Do not read this project as claiming:

```text
Crystal replaces Merkle proofs.
Crystal roots are adversarial commitments by themselves.
The current protocol is production fraud-proof sound.
The current protocol has production slashing, bonding, or finality integration.
The current benchmarks prove gas superiority.
```

## Reviewer Questions This Packet Should Answer

```text
What does Crystal add? A cheap structural localization signal.
What proves adversarial binding? The hash/Merkle anchor.
What is on chain now? Compact verification, same-path binding, pending challenge lifecycle.
What is not on chain now? Sound respondent counterproof and economic consequences.
Can I reproduce the evidence? Yes, with the commands above.
```
