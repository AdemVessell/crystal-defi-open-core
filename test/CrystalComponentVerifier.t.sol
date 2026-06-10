// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../contracts/CrystalComponentVerifier.sol";

contract CrystalComponentVerifierTest is Test {
    CrystalComponentVerifier public verifier;

    function setUp() public {
        verifier = new CrystalComponentVerifier();
        for (uint256 h = 0; h < 8; h++) {
            verifier.initializeHead(h, _componentTable(h));
        }
        verifier.finalizeInitialization();
    }

    function test_componentTablesAreCompact() public view {
        uint256 totalBytes = 0;
        for (uint256 h = 0; h < 8; h++) {
            totalBytes += verifier.componentDataLength(h);
        }
        assertEq(totalBytes, 512, "component tables should total 512 bytes");
    }

    function test_foldMatchesSdkKnownRootForPair() public view {
        uint8[8] memory expected = [uint8(3), 137, 86, 186, 54, 198, 47, 27];
        for (uint256 h = 0; h < 8; h++) {
            assertEq(verifier.fold(10, 20, h), expected[h], "fold should match SDK table");
        }
    }

    function test_verifyTreeRootMatchesSdkKnownRoot() public view {
        bytes memory tree = _encodeInternal(
            _encodeInternal(_encodeLeaf(10), _encodeLeaf(20)),
            _encodeInternal(_encodeLeaf(30), _encodeLeaf(40))
        );
        bytes32 expectedRoot = hex"0c4aedf82d02192b000000000000000000000000000000000000000000000000";

        (bool valid, bytes32 computedRoot) = verifier.verifyTreeRoot(tree, expectedRoot);

        assertTrue(valid, "known SDK root should verify");
        assertEq(computedRoot, expectedRoot, "computed root should match SDK root");
    }

    function test_commitTreeStoresPerTreeRoot() public {
        bytes32 blockHash = keccak256("block-a");
        bytes32 expectedRoot = hex"0c4aedf82d02192b000000000000000000000000000000000000000000000000";

        verifier.commitTree(blockHash, 3, expectedRoot);

        assertTrue(verifier.isTreeCommitted(blockHash, 3), "tree should be marked committed");
        assertEq(verifier.getTreeRoot(blockHash, 3), expectedRoot, "stored root should match");
        assertFalse(verifier.isTreeCommitted(blockHash, 4), "tree index should isolate roots");
    }

    function test_commitTreeRejectsOverwrite() public {
        bytes32 blockHash = keccak256("block-a");
        bytes32 expectedRoot = hex"0c4aedf82d02192b000000000000000000000000000000000000000000000000";

        verifier.commitTree(blockHash, 3, expectedRoot);

        vm.expectRevert("CrystalComponentVerifier: tree already committed");
        verifier.commitTree(blockHash, 3, expectedRoot);
    }

    function test_commitAnchoredTreeStoresCrystalAndMerkleRoots() public {
        bytes32 blockHash = keccak256("block-anchor");
        bytes32 crystalRoot = hex"0c4aedf82d02192b000000000000000000000000000000000000000000000000";
        bytes32 merkleRoot = hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";

        verifier.commitAnchoredTree(blockHash, 1, crystalRoot, merkleRoot);

        assertTrue(verifier.isTreeCommitted(blockHash, 1), "anchored tree should be committed");
        assertEq(
            verifier.getTreeRoot(blockHash, 1), crystalRoot, "stored crystal root should match"
        );
        assertEq(
            verifier.getTreeMerkleRoot(blockHash, 1), merkleRoot, "stored merkle root should match"
        );
        assertEq(
            uint256(verifier.getAnchoredTreeStatus(blockHash, 1)),
            uint256(CrystalComponentVerifier.AnchoredTreeStatus.Active),
            "anchored tree should open as active"
        );
    }

    function test_commitAnchoredTreeOpensChallengeWindow() public {
        bytes32 blockHash = keccak256("block-window");
        bytes32 crystalRoot = hex"0c4aedf82d02192b000000000000000000000000000000000000000000000000";
        bytes32 merkleRoot = hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";
        uint64 committedAt = uint64(block.timestamp);

        verifier.commitAnchoredTree(blockHash, 1, crystalRoot, merkleRoot);

        uint64 deadline = verifier.getAnchoredTreeChallengeDeadline(blockHash, 1);
        assertEq(
            deadline,
            committedAt + verifier.DEFAULT_CHALLENGE_WINDOW_SECONDS(),
            "deadline should use default window"
        );

        (
            CrystalComponentVerifier.AnchoredTreeStatus status,
            bytes32 storedCrystalRoot,
            bytes32 storedMerkleRoot,
            address sequencer,
            uint64 storedCommittedAt,
            uint64 storedDeadline
        ) = verifier.anchoredTreeCommitments(blockHash, 1);

        assertEq(uint256(status), uint256(CrystalComponentVerifier.AnchoredTreeStatus.Active));
        assertEq(storedCrystalRoot, crystalRoot, "stored crystal root should match");
        assertEq(storedMerkleRoot, merkleRoot, "stored merkle root should match");
        assertEq(sequencer, address(this), "sequencer should match");
        assertEq(storedCommittedAt, committedAt, "committed timestamp should match");
        assertEq(storedDeadline, deadline, "stored deadline should match");
    }

    function test_commitAnchoredTreeWithWindowRejectsZeroWindow() public {
        bytes32 blockHash = keccak256("block-empty-window");
        bytes32 crystalRoot = hex"0c4aedf82d02192b000000000000000000000000000000000000000000000000";
        bytes32 merkleRoot = hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";

        vm.expectRevert("CrystalComponentVerifier: empty challenge window");
        verifier.commitAnchoredTreeWithWindow(blockHash, 1, crystalRoot, merkleRoot, 0);
    }

    function test_commitAnchoredTreeWithWindowRejectsDeadlineOverflow() public {
        bytes32 blockHash = keccak256("block-window-overflow");
        bytes32 crystalRoot = hex"0c4aedf82d02192b000000000000000000000000000000000000000000000000";
        bytes32 merkleRoot = hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";

        vm.warp(uint256(type(uint64).max));
        vm.expectRevert("CrystalComponentVerifier: challenge deadline overflow");
        verifier.commitAnchoredTreeWithWindow(blockHash, 1, crystalRoot, merkleRoot, 1);
    }

    function test_finalizeAnchoredTreeRejectsBeforeDeadline() public {
        bytes32 blockHash = keccak256("block-finalize-early");
        bytes32 crystalRoot = hex"0c4aedf82d02192b000000000000000000000000000000000000000000000000";
        bytes32 merkleRoot = hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";

        verifier.commitAnchoredTreeWithWindow(blockHash, 1, crystalRoot, merkleRoot, 10);

        vm.expectRevert("CrystalComponentVerifier: challenge window open");
        verifier.finalizeAnchoredTree(blockHash, 1);
    }

    function test_finalizeAnchoredTreeAfterDeadline() public {
        bytes32 blockHash = keccak256("block-finalize");
        bytes32 crystalRoot = hex"0c4aedf82d02192b000000000000000000000000000000000000000000000000";
        bytes32 merkleRoot = hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";

        verifier.commitAnchoredTreeWithWindow(blockHash, 1, crystalRoot, merkleRoot, 10);
        vm.warp(block.timestamp + 10);
        verifier.finalizeAnchoredTree(blockHash, 1);

        assertEq(
            uint256(verifier.getAnchoredTreeStatus(blockHash, 1)),
            uint256(CrystalComponentVerifier.AnchoredTreeStatus.Finalized),
            "anchored tree should finalize after deadline"
        );
    }

    function test_submitTreeConsistencyChallengeFlagsMismatch() public {
        bytes32 blockHash = keccak256("block-b");
        bytes memory tree = _encodeInternal(
            _encodeInternal(_encodeLeaf(10), _encodeLeaf(20)),
            _encodeInternal(_encodeLeaf(30), _encodeLeaf(40))
        );
        bytes32 wrongRoot = hex"ffffffffffffffff000000000000000000000000000000000000000000000000";

        verifier.commitTree(blockHash, 0, wrongRoot);
        verifier.submitTreeConsistencyChallenge(blockHash, 0, tree);

        assertTrue(verifier.isChallenged(blockHash), "block should be marked challenged");
    }

    function test_submitTreeConsistencyChallengeRejectsMatchingRoot() public {
        bytes32 blockHash = keccak256("block-c");
        bytes memory tree = _encodeInternal(
            _encodeInternal(_encodeLeaf(10), _encodeLeaf(20)),
            _encodeInternal(_encodeLeaf(30), _encodeLeaf(40))
        );
        bytes32 expectedRoot = hex"0c4aedf82d02192b000000000000000000000000000000000000000000000000";

        verifier.commitTree(blockHash, 0, expectedRoot);

        vm.expectRevert("CrystalComponentVerifier: no mismatch detected");
        verifier.submitTreeConsistencyChallenge(blockHash, 0, tree);
    }

    function test_verifyCrystalPathWitnessMatchesSdkKnownRoot() public view {
        bytes memory witness = hex"038956ba36c62f1b0100179566aa16d21b27";
        bytes32 expectedRoot = hex"0c4aedf82d02192b000000000000000000000000000000000000000000000000";

        (bool valid, bytes32 computedRoot) = verifier.verifyCrystalPath(witness, expectedRoot);

        assertTrue(valid, "root.L witness should verify");
        assertEq(computedRoot, expectedRoot, "computed witness root should match");
    }

    function test_verifyCrystalPathWitnessSupportsMultiStepPath() public view {
        bytes memory witness = hex"282828282828282802011e1e1e1e1e1e1e1e01038956ba36c62f1b";
        bytes32 expectedRoot = hex"0c4aedf82d02192b000000000000000000000000000000000000000000000000";

        (bool valid, bytes32 computedRoot) = verifier.verifyCrystalPath(witness, expectedRoot);

        assertTrue(valid, "root.R.R leaf witness should verify");
        assertEq(computedRoot, expectedRoot, "computed witness root should match");
    }

    function test_verifyCrystalPathWitnessMatchesObservedRoot() public view {
        bytes memory witness = hex"0a0a0a0a0a0a0a0a0100360cae210c53052d";
        bytes32 expectedRoot = hex"118dfd9b12cd3d0a000000000000000000000000000000000000000000000000";

        (bool valid, bytes32 computedRoot) = verifier.verifyCrystalPath(witness, expectedRoot);

        assertTrue(valid, "observed root.L witness should verify");
        assertEq(computedRoot, expectedRoot, "computed witness root should match");
    }

    function test_submitCrystalPathConsistencyChallengeFlagsMismatch() public {
        bytes32 blockHash = keccak256("block-d");
        bytes memory witness = hex"038956ba36c62f1b0100179566aa16d21b27";
        bytes32 wrongRoot = hex"118dfd9b12cd3d0a000000000000000000000000000000000000000000000000";

        verifier.commitTree(blockHash, 0, wrongRoot);
        verifier.submitCrystalPathConsistencyChallenge(blockHash, 0, witness);

        assertTrue(verifier.isChallenged(blockHash), "block should be marked challenged");
    }

    function test_submitCrystalPathConsistencyChallengeRejectsMatchingRoot() public {
        bytes32 blockHash = keccak256("block-e");
        bytes memory witness = hex"038956ba36c62f1b0100179566aa16d21b27";
        bytes32 expectedRoot = hex"0c4aedf82d02192b000000000000000000000000000000000000000000000000";

        verifier.commitTree(blockHash, 0, expectedRoot);

        vm.expectRevert("CrystalComponentVerifier: no mismatch detected");
        verifier.submitCrystalPathConsistencyChallenge(blockHash, 0, witness);
    }

    function test_rejectsTrailingCrystalPathWitnessData() public {
        bytes memory witness = hex"038956ba36c62f1b0100179566aa16d21b2799";
        bytes32 expectedRoot = hex"0c4aedf82d02192b000000000000000000000000000000000000000000000000";

        vm.expectRevert("CrystalComponentVerifier: trailing path witness data");
        verifier.verifyCrystalPath(witness, expectedRoot);
    }

    function test_verifyMerklePathMatchesSdkKnownRoot() public view {
        bytes32 targetHash = hex"4cf8b5478ccbad8aaff6d5d7a5224f0577a8ba3bd97b12dba9dc3081c30aa937";
        bytes memory proof =
            hex"0100bbfe0762ecf04769e499b88b12ef2549fa065e6d0608eb154f66ca62e251ba80";
        bytes32 expectedMerkleRoot =
            hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";

        (bool valid, bytes32 computedRoot) =
            verifier.verifyMerklePath(targetHash, proof, expectedMerkleRoot);

        assertTrue(valid, "root.L Merkle proof should verify");
        assertEq(computedRoot, expectedMerkleRoot, "computed Merkle root should match");
    }

    function test_verifyMerklePathSupportsMultiStepPath() public view {
        bytes32 targetHash = hex"2ee788372518190a6ab539cbb20331df1040f21846e3ba836c269aee907c894c";
        bytes memory proof =
            hex"0201b3fe2f9bd5354b63ae8d0df01e7ad3074f42cbc1ac1f693b64d76ab5e0806587014cf8b5478ccbad8aaff6d5d7a5224f0577a8ba3bd97b12dba9dc3081c30aa937";
        bytes32 expectedMerkleRoot =
            hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";

        (bool valid, bytes32 computedRoot) =
            verifier.verifyMerklePath(targetHash, proof, expectedMerkleRoot);

        assertTrue(valid, "root.R.R Merkle proof should verify");
        assertEq(computedRoot, expectedMerkleRoot, "computed Merkle root should match");
    }

    function test_verifyLeafMerklePathMatchesSdkKnownRoot() public view {
        bytes memory proof =
            hex"0100e34894d6808065397d72586854d58ff0c02bbd15b6b3b5b00a00f7687d6f9b10";
        bytes32 expectedMerkleRoot =
            hex"08c2b2187f57094c5a06d1143d4bad46840302d0ad10485e221986aca4ba03e4";

        (bool valid, bytes32 computedRoot) =
            verifier.verifyLeafMerklePath(10, proof, expectedMerkleRoot);

        assertTrue(valid, "observed root.L leaf Merkle proof should verify");
        assertEq(computedRoot, expectedMerkleRoot, "computed Merkle root should match");
    }

    function test_verifyLocalizedPathChecksCrystalAndMerkle() public view {
        bytes memory crystalWitness = hex"038956ba36c62f1b0100179566aa16d21b27";
        bytes32 expectedCrystalRoot =
            hex"0c4aedf82d02192b000000000000000000000000000000000000000000000000";
        bytes32 targetMerkleHash =
            hex"4cf8b5478ccbad8aaff6d5d7a5224f0577a8ba3bd97b12dba9dc3081c30aa937";
        bytes memory merkleProof =
            hex"0100bbfe0762ecf04769e499b88b12ef2549fa065e6d0608eb154f66ca62e251ba80";
        bytes32 expectedMerkleRoot =
            hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";

        (
            bool crystalValid,
            bool merkleValid,
            bytes32 computedCrystalRoot,
            bytes32 computedMerkleRoot
        ) = verifier.verifyLocalizedPath(
            crystalWitness, expectedCrystalRoot, targetMerkleHash, merkleProof, expectedMerkleRoot
        );

        assertTrue(crystalValid, "Crystal witness should verify");
        assertTrue(merkleValid, "Merkle proof should verify");
        assertEq(computedCrystalRoot, expectedCrystalRoot, "computed Crystal root should match");
        assertEq(computedMerkleRoot, expectedMerkleRoot, "computed Merkle root should match");
    }

    function test_verifyLocalizedPathSupportsMultiStepSamePathBinding() public view {
        bytes memory crystalWitness = hex"282828282828282802011e1e1e1e1e1e1e1e01038956ba36c62f1b";
        bytes32 expectedCrystalRoot =
            hex"0c4aedf82d02192b000000000000000000000000000000000000000000000000";
        bytes32 targetMerkleHash =
            hex"2ee788372518190a6ab539cbb20331df1040f21846e3ba836c269aee907c894c";
        bytes memory merkleProof =
            hex"0201b3fe2f9bd5354b63ae8d0df01e7ad3074f42cbc1ac1f693b64d76ab5e0806587014cf8b5478ccbad8aaff6d5d7a5224f0577a8ba3bd97b12dba9dc3081c30aa937";
        bytes32 expectedMerkleRoot =
            hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";

        (
            bool crystalValid,
            bool merkleValid,
            bytes32 computedCrystalRoot,
            bytes32 computedMerkleRoot
        ) = verifier.verifyLocalizedPath(
            crystalWitness, expectedCrystalRoot, targetMerkleHash, merkleProof, expectedMerkleRoot
        );

        assertTrue(crystalValid, "Crystal witness should verify");
        assertTrue(merkleValid, "Merkle proof should verify");
        assertEq(computedCrystalRoot, expectedCrystalRoot, "computed Crystal root should match");
        assertEq(computedMerkleRoot, expectedMerkleRoot, "computed Merkle root should match");
    }

    function test_verifyLocalizedPathBindingAcceptsSamePath() public view {
        bytes memory crystalWitness = hex"038956ba36c62f1b0100179566aa16d21b27";
        bytes memory merkleProof =
            hex"0100bbfe0762ecf04769e499b88b12ef2549fa065e6d0608eb154f66ca62e251ba80";

        assertTrue(
            verifier.verifyLocalizedPathBinding(crystalWitness, merkleProof),
            "matching local path encodings should bind"
        );
    }

    function test_verifyLocalizedPathRejectsPathSideMismatch() public {
        bytes memory crystalWitness = hex"038956ba36c62f1b0101179566aa16d21b27";
        bytes32 expectedCrystalRoot =
            hex"0c4aedf82d02192b000000000000000000000000000000000000000000000000";
        bytes32 targetMerkleHash =
            hex"4cf8b5478ccbad8aaff6d5d7a5224f0577a8ba3bd97b12dba9dc3081c30aa937";
        bytes memory merkleProof =
            hex"0100bbfe0762ecf04769e499b88b12ef2549fa065e6d0608eb154f66ca62e251ba80";
        bytes32 expectedMerkleRoot =
            hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";

        vm.expectRevert("CrystalComponentVerifier: localized path mismatch");
        verifier.verifyLocalizedPath(
            crystalWitness, expectedCrystalRoot, targetMerkleHash, merkleProof, expectedMerkleRoot
        );
    }

    function test_verifyLocalizedPathRejectsPathDepthMismatch() public {
        bytes memory crystalWitness = hex"038956ba36c62f1b0100179566aa16d21b27";
        bytes32 expectedCrystalRoot =
            hex"0c4aedf82d02192b000000000000000000000000000000000000000000000000";
        bytes32 targetMerkleHash =
            hex"4cf8b5478ccbad8aaff6d5d7a5224f0577a8ba3bd97b12dba9dc3081c30aa937";
        bytes memory merkleProof = hex"00";
        bytes32 expectedMerkleRoot =
            hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";

        vm.expectRevert("CrystalComponentVerifier: localized path depth mismatch");
        verifier.verifyLocalizedPath(
            crystalWitness, expectedCrystalRoot, targetMerkleHash, merkleProof, expectedMerkleRoot
        );
    }

    function test_rejectsTrailingMerkleProofData() public {
        bytes32 targetHash = hex"4cf8b5478ccbad8aaff6d5d7a5224f0577a8ba3bd97b12dba9dc3081c30aa937";
        bytes memory proof =
            hex"0100bbfe0762ecf04769e499b88b12ef2549fa065e6d0608eb154f66ca62e251ba8099";
        bytes32 expectedMerkleRoot =
            hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";

        vm.expectRevert("CrystalComponentVerifier: trailing merkle proof data");
        verifier.verifyMerklePath(targetHash, proof, expectedMerkleRoot);
    }

    function test_submitAnchoredLocalizedChallengeOpensPendingMismatch() public {
        bytes32 blockHash = keccak256("block-anchored-challenge");
        bytes32 wrongCrystalRoot =
            hex"118dfd9b12cd3d0a000000000000000000000000000000000000000000000000";
        bytes32 postedMerkleRoot =
            hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";
        bytes memory crystalWitness = hex"038956ba36c62f1b0100179566aa16d21b27";
        bytes32 targetMerkleHash =
            hex"4cf8b5478ccbad8aaff6d5d7a5224f0577a8ba3bd97b12dba9dc3081c30aa937";
        bytes memory merkleProof =
            hex"0100bbfe0762ecf04769e499b88b12ef2549fa065e6d0608eb154f66ca62e251ba80";

        verifier.commitAnchoredTree(blockHash, 0, wrongCrystalRoot, postedMerkleRoot);
        bytes32 challengeId = verifier.submitAnchoredLocalizedChallenge(
            blockHash, 0, crystalWitness, targetMerkleHash, merkleProof
        );

        {
            (
                CrystalComponentVerifier.ChallengeStatus status,
                bytes32 storedBlockHash,
                uint256 storedTreeIndex,
                address challenger,,,,,,,
            ) = verifier.localizedChallenges(challengeId);
            assertEq(
                uint256(status), uint256(CrystalComponentVerifier.ChallengeStatus.PendingMismatch)
            );
            assertEq(storedBlockHash, blockHash, "stored block hash should match");
            assertEq(storedTreeIndex, 0, "stored tree index should match");
            assertEq(challenger, address(this), "challenger should match");
        }
        {
            (
                ,,,,
                bytes32 postedCrystalRoot,
                bytes32 storedMerkleRoot,
                bytes32 computedCrystalRoot,
                bytes32 computedMerkleRoot,
                bytes32 storedTargetMerkleHash,,
            ) = verifier.localizedChallenges(challengeId);
            assertEq(postedCrystalRoot, wrongCrystalRoot, "posted crystal root should match");
            assertEq(storedMerkleRoot, postedMerkleRoot, "posted merkle root should match");
            assertEq(
                computedCrystalRoot,
                hex"0c4aedf82d02192b000000000000000000000000000000000000000000000000",
                "computed crystal root should match witness"
            );
            assertEq(
                computedMerkleRoot, postedMerkleRoot, "computed merkle root should match anchor"
            );
            assertEq(storedTargetMerkleHash, targetMerkleHash, "target Merkle hash should match");
        }
        {
            (,,,,,,,,, uint64 openedAt, uint64 responseDeadline) =
                verifier.localizedChallenges(challengeId);
            assertEq(
                responseDeadline,
                openedAt + verifier.DEFAULT_CHALLENGE_RESPONSE_WINDOW_SECONDS(),
                "response deadline should use default window"
            );
        }
        assertFalse(
            verifier.isChallenged(blockHash), "block should not be finalized as challenged yet"
        );
        assertEq(
            uint256(verifier.getAnchoredTreeStatus(blockHash, 0)),
            uint256(CrystalComponentVerifier.AnchoredTreeStatus.Challenged),
            "anchored tree should wait in challenged state"
        );
    }

    function test_resolveAnchoredLocalizedChallengeInvalidatesAfterResponseDeadline() public {
        bytes32 blockHash = keccak256("block-anchored-resolve");
        bytes32 wrongCrystalRoot =
            hex"118dfd9b12cd3d0a000000000000000000000000000000000000000000000000";
        bytes32 postedMerkleRoot =
            hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";
        bytes memory crystalWitness = hex"038956ba36c62f1b0100179566aa16d21b27";
        bytes32 targetMerkleHash =
            hex"4cf8b5478ccbad8aaff6d5d7a5224f0577a8ba3bd97b12dba9dc3081c30aa937";
        bytes memory merkleProof =
            hex"0100bbfe0762ecf04769e499b88b12ef2549fa065e6d0608eb154f66ca62e251ba80";

        verifier.commitAnchoredTree(blockHash, 0, wrongCrystalRoot, postedMerkleRoot);
        bytes32 challengeId = verifier.submitAnchoredLocalizedChallenge(
            blockHash, 0, crystalWitness, targetMerkleHash, merkleProof
        );

        (CrystalComponentVerifier.ChallengeStatus pendingStatus,,,,,,,,,, uint64 responseDeadline) =
            verifier.localizedChallenges(challengeId);
        assertEq(
            uint256(pendingStatus),
            uint256(CrystalComponentVerifier.ChallengeStatus.PendingMismatch)
        );

        vm.warp(responseDeadline);
        verifier.resolveAnchoredLocalizedChallenge(challengeId);

        (CrystalComponentVerifier.ChallengeStatus resolvedStatus,,,,,,,,,,) =
            verifier.localizedChallenges(challengeId);
        assertEq(
            uint256(resolvedStatus),
            uint256(CrystalComponentVerifier.ChallengeStatus.ResolvedMismatch)
        );
        assertTrue(verifier.isChallenged(blockHash), "block should be challenged after resolution");
        assertEq(
            uint256(verifier.getAnchoredTreeStatus(blockHash, 0)),
            uint256(CrystalComponentVerifier.AnchoredTreeStatus.Invalidated),
            "anchored tree should be invalidated after resolution"
        );
    }

    function test_resolveAnchoredLocalizedChallengeRejectsBeforeResponseDeadline() public {
        bytes32 blockHash = keccak256("block-resolve-early");
        bytes32 wrongCrystalRoot =
            hex"118dfd9b12cd3d0a000000000000000000000000000000000000000000000000";
        bytes32 postedMerkleRoot =
            hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";
        bytes memory crystalWitness = hex"038956ba36c62f1b0100179566aa16d21b27";
        bytes32 targetMerkleHash =
            hex"4cf8b5478ccbad8aaff6d5d7a5224f0577a8ba3bd97b12dba9dc3081c30aa937";
        bytes memory merkleProof =
            hex"0100bbfe0762ecf04769e499b88b12ef2549fa065e6d0608eb154f66ca62e251ba80";

        verifier.commitAnchoredTree(blockHash, 0, wrongCrystalRoot, postedMerkleRoot);
        bytes32 challengeId = verifier.submitAnchoredLocalizedChallenge(
            blockHash, 0, crystalWitness, targetMerkleHash, merkleProof
        );

        vm.expectRevert("CrystalComponentVerifier: response window open");
        verifier.resolveAnchoredLocalizedChallenge(challengeId);
    }

    function test_resolveAnchoredLocalizedChallengeRejectsDoubleResolve() public {
        bytes32 blockHash = keccak256("block-resolve-double");
        bytes32 wrongCrystalRoot =
            hex"118dfd9b12cd3d0a000000000000000000000000000000000000000000000000";
        bytes32 postedMerkleRoot =
            hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";
        bytes memory crystalWitness = hex"038956ba36c62f1b0100179566aa16d21b27";
        bytes32 targetMerkleHash =
            hex"4cf8b5478ccbad8aaff6d5d7a5224f0577a8ba3bd97b12dba9dc3081c30aa937";
        bytes memory merkleProof =
            hex"0100bbfe0762ecf04769e499b88b12ef2549fa065e6d0608eb154f66ca62e251ba80";

        verifier.commitAnchoredTree(blockHash, 0, wrongCrystalRoot, postedMerkleRoot);
        bytes32 challengeId = verifier.submitAnchoredLocalizedChallenge(
            blockHash, 0, crystalWitness, targetMerkleHash, merkleProof
        );

        vm.warp(block.timestamp + verifier.DEFAULT_CHALLENGE_RESPONSE_WINDOW_SECONDS());
        verifier.resolveAnchoredLocalizedChallenge(challengeId);

        vm.expectRevert("CrystalComponentVerifier: challenge not pending");
        verifier.resolveAnchoredLocalizedChallenge(challengeId);
    }

    function test_finalizeAnchoredTreeRejectsChallengedTree() public {
        bytes32 blockHash = keccak256("block-finalize-challenged");
        bytes32 wrongCrystalRoot =
            hex"118dfd9b12cd3d0a000000000000000000000000000000000000000000000000";
        bytes32 postedMerkleRoot =
            hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";
        bytes memory crystalWitness = hex"038956ba36c62f1b0100179566aa16d21b27";
        bytes32 targetMerkleHash =
            hex"4cf8b5478ccbad8aaff6d5d7a5224f0577a8ba3bd97b12dba9dc3081c30aa937";
        bytes memory merkleProof =
            hex"0100bbfe0762ecf04769e499b88b12ef2549fa065e6d0608eb154f66ca62e251ba80";

        verifier.commitAnchoredTreeWithWindow(blockHash, 0, wrongCrystalRoot, postedMerkleRoot, 10);
        verifier.submitAnchoredLocalizedChallenge(
            blockHash, 0, crystalWitness, targetMerkleHash, merkleProof
        );

        vm.warp(block.timestamp + 10);
        vm.expectRevert("CrystalComponentVerifier: anchored tree not active");
        verifier.finalizeAnchoredTree(blockHash, 0);
    }

    function test_submitAnchoredLocalizedChallengeRejectsPendingTree() public {
        bytes32 blockHash = keccak256("block-pending-no-duplicate");
        bytes32 wrongCrystalRoot =
            hex"118dfd9b12cd3d0a000000000000000000000000000000000000000000000000";
        bytes32 postedMerkleRoot =
            hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";
        bytes memory crystalWitness = hex"038956ba36c62f1b0100179566aa16d21b27";
        bytes32 targetMerkleHash =
            hex"4cf8b5478ccbad8aaff6d5d7a5224f0577a8ba3bd97b12dba9dc3081c30aa937";
        bytes memory merkleProof =
            hex"0100bbfe0762ecf04769e499b88b12ef2549fa065e6d0608eb154f66ca62e251ba80";

        verifier.commitAnchoredTree(blockHash, 0, wrongCrystalRoot, postedMerkleRoot);
        verifier.submitAnchoredLocalizedChallenge(
            blockHash, 0, crystalWitness, targetMerkleHash, merkleProof
        );

        vm.expectRevert("CrystalComponentVerifier: anchored tree not active");
        verifier.submitAnchoredLocalizedChallenge(
            blockHash, 0, crystalWitness, targetMerkleHash, merkleProof
        );
    }

    function test_resolveAnchoredLocalizedChallengeRejectsUnknownChallenge() public {
        vm.expectRevert("CrystalComponentVerifier: challenge not pending");
        verifier.resolveAnchoredLocalizedChallenge(keccak256("unknown-challenge"));
    }

    function test_submitAnchoredLocalizedChallengeRejectsResponseDeadlineOverflow() public {
        bytes32 blockHash = keccak256("block-response-overflow");
        bytes32 wrongCrystalRoot =
            hex"118dfd9b12cd3d0a000000000000000000000000000000000000000000000000";
        bytes32 postedMerkleRoot =
            hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";
        bytes memory crystalWitness = hex"038956ba36c62f1b0100179566aa16d21b27";
        bytes32 targetMerkleHash =
            hex"4cf8b5478ccbad8aaff6d5d7a5224f0577a8ba3bd97b12dba9dc3081c30aa937";
        bytes memory merkleProof =
            hex"0100bbfe0762ecf04769e499b88b12ef2549fa065e6d0608eb154f66ca62e251ba80";

        vm.warp(
            uint256(type(uint64).max) - verifier.DEFAULT_CHALLENGE_RESPONSE_WINDOW_SECONDS() + 1
        );
        verifier.commitAnchoredTreeWithWindow(blockHash, 0, wrongCrystalRoot, postedMerkleRoot, 1);

        vm.expectRevert("CrystalComponentVerifier: response deadline overflow");
        verifier.submitAnchoredLocalizedChallenge(
            blockHash, 0, crystalWitness, targetMerkleHash, merkleProof
        );
    }

    function test_submitAnchoredLocalizedChallengeRejectsMerkleAnchorMismatch() public {
        bytes32 blockHash = keccak256("block-anchor-mismatch");
        bytes32 wrongCrystalRoot =
            hex"118dfd9b12cd3d0a000000000000000000000000000000000000000000000000";
        bytes32 wrongMerkleRoot =
            hex"08c2b2187f57094c5a06d1143d4bad46840302d0ad10485e221986aca4ba03e4";
        bytes memory crystalWitness = hex"038956ba36c62f1b0100179566aa16d21b27";
        bytes32 targetMerkleHash =
            hex"4cf8b5478ccbad8aaff6d5d7a5224f0577a8ba3bd97b12dba9dc3081c30aa937";
        bytes memory merkleProof =
            hex"0100bbfe0762ecf04769e499b88b12ef2549fa065e6d0608eb154f66ca62e251ba80";

        verifier.commitAnchoredTree(blockHash, 0, wrongCrystalRoot, wrongMerkleRoot);

        vm.expectRevert("CrystalComponentVerifier: merkle anchor mismatch");
        verifier.submitAnchoredLocalizedChallenge(
            blockHash, 0, crystalWitness, targetMerkleHash, merkleProof
        );
    }

    function test_submitAnchoredLocalizedChallengeRejectsPathMismatch() public {
        bytes32 blockHash = keccak256("block-path-mismatch");
        bytes32 wrongCrystalRoot =
            hex"118dfd9b12cd3d0a000000000000000000000000000000000000000000000000";
        bytes32 postedMerkleRoot =
            hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";
        bytes memory crystalWitness = hex"038956ba36c62f1b0101179566aa16d21b27";
        bytes32 targetMerkleHash =
            hex"4cf8b5478ccbad8aaff6d5d7a5224f0577a8ba3bd97b12dba9dc3081c30aa937";
        bytes memory merkleProof =
            hex"0100bbfe0762ecf04769e499b88b12ef2549fa065e6d0608eb154f66ca62e251ba80";

        verifier.commitAnchoredTree(blockHash, 0, wrongCrystalRoot, postedMerkleRoot);

        vm.expectRevert("CrystalComponentVerifier: localized path mismatch");
        verifier.submitAnchoredLocalizedChallenge(
            blockHash, 0, crystalWitness, targetMerkleHash, merkleProof
        );
    }

    function test_submitAnchoredLocalizedChallengeRejectsMatchingCrystalRoot() public {
        bytes32 blockHash = keccak256("block-no-mismatch");
        bytes32 expectedCrystalRoot =
            hex"0c4aedf82d02192b000000000000000000000000000000000000000000000000";
        bytes32 postedMerkleRoot =
            hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";
        bytes memory crystalWitness = hex"038956ba36c62f1b0100179566aa16d21b27";
        bytes32 targetMerkleHash =
            hex"4cf8b5478ccbad8aaff6d5d7a5224f0577a8ba3bd97b12dba9dc3081c30aa937";
        bytes memory merkleProof =
            hex"0100bbfe0762ecf04769e499b88b12ef2549fa065e6d0608eb154f66ca62e251ba80";

        verifier.commitAnchoredTree(blockHash, 0, expectedCrystalRoot, postedMerkleRoot);

        vm.expectRevert("CrystalComponentVerifier: no mismatch detected");
        verifier.submitAnchoredLocalizedChallenge(
            blockHash, 0, crystalWitness, targetMerkleHash, merkleProof
        );
    }

    function test_submitAnchoredLocalizedChallengeRejectsAfterWindow() public {
        bytes32 blockHash = keccak256("block-window-closed");
        bytes32 wrongCrystalRoot =
            hex"118dfd9b12cd3d0a000000000000000000000000000000000000000000000000";
        bytes32 postedMerkleRoot =
            hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";
        bytes memory crystalWitness = hex"038956ba36c62f1b0100179566aa16d21b27";
        bytes32 targetMerkleHash =
            hex"4cf8b5478ccbad8aaff6d5d7a5224f0577a8ba3bd97b12dba9dc3081c30aa937";
        bytes memory merkleProof =
            hex"0100bbfe0762ecf04769e499b88b12ef2549fa065e6d0608eb154f66ca62e251ba80";

        verifier.commitAnchoredTreeWithWindow(blockHash, 0, wrongCrystalRoot, postedMerkleRoot, 10);
        vm.warp(block.timestamp + 10);

        vm.expectRevert("CrystalComponentVerifier: challenge window closed");
        verifier.submitAnchoredLocalizedChallenge(
            blockHash, 0, crystalWitness, targetMerkleHash, merkleProof
        );
    }

    function test_submitAnchoredLocalizedChallengeRejectsFinalizedTree() public {
        bytes32 blockHash = keccak256("block-finalized-no-challenge");
        bytes32 wrongCrystalRoot =
            hex"118dfd9b12cd3d0a000000000000000000000000000000000000000000000000";
        bytes32 postedMerkleRoot =
            hex"ee3ac96a16b5bffff2563ef3c8ec7df539866c0c901b7945ac5419b920569d2e";
        bytes memory crystalWitness = hex"038956ba36c62f1b0100179566aa16d21b27";
        bytes32 targetMerkleHash =
            hex"4cf8b5478ccbad8aaff6d5d7a5224f0577a8ba3bd97b12dba9dc3081c30aa937";
        bytes memory merkleProof =
            hex"0100bbfe0762ecf04769e499b88b12ef2549fa065e6d0608eb154f66ca62e251ba80";

        verifier.commitAnchoredTreeWithWindow(blockHash, 0, wrongCrystalRoot, postedMerkleRoot, 10);
        vm.warp(block.timestamp + 10);
        verifier.finalizeAnchoredTree(blockHash, 0);

        vm.expectRevert("CrystalComponentVerifier: anchored tree not active");
        verifier.submitAnchoredLocalizedChallenge(
            blockHash, 0, crystalWitness, targetMerkleHash, merkleProof
        );
    }

    function test_differentStructureMatchesSdkKnownRoot() public view {
        bytes memory tree = _encodeInternal(
            _encodeLeaf(10),
            _encodeInternal(_encodeLeaf(20), _encodeInternal(_encodeLeaf(30), _encodeLeaf(40)))
        );
        bytes32 expectedRoot = hex"118dfd9b12cd3d0a000000000000000000000000000000000000000000000000";

        (bool valid, bytes32 computedRoot) = verifier.verifyTreeRoot(tree, expectedRoot);

        assertTrue(valid, "known SDK right-deep root should verify");
        assertEq(computedRoot, expectedRoot, "computed root should match SDK root");
    }

    function test_rejectsTrailingTreeData() public {
        bytes memory tree = bytes.concat(_encodeInternal(_encodeLeaf(10), _encodeLeaf(20)), hex"99");
        bytes32 expectedRoot = hex"038956ba36c62f1b000000000000000000000000000000000000000000000000";

        vm.expectRevert("CrystalComponentVerifier: trailing tree data");
        verifier.verifyTreeRoot(tree, expectedRoot);
    }

    function _encodeLeaf(uint8 state) internal pure returns (bytes memory) {
        bytes memory encoded = new bytes(9);
        encoded[0] = 0x00;
        for (uint256 h = 0; h < 8; h++) {
            encoded[1 + h] = bytes1(state);
        }
        return encoded;
    }

    function _encodeInternal(bytes memory left, bytes memory right)
        internal
        pure
        returns (bytes memory)
    {
        return bytes.concat(hex"01", left, right);
    }

    function _componentTable(uint256 head) internal pure returns (bytes memory) {
        if (head == 0) {
            return hex"00010002020302030302010103020300010302010301010302000103010101020300010101030101020002000003010300020002010103010103030101030200";
        }
        if (head == 1) {
            return hex"01000200020201030101000300000100000100010303000300020103030301020000010103000102000001020203010202010002000301000200010001020301";
        }
        if (head == 2) {
            return hex"03000203000100030201010203000200010200030203030203010203000101010001030301000201000000000200010301020301030303030200010101010001";
        }
        if (head == 3) {
            return hex"00010100030300000203000301030302020000000203000102020200030002010003010001000201010203010300030102010000020303000002030302030102";
        }
        if (head == 4) {
            return hex"01000000030003020200010102030000000000000203020303010200010201000103000000000102030302020302000100030201020003030201010102000200";
        }
        if (head == 5) {
            return hex"01000300020100020200020102000200010003010002030103010003020100000100020302010100000100010000000003030301020200020100020101000000";
        }
        if (head == 6) {
            return hex"01010301010003000301030100000001030300000302010100030302010202030302020003000103020100030000000000030102030003000102000100020102";
        }
        if (head == 7) {
            return hex"01030301030201020302000003030103030303030303020100020302030201000301000102000203000302030003030000010001020300000203010303000201";
        }
        revert("invalid head");
    }
}
