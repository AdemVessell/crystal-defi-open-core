# Counterproof Semantics V0

Status: specification draft only.

## Purpose

Define what a respondent would need to prove before the contract can safely add
a respondent counterproof entrypoint.

This document intentionally does not add Solidity behavior. The current
contract resolves pending localized mismatches by timeout. A counterproof path
should be added only after the proof semantics below are made sound and tested.

## Current Challenger Proof

Today, an anchored localized challenger proves:

```text
there is a posted Crystal root for blockHash/treeIndex
there is a posted Merkle root for the same blockHash/treeIndex
the supplied Crystal witness and Merkle proof describe the same path sides and depth
the Merkle proof reaches the posted Merkle root
the Crystal witness recomputes a Crystal root different from the posted Crystal root
the challenge was submitted before the challenge deadline
```

This is enough to record a pending localized mismatch and, after the response
deadline, invalidate the bad anchored commitment in the prototype.

## What The Challenger Does Not Yet Prove

The current challenger path does not fully prove:

```text
same transaction identity beyond path encoding
same leaf identity across all tree encodings
that the target Merkle hash is semantically the same object as the Crystal target root
that the posted tree is unavailable or malicious rather than differently encoded
production economic fault
```

That is why the current challenge remains a localized mismatch mechanism, not a
complete production fraud-proof game.

## Valid Defense Types

A future respondent defense may be sound if it proves one of these cases:

```text
matching-root defense: the respondent shows a same-path Crystal witness and Merkle proof that recompute the posted Crystal root under the posted Merkle root.
invalid-challenge defense: the respondent shows the challenger proof is malformed, path-mismatched, stale, or not bound to the posted Merkle root.
identity-mismatch defense: the respondent shows the challenger compared different leaf identities, transaction identities, or encoding domains.
superseded-commitment defense: the respondent shows the challenge targets a commitment that was already finalized, invalidated, or replaced under an accepted protocol rule.
```

The first defense is the only candidate for a positive counterproof. It still
requires a precise binding between the local Merkle target and the local Crystal
target before it should become Solidity code.

## Fake Counterproofs To Reject

Do not accept a respondent proof if it only shows:

```text
a different path that reaches the same Merkle root
a Crystal witness without a matching Merkle proof
a Merkle proof without a matching Crystal witness
a matching Crystal root under a different table commitment
a matching Merkle root under a different tree encoding version
a claim about the full tree without local path binding
a hash of a leaf that is not tied to the same transaction or leaf identity
```

These defenses can look plausible while failing to answer the challenged local
claim.

## Required Binding Before Solidity

Before adding `respondAnchoredLocalizedChallenge`, the design must bind:

```text
blockHash
treeIndex
postedCrystalRoot
postedMerkleRoot
tableCommitment
treeEncodingVersion
leafMappingVersion
localized path
target Merkle hash
target Crystal root
leaf or transaction identity
```

The implementation must make it impossible for a respondent to defend a
different object than the challenger attacked.

## V0 Decision

For this sprint:

```text
do not add a respondent counterproof contract entrypoint
do not add slashing or bonding
do not claim fraud-proof soundness
keep timeout resolution as a prototype invalidation mechanism
write tests only after a valid defense object is specified
```

## Next Proof Work

Required next steps:

```text
define canonical leaf identity
define target hash to Crystal target binding
define positive matching-root defense payload
define invalid-challenge defense payload
write adversarial examples for path substitution and identity substitution
only then add Solidity tests and ABI
```
