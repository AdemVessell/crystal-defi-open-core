# External Reproduction Log

Status: public reproduction evidence log.

## 2026-06-11: Grok Automated Fresh-Clone Reproduction

Reviewer:

```text
Grok / Arkhe_Grok automated outside reproduction
```

Repository:

```text
https://github.com/AdemVessell/crystal-defi-open-core
```

Commit:

```text
8fbbcc1f7edd3216ca3d0434b00e42fb48744e50
```

Environment:

```text
OS: macOS 26.0.1, Darwin 25.0.0, arm64
Python: 3.9.6
forge: 1.7.1-Homebrew, commit 4072e48705af9d93e3c0f6e29e93b5e9a40caed8
anvil: 1.7.1-Homebrew, commit 4072e48705af9d93e3c0f6e29e93b5e9a40caed8
```

Result:

```text
PASS / PASS
```

Two clean clones were run:

```text
/tmp/crystal-defi-fresh-verify
/tmp/crystal-defi-outside-verify
```

Both runs reproduced:

```text
forge test -vv: 67/67 tests passed
Python compile check: pass
adversarial_grinding_harness.py: pass, with expected Crystal collision warning
baseline_structural_harness.py: pass
proof_payload_baseline_harness.py: pass
component_table_equivalence.py: ok true, 8/8 heads match
devnet_observatory_demo.py: ok true
check_open_core_boundary.py: ok true, 0 findings
grant_readiness_check.py: no blocking items
```

No private keys, funded wallets, RPC credentials, or production infrastructure
were required.

Expected caveats:

```text
The adversarial grinding harness takes about 40 seconds.
The research and demo commands rewrite local result snapshots.
The grant-readiness result uses ok_except_known_blockers: true with blockers empty.
Devnet transaction hashes and timestamps differ across local runs.
```

Boundary:

```text
This is machine-assisted outside reproduction, not a human security audit,
protocol endorsement, production-readiness sign-off, or novelty proof.
```

Current consequence:

```text
The public open-core repository has passed an external-agent fresh-clone
reproduction attempt. GitHub Issue #1 remains open for independent human
reproduction.
```

