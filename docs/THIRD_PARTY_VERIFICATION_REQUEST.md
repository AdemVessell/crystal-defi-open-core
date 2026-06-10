# Third-Party Verification Request

Status: public reviewer outreach note.

## Request

CrystalDefi open-core needs one or more independent fresh-clone verification
runs. The requested review is intentionally narrow:

```text
Clone the public repo.
Run the documented verification commands.
Report whether the tests, research harnesses, devnet demo, readiness check, and
open-core boundary scan reproduce from a clean checkout.
```

Start with:

```text
docs/FRESH_CLONE_VERIFICATION.md
```

Repository:

```text
https://github.com/AdemVessell/crystal-defi-open-core
```

## Boundary

The current claim is:

```text
Crystal localizes; hash/Merkle anchors prove.
```

The requested verification is not a security audit, endorsement, grant review,
or production-readiness certification.

## X Post Draft

Single-post draft:

```text
Looking for 1 independent reviewer to fresh-clone/run CrystalDefi open-core and report whether the tests/devnet/readiness checks reproduce. Narrow claim: Crystal localizes; hash/Merkle anchors prove. Repo + checklist: https://github.com/AdemVessell/crystal-defi-open-core
```

Thread draft:

```text
1/ Looking for an independent fresh-clone verification of CrystalDefi open-core.

The ask is narrow: clone the repo, run the documented checks, and report whether the tests/devnet/readiness evidence reproduces.

https://github.com/AdemVessell/crystal-defi-open-core
```

```text
2/ Current claim boundary:

Crystal localizes; hash/Merkle anchors prove.

This is not a Merkle replacement claim, not production fraud-proof soundness, and not a gas-superiority claim.
```

```text
3/ Checklist:

docs/FRESH_CLONE_VERIFICATION.md

Ideal reply: OS, Foundry/Python versions, commit hash, PASS/FAIL/PARTIAL, and any unexpected output.
```

## Good Reviewer Fit

Useful reviewers include:

```text
Ethereum protocol or tooling engineers
Foundry/Solidity developers
rollup/fault-proof researchers
watcher/indexer developers
security reviewers comfortable with bounded reproduction checks
```

## What To Ask Them Not To Do

Do not ask reviewers to:

```text
use private keys
fund wallets
deploy to testnet
audit economic security
endorse novelty
review closed-source material
```
