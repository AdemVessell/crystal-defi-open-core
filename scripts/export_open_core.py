#!/usr/bin/env python3
"""Export the grant-facing Crystal DeFi open core package.

The source lane can keep its existing license posture. This script creates a
separate Apache-2.0 sibling package that contains the grant-funded public-goods
surface: SDK, verifier contracts, tests, watcher, research harnesses, docs, and
demo scripts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT.parent / "crystal-defi-open-core"

FILES = [
    ".gitignore",
    "README.md",
    "foundry.toml",
    "contracts/CrystalVerifier.sol",
    "contracts/CrystalComponentVerifier.sol",
    "test/CrystalVerifier.t.sol",
    "test/CrystalComponentVerifier.t.sol",
    "script/Deploy.s.sol",
    "sdk/crystal_committer.py",
    "watcher/crystal_watcher.py",
    "research/adversarial_grinding_harness.py",
    "research/baseline_structural_harness.py",
    "research/component_table_equivalence.py",
    "research/proof_payload_baseline_harness.py",
    "research/results/adversarial_grinding_latest.json",
    "research/results/adversarial_grinding_latest.md",
    "research/results/structural_baselines_latest.json",
    "research/results/structural_baselines_latest.md",
    "research/results/proof_payload_baselines_latest.json",
    "research/results/proof_payload_baselines_latest.md",
    "docs/ANCHORED_CHALLENGE_PAYLOAD_V0.md",
    "docs/CHALLENGE_GAME_STATE_MACHINE_V0.md",
    "docs/COUNTERPROOF_SEMANTICS_V0.md",
    "docs/CRYSTALDEFI_LONG_TERM_EXECUTION_PLAN.md",
    "docs/ETHEREUM_ESP_GRANT_PACKET.md",
    "docs/ESP_OFFICE_HOURS_PREP.md",
    "docs/LOCAL_CRYSTAL_WITNESS_V1.md",
    "docs/PRODUCTION_HARDENING_PLAN.md",
    "docs/PUBLIC_TECHNICAL_REPORT.md",
    "docs/REVIEWER_PACKET.md",
    "docs/TESTNET_READINESS_CHECKLIST.md",
    "demo/results/devnet_observatory_latest.json",
    "demo/results/devnet_observatory_latest.md",
    "scripts/grant_readiness_check.py",
    "scripts/export_open_core.py",
    "scripts/devnet_observatory_demo.py",
]

DIRECTORIES = [
    "lib/forge-std",
]

TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".sol",
    ".toml",
    ".json",
    ".gitignore",
}

APACHE_LICENSE = """Apache License
Version 2.0, January 2004
https://www.apache.org/licenses/

TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

1. Definitions.

"License" shall mean the terms and conditions for use, reproduction, and
distribution as defined by Sections 1 through 9 of this document.

"Licensor" shall mean the copyright owner or entity authorized by the copyright
owner that is granting the License.

"Legal Entity" shall mean the union of the acting entity and all other entities
that control, are controlled by, or are under common control with that entity.
For the purposes of this definition, "control" means (i) the power, direct or
indirect, to cause the direction or management of such entity, whether by
contract or otherwise, or (ii) ownership of fifty percent (50%) or more of the
outstanding shares, or (iii) beneficial ownership of such entity.

"You" (or "Your") shall mean an individual or Legal Entity exercising
permissions granted by this License.

"Source" form shall mean the preferred form for making modifications, including
but not limited to software source code, documentation source, and configuration
files.

"Object" form shall mean any form resulting from mechanical transformation or
translation of a Source form, including but not limited to compiled object code,
generated documentation, and conversions to other media types.

"Work" shall mean the work of authorship, whether in Source or Object form,
made available under the License, as indicated by a copyright notice that is
included in or attached to the work.

"Derivative Works" shall mean any work, whether in Source or Object form, that
is based on (or derived from) the Work and for which the editorial revisions,
annotations, elaborations, or other modifications represent, as a whole, an
original work of authorship. For the purposes of this License, Derivative Works
shall not include works that remain separable from, or merely link (or bind by
name) to the interfaces of, the Work and Derivative Works thereof.

