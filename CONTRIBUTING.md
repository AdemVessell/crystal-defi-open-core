# Contributing

CrystalDefi open-core is a research prototype. Contributions should preserve
the current claim boundary:

```text
Crystal localizes; hash/Merkle anchors prove.
```

## Useful Contributions

Useful contributions include:

```text
fresh-clone verification reports
Foundry or Python reproducibility fixes
same-query benchmark additions
prior-art corrections
watcher/indexer integration notes
counterproof semantics review
malformed-proof test cases
documentation that sharpens non-claims
```

## Before Opening A Pull Request

Run:

```bash
forge test -vv
python3 -m py_compile sdk/crystal_committer.py watcher/crystal_watcher.py research/*.py scripts/*.py
python3 scripts/devnet_observatory_demo.py
python3 scripts/grant_readiness_check.py
```

For research-result changes, also run the relevant harness under `research/`
and commit the regenerated result file if the change is intentional.

## Claim Discipline

Do not add language claiming:

```text
Merkle replacement
standalone cryptographic commitment security
production fraud-proof soundness
production slashing or bonding
consensus, finality, or data availability
gas superiority without same-query evidence
```

## Issues

When opening an issue, include:

```text
commit hash
OS
Python version
Foundry version
command run
expected result
actual result
```

Do not post private keys, funded wallet details, secrets, API tokens, or
private infrastructure URLs.

