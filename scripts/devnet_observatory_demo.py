#!/usr/bin/env python3
"""Run a local Crystal DeFi devnet observatory demo.

This starts Anvil unless --rpc-url is supplied, deploys the compact component
verifier, initializes the 512-byte component table set, posts an intentionally
wrong per-tree root, submits a local path-witness consistency challenge, and
advances the response window to resolve the pending challenge before writing
reproducible JSON/Markdown evidence under demo/results/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "demo" / "results"
DEFAULT_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

sys.path.insert(0, str(ROOT / "sdk"))
from crystal_committer import CrystalCommitter, parse_tree  # noqa: E402


class CommandError(RuntimeError):
    def __init__(self, command: list[str], completed: subprocess.CompletedProcess[str]):
        self.command = command
        self.completed = completed
        super().__init__(
            "command failed\n"
            f"command: {' '.join(command)}\n"
            f"exit: {completed.returncode}\n"
            f"stdout: {completed.stdout[-2000:]}\n"
            f"stderr: {completed.stderr[-2000:]}"
        )


def require_tool(name: str) -> str:
    tool = shutil.which(name)
    if not tool:
        raise SystemExit(f"Required tool not found on PATH: {name}")
    return tool


def run(command: list[str], timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("NO_COLOR", "1")
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if check and completed.returncode != 0:
        raise CommandError(command, completed)
    return completed


def parse_json_output(text: str) -> dict[str, Any]:
    for line in reversed(text.splitlines()):
        candidate = line.strip()
        if candidate.startswith("{") and candidate.endswith("}"):
            return json.loads(candidate)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError(f"no JSON object found in output: {text[-1000:]}")


def find_free_port(preferred: int) -> int:
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(f"no free local port found from {preferred} to {preferred + 19}")


def wait_for_rpc(rpc_url: str, cast: str, timeout_seconds: int = 20) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        completed = run([cast, "chain-id", "--rpc-url", rpc_url], timeout=5, check=False)
        if completed.returncode == 0:
            return
        time.sleep(0.25)
    raise RuntimeError(f"RPC endpoint did not become ready: {rpc_url}")


def start_anvil(anvil: str, cast: str, preferred_port: int) -> tuple[subprocess.Popen[str], str]:
    port = find_free_port(preferred_port)
    rpc_url = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [anvil, "--host", "127.0.0.1", "--port", str(port), "--silent"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        wait_for_rpc(rpc_url, cast)
    except Exception:
        process.terminate()
        process.wait(timeout=5)
        raise
    return process, rpc_url


def tx_hash(receipt: dict[str, Any]) -> str | None:
    return receipt.get("transactionHash") or receipt.get("hash")


def parse_quantity(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        token = value.strip().split()[0]
        if not token:
            return None
        if token.startswith("0x"):
            return int(token, 16)
        return int(token)
    return None


def receipt_gas_used(receipt: dict[str, Any]) -> int | None:
    return parse_quantity(receipt.get("gasUsed") or receipt.get("gas_used"))


def hex_byte_length(hex_data: str) -> int:
    value = hex_data[2:] if hex_data.startswith("0x") else hex_data
    return len(value) // 2


def deploy_contract(forge: str, rpc_url: str, private_key: str) -> dict[str, Any]:
    completed = run(
        [
            forge,
            "create",
            "contracts/CrystalComponentVerifier.sol:CrystalComponentVerifier",
            "--rpc-url",
            rpc_url,
            "--private-key",
            private_key,
            "--broadcast",
            "--json",
        ],
        timeout=180,
    )
    deployed = parse_json_output(completed.stdout + "\n" + completed.stderr)
    address = deployed.get("deployedTo") or deployed.get("contractAddress")
    if not address:
        raise RuntimeError(f"forge create JSON did not include deployed address: {deployed}")
    deployed["address"] = address
    return deployed


def cast_send(cast: str, rpc_url: str, private_key: str, args: list[str]) -> dict[str, Any]:
    completed = run(
        [
            cast,
            "send",
            *args,
            "--rpc-url",
            rpc_url,
            "--private-key",
            private_key,
            "--json",
        ],
        timeout=120,
    )
    return parse_json_output(completed.stdout + "\n" + completed.stderr)


def cast_call(cast: str, rpc_url: str, args: list[str]) -> str:
    completed = run([cast, "call", *args, "--rpc-url", rpc_url], timeout=60)
    return completed.stdout.strip()


def cast_calldata(cast: str, args: list[str]) -> str:
    completed = run([cast, "calldata", *args], timeout=30)
    return completed.stdout.strip()


def cast_rpc(cast: str, rpc_url: str, method: str, params: list[str] | None = None) -> str:
    completed = run([cast, "rpc", "--rpc-url", rpc_url, method, *(params or [])], timeout=30)
    return completed.stdout.strip()


def wallet_address(cast: str, private_key: str) -> str:
    completed = run([cast, "wallet", "address", "--private-key", private_key], timeout=30)
    return completed.stdout.strip()


def cast_first_word(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    return stripped.splitlines()[0].split()[0]


def write_markdown(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# Crystal DeFi Devnet Observatory Demo",
        "",
        f"Generated UTC: `{result['generated_at_utc']}`",
        "",
        "## Result",
        "",
        "```text",
        f"ok: {result['ok']}",
        f"contract: {result['contract_address']}",
        f"rpc_url: {result['rpc_url']}",
        f"challenge_marked: {result['challenge_marked']}",
        f"challenge_pending: {result['challenge_pending']}",
        f"challenge_resolved: {result['challenge_resolved']}",
        f"challenge_invalidated: {result['challenge_invalidated']}",
        "```",
        "",
        "## Scenario",
        "",
        "```text",
        f"claimed_tree: {result['claimed_tree']}",
        f"observed_tree: {result['observed_tree']}",
        f"block_hash: {result['block_hash']}",
        f"tree_index: {result['tree_index']}",
        f"challenge_id: {result['anchored_challenge_id']}",
        "```",
        "",
        "## Roots",
        "",
        "```text",
        f"claimed_crystal_root: 0x{result['claimed_package']['crystal_root_hex']}",
        f"posted_wrong_root: {result['posted_wrong_root']}",
        f"claimed_witness_encoded: {result['claimed_witness_encoded']}",
        f"claimed_witness_encoded_length: {result['claimed_witness_encoded_length']}",
        f"claimed_merkle_proof_encoded: {result['claimed_merkle_proof_encoded']}",
        f"claimed_merkle_proof_encoded_length: {result['claimed_merkle_proof_encoded_length']}",
        f"localized_v1_proof_bytes: {result['localized_v1_proof_bytes']}",
        f"commit_tx_calldata_bytes: {result['commit_tx_calldata_bytes']}",
        f"challenge_tx_calldata_bytes: {result['challenge_tx_calldata_bytes']}",
        f"resolve_tx_calldata_bytes: {result['resolve_tx_calldata_bytes']}",
        f"claimed_anchor_sha256: {result['claimed_package']['anchor_sha256']}",
        f"observed_anchor_sha256: {result['observed_package']['anchor_sha256']}",
        f"posted_merkle_root: {result['posted_merkle_root']}",
        "```",
        "",
        "## On-Chain Calls",
        "",
        "```text",
        f"deploy_tx: {result['deploy_tx']}",
        f"commit_tx: {result['commit_tx']}",
        f"commit_gas_used: {result['commit_gas_used']}",
        f"challenge_tx: {result['challenge_tx']}",
        f"challenge_gas_used: {result['challenge_gas_used']}",
        f"resolve_tx: {result['resolve_tx']}",
        f"resolve_gas_used: {result['resolve_gas_used']}",
        f"anchored_status_after_commit_output: {result['anchored_status_after_commit_output']}",
        f"anchored_deadline_output: {result['anchored_deadline_output']}",
        f"anchored_status_after_submit_output: {result['anchored_status_after_submit_output']}",
        f"anchored_status_after_resolve_output: {result['anchored_status_after_resolve_output']}",
        f"anchored_commitment_after_submit_output: {result['anchored_commitment_after_submit_output']}",
        f"anchored_commitment_after_resolve_output: {result['anchored_commitment_after_resolve_output']}",
        f"anchored_challenge_pending_record_output: {result['anchored_challenge_pending_record_output']}",
        f"anchored_challenge_resolved_record_output: {result['anchored_challenge_resolved_record_output']}",
        f"verify_call_output: {result['verify_call_output']}",
        f"witness_call_output: {result['witness_call_output']}",
        f"localized_path_call_output: {result['localized_path_call_output']}",
        f"localized_path_binding_call_output: {result['localized_path_binding_call_output']}",
        f"is_challenged_output: {result['is_challenged_output']}",
        "```",
        "",
        "## Boundary",
        "",
        "Crystal roots are used here as structural signals. The demo posts a",
        "wrong root and challenges it with a local Crystal path witness on a",
        "local Ethereum devnet. It also verifies the localized Merkle path for",
        "the same claimed path. The anchored commitment opens an explicit",
        "challenge window, records the localized mismatch as pending, then",
        "invalidates the posted commitment only after the response window is",
        "advanced and the challenge is resolved. Production economic",
        "consequences remain out of scope.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Crystal DeFi local devnet demo")
    parser.add_argument("--rpc-url", default=None, help="use an existing Ethereum JSON-RPC endpoint")
    parser.add_argument("--port", type=int, default=8545, help="preferred Anvil port when starting devnet")
    parser.add_argument("--private-key", default=DEFAULT_PRIVATE_KEY, help="deployer key")
    parser.add_argument("--claimed-tree", default="((10,20),(30,40))")
    parser.add_argument("--observed-tree", default="(10,(20,(30,40)))")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--keep-anvil", action="store_true", help="leave started Anvil process running")
    args = parser.parse_args()

    forge = require_tool("forge")
    cast = require_tool("cast")
    anvil = require_tool("anvil")

    anvil_process: subprocess.Popen[str] | None = None
    rpc_url = args.rpc_url
    if rpc_url is None:
        anvil_process, rpc_url = start_anvil(anvil, cast, args.port)
    else:
        wait_for_rpc(rpc_url, cast)

    try:
        committer = CrystalCommitter()
        challenger = wallet_address(cast, args.private_key)
        claimed_tree = parse_tree(args.claimed_tree)
        observed_tree = parse_tree(args.observed_tree)
        claimed_package = committer.commitment_package(claimed_tree)
        observed_package = committer.commitment_package(observed_tree)
        v1_payload = committer.challenge_payload_v1(claimed_tree, observed_tree)
        claimed_witness = v1_payload["local_crystal_witnesses"]["claimed"]
        claimed_merkle_proof = v1_payload["local_merkle_proofs"]["claimed"]
        component_tables = committer.export_component_tables_hex()

        deployment = deploy_contract(forge, rpc_url, args.private_key)
        address = deployment["address"]

        init_txs = []
        for head_index, table_hex in enumerate(component_tables):
            receipt = cast_send(
                cast,
                rpc_url,
                args.private_key,
                [
                    address,
                    "initializeHead(uint256,bytes)",
                    str(head_index),
                    table_hex,
                ],
            )
            init_txs.append({"head": head_index, "tx": tx_hash(receipt), "receipt": receipt})

        finalize_receipt = cast_send(
            cast,
            rpc_url,
            args.private_key,
            [address, "finalizeInitialization()"],
        )

        block_hash = "0x" + hashlib.sha256(b"crystal-defi-demo-block-v0").hexdigest()
        tree_index = 0
        posted_wrong_root = "0x" + observed_package["crystal_root_hex"]
        claimed_root = "0x" + claimed_package["crystal_root_hex"]
        calldata = claimed_package["calldata"]
        witness_data = claimed_witness["encoded"]
        target_merkle_hash = "0x" + claimed_merkle_proof["node_hash_sha256"]
        merkle_proof_data = claimed_merkle_proof["encoded"]
        expected_merkle_root = "0x" + claimed_merkle_proof["merkle_root_sha256"]
        localized_v1_proof_bytes = (
            claimed_witness["encoded_length"]
            + 32
            + claimed_merkle_proof["encoded_length"]
        )

        verify_call_output = cast_call(
            cast,
            rpc_url,
            [
                address,
                "verifyTreeRoot(bytes,bytes32)(bool,bytes32)",
                calldata,
                claimed_root,
            ],
        )

        witness_call_output = cast_call(
            cast,
            rpc_url,
            [
                address,
                "verifyCrystalPath(bytes,bytes32)(bool,bytes32)",
                witness_data,
                claimed_root,
            ],
        )

        localized_path_call_output = cast_call(
            cast,
            rpc_url,
            [
                address,
                "verifyLocalizedPath(bytes,bytes32,bytes32,bytes,bytes32)(bool,bool,bytes32,bytes32)",
                witness_data,
                claimed_root,
                target_merkle_hash,
                merkle_proof_data,
                expected_merkle_root,
            ],
        )

        localized_path_binding_call_output = cast_call(
            cast,
            rpc_url,
            [
                address,
                "verifyLocalizedPathBinding(bytes,bytes)(bool)",
                witness_data,
                merkle_proof_data,
            ],
        )

        commit_calldata = cast_calldata(
            cast,
            [
                "commitAnchoredTree(bytes32,uint256,bytes32,bytes32)",
                block_hash,
                str(tree_index),
                posted_wrong_root,
                expected_merkle_root,
            ],
        )

        challenge_calldata = cast_calldata(
            cast,
            [
                "submitAnchoredLocalizedChallenge(bytes32,uint256,bytes,bytes32,bytes)",
                block_hash,
                str(tree_index),
                witness_data,
                target_merkle_hash,
                merkle_proof_data,
            ],
        )

        commit_receipt = cast_send(
            cast,
            rpc_url,
            args.private_key,
            [
                address,
                "commitAnchoredTree(bytes32,uint256,bytes32,bytes32)",
                block_hash,
                str(tree_index),
                posted_wrong_root,
                expected_merkle_root,
            ],
        )

        anchored_status_after_commit_output = cast_call(
            cast,
            rpc_url,
            [
                address,
                "getAnchoredTreeStatus(bytes32,uint256)(uint8)",
                block_hash,
                str(tree_index),
            ],
        )

        anchored_deadline_output = cast_call(
            cast,
            rpc_url,
            [
                address,
                "getAnchoredTreeChallengeDeadline(bytes32,uint256)(uint64)",
                block_hash,
                str(tree_index),
            ],
        )

        anchored_challenge_id = cast_call(
            cast,
            rpc_url,
            [
                address,
                "computeLocalizedChallengeId(bytes32,uint256,address,bytes32,bytes32,bytes32,bytes32)(bytes32)",
                block_hash,
                str(tree_index),
                challenger,
                posted_wrong_root,
                expected_merkle_root,
                claimed_root,
                target_merkle_hash,
            ],
        )

        resolve_calldata = cast_calldata(
            cast,
            [
                "resolveAnchoredLocalizedChallenge(bytes32)",
                anchored_challenge_id,
            ],
        )

        challenge_receipt = cast_send(
            cast,
            rpc_url,
            args.private_key,
            [
                address,
                "submitAnchoredLocalizedChallenge(bytes32,uint256,bytes,bytes32,bytes)",
                block_hash,
                str(tree_index),
                witness_data,
                target_merkle_hash,
                merkle_proof_data,
            ],
        )

        anchored_challenge_pending_record_output = cast_call(
            cast,
            rpc_url,
            [
                address,
                "localizedChallenges(bytes32)(uint8,bytes32,uint256,address,bytes32,bytes32,bytes32,bytes32,bytes32,uint64,uint64)",
                anchored_challenge_id,
            ],
        )

        anchored_status_after_submit_output = cast_call(
            cast,
            rpc_url,
            [
                address,
                "getAnchoredTreeStatus(bytes32,uint256)(uint8)",
                block_hash,
                str(tree_index),
            ],
        )

        anchored_commitment_after_submit_output = cast_call(
            cast,
            rpc_url,
            [
                address,
                "anchoredTreeCommitments(bytes32,uint256)(uint8,bytes32,bytes32,address,uint64,uint64)",
                block_hash,
                str(tree_index),
            ],
        )

        cast_rpc(cast, rpc_url, "evm_increaseTime", ["3600"])
        cast_rpc(cast, rpc_url, "evm_mine")

        resolve_receipt = cast_send(
            cast,
            rpc_url,
            args.private_key,
            [
                address,
                "resolveAnchoredLocalizedChallenge(bytes32)",
                anchored_challenge_id,
            ],
        )

        anchored_challenge_resolved_record_output = cast_call(
            cast,
            rpc_url,
            [
                address,
                "localizedChallenges(bytes32)(uint8,bytes32,uint256,address,bytes32,bytes32,bytes32,bytes32,bytes32,uint64,uint64)",
                anchored_challenge_id,
            ],
        )

        anchored_status_after_resolve_output = cast_call(
            cast,
            rpc_url,
            [
                address,
                "getAnchoredTreeStatus(bytes32,uint256)(uint8)",
                block_hash,
                str(tree_index),
            ],
        )

        anchored_commitment_after_resolve_output = cast_call(
            cast,
            rpc_url,
            [
                address,
                "anchoredTreeCommitments(bytes32,uint256)(uint8,bytes32,bytes32,address,uint64,uint64)",
                block_hash,
                str(tree_index),
            ],
        )

        is_challenged_output = cast_call(
            cast,
            rpc_url,
            [address, "isChallenged(bytes32)(bool)", block_hash],
        )
        challenge_marked = "true" in is_challenged_output.lower()
        localized_path_bound = "true" in localized_path_binding_call_output.lower()
        challenge_pending = cast_first_word(anchored_challenge_pending_record_output) == "1"
        challenge_resolved = cast_first_word(anchored_challenge_resolved_record_output) == "2"
        challenge_status_challenged = cast_first_word(anchored_status_after_submit_output) == "2"
        challenge_invalidated = cast_first_word(anchored_status_after_resolve_output) == "4"
        ok = (
            challenge_pending
            and challenge_resolved
            and challenge_status_challenged
            and challenge_marked
            and challenge_invalidated
            and localized_path_bound
        )

        result = {
            "ok": ok,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "rpc_url": rpc_url,
            "contract_address": address,
            "challenger": challenger,
            "deploy_tx": deployment.get("transactionHash") or deployment.get("txHash"),
            "init_txs": init_txs,
            "finalize_tx": tx_hash(finalize_receipt),
            "commit_tx": tx_hash(commit_receipt),
            "challenge_tx": tx_hash(challenge_receipt),
            "resolve_tx": tx_hash(resolve_receipt),
            "commit_gas_used": receipt_gas_used(commit_receipt),
            "challenge_gas_used": receipt_gas_used(challenge_receipt),
            "resolve_gas_used": receipt_gas_used(resolve_receipt),
            "claimed_tree": args.claimed_tree,
            "observed_tree": args.observed_tree,
            "claimed_package": claimed_package,
            "observed_package": observed_package,
            "challenge_v1_payload": v1_payload,
            "claimed_witness_encoded": witness_data,
            "claimed_witness_encoded_length": claimed_witness["encoded_length"],
            "claimed_merkle_proof_encoded": merkle_proof_data,
            "claimed_merkle_proof_encoded_length": claimed_merkle_proof["encoded_length"],
            "target_merkle_hash_bytes": 32,
            "localized_v1_proof_bytes": localized_v1_proof_bytes,
            "full_tree_calldata_bytes": hex_byte_length(calldata),
            "commit_tx_calldata": commit_calldata,
            "commit_tx_calldata_bytes": hex_byte_length(commit_calldata),
            "challenge_tx_calldata": challenge_calldata,
            "challenge_tx_calldata_bytes": hex_byte_length(challenge_calldata),
            "resolve_tx_calldata": resolve_calldata,
            "resolve_tx_calldata_bytes": hex_byte_length(resolve_calldata),
            "posted_wrong_root": posted_wrong_root,
            "posted_merkle_root": expected_merkle_root,
            "block_hash": block_hash,
            "tree_index": tree_index,
            "anchored_challenge_id": anchored_challenge_id,
            "anchored_challenge_record_output": anchored_challenge_resolved_record_output,
            "anchored_challenge_pending_record_output": anchored_challenge_pending_record_output,
            "anchored_challenge_resolved_record_output": anchored_challenge_resolved_record_output,
            "anchored_status_after_commit_output": anchored_status_after_commit_output,
            "anchored_deadline_output": anchored_deadline_output,
            "anchored_status_after_challenge_output": anchored_status_after_resolve_output,
            "anchored_status_after_submit_output": anchored_status_after_submit_output,
            "anchored_status_after_resolve_output": anchored_status_after_resolve_output,
            "anchored_commitment_after_challenge_output": anchored_commitment_after_resolve_output,
            "anchored_commitment_after_submit_output": anchored_commitment_after_submit_output,
            "anchored_commitment_after_resolve_output": anchored_commitment_after_resolve_output,
            "verify_call_output": verify_call_output,
            "witness_call_output": witness_call_output,
            "localized_path_call_output": localized_path_call_output,
            "localized_path_binding_call_output": localized_path_binding_call_output,
            "is_challenged_output": is_challenged_output,
            "challenge_marked": challenge_marked,
            "challenge_pending": challenge_pending,
            "challenge_resolved": challenge_resolved,
            "challenge_status_challenged": challenge_status_challenged,
            "localized_path_bound": localized_path_bound,
            "challenge_invalidated": challenge_invalidated,
            "boundary": "Crystal localizes; hash anchors prove.",
        }

        results_dir = args.results_dir.expanduser().resolve()
        results_dir.mkdir(parents=True, exist_ok=True)
        json_path = results_dir / "devnet_observatory_latest.json"
        md_path = results_dir / "devnet_observatory_latest.md"
        json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        write_markdown(result, md_path)

        print(
            json.dumps(
                {
                    "ok": ok,
                    "contract_address": address,
                    "json": str(json_path),
                    "markdown": str(md_path),
                    "challenge_marked": challenge_marked,
                    "challenge_pending": challenge_pending,
                    "challenge_resolved": challenge_resolved,
                    "localized_path_bound": localized_path_bound,
                    "challenge_invalidated": challenge_invalidated,
                },
                indent=2,
            )
        )
        return 0 if ok else 1
    finally:
        if anvil_process is not None and not args.keep_anvil:
            anvil_process.terminate()
            try:
                anvil_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                anvil_process.kill()
                anvil_process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