"Contribution" shall mean any work of authorship, including the original
version of the Work and any modifications or additions to that Work or
Derivative Works thereof, that is intentionally submitted to Licensor for
inclusion in the Work by the copyright owner or by an individual or Legal Entity
authorized to submit on behalf of the copyright owner. For the purposes of this
definition, "submitted" means any form of electronic, verbal, or written
communication sent to the Licensor or its representatives, including but not
limited to communication on electronic mailing lists, source code control
systems, and issue tracking systems that are managed by, or on behalf of, the
Licensor for the purpose of discussing and improving the Work, but excluding
communication that is conspicuously marked or otherwise designated in writing by
the copyright owner as "Not a Contribution."

"Contributor" shall mean Licensor and any individual or Legal Entity on behalf
of whom a Contribution has been received by Licensor and subsequently
incorporated within the Work.

2. Grant of Copyright License. Subject to the terms and conditions of this
License, each Contributor hereby grants to You a perpetual, worldwide,
non-exclusive, no-charge, royalty-free, irrevocable copyright license to
reproduce, prepare Derivative Works of, publicly display, publicly perform,
sublicense, and distribute the Work and such Derivative Works in Source or
Object form.

3. Grant of Patent License. Subject to the terms and conditions of this License,
each Contributor hereby grants to You a perpetual, worldwide, non-exclusive,
no-charge, royalty-free, irrevocable patent license to make, have made, use,
offer to sell, sell, import, and otherwise transfer the Work, where such license
applies only to those patent claims licensable by such Contributor that are
necessarily infringed by their Contribution(s) alone or by combination of their
Contribution(s) with the Work to which such Contribution(s) was submitted. If
You institute patent litigation against any entity alleging that the Work or a
Contribution incorporated within the Work constitutes direct or contributory
patent infringement, then any patent licenses granted to You under this License
for that Work shall terminate as of the date such litigation is filed.

4. Redistribution. You may reproduce and distribute copies of the Work or
Derivative Works thereof in any medium, with or without modifications, and in
Source or Object form, provided that You meet the following conditions:

(a) You must give any other recipients of the Work or Derivative Works a copy of
this License; and

(b) You must cause any modified files to carry prominent notices stating that
You changed the files; and

(c) You must retain, in the Source form of any Derivative Works that You
distribute, all copyright, patent, trademark, and attribution notices from the
Source form of the Work, excluding those notices that do not pertain to any part
of the Derivative Works; and

(d) If the Work includes a "NOTICE" text file as part of its distribution, then
any Derivative Works that You distribute must include a readable copy of the
attribution notices contained within such NOTICE file, excluding those notices
that do not pertain to any part of the Derivative Works, in at least one of the
following places: within a NOTICE text file distributed as part of the
Derivative Works; within the Source form or documentation, if provided along
with the Derivative Works; or, within a display generated by the Derivative
Works, if and wherever such third-party notices normally appear. The contents of
the NOTICE file are for informational purposes only and do not modify the
License. You may add Your own attribution notices within Derivative Works that
You distribute, alongside or as an addendum to the NOTICE text from the Work,
provided that such additional attribution notices cannot be construed as
modifying the License.

You may add Your own copyright statement to Your modifications and may provide
additional or different license terms and conditions for use, reproduction, or
distribution of Your modifications, or for any such Derivative Works as a whole,
provided Your use, reproduction, and distribution of the Work otherwise complies
with the conditions stated in this License.

5. Submission of Contributions. Unless You explicitly state otherwise, any
Contribution intentionally submitted for inclusion in the Work by You to the
Licensor shall be under the terms and conditions of this License, without any
additional terms or conditions. Notwithstanding the above, nothing herein shall
supersede or modify the terms of any separate license agreement you may have
executed with Licensor regarding such Contributions.

