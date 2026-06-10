#!/usr/bin/env python3
"""Crystal DeFi grant-readiness checklist.

This script is intentionally conservative. It does not decide whether a grant
will be awarded; it reports whether the local artifact has the evidence and
public-goods boundaries a reviewer is likely to expect.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPEN_CORE_ROOT = ROOT.parent / "crystal-defi-open-core"


def exists(path: str) -> bool:
    return (ROOT / path).exists()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def first_word(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    return stripped.splitlines()[0].split()[0]


def has_open_license(path: Path) -> bool:
    if not path.exists():
        return False
    text = read_text(path).lower()
    return ("apache license" in text or "mit license" in text) and "busl" not in text


def open_core_resolved() -> bool:
    source_license = ROOT / "LICENSE"
    sibling_license = OPEN_CORE_ROOT / "LICENSE"
    sibling_manifest = OPEN_CORE_ROOT / "OPEN_CORE_MANIFEST.json"
    return (
        has_open_license(source_license)
        or (has_open_license(sibling_license) and sibling_manifest.exists())
    )


def current_directory_is_open_core() -> bool:
    return has_open_license(ROOT / "LICENSE") and (ROOT / "OPEN_CORE_MANIFEST.json").exists()


def demo_result_ok() -> bool:
    result_path = ROOT / "demo/results/devnet_observatory_latest.json"
    if not result_path.exists():
        return False
    try:
        result = json.loads(read_text(result_path))
    except json.JSONDecodeError:
        return False
    v1_payload = result.get("challenge_v1_payload", {})
    return bool(
        result.get("ok")
        and result.get("challenge_marked")
        and v1_payload.get("full_tree_calldata_included") is False
        and result.get("claimed_witness_encoded")
        and result.get("claimed_witness_encoded_length", 0) > 0
        and result.get("claimed_merkle_proof_encoded")
        and result.get("claimed_merkle_proof_encoded_length", 0) > 0
        and "true" in result.get("localized_path_call_output", "").lower()
        and "true" in result.get("localized_path_binding_call_output", "").lower()
        and result.get("localized_path_bound")
        and result.get("anchored_challenge_id")
        and result.get("posted_merkle_root")
        and first_word(result.get("anchored_challenge_pending_record_output", "")) == "1"
        and first_word(result.get("anchored_challenge_resolved_record_output", "")) == "2"
        and first_word(result.get("anchored_status_after_commit_output", "")) == "1"
        and first_word(result.get("anchored_status_after_submit_output", "")) == "2"
        and first_word(result.get("anchored_status_after_resolve_output", "")) == "4"
        and result.get("challenge_pending")
        and result.get("challenge_resolved")
        and result.get("challenge_invalidated")
        and result.get("localized_v1_proof_bytes", 0) > 0
        and result.get("commit_tx_calldata_bytes", 0) > 0
        and result.get("challenge_tx_calldata_bytes", 0) > 0
        and result.get("resolve_tx_calldata_bytes", 0) > 0
        and result.get("commit_gas_used", 0) > 0
        and result.get("challenge_gas_used", 0) > 0
        and result.get("resolve_gas_used", 0) > 0
    )


def proof_payload_baseline_result_ok() -> bool:
    result_path = ROOT / "research/results/proof_payload_baselines_latest.json"
    if not result_path.exists():
        return False
    try:
        result = json.loads(read_text(result_path))
    except json.JSONDecodeError:
        return False
    rows = result.get("rows", [])
    leaf_counts = {row.get("leaf_count") for row in rows}
    return bool(
        rows
        and {4, 8, 16, 32, 64, 128, 256, 512}.issubset(leaf_counts)
        and all(row.get("anchored_v1_local_path_bytes", 0) > 0 for row in rows)
        and all(row.get("anchored_v1_crystal_witness_bytes", 0) > 0 for row in rows)
        and all(row.get("anchored_v1_merkle_proof_bytes", 0) > 0 for row in rows)
    )


def run(command: list[str]) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=120,
        )
        return completed.returncode == 0, completed.stdout[-2000:]
    except Exception as exc:
        return False, str(exc)


def main() -> int:
    checks = []

    required_files = [
        "README.md",
        "docs/PRODUCTION_HARDENING_PLAN.md",
        "docs/ANCHORED_CHALLENGE_PAYLOAD_V0.md",
        "docs/LOCAL_CRYSTAL_WITNESS_V1.md",
        "docs/ETHEREUM_ESP_GRANT_PACKET.md",
        "docs/CRYSTALDEFI_LONG_TERM_EXECUTION_PLAN.md",
        "docs/PUBLIC_TECHNICAL_REPORT.md",
        "docs/REVIEWER_PACKET.md",
        "docs/COUNTERPROOF_SEMANTICS_V0.md",
        "docs/CHALLENGE_GAME_STATE_MACHINE_V0.md",
        "docs/TESTNET_READINESS_CHECKLIST.md",
        "docs/ESP_OFFICE_HOURS_PREP.md",
        "docs/FRESH_CLONE_VERIFICATION.md",
        "docs/PRIOR_ART_POSITIONING_APPENDIX.md",
        "docs/THIRD_PARTY_VERIFICATION_REQUEST.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "contracts/CrystalVerifier.sol",
        "contracts/CrystalComponentVerifier.sol",
        "test/CrystalVerifier.t.sol",
        "test/CrystalComponentVerifier.t.sol",
        "research/adversarial_grinding_harness.py",
        "research/baseline_structural_harness.py",
        "research/proof_payload_baseline_harness.py",
        "research/component_table_equivalence.py",
        "scripts/check_open_core_boundary.py",
        "scripts/export_open_core.py",
        "scripts/devnet_observatory_demo.py",
    ]
    for path in required_files:
        checks.append({"name": f"file:{path}", "ok": exists(path)})

    python_files = [
        "sdk/crystal_committer.py",
        "watcher/crystal_watcher.py",
        *[
            str(path.relative_to(ROOT))
            for path in sorted((ROOT / "research").glob("*.py"))
        ],
        *[
            str(path.relative_to(ROOT))
            for path in sorted((ROOT / "scripts").glob("*.py"))
        ],
    ]

    command_checks = [
        ("python_compile", ["python3", "-m", "py_compile", *python_files]),
        ("component_equivalence", ["python3", "research/component_table_equivalence.py"]),
        ("sdk_package", ["python3", "sdk/crystal_committer.py", "package", "--tree", "((10,20),(30,40))"]),
        (
            "sdk_challenge",
            [
                "python3",
                "sdk/crystal_committer.py",
                "challenge",
                "--claimed-tree",
                "((10,20),(30,40))",
                "--observed-tree",
                "(10,(20,(30,40)))",
            ],
        ),
        (
            "sdk_challenge_v1",
            [
                "python3",
                "sdk/crystal_committer.py",
                "challenge-v1",
                "--claimed-tree",
                "((10,20),(30,40))",
                "--observed-tree",
                "(10,(20,(30,40)))",
            ],
        ),
        ("open_core_boundary", ["python3", "scripts/check_open_core_boundary.py"]),
        ("foundry_tests", ["forge", "test"]),
    ]

    for name, command in command_checks:
        ok, output = run(command)
        checks.append({"name": name, "ok": ok, "tail": output})

    checks.append(
        {
            "name": "proof_payload_v1_byte_baselines",
            "ok": proof_payload_baseline_result_ok(),
            "blocking": True,
            "note": "Run research/proof_payload_baseline_harness.py to refresh V1 byte baselines.",
        }
    )

    grant_packet = (ROOT / "docs/ETHEREUM_ESP_GRANT_PACKET.md").read_text(encoding="utf-8")
    license_gate_called_out = (
        ("BUSL-1.1" in grant_packet and "Apache-2.0" in grant_packet)
        or current_directory_is_open_core()
    )
    checks.append({"name": "license_gate_called_out", "ok": license_gate_called_out})

    # A resolved license split requires an actual open-source license file or
    # generated sibling package, not only a note in the grant packet.
    open_license_resolved = open_core_resolved()
    checks.append(
        {
            "name": "open_source_license_resolved",
            "ok": open_license_resolved,
            "blocking": True,
            "note": "Run scripts/export_open_core.py --force to generate the Apache-2.0 grant boundary.",
        }
    )

    checks.append(
        {
            "name": "devnet_observatory_demo_result",
            "ok": demo_result_ok(),
            "blocking": True,
            "note": "Run scripts/devnet_observatory_demo.py to produce on-chain demo evidence.",
        }
    )

    ok = all(item["ok"] for item in checks if not item.get("blocking"))
    blockers = [item for item in checks if item.get("blocking") and not item["ok"]]
    result = {
        "ok_except_known_blockers": ok,
        "blocking_items": blockers,
        "checks": checks,
    }
    print(json.dumps(result, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
