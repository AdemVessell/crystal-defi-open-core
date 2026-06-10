# Challenge Game State Machine V0

Status: protocol specification draft.

## Purpose

Document the current anchored localized challenge game exactly as implemented
by `CrystalComponentVerifier`.

This is not a production finality or slashing spec.

## Anchored Tree States

Current enum:

```text
None = 0
Active = 1
Challenged = 2
Finalized = 3
Invalidated = 4
```

Allowed transitions:

```text
None -> Active
Active -> Finalized
Active -> Challenged
Challenged -> Invalidated
Active -> Invalidated for legacy full-tree/path consistency challenges
```

Disallowed transitions:

```text
Challenged -> Finalized
Finalized -> Challenged
Finalized -> Invalidated through anchored localized challenge
Invalidated -> Finalized
Invalidated -> Challenged
```

## Localized Challenge States

Current enum:

```text
None = 0
PendingMismatch = 1
ResolvedMismatch = 2
```

Allowed transitions:

```text
None -> PendingMismatch
PendingMismatch -> ResolvedMismatch
```

Disallowed transitions:

```text
None -> ResolvedMismatch
ResolvedMismatch -> PendingMismatch
ResolvedMismatch -> ResolvedMismatch
```

## Commit Path

`commitAnchoredTree` and `commitAnchoredTreeWithWindow` require:

```text
nonzero Crystal root
nonzero Merkle root
positive challenge window
no existing tree root at blockHash/treeIndex
no existing anchored tree commitment at blockHash/treeIndex
deadline fits uint64
```

Result:

```text
tree root stored
Merkle root stored
commitment status = Active
challenge deadline opened
```

## Finalize Path

`finalizeAnchoredTree` requires:

```text
commitment status is Active
block timestamp is at or after challengeDeadline
```

Result:

```text
commitment status = Finalized
```

Finalization rejects a challenged tree.

## Anchored Localized Challenge Submit Path

`submitAnchoredLocalizedChallenge` requires:

```text
posted Crystal root exists
posted Merkle root exists
anchored commitment status is Active
current time is before challengeDeadline
Crystal witness and Merkle proof have same depth
Crystal witness and Merkle proof have same path sides
Merkle proof recomputes the posted Merkle root
Crystal witness recomputes a root different from the posted Crystal root
challenge id is unused
response deadline fits uint64
```

Result:

```text
localized challenge status = PendingMismatch
anchored commitment status = Challenged
responseDeadline = openedAt + DEFAULT_CHALLENGE_RESPONSE_WINDOW_SECONDS
```

The block is not marked challenged at submit time. The anchored commitment is
not invalidated at submit time.

## Resolve Path

`resolveAnchoredLocalizedChallenge` requires:

```text
localized challenge status is PendingMismatch
current time is at or after responseDeadline
```

Result:

```text
localized challenge status = ResolvedMismatch
challenged[blockHash] = true
anchored commitment status = Invalidated
```

## Malformed Proof Behavior

Malformed challenge submissions revert before state changes:

```text
missing tree commitment
missing Merkle commitment
finalized or already challenged anchored tree
closed challenge window
path-depth mismatch
path-side mismatch
malformed Crystal witness
malformed Merkle proof
Merkle anchor mismatch
matching Crystal root
duplicate challenge id
response deadline overflow
```

## Watcher Expectations

The watcher should treat the current game as:

```text
structural-divergence reporting
local proof routing
anchored mismatch challenge generation
not fraud-proof finality
not economic punishment
```

Watcher output should preserve:

```text
blockHash
treeIndex
posted Crystal root
posted Merkle root
localized path
Crystal witness bytes
target Merkle hash
Merkle proof bytes
table commitment
tree encoding version
leaf mapping version
```

## Economic Consequence Options

Future choices, not implemented:

```text
invalidation-only
bonded challenge
sequencer bond slashing
reputation flag
watcher alert only
```

No economic consequence should be added until counterproof semantics are sound.