6. Trademarks. This License does not grant permission to use the trade names,
trademarks, service marks, or product names of the Licensor, except as required
for reasonable and customary use in describing the origin of the Work and
reproducing the content of the NOTICE file.

7. Disclaimer of Warranty. Unless required by applicable law or agreed to in
writing, Licensor provides the Work on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied, including, without
limitation, any warranties or conditions of TITLE, NON-INFRINGEMENT,
MERCHANTABILITY, or FITNESS FOR A PARTICULAR PURPOSE. You are solely
responsible for determining the appropriateness of using or redistributing the
Work and assume any risks associated with Your exercise of permissions under
this License.

8. Limitation of Liability. In no event and under no legal theory, whether in
tort (including negligence), contract, or otherwise, unless required by
applicable law (such as deliberate and grossly negligent acts) or agreed to in
writing, shall any Contributor be liable to You for damages, including any
direct, indirect, special, incidental, or consequential damages of any character
arising as a result of this License or out of the use or inability to use the
Work (including but not limited to damages for loss of goodwill, work stoppage,
computer failure or malfunction, or any and all other commercial damages or
losses), even if such Contributor has been advised of the possibility of such
damages.

9. Accepting Warranty or Additional Liability. While redistributing the Work or
Derivative Works thereof, You may choose to offer, and charge a fee for,
acceptance of support, warranty, indemnity, or other liability obligations
and/or rights consistent with this License. However, in accepting such
obligations, You may act only on Your own behalf and on Your sole
responsibility, not on behalf of any other Contributor, and only if You agree to
indemnify, defend, and hold each Contributor harmless for any liability incurred
by, or claims asserted against, such Contributor by reason of your accepting any
such warranty or additional liability.
"""

NOTICE = """Crystal DeFi Open Core

Copyright 2026 Arkhe Technologic.

This package is the grant-facing open-core export of the Crystal DeFi
structural-divergence monitoring prototype. It is licensed under Apache-2.0.

The source workspace may contain separate BUSL/proprietary lanes. Those lanes
are outside this generated open-core package unless their files are explicitly
included here.

The vendored `lib/forge-std` test dependency is third-party software and keeps
its own MIT/Apache license files in that directory.
"""

BOUNDARY = """# Crystal DeFi Open Core Boundary

This directory is generated by `scripts/export_open_core.py`.

License: Apache-2.0.

Included grant-facing scope:

```text
Python SDK and CLI
Solidity verifier prototypes and Foundry tests
Vendored Foundry forge-std test dependency under its own licenses
Watcher and local demo scripts
Research harnesses and latest result snapshots
Grant, hardening, and challenge-payload documentation
```

Excluded scope:

```text
commercial deployment claims
token economics
production slashing assumptions
unanchored Crystal commitment claims
private or BUSL lanes not copied into this package
```

Technical claim boundary:

