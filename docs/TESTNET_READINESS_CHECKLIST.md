# CrystalDefi Testnet Readiness Checklist

Status: blocked until explicit deployment approval, funded wallet, and target
network are provided.

## Current Position

The project has a local Anvil devnet demo. It is not yet deployed to Sepolia or
another public Ethereum testnet.

## Preconditions

Required before any testnet deployment:

```text
explicit user approval to deploy
target network selected
funded deployer wallet available
RPC URL available
private key or signer path configured without exposing plaintext in docs
contract owner address confirmed
deployment artifact path selected
gas budget accepted
```

## Technical Gates

Must pass immediately before deployment:

```bash
forge test -vv
python3 -m py_compile sdk/crystal_committer.py watcher/crystal_watcher.py research/*.py scripts/*.py
python3 scripts/devnet_observatory_demo.py
python3 scripts/grant_readiness_check.py
```

Open-core gate must also pass:

```bash
python3 scripts/export_open_core.py --force
cd ../crystal-defi-open-core
forge test -vv
python3 scripts/devnet_observatory_demo.py
python3 scripts/grant_readiness_check.py
```

## Deployment Plan

When approved:

```text
deploy CrystalComponentVerifier
initialize all 8 compact component tables
finalize initialization
commit a sample anchored tree
submit a sample localized challenge
wait or time-travel only on local forks, not public testnet
resolve only when the public response deadline has elapsed
record transaction hashes and gas usage
```

## Post-Deployment Evidence

Record:

```text
network name
chain id
contract address
deployer address
initialize transactions
finalizeInitialization transaction
sample commit transaction
sample challenge transaction
sample resolve transaction if performed
block explorer links
gas used
ABI version
source commit or source packet hash
```

## Blockers

Do not deploy if any are true:

```text
counterproof semantics are being represented as implemented
economic consequences are enabled
public docs imply production fraud-proof soundness
private key would be written to repo or logs
open-core export is stale
grant-readiness gate has blockers
```

## V0 Decision

For the current four-week sprint:

```text
prepare the checklist
do not deploy by default
do not request live funds automatically
do not add testnet deployment claims to public report until actual transactions exist
```
