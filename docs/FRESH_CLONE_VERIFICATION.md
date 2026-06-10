# Fresh-Clone Verification

Status: public replication checklist.

## Purpose

This file gives an independent reviewer a narrow, reproducible check for the
public open-core repository. The goal is not to endorse the protocol or prove
production security. The goal is to answer:

```text
Can a fresh clone reproduce the current tests, devnet lifecycle, readiness
check, and published research result files?
```

## Requirements

Expected local tools:

```text
git
python3
Foundry: forge and anvil
ripgrep: rg, optional but recommended
```

No private keys, funded wallets, RPC credentials, or production infrastructure
are required.

## Clean Clone

```bash
tmpdir="$(mktemp -d)"
cd "$tmpdir"
git clone https://github.com/AdemVessell/crystal-defi-open-core.git
cd crystal-defi-open-core
git rev-parse HEAD
```

Record the commit hash in any review note.

## Verification Commands

```bash
forge test -vv
python3 -m py_compile sdk/crystal_committer.py watcher/crystal_watcher.py research/*.py scripts/*.py
python3 research/adversarial_grinding_harness.py
python3 research/baseline_structural_harness.py
python3 research/proof_payload_baseline_harness.py
python3 research/component_table_equivalence.py
python3 scripts/devnet_observatory_demo.py
python3 scripts/check_open_core_boundary.py
python3 scripts/grant_readiness_check.py
```

Expected boundary-scan result:

```text
ok: true
```

## Expected High-Level Results

```text
Foundry tests pass.
Python compile check passes.
Research harnesses regenerate result files.
Component-table equivalence check passes.
Devnet demo reports ok: true.
Grant-readiness check reports no blocking items.
Open-core boundary scan reports ok: true.
```

The devnet demo writes fresh local transaction hashes and timestamps. Those
values are expected to differ from the committed evidence files.

## What This Verifies

This verifies:

```text
the repository is cloneable
the Solidity test suite runs
the Python SDK, watcher, scripts, and research harnesses compile
the local Anvil challenge lifecycle reproduces
the grant-readiness gate has no blockers
the open-core source boundary does not contain excluded license markers
```

This does not verify:

```text
production fraud-proof soundness
counterproof completeness
economic security
mainnet or testnet deployment readiness
gas superiority against Merkle, SSZ, or Verkle systems
novelty against all prior art
```

## Reviewer Report Template

```text
Reviewer:
Date:
OS:
Python version:
Foundry version:
Repo commit:

Commands run:

Result:
PASS / FAIL / PARTIAL

Notes:

Unexpected output:

Did any command require private keys or funded accounts?
No / Yes, explain:
```
