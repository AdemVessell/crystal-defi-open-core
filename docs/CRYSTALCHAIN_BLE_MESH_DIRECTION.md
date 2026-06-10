# CrystalChain BLE Mesh Direction

Status: sober product-direction note.

Snapshot: 2026-06-11.

## Purpose

This note updates the public CrystalDefi packet with the stronger current
product thesis:

```text
CrystalDefi is useful as reproducible science and grant-facing evidence.
CrystalChain over local-first BLE mesh is the more natural product battlefield.
```

The claim remains narrow:

```text
Crystal localizes; hash anchors prove.
```

## Bottom Line

The Ethereum/rollup framing is technically useful but not the best first
product surface. Ethereum already has mature hash commitments, Merkle/SSZ proof
systems, and dispute-game designs. CrystalDefi can still be a useful
observer-side structural alarm, but it should not be pitched as a missing
rollup primitive.

The stronger direction is:

```text
local-first mesh ledger with compact divergence beacons and anchored segment
repair
```

In that setting, Crystal is not competing with Merkle proofs. It is routing
repair work under a tight transport budget.

## Why BLE Mesh Fits Better

BLE/local mesh systems have constraints that match the Crystal problem shape:

```text
tiny packet budgets
partial peer views
messy reconnect and partition merge
no practical room for heavyweight dispute games on small devices
need to detect divergence without reflooding the whole local history
need to hold conflict instead of silently merging forked histories
```

The useful architecture is:

```text
periodic beacon:
  small Crystal chain signal plus cryptographic head anchor

comparison:
  peers cheaply notice that local histories differ

repair:
  request the first missing or first divergent segment

proof:
  Ed25519 signatures and BLAKE3/Merkle/native-chain anchors bind the data
```

Crystal's job is to make the disagreement easy to route. It is not the security
anchor by itself.

## Concrete Target Shape

The target mesh flow is:

```text
peer A broadcasts compact head beacon
peer B compares head and local chain summary
if remote extends local:
  request block suffix from first missing height
if histories diverge:
  request divergence witness at first mismatch height
  hold conflict
  do not auto-merge
  repair only after a defined policy chooses or reconciles a branch
```

The expected transport split is:

```text
broadcast:
  low-TTL commitment beacons

unicast:
  witness requests
  witness responses
  block repair chunks
```

This is compatible with systems such as BitChat-style BLE mesh transports, but
this repository does not currently include a BitChat integration.

## Current Evidence Boundary

This open-core repository demonstrates:

```text
Crystal structural folding
anchored local Crystal/Merkle challenge packaging
negative collision results for unanchored Crystal roots
same-query proof-size comparisons
local Anvil challenge lifecycle evidence
grant/reviewer packet discipline
```

The BLE mesh direction is currently a direction note, not a public production
implementation in this repository.

Work in the broader CrystalChain lane has begun testing BLE-sized frames and
simulated sync behavior, but that lane must be exported as its own reproducible
public artifact before the public claim can become:

```text
reviewers can clone this repo and reproduce the BLE mesh transcript
```

Until then, phrase the BLE work as:

```text
current product direction
local/private simulation evidence
next public artifact
```

Do not phrase it as:

```text
field-tested BLE networking
BitChat integration
production mesh consensus
adversarial mesh security
blockchain replacement primitive
```

## Sober Reasons This Is Interesting

The direction is interesting because it changes the metric.

Ethereum-facing evaluation asks:

```text
Does this beat Merkle/SSZ/dispute-game systems on gas, proof size, or soundness?
```

Current answer:

```text
No demonstrated superiority yet.
```

BLE mesh evaluation asks:

```text
Can peers detect divergence and request only the relevant repair segment under
small packet, low-power, intermittently connected conditions?
```

Current answer:

```text
Plausible enough to build and measure.
```

That is a better first product test because Crystal's useful property is local
structural routing, not standalone cryptographic binding.

## Near-Term Public Work

The next public artifact should be a separate CrystalChain/BLE packet or repo
with:

```text
compact binary beacon codec
BLE packet-count transcript
prefix catch-up scenario
partition/fork hold scenario
duplicate/replay rejection
first-mismatch witness request/response
honest byte counts for block repair and witness payloads
clear non-claims
```

Promotion gate:

```text
The BLE transcript must be cloneable, runnable, and negative-results-friendly.
If witness or repair payloads are too large, the report must say that directly.
```

## Public Framing

Use:

```text
local-first mesh ledger research
compact divergence beacon
anchored segment repair
hold-conflict sync policy
BLE transport-budget experiment
Crystal as repair router
hash/signature anchors as proof layer
```

Avoid:

```text
Merkle replacement
rollup fraud-proof replacement
production BLE blockchain
BitChat integration already done
new cryptographic commitment
gas-superior Ethereum verifier
```

## Relation To CrystalDefi

CrystalDefi remains valuable because it forces discipline:

```text
negative results are public
adversarial boundaries are explicit
anchors are mandatory
reviewer commands exist
unsupported claims are rejected
```

That same discipline should be carried into CrystalChain/BLE. The product story
is different, but the scientific rule is the same:

```text
show the packet counts
show the conflict behavior
show the unresolved gaps
do not outrun the evidence
```
