"""
Crystal Committer SDK
=====================
Python SDK for Crystal structural divergence checks plus hash anchors.

Usage:
    from crystal_committer import CrystalCommitter

    committer = CrystalCommitter()
    root, trace = committer.commit(tree)
    is_valid = committer.verify(tree, root)
    tree_bytes = committer.encode_for_chain(tree)

CLI:
    python crystal_committer.py commit --tree '((10,20),(30,40))'
    python crystal_committer.py verify --tree '((10,20),(30,40))' --root 'ab12...'
    python crystal_committer.py encode --tree '((10,20),(30,40))' --output tree.bin

Licensed under Apache-2.0.
"""

import numpy as np
import struct
import json
import sys
import hashlib
from typing import List, Tuple, Optional, Union
from dataclasses import dataclass

# ──────────────────────────────────────────────
#  Constants
# ──────────────────────────────────────────────

STATE_SIZE = 256
N_HEADS = 8
TABLE_SIZE = STATE_SIZE * STATE_SIZE
ANCHOR_DOMAIN = b"crystal-defi:v1:tree"
TABLE_DOMAIN = b"crystal-defi:v1:component-tables"
ENCODING_VERSION = "crystal-defi-tree-v1"
LEAF_MAPPING_VERSION = "uint8-leaf-state-v1"

# ──────────────────────────────────────────────
#  Tree Structure
# ──────────────────────────────────────────────

@dataclass
class CrystalLeaf:
    """Leaf node with a crystal state value (0-255)."""
    state: int

    def __post_init__(self):
        assert 0 <= self.state < STATE_SIZE, f"State must be 0-255, got {self.state}"

@dataclass
class CrystalNode:
    """Internal node — composition of left and right children."""
    left: Union['CrystalNode', CrystalLeaf]
    right: Union['CrystalNode', CrystalLeaf]

# Type alias
CrystalTree = Union[CrystalNode, CrystalLeaf]

def leaf(state: int) -> CrystalLeaf:
    """Create a leaf node."""
    return CrystalLeaf(state=state % STATE_SIZE)

def node(left: CrystalTree, right: CrystalTree) -> CrystalNode:
    """Create an internal node."""
    return CrystalNode(left=left, right=right)

def is_leaf(tree: CrystalTree) -> bool:
    return isinstance(tree, CrystalLeaf)

def get_leaves(tree: CrystalTree) -> List[int]:
    if is_leaf(tree):
        return [tree.state]
    return get_leaves(tree.left) + get_leaves(tree.right)

def tree_depth(tree: CrystalTree) -> int:
    if is_leaf(tree):
        return 0
    return 1 + max(tree_depth(tree.left), tree_depth(tree.right))

def tree_structure(tree: CrystalTree) -> str:
    if is_leaf(tree):
        return "L"
    return f"({tree_structure(tree.left)},{tree_structure(tree.right)})"


def localize_difference(tree_a: CrystalTree, tree_b: CrystalTree, path: str = "root") -> dict:
    """Return the first structural or leaf-value difference between two trees."""
    if is_leaf(tree_a) and is_leaf(tree_b):
        if tree_a.state == tree_b.state:
            return {
                "path": None,
                "difference": "none",
            }
        return {
            "path": path,
            "difference": "leaf_value_mismatch",
            "a": tree_a.state,
            "b": tree_b.state,
        }

    if is_leaf(tree_a) != is_leaf(tree_b):
        return {
            "path": path,
            "difference": "node_type_mismatch",
            "a": "leaf" if is_leaf(tree_a) else "internal",
            "b": "leaf" if is_leaf(tree_b) else "internal",
        }

    left = localize_difference(tree_a.left, tree_b.left, path + ".L")
    if left["difference"] != "none":
        return left
    return localize_difference(tree_a.right, tree_b.right, path + ".R")


def merkle_root(tree: CrystalTree) -> bytes:
    """Domain-separated SHA-256 tree root that commits to shape and order."""
    if is_leaf(tree):
        return hashlib.sha256(b"\x00" + bytes([tree.state])).digest()
    return hashlib.sha256(b"\x01" + merkle_root(tree.left) + merkle_root(tree.right)).digest()


