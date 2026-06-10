# Crystal DeFi Proof Payload Baselines

Generated: `2026-06-10T18:12:36Z`

## Boundary

V0 Crystal package includes the full encoded tree. Anchored V1 removes full-tree calldata from the challenge path and measures the local Crystal witness plus same-path Merkle proof. Merkle/SSZ/sparse rows are membership/update proof surfaces, not full-tree witnesses.

| Leaves | Depth | V0 Crystal package | Tree calldata | Anchored V1 local path | V1 Crystal witness | V1 Merkle proof | Merkle membership | SSZ proof | Sparse Merkle uint8 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `4` | `2` | `111` | `39` | `126` | `27` | `67` | `101` | `105` | `290` |
| `8` | `3` | `151` | `79` | `168` | `36` | `100` | `133` | `137` | `290` |
| `16` | `4` | `231` | `159` | `210` | `45` | `133` | `165` | `169` | `290` |
| `32` | `5` | `391` | `319` | `252` | `54` | `166` | `197` | `201` | `290` |
| `64` | `6` | `711` | `639` | `294` | `63` | `199` | `229` | `233` | `290` |
| `128` | `7` | `1351` | `1279` | `336` | `72` | `232` | `261` | `265` | `290` |
| `256` | `8` | `2631` | `2559` | `378` | `81` | `265` | `293` | `297` | `290` |
| `512` | `9` | `5191` | `5119` | `420` | `90` | `298` | `325` | `329` | `290` |

## Interpretation

- V0 Crystal package is a full-tree anchored witness and should not be compared to compact membership proofs as if it were minimal.
- Anchored V1 removes full-tree calldata from the challenge path and measures only the local Crystal witness plus same-path Merkle proof.
- V1 is not a Merkle replacement. The Merkle/SSZ/sparse-Merkle rows remain the binding proof-size baselines.
