# ESP Office Hours / Project Feedback Prep

Status: draft prep note.

## Current Route

Use Office Hours or Project Feedback before submitting if the active Wishlist
or RFP fit remains uncertain.

Current facts checked on 2026-06-11:

```text
ESP supports free/open-source, non-commercial, builder-enabling work.
Applications should include methodology, timeline, and deliverables.
Open rounds page reports no active open rounds.
Wishlist is the best general route if no RFP directly fits.
The DeFi risk-intelligence RFP is not a direct fit for CrystalDefi.
```

Reference URLs:

```text
https://esp.ethereum.foundation/applicants
https://esp.ethereum.foundation/applicants/open-rounds
https://esp.ethereum.foundation/applicants/wishlist
https://esp.ethereum.foundation/applicants/rfp
https://esp.ethereum.foundation/applicants/office-hours/apply
```

## Project Summary

CrystalDefi is an open-source structural divergence monitoring prototype for
Ethereum-adjacent transaction trees. It uses compact Crystal roots to localize
where two tree views disagree, while standard hash/Merkle anchors provide the
adversarial binding.

One-sentence boundary:

```text
Crystal localizes; hash/Merkle anchors prove.
```

## What To Ask ESP

Ask:

```text
Would this fit better as a Wishlist application for monitoring/data-driven research, or should it wait for a more specific RFP?
Is the Glamsterdam Wishlist a reasonable route if scoped as impact-analysis and monitoring tooling?
Would ESP prefer a smaller public report/tooling grant before any protocol-game work?
Are the current non-claims and open-core boundary sufficient for eligibility review?
Given that production rollups already localize disputes through execution traces
and state-transition games, is an observer-side structural alarm still within
ESP's useful research/tooling scope?
```

Do not ask:

```text
for support to commercialize a DeFi product
for endorsement of Crystal as a Merkle replacement
for validation of production fraud-proof soundness
for funding of closed-source work
```

## Links To Provide

Attach or link:

```text
open-core repository: https://github.com/AdemVessell/crystal-defi-open-core
latest release: https://github.com/AdemVessell/crystal-defi-open-core/releases/tag/v0.1.4-open-core
docs/PUBLIC_TECHNICAL_REPORT.md
docs/REVIEWER_PACKET.md
docs/EXTERNAL_REPRODUCTION_LOG.md
docs/ROLLUP_FIT_AND_PRIOR_ART_RESPONSE.md
docs/ETHEREUM_ESP_GRANT_PACKET.md
demo/results/devnet_observatory_latest.md
research/results/proof_payload_baselines_latest.md
research/results/adversarial_grinding_latest.md
```

## Current Reproduction Evidence

As of 2026-06-11:

```text
Grok / Arkhe_Grok completed two machine-assisted fresh-clone reproduction runs
against public commit 8fbbcc1f7edd3216ca3d0434b00e42fb48744e50.

Result: PASS / PASS.

Reproduced: 67 Foundry tests, Python compile, research harnesses, component
equivalence, local Anvil devnet lifecycle, open-core boundary scan, and
grant-readiness check with no blocking items.

Boundary: not a human security audit, endorsement, or production-readiness
sign-off.
```

## Fit Language

Use:

```text
builder tooling
monitoring tooling
data-driven research
infrastructure research
security-adjacent proof and challenge tooling
```

Avoid:

```text
new blockchain
production DeFi security product
standalone fraud proof
token system
Merkle replacement
```