def encode_merkle_path_steps(siblings_from_node_to_root: list) -> bytes:
    """Encode Merkle proof path steps for Solidity verification.

    Format:
        step count:     1 byte
        repeated step:
          sibling side: 0x00 when sibling is right/current is left
                        0x01 when sibling is left/current is right
          sibling hash: 32 bytes
    """
    if len(siblings_from_node_to_root) > 255:
        raise ValueError("Merkle path has too many steps")
    encoded = bytearray([len(siblings_from_node_to_root)])
    for sibling in siblings_from_node_to_root:
        side = sibling["side"]
        if side == "R":
            encoded.append(0)
        elif side == "L":
            encoded.append(1)
        else:
            raise ValueError(f"invalid sibling side: {side}")
        encoded.extend(bytes.fromhex(sibling["hash"]))
    return bytes(encoded)


def _path_parts(path: str) -> List[str]:
    if path in ("", "root", None):
        return []
    parts = path.split(".")
    if parts and parts[0] == "root":
        parts = parts[1:]
    return parts


def merkle_localization_proof(tree: CrystalTree, path: str) -> dict:
    """Return a Merkle proof for the subtree/leaf at path."""
    parts = _path_parts(path)
    siblings_root_to_node = []
    current = tree

    for part in parts:
        if is_leaf(current):
            return {
                "path": path,
                "available": False,
                "reason": "path_enters_leaf",
                "merkle_root_sha256": merkle_root(tree).hex(),
            }
        if part == "L":
            siblings_root_to_node.append({"side": "R", "hash": merkle_root(current.right).hex()})
            current = current.left
        elif part == "R":
            siblings_root_to_node.append({"side": "L", "hash": merkle_root(current.left).hex()})
            current = current.right
        else:
            return {
                "path": path,
                "available": False,
                "reason": "invalid_path",
                "merkle_root_sha256": merkle_root(tree).hex(),
            }

    node_type = "leaf" if is_leaf(current) else "internal"
    leaf_value = current.state if is_leaf(current) else None
    siblings = list(reversed(siblings_root_to_node))
    encoded = encode_merkle_path_steps(siblings)
    return {
        "path": path,
        "available": True,
        "node_type": node_type,
        "leaf_value": leaf_value,
        "node_hash_sha256": merkle_root(current).hex(),
        "merkle_root_sha256": merkle_root(tree).hex(),
        "siblings_from_node_to_root": siblings,
        "encoded": "0x" + encoded.hex(),
        "encoded_length": len(encoded),
        "proof_bytes_minimal": len(siblings) * 32 + 32 + (1 if is_leaf(current) else 0),
    }


def subtree_at_path(tree: CrystalTree, path: str) -> CrystalTree:
    """Return the subtree at a root/L/R path."""
    current = tree
    for part in _path_parts(path):
        if is_leaf(current):
            raise ValueError(f"path {path} enters a leaf at {part}")
        if part == "L":
            current = current.left
        elif part == "R":
            current = current.right
        else:
            raise ValueError(f"invalid path component: {part}")
    return current

# ──────────────────────────────────────────────
#  Table Construction
# ──────────────────────────────────────────────

def build_crystal_components(head_id: int, seed_base: int = 10000) -> np.ndarray:
    """Build the compact 4x4 component tables for one head.

    Returns:
        4x4x4 uint8 array. Each component entry is in 0..3 and contributes
        two bits to the final 8-bit fold result.
    """
    component_tables = np.zeros((4, 4, 4), dtype=np.uint8)
    for k in range(4):
        for ci in range(4):
            for cj in range(4):
                idx = (head_id * 4 + k) * 16 + ci * 4 + cj
                rng = np.random.RandomState(idx + head_id * seed_base)
                component_tables[k, ci, cj] = rng.randint(4)
    return component_tables


