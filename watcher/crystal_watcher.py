"""
Crystal Watcher Service
========================
Off-chain monitoring service that watches L2 blocks, re-folds Crystal
commitments, computes hash anchors, and reports structural divergence.

Run as standalone server:
    python crystal_watcher.py --port 8420

API endpoints:
    POST /verify          — verify a tree against a claimed root
    POST /compare         — compare two trees for structural divergence
    POST /verify-block    — verify all trees in a block
    POST /encode          — encode tree for on-chain calldata
    GET  /health          — health check
    GET  /stats           — verification statistics

Licensed under Apache-2.0.
"""

import json
import time
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sdk'))
from crystal_committer import (
    CrystalCommitter, CrystalTree, CrystalLeaf, CrystalNode,
    parse_tree, tree_structure, get_leaves, tree_depth,
    leaf, node, is_leaf, N_HEADS
)

# ──────────────────────────────────────────────
#  Watcher State
# ──────────────────────────────────────────────

class WatcherState:
    """Tracks verification statistics and structural-divergence events."""

    def __init__(self):
        self.committer = CrystalCommitter()
        self.trees_verified = 0
        self.blocks_verified = 0
        self.structural_divergence_events = 0
        self.fraud_proofs_generated = 0  # Deprecated compatibility counter.
        self.structural_mismatches = 0
        self.start_time = time.time()
        self.recent_proofs = []  # Deprecated name: last 100 divergence reports.

    def verify_tree(self, tree: CrystalTree, claimed_root: tuple) -> Dict[str, Any]:
        """Verify a single tree against a claimed root."""
        computed_root, traces = self.committer.commit(tree)
        is_valid = computed_root == claimed_root
        self.trees_verified += 1

        if not is_valid:
            self.structural_mismatches += 1

        heads_match = [computed_root[h] == claimed_root[h] for h in range(N_HEADS)]

        return {
            'valid': is_valid,
            'claimed_root': list(claimed_root),
            'computed_root': list(computed_root),
            'anchor_sha256': self.committer.anchor_digest(tree),
            'table_commitment_sha256': self.committer.table_commitment(),
            'heads_match': heads_match,
            'heads_matching': sum(heads_match),
            'structure': tree_structure(tree),
            'n_leaves': len(get_leaves(tree)),
            'depth': tree_depth(tree),
        }

    def compare_trees(self, tree_a: CrystalTree, tree_b: CrystalTree) -> Dict[str, Any]:
        """Compare two trees and report structural divergence."""
        root_a, _ = self.committer.commit(tree_a)
        root_b, _ = self.committer.commit(tree_b)

        leaves_a = sorted(get_leaves(tree_a))
        leaves_b = sorted(get_leaves(tree_b))
        same_leaves = leaves_a == leaves_b
        different_root = root_a != root_b
        heads_differ = sum(1 for h in range(N_HEADS) if root_a[h] != root_b[h])

        structural_divergence = same_leaves and different_root

        if structural_divergence:
            self.structural_divergence_events += 1
            self.fraud_proofs_generated += 1
            proof = {
                'timestamp': time.time(),
                'type': 'structural_divergence',
                'structure_a': tree_structure(tree_a),
                'structure_b': tree_structure(tree_b),
                'root_a': list(root_a),
                'root_b': list(root_b),
                'heads_differ': heads_differ,
            }
            self.recent_proofs.append(proof)
            if len(self.recent_proofs) > 100:
                self.recent_proofs = self.recent_proofs[-100:]

        return {
            'structural_divergence': structural_divergence,
            'structural_fraud_detected_deprecated': structural_divergence,
            'same_leaves': same_leaves,
            'different_crystal_root': different_root,
            'heads_that_differ': heads_differ,
            'structure_a': tree_structure(tree_a),
            'structure_b': tree_structure(tree_b),
            'root_a': list(root_a),
            'root_b': list(root_b),
            'root_a_hex': self.committer.root_to_bytes32(root_a).hex(),
            'root_b_hex': self.committer.root_to_bytes32(root_b).hex(),
            'anchor_a_sha256': self.committer.anchor_digest(tree_a),
            'anchor_b_sha256': self.committer.anchor_digest(tree_b),
            'different_anchor': self.committer.anchor_digest(tree_a) != self.committer.anchor_digest(tree_b),
            'table_commitment_sha256': self.committer.table_commitment(),
            'localization': self.committer.challenge_payload(tree_a, tree_b)['localization'],
            'calldata_a': '0x' + self.committer.encode_for_chain(tree_a).hex(),
            'calldata_b': '0x' + self.committer.encode_for_chain(tree_b).hex(),
        }

    def verify_block(self, trees_and_roots: list) -> Dict[str, Any]:
        """Verify all trees in a block."""
        results = []
        all_valid = True

        for item in trees_and_roots:
            tree = parse_tree(item['tree'])
            claimed = tuple(item['root'])
            result = self.verify_tree(tree, claimed)
            results.append(result)
            if not result['valid']:
                all_valid = False

        self.blocks_verified += 1

        return {
            'block_valid': all_valid,
            'trees_checked': len(results),
            'trees_valid': sum(1 for r in results if r['valid']),
            'trees_invalid': sum(1 for r in results if not r['valid']),
            'results': results,
        }

    def get_stats(self) -> Dict[str, Any]:
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': round(uptime, 1),
            'trees_verified': self.trees_verified,
            'blocks_verified': self.blocks_verified,
            'structural_divergence_events': self.structural_divergence_events,
            'fraud_proofs_generated': self.fraud_proofs_generated,
            'structural_mismatches': self.structural_mismatches,
            'verification_rate': round(self.trees_verified / max(uptime, 1), 1),
            'recent_proofs': self.recent_proofs[-10:],
        }

