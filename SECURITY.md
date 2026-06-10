# Security Policy

## Status

CrystalDefi open-core is a research prototype. It is not production DeFi
infrastructure, not a live-chain deployment, and not a system that should hold
funds.

## Supported Versions

Security review should target the current `main` branch and the latest public
release tag.

## Reporting

For non-sensitive issues, open a public GitHub issue with reproduction steps.

For sensitive issues that could mislead reviewers, break the local verifier, or
create an exploitable production pattern if copied, use GitHub's private
vulnerability reporting if available for this repository. If private reporting
is not available, open a minimal public issue that says a private security
discussion is needed, without publishing exploit details.

Do not include:

```text
private keys
funded accounts
API tokens
secret RPC URLs
personal credentials
third-party confidential code
```

## Scope

In scope:

```text
incorrect verifier behavior
malformed proof handling
challenge-state inconsistencies
watcher output that misrepresents evidence
grant-readiness or export behavior that leaks excluded code
documentation that overstates security
```

Out of scope:

```text
mainnet asset loss, because there is no production deployment
token economics, because none are implemented here
closed-source extensions not present in this repository
social engineering or credential attacks
```