def build_crystal_table(head_id: int, seed_base: int = 10000) -> np.ndarray:
    """Build one PathCrystal composition table via 4x4 component decomposition.

    Args:
        head_id: Which head (0 to N_HEADS-1).
        seed_base: Base seed for reproducibility.

    Returns:
        256x256 uint8 numpy array — the composition table.
    """
    component_tables = build_crystal_components(head_id, seed_base)

    ii, jj = np.meshgrid(np.arange(STATE_SIZE), np.arange(STATE_SIZE), indexing='ij')
    result = np.zeros((STATE_SIZE, STATE_SIZE), dtype=np.uint8)
    for k in range(4):
        ci = (ii >> (2 * k)) & 3
        cj = (jj >> (2 * k)) & 3
        result |= (component_tables[k, ci, cj].astype(np.uint8) << (2 * k))
    return result

def build_crystal_bank(n_heads: int = N_HEADS, seed_base: int = 10000) -> List[np.ndarray]:
    """Build a full crystal bank (all heads)."""
    return [build_crystal_table(h, seed_base) for h in range(n_heads)]

# ──────────────────────────────────────────────
#  Committer
# ──────────────────────────────────────────────

class CrystalCommitter:
    """The crystal commitment engine.

    Folds transaction trees through non-associative composition tables
    to produce structure-dependent root fingerprints.
    """

    def __init__(self, n_heads: int = N_HEADS, seed_base: int = 10000, tables: Optional[List[np.ndarray]] = None):
        self.n_heads = n_heads
        self.seed_base = seed_base
        self._component_export_available = tables is None
        if tables is not None:
            self.tables = tables
        else:
            self.tables = build_crystal_bank(n_heads, seed_base)

    def fold(self, tree: CrystalTree, head: int) -> Tuple[int, List[int]]:
        """Fold a tree through one crystal head.

        Returns:
            (root_state, trace) where trace is the list of all states
            encountered during the fold (leaves + internal nodes).
        """
        table = self.tables[head]
        return self._fold_recursive(tree, table)

    def _fold_recursive(self, tree: CrystalTree, table: np.ndarray) -> Tuple[int, List[int]]:
        if is_leaf(tree):
            return tree.state, [tree.state]

        left_state, left_trace = self._fold_recursive(tree.left, table)
        right_state, right_trace = self._fold_recursive(tree.right, table)
        root = int(table[left_state, right_state])
        return root, left_trace + right_trace + [root]

    def commit(self, tree: CrystalTree) -> Tuple[tuple, List[List[int]]]:
        """Produce a crystal commitment for a tree.

        Returns:
            (root_fingerprint, per_head_traces)
            root_fingerprint is a tuple of N_HEADS uint8 values.
        """
        roots = []
        traces = []
        for h in range(self.n_heads):
            root, trace = self.fold(tree, h)
            roots.append(root)
            traces.append(trace)
        return tuple(roots), traces

    def verify(self, tree: CrystalTree, claimed_root: tuple) -> bool:
        """Verify a crystal commitment by re-folding (forward consistency).

        Args:
            tree: The transaction tree.
            claimed_root: The root fingerprint to verify against.

        Returns:
            True if the tree folds to the claimed root.
        """
        computed_root, _ = self.commit(tree)
        return computed_root == claimed_root

    def commit_batch(self, trees: List[CrystalTree]) -> List[Tuple[tuple, List[List[int]]]]:
        """Commit a batch of trees."""
        return [self.commit(tree) for tree in trees]

    def aggregate_roots(self, roots: List[tuple]) -> tuple:
        """Aggregate multiple per-tree roots into a single block root.

        Folds roots sequentially through the crystal tables.
        """
        if not roots:
            return (0,) * self.n_heads

        agg = list(roots[0])
        for root in roots[1:]:
            for h in range(self.n_heads):
                agg[h] = int(self.tables[h][agg[h], root[h]])
        return tuple(agg)

    # ──────────────────────────────────────
    #  Serialization (for on-chain calldata)
    # ──────────────────────────────────────

    def encode_for_chain(self, tree: CrystalTree) -> bytes:
        """Encode a tree into the on-chain binary format.

        Format:
            Leaf:     0x00 + N_HEADS bytes (leaf state repeated)
            Internal: 0x01 + left_encoding + right_encoding
        """
        if is_leaf(tree):
            return bytes([0x00] + [tree.state] * self.n_heads)
        left_bytes = self.encode_for_chain(tree.left)
        right_bytes = self.encode_for_chain(tree.right)
        return bytes([0x01]) + left_bytes + right_bytes

    def anchor_digest(self, tree: CrystalTree, domain: bytes = ANCHOR_DOMAIN) -> str:
        """Return a domain-separated SHA-256 anchor for the encoded tree.

        This digest is the cryptographic binding surface. The Crystal root is
        the compact structural signal; the anchor digest is what prevents a
        same-root structural collision from being accepted as equivalent.
        """
        h = hashlib.sha256()
        h.update(domain)
        h.update(b"\x00")
        h.update(self.encode_for_chain(tree))
        return h.hexdigest()

    def table_commitment(self) -> str:
        """Return a SHA-256 commitment to the active table material."""
        h = hashlib.sha256()
        h.update(TABLE_DOMAIN)
        h.update(b"\x00")
        h.update(bytes([self.n_heads]))
        if self._component_export_available:
            h.update(b"component_4x4_unpacked")
            for table in self.export_component_tables():
                h.update(len(table).to_bytes(2, "big"))
                h.update(table)
        else:
            h.update(b"full_256x256")
            for table in self.export_tables():
                h.update(len(table).to_bytes(4, "big"))
                h.update(table)
        return h.hexdigest()

    def commitment_package(self, tree: CrystalTree) -> dict:
        """Return the production-facing Crystal + cryptographic anchor package."""
        root, traces = self.commit(tree)
        calldata = self.encode_for_chain(tree)
        return {
            "encoding_version": ENCODING_VERSION,
            "leaf_mapping_version": LEAF_MAPPING_VERSION,
            "anchor_domain": ANCHOR_DOMAIN.decode("ascii"),
            "table_domain": TABLE_DOMAIN.decode("ascii"),
            "table_format": (
                "component_4x4_tables_unpacked_bytes"
                if self._component_export_available
                else "full_256x256_tables"
            ),
            "table_commitment_sha256": self.table_commitment(),
            "crystal_root": list(root),
            "crystal_root_hex": self.root_to_bytes32(root).hex(),
            "anchor_sha256": self.anchor_digest(tree),
            "merkle_root_sha256": merkle_root(tree).hex(),
            "calldata": "0x" + calldata.hex(),
            "calldata_length": len(calldata),
            "structure": tree_structure(tree),
            "leaves": get_leaves(tree),
            "depth": tree_depth(tree),
            "trace_lengths": [len(t) for t in traces],
        }

    def challenge_payload(self, claimed_tree: CrystalTree, observed_tree: CrystalTree) -> dict:
        """Return an anchored structural-divergence challenge payload."""
        claimed_root, _ = self.commit(claimed_tree)
        observed_root, _ = self.commit(observed_tree)
        same_sorted_leaves = sorted(get_leaves(claimed_tree)) == sorted(get_leaves(observed_tree))
        localization = localize_difference(claimed_tree, observed_tree)
        localization_path = localization.get("path")
        return {
            "payload_version": "crystal-defi-challenge-v0",
            "challenge_type": "structural_divergence",
            "same_sorted_leaves": same_sorted_leaves,
            "different_crystal_root": claimed_root != observed_root,
            "different_anchor": self.anchor_digest(claimed_tree) != self.anchor_digest(observed_tree),
            "heads_that_differ": sum(1 for h in range(self.n_heads) if claimed_root[h] != observed_root[h]),
            "localization": localization,
            "local_merkle_proofs": {
                "claimed": merkle_localization_proof(claimed_tree, localization_path)
                if localization_path
                else None,
                "observed": merkle_localization_proof(observed_tree, localization_path)
                if localization_path
                else None,
            },
            "claimed": self.commitment_package(claimed_tree),
            "observed": self.commitment_package(observed_tree),
            "boundary": (
                "This payload localizes a structural disagreement, includes local Merkle "
                "proofs for the first differing path, and still carries full encoded trees "
                "for prototype verification."
            ),
        }

    def crystal_path_witness(self, tree: CrystalTree, path: str) -> dict:
        """Return a compact local Crystal witness for one path.

        The witness carries the localized subtree Crystal root plus sibling
        Crystal roots from that node back to the global tree root. It is not a
        cryptographic membership proof. Pair it with the Merkle/anchor proof
        for adversarial binding.
        """
        parts = _path_parts(path)
        current = tree
        siblings_root_to_node = []

        for part in parts:
            if is_leaf(current):
                return {
                    "witness_version": "crystal-defi-local-crystal-witness-v1",
                    "path": path,
                    "available": False,
                    "reason": "path_enters_leaf",
                }
            if part == "L":
                sibling = current.right
                sibling_root, _ = self.commit(sibling)
                siblings_root_to_node.append({
                    "sibling_side": "R",
                    "sibling_crystal_root": list(sibling_root),
                    "sibling_merkle_hash_sha256": merkle_root(sibling).hex(),
                    "sibling_structure": tree_structure(sibling),
                })
                current = current.left
            elif part == "R":
                sibling = current.left
                sibling_root, _ = self.commit(sibling)
                siblings_root_to_node.append({
                    "sibling_side": "L",
                    "sibling_crystal_root": list(sibling_root),
                    "sibling_merkle_hash_sha256": merkle_root(sibling).hex(),
                    "sibling_structure": tree_structure(sibling),
                })
                current = current.right
            else:
                return {
                    "witness_version": "crystal-defi-local-crystal-witness-v1",
                    "path": path,
                    "available": False,
                    "reason": "invalid_path",
                }

        target_root, _ = self.commit(current)
        full_root, _ = self.commit(tree)
        witness = {
            "witness_version": "crystal-defi-local-crystal-witness-v1",
            "path": path,
            "available": True,
            "target": {
                "node_type": "leaf" if is_leaf(current) else "internal",
                "leaf_value": current.state if is_leaf(current) else None,
                "structure": tree_structure(current),
                "crystal_root": list(target_root),
                "merkle_hash_sha256": merkle_root(current).hex(),
            },
            "steps_from_node_to_root": list(reversed(siblings_root_to_node)),
            "expected_root": list(full_root),
            "expected_root_hex": self.root_to_bytes32(full_root).hex(),
            "boundary": (
                "Local Crystal recomputation witness only. Pair with the Merkle "
                "proof and anchor digest to bind the localized node cryptographically."
            ),
        }
        computed_root = self.recompute_crystal_path_witness(witness)
        encoded = self.encode_crystal_path_witness(witness)
        witness.update({
            "computed_root": list(computed_root),
            "computed_root_hex": self.root_to_bytes32(computed_root).hex(),
            "valid": computed_root == full_root,
            "encoded": "0x" + encoded.hex(),
            "encoded_length": len(encoded),
        })
        return witness

    def encode_crystal_path_witness(self, witness: dict) -> bytes:
        """Encode a local Crystal witness for Solidity verification.

        Format:
            target root:       8 bytes
            step count:        1 byte
            repeated step:
              sibling side:    0x00 when sibling is right/current is left
                               0x01 when sibling is left/current is right
              sibling root:    8 bytes
        """
        if not witness.get("available"):
            raise ValueError("cannot encode unavailable witness")
        steps = witness["steps_from_node_to_root"]
        if len(steps) > 255:
            raise ValueError("path witness has too many steps")

        encoded = bytearray(witness["target"]["crystal_root"])
        if len(encoded) != self.n_heads:
            raise ValueError("target root length does not match head count")
        encoded.append(len(steps))

        for step in steps:
            side = step["sibling_side"]
            if side == "R":
                encoded.append(0)
            elif side == "L":
                encoded.append(1)
            else:
                raise ValueError(f"invalid sibling side: {side}")
            sibling = bytes(step["sibling_crystal_root"])
            if len(sibling) != self.n_heads:
                raise ValueError("sibling root length does not match head count")
            encoded.extend(sibling)

        return bytes(encoded)

    def recompute_crystal_path_witness(self, witness: dict) -> tuple:
        """Recompute the global Crystal root from a local path witness."""
        roots = list(witness["target"]["crystal_root"])
        for step in witness["steps_from_node_to_root"]:
            sibling = step["sibling_crystal_root"]
            next_roots = []
            for h in range(self.n_heads):
                if step["sibling_side"] == "R":
                    next_roots.append(int(self.tables[h][roots[h], sibling[h]]))
                elif step["sibling_side"] == "L":
                    next_roots.append(int(self.tables[h][sibling[h], roots[h]]))
                else:
                    raise ValueError(f"invalid sibling side: {step['sibling_side']}")
            roots = next_roots
        return tuple(roots)

    def challenge_payload_v1(self, claimed_tree: CrystalTree, observed_tree: CrystalTree) -> dict:
        """Return a draft V1 payload without full-tree calldata fields."""
        claimed_root, _ = self.commit(claimed_tree)
        observed_root, _ = self.commit(observed_tree)
        same_sorted_leaves = sorted(get_leaves(claimed_tree)) == sorted(get_leaves(observed_tree))
        localization = localize_difference(claimed_tree, observed_tree)
        localization_path = localization.get("path") or "root"
        claimed_package = self.commitment_package(claimed_tree)
        observed_package = self.commitment_package(observed_tree)

        def compact_commitment(package: dict) -> dict:
            return {
                key: value
                for key, value in package.items()
                if key not in ("calldata", "calldata_length", "trace_lengths")
            }

        return {
            "payload_version": "crystal-defi-challenge-v1-draft",
            "challenge_type": "structural_divergence",
            "same_sorted_leaves": same_sorted_leaves,
            "different_crystal_root": claimed_root != observed_root,
            "different_anchor": self.anchor_digest(claimed_tree) != self.anchor_digest(observed_tree),
            "heads_that_differ": sum(1 for h in range(self.n_heads) if claimed_root[h] != observed_root[h]),
            "localization": localization,
            "local_crystal_witnesses": {
                "claimed": self.crystal_path_witness(claimed_tree, localization_path),
                "observed": self.crystal_path_witness(observed_tree, localization_path),
            },
            "local_merkle_proofs": {
                "claimed": merkle_localization_proof(claimed_tree, localization_path),
                "observed": merkle_localization_proof(observed_tree, localization_path),
            },
            "claimed_commitment": compact_commitment(claimed_package),
            "observed_commitment": compact_commitment(observed_package),
            "full_tree_calldata_included": False,
            "boundary": (
                "Draft V1 removes full-tree calldata and carries local Crystal "
                "witnesses plus local Merkle proofs. Solidity verifies the local "
                "Crystal path and Merkle path, and the anchored challenge binds "
                "their path encodings plus the expected Merkle root to a posted "
                "per-tree anchor. The compact verifier now has active, challenged, "
                "finalized, and invalidated commitment states plus a pending-to-"
                "resolved localized challenge timeout. Remaining hardening gates "
                "are sound counterproof semantics, economic consequences, and "
                "production finality integration."
            ),
        }

    def decode_from_chain(self, data: bytes, offset: int = 0) -> Tuple[CrystalTree, int]:
        """Decode a tree from on-chain binary format."""
        node_type = data[offset]
        offset += 1

        if node_type == 0x00:
            state = data[offset]  # all heads have same leaf state
            offset += self.n_heads
            return CrystalLeaf(state=state), offset
        elif node_type == 0x01:
            left_tree, offset = self.decode_from_chain(data, offset)
            right_tree, offset = self.decode_from_chain(data, offset)
            return CrystalNode(left=left_tree, right=right_tree), offset
        else:
            raise ValueError(f"Invalid node type: {node_type}")

    def root_to_bytes32(self, root: tuple) -> bytes:
        """Pack a root fingerprint into 32 bytes (Solidity bytes32 format)."""
        result = bytearray(32)
        for h in range(self.n_heads):
            result[h] = root[h]
        return bytes(result)

    def bytes32_to_root(self, data: bytes) -> tuple:
        """Unpack a bytes32 into a root fingerprint."""
        return tuple(data[h] for h in range(self.n_heads))

    def export_tables(self) -> List[bytes]:
        """Export tables as raw bytes for on-chain deployment."""
        return [table.tobytes() for table in self.tables]

    def export_tables_hex(self) -> List[str]:
        """Export tables as hex strings for Solidity deployment."""
        return ['0x' + table.tobytes().hex() for table in self.tables]

    def export_component_tables(self) -> List[bytes]:
        """Export compact 4x4 component tables for production verifier work.

        Each head exports 64 bytes:
            4 components * 4 left states * 4 right states

        Each byte stores a two-bit value in the low bits. This is intentionally
        verbose versus bit-packing so Solidity prototype code can be simpler.
        """
        if not self._component_export_available:
            raise ValueError("Component export is only available for generated default tables")
        return [
            build_crystal_components(h, self.seed_base).reshape(-1).tobytes()
            for h in range(self.n_heads)
        ]

    def export_component_tables_hex(self) -> List[str]:
        """Export compact component tables as hex strings."""
        return ['0x' + table.hex() for table in self.export_component_tables()]