```text
Crystal localizes; hash anchors prove.
```
"""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_text_file(relative_path: str) -> bool:
    path = Path(relative_path)
    return path.suffix in TEXT_SUFFIXES or path.name in TEXT_SUFFIXES


def rewrite_text(relative_path: str, text: str) -> str:
    text = text.replace("SPDX-License-Identifier: Apache-2.0", "SPDX-License-Identifier: Apache-2.0")
    text = text.replace("Licensed under Apache-2.0.", "Licensed under Apache-2.0.")
    text = text.replace("Apache-2.0", "Apache-2.0")
    text = text.replace("Copyright 2026 Arkhe Technologic", "Copyright 2026 Arkhe Technologic")
    text = text.replace("This open-core export is Apache-2.0.", "This open-core export is Apache-2.0.")
    text = text.replace(
        "That is a blocker for an EF/ESP grant unless the grant-funded core is split into\n"
        "a truly open-source public-goods package.",
        "The grant-funded core is split here as a truly open-source public-goods package.",
    )
    text = text.replace(
        "This generated export is the proposed resolved boundary; verify ownership and legal approval before submission.",
        "This generated export is the proposed resolved boundary; verify ownership and legal approval before submission.",
    )
    if relative_path == "README.md":
        text = (
            "# Crystal DeFi Open Core - Structural Divergence Layer\n\n"
            "Apache-2.0 grant-facing export of the Crystal DeFi prototype.\n\n"
            + text.split("\n", 1)[1]
        )
    return text


def copy_file(relative_path: str, output: Path) -> dict:
    source = ROOT / relative_path
    target = output / relative_path
    if not source.exists():
        return {"path": relative_path, "copied": False, "reason": "source_missing"}

    target.parent.mkdir(parents=True, exist_ok=True)
    if is_text_file(relative_path):
        text = source.read_text(encoding="utf-8")
        target.write_text(rewrite_text(relative_path, text), encoding="utf-8")
    else:
        shutil.copy2(source, target)

    return {
        "path": relative_path,
        "copied": True,
        "sha256": sha256_file(target),
    }


def copy_directory(relative_path: str, output: Path) -> dict:
    source = ROOT / relative_path
    target = output / relative_path
    if not source.exists():
        return {"path": relative_path, "copied": False, "reason": "source_missing"}

    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns(".git", "cache", "out", "node_modules"),
    )

    h = hashlib.sha256()
    file_count = 0
    for file_path in sorted(path for path in target.rglob("*") if path.is_file()):
        file_count += 1
        rel = file_path.relative_to(target).as_posix()
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(sha256_file(file_path).encode("ascii"))
        h.update(b"\0")

    return {
        "path": relative_path,
        "copied": True,
        "type": "directory",
        "file_count": file_count,
        "sha256_tree": h.hexdigest(),
    }


def write_generated_files(output: Path) -> list[dict]:
    generated = {
        "LICENSE": APACHE_LICENSE,
        "NOTICE": NOTICE,
        "OPEN_CORE_BOUNDARY.md": BOUNDARY,
    }
    entries = []
    for relative_path, text in generated.items():
        target = output / relative_path
        target.write_text(text, encoding="utf-8")
        entries.append({"path": relative_path, "copied": True, "sha256": sha256_file(target)})
    return entries


def replace_output_preserving_git(output: Path) -> None:
    git_dir = output / ".git"
    preserved_git: Path | None = None
    if git_dir.exists():
        tmp_dir = Path(tempfile.mkdtemp(prefix="crystal-open-core-git-"))
        preserved_git = tmp_dir / ".git"
        shutil.move(str(git_dir), preserved_git)

    shutil.rmtree(output)
    output.mkdir(parents=True)

    if preserved_git is not None:
        shutil.move(str(preserved_git), output / ".git")
        try:
            preserved_git.parent.rmdir()
        except OSError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Apache-2.0 Crystal DeFi open core package")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true", help="replace an existing output directory")
    args = parser.parse_args()

    output = args.output.expanduser().resolve()
    if output == ROOT.resolve():
        raise SystemExit("Refusing to export over the source directory.")
    if output.exists():
        if not args.force:
            raise SystemExit(f"{output} exists; pass --force to replace it.")
        replace_output_preserving_git(output)
    else:
        output.mkdir(parents=True)

    manifest_entries = [copy_file(relative_path, output) for relative_path in FILES]
    manifest_entries.extend(copy_directory(relative_path, output) for relative_path in DIRECTORIES)
    manifest_entries.extend(write_generated_files(output))

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "crystal-defi source workspace",
        "output": "crystal-defi-open-core package",
        "license": "Apache-2.0",
        "technical_claim": "Crystal localizes; hash anchors prove.",
        "entries": manifest_entries,
    }
    manifest_path = output / "OPEN_CORE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    copied = sum(1 for item in manifest_entries if item.get("copied"))
    missing = [item["path"] for item in manifest_entries if not item.get("copied")]
    print(
        json.dumps(
            {
                "ok": not missing,
                "output": str(output),
                "copied_files": copied,
                "missing_files": missing,
                "manifest": str(manifest_path),
            },
            indent=2,
        )
    )
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