# ──────────────────────────────────────────────
#  HTTP Handler
# ──────────────────────────────────────────────

state = WatcherState()

class WatcherHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the watcher API."""

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def _read_body(self) -> dict:
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        return json.loads(body) if body else {}

    def do_OPTIONS(self):
        self._send_json({})

    def do_GET(self):
        if self.path == '/health':
            self._send_json({'status': 'ok', 'service': 'crystal-watcher'})

        elif self.path == '/stats':
            self._send_json(state.get_stats())

        else:
            self._send_json({'error': 'not found'}, 404)

    def do_POST(self):
        try:
            body = self._read_body()

            if self.path == '/verify':
                tree = parse_tree(body['tree'])
                claimed_root = tuple(body['root'])
                result = state.verify_tree(tree, claimed_root)
                self._send_json(result)

            elif self.path == '/compare':
                tree_a = parse_tree(body['tree_a'])
                tree_b = parse_tree(body['tree_b'])
                result = state.compare_trees(tree_a, tree_b)
                self._send_json(result)

            elif self.path == '/challenge':
                claimed_tree = parse_tree(body['claimed_tree'])
                observed_tree = parse_tree(body['observed_tree'])
                self._send_json(state.committer.challenge_payload(claimed_tree, observed_tree))

            elif self.path == '/challenge-v1':
                claimed_tree = parse_tree(body['claimed_tree'])
                observed_tree = parse_tree(body['observed_tree'])
                self._send_json(state.committer.challenge_payload_v1(claimed_tree, observed_tree))

            elif self.path == '/witness':
                tree = parse_tree(body['tree'])
                self._send_json(state.committer.crystal_path_witness(tree, body['path']))

            elif self.path == '/verify-block':
                result = state.verify_block(body['trees'])
                self._send_json(result)

            elif self.path == '/encode':
                tree = parse_tree(body['tree'])
                self._send_json(state.committer.commitment_package(tree))

            elif self.path == '/commit':
                tree = parse_tree(body['tree'])
                self._send_json(state.committer.commitment_package(tree))

            else:
                self._send_json({'error': 'not found'}, 404)

        except Exception as e:
            self._send_json({'error': str(e)}, 400)

    def log_message(self, format, *args):
        # Quieter logging
        pass

# ──────────────────────────────────────────────
#  Server
# ──────────────────────────────────────────────

def run_server(port: int = 8420):
    server = HTTPServer(('0.0.0.0', port), WatcherHandler)
    print(f"Crystal Watcher running on port {port}")
    print(f"  POST /commit        — compute crystal commitment")
    print(f"  POST /verify        — verify tree against root")
    print(f"  POST /compare       — detect structural divergence")
    print(f"  POST /challenge     — emit anchored challenge payload")
    print(f"  POST /challenge-v1  — emit draft V1 local-witness challenge payload")
    print(f"  POST /witness       — emit a local Crystal path witness")
    print(f"  POST /verify-block  — verify all trees in a block")
    print(f"  POST /encode        — encode tree for on-chain calldata")
    print(f"  GET  /health        — health check")
    print(f"  GET  /stats         — verification statistics")
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Crystal Watcher Service')
    parser.add_argument('--port', type=int, default=8420, help='Port (default: 8420)')
    args = parser.parse_args()
    run_server(args.port)