# ──────────────────────────────────────────────
#  Tree Parsing (from string notation)
# ──────────────────────────────────────────────

def parse_tree(s: str) -> CrystalTree:
    """Parse a tree from string notation.

    Examples:
        '42'           -> leaf(42)
        '(10,20)'      -> node(leaf(10), leaf(20))
        '((10,20),30)' -> node(node(leaf(10), leaf(20)), leaf(30))
    """
    s = s.strip()
    if not s.startswith('('):
        return leaf(int(s))

    # Find the comma that splits left and right at this depth
    depth = 0
    for i, ch in enumerate(s):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif ch == ',' and depth == 1:
            left_str = s[1:i]
            right_str = s[i+1:-1]
            return node(parse_tree(left_str), parse_tree(right_str))

    raise ValueError(f"Invalid tree string: {s}")

# ──────────────────────────────────────────────
#  CLI
# ──────────────────────────────────────────────

def cli():
    import argparse

    parser = argparse.ArgumentParser(description='Crystal Committer - structural divergence checks for transaction trees')
    subparsers = parser.add_subparsers(dest='command')

    # commit
    p_commit = subparsers.add_parser('commit', help='Compute crystal commitment for a tree')
    p_commit.add_argument('--tree', required=True, help='Tree in string notation, e.g. "((10,20),(30,40))"')

    # verify
    p_verify = subparsers.add_parser('verify', help='Verify a crystal commitment')
    p_verify.add_argument('--tree', required=True, help='Tree in string notation')
    p_verify.add_argument('--root', required=True, help='Expected root as comma-separated ints')

    # encode
    p_encode = subparsers.add_parser('encode', help='Encode tree for on-chain calldata')
    p_encode.add_argument('--tree', required=True, help='Tree in string notation')
    p_encode.add_argument('--output', default=None, help='Output file (default: stdout hex)')

    # package
    p_package = subparsers.add_parser('package', help='Emit anchored commitment package for a tree')
    p_package.add_argument('--tree', required=True, help='Tree in string notation')

    # challenge
    p_challenge = subparsers.add_parser('challenge', help='Emit anchored structural-divergence challenge payload')
    p_challenge.add_argument('--claimed-tree', required=True, help='Claimed tree in string notation')
    p_challenge.add_argument('--observed-tree', required=True, help='Observed tree in string notation')

    # challenge-v1
    p_challenge_v1 = subparsers.add_parser(
        'challenge-v1',
        help='Emit draft V1 local-witness challenge payload without full-tree calldata'
    )
    p_challenge_v1.add_argument('--claimed-tree', required=True, help='Claimed tree in string notation')
    p_challenge_v1.add_argument('--observed-tree', required=True, help='Observed tree in string notation')

    # witness
    p_witness = subparsers.add_parser('witness', help='Emit a local Crystal path witness')
    p_witness.add_argument('--tree', required=True, help='Tree in string notation')
    p_witness.add_argument('--path', required=True, help='Path such as root, root.L, or root.R.R')

    # export-tables
    p_export = subparsers.add_parser('export-tables', help='Export crystal tables for contract deployment')
    p_export.add_argument('--output', default='tables.json', help='Output JSON file')

    # export-components
    p_export_components = subparsers.add_parser(
        'export-components',
        help='Export compact component tables for production verifier work'
    )
    p_export_components.add_argument('--output', default='component_tables.json', help='Output JSON file')

    # compare
    p_compare = subparsers.add_parser('compare', help='Compare two trees (detect structural divergence)')
    p_compare.add_argument('--tree-a', required=True, help='First tree')
    p_compare.add_argument('--tree-b', required=True, help='Second tree')

    args = parser.parse_args()
    committer = CrystalCommitter()

    if args.command == 'commit':
        tree = parse_tree(args.tree)
        root, traces = committer.commit(tree)
        print(json.dumps({
            'root': list(root),
            'root_hex': committer.root_to_bytes32(root).hex(),
            'anchor_sha256': committer.anchor_digest(tree),
            'table_commitment_sha256': committer.table_commitment(),
            'structure': tree_structure(tree),
            'leaves': get_leaves(tree),
            'depth': tree_depth(tree),
        }, indent=2))

    elif args.command == 'verify':
        tree = parse_tree(args.tree)
        root = tuple(int(x) for x in args.root.split(','))
        is_valid = committer.verify(tree, root)
        print(json.dumps({
            'valid': is_valid,
            'claimed_root': list(root),
            'structure': tree_structure(tree),
        }, indent=2))

    elif args.command == 'encode':
        tree = parse_tree(args.tree)
        data = committer.encode_for_chain(tree)
        if args.output:
            with open(args.output, 'wb') as f:
                f.write(data)
            print(f"Encoded {len(data)} bytes to {args.output}")
        else:
            print(f"0x{data.hex()}")

    elif args.command == 'package':
        tree = parse_tree(args.tree)
        print(json.dumps(committer.commitment_package(tree), indent=2))

    elif args.command == 'challenge':
        claimed_tree = parse_tree(args.claimed_tree)
        observed_tree = parse_tree(args.observed_tree)
        print(json.dumps(committer.challenge_payload(claimed_tree, observed_tree), indent=2))

    elif args.command == 'challenge-v1':
        claimed_tree = parse_tree(args.claimed_tree)
        observed_tree = parse_tree(args.observed_tree)
        print(json.dumps(committer.challenge_payload_v1(claimed_tree, observed_tree), indent=2))

    elif args.command == 'witness':
        tree = parse_tree(args.tree)
        print(json.dumps(committer.crystal_path_witness(tree, args.path), indent=2))

    elif args.command == 'export-tables':
        tables_hex = committer.export_tables_hex()
        output = {
            'n_heads': committer.n_heads,
            'state_size': STATE_SIZE,
            'format': 'full_256x256_tables',
            'tables': tables_hex,
        }
        with open(args.output, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"Exported {len(tables_hex)} tables to {args.output}")

    elif args.command == 'export-components':
        tables_hex = committer.export_component_tables_hex()
        output = {
            'n_heads': committer.n_heads,
            'state_size': STATE_SIZE,
            'format': 'component_4x4_tables_unpacked_bytes',
            'bytes_per_head': 64,
            'tables': tables_hex,
        }
        with open(args.output, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"Exported {len(tables_hex)} compact component tables to {args.output}")

    elif args.command == 'compare':
        tree_a = parse_tree(args.tree_a)
        tree_b = parse_tree(args.tree_b)
        root_a, _ = committer.commit(tree_a)
        root_b, _ = committer.commit(tree_b)

        leaves_a = sorted(get_leaves(tree_a))
        leaves_b = sorted(get_leaves(tree_b))
        same_leaves = leaves_a == leaves_b
        different_root = root_a != root_b
        heads_differ = sum(1 for h in range(N_HEADS) if root_a[h] != root_b[h])

        structural_divergence = same_leaves and different_root

        print(json.dumps({
            'structure_a': tree_structure(tree_a),
            'structure_b': tree_structure(tree_b),
            'same_leaves': same_leaves,
            'different_crystal_root': different_root,
            'heads_that_differ': heads_differ,
            'root_a': list(root_a),
            'root_b': list(root_b),
            'anchor_a_sha256': committer.anchor_digest(tree_a),
            'anchor_b_sha256': committer.anchor_digest(tree_b),
            'different_anchor': committer.anchor_digest(tree_a) != committer.anchor_digest(tree_b),
            'structural_divergence': structural_divergence,
            'structural_fraud_deprecated': structural_divergence,
        }, indent=2))

    else:
        parser.print_help()

if __name__ == '__main__':
    cli()
