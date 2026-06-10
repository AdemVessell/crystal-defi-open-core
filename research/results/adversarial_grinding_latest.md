# Crystal DeFi Adversarial Grinding Harness

Generated: `2026-06-10T18:13:19Z`
Seed: `1337`

## Verdict

Crystal collisions were found under the tested same-multiset adversary. Do not use unanchored Crystal roots as adversarial commitments; frame Crystal as a localization/checking layer.

## Exhaustive Same-Multiset Enumeration

| Leaves | Candidates | Crystal unique | Crystal collisions | SHA-8 unique | SHA-8 collisions |
|---:|---:|---:|---:|---:|---:|
| `2` | `2` | `2` | `0` | `2` | `0` |
| `3` | `12` | `12` | `0` | `12` | `0` |
| `4` | `120` | `120` | `0` | `120` | `0` |
| `5` | `1680` | `1570` | `110` | `1680` | `0` |
| `6` | `30240` | `26702` | `3538` | `30240` | `0` |

## Random Grinding Campaigns

- Hits found: `0` across `600000` candidate attempts.

## Boundary

- A no-hit run is not a proof of cryptographic soundness.
- A Crystal collision is a hard demotion for unanchored security claims.
- SHA-256 full digest is treated as the anchor baseline, not as a Crystal competitor.
- Crystal should be framed as a structural divergence monitor unless this harness and later formal analysis justify stronger language.
