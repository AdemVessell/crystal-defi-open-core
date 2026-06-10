// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../contracts/CrystalVerifier.sol";

/**
 * @title CrystalVerifierTest
 * @notice Foundry test suite for the CrystalVerifier contract.
 *
 * Tests:
 *   1. Table initialization and finalization
 *   2. Single fold correctness
 *   3. Tree encoding, decoding, and fold verification
 *   4. Block commitment and root verification
 *   5. Fraud proof: root mismatch
 *   6. MEV fraud proof: structural reorganization
 *   7. Root packing/unpacking roundtrip
 *   8. Gas benchmarking
 */
contract CrystalVerifierTest is Test {
    CrystalVerifier public verifier;

    address public owner = address(this);
    address public sequencer = address(0xBEEF);
    address public challenger = address(0xCAFE);

    function setUp() public {
        verifier = new CrystalVerifier();
        _initializeTables();
    }

    // ──────────────────────────────────────
    //  Helper: Initialize with test tables
    // ──────────────────────────────────────

    function _initializeTables() internal {
        for (uint256 h = 0; h < 8; h++) {
            bytes memory tableData = new bytes(65536);
            // Fill with a simple non-associative pattern:
            // fold(i, j) = (i * (h+3) + j * (h+7) + h*17) % 256
            // This is non-associative because the coefficients differ per position.
            for (uint256 i = 0; i < 256; i++) {
                for (uint256 j = 0; j < 256; j++) {
                    tableData[i * 256 + j] =
                        bytes1(uint8((i * (h + 3) + j * (h + 7) + h * 17) % 256));
                }
            }
            verifier.initializeHead(h, tableData);
        }
        verifier.finalizeInitialization();
    }

    // ──────────────────────────────────────
    //  Helper: Encode trees
    // ──────────────────────────────────────

    function _encodeLeaf(uint8 state) internal pure returns (bytes memory) {
        // Leaf: 0x00 ++ state repeated N_HEADS times
        bytes memory encoded = new bytes(9); // 1 + 8
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
        // Internal: 0x01 ++ left ++ right
        bytes memory encoded = new bytes(1 + left.length + right.length);
        encoded[0] = 0x01;
        for (uint256 i = 0; i < left.length; i++) {
            encoded[1 + i] = left[i];
        }
        for (uint256 i = 0; i < right.length; i++) {
            encoded[1 + left.length + i] = right[i];
        }
        return encoded;
    }

    // ──────────────────────────────────────
    //  Test: Initialization
    // ──────────────────────────────────────

    function test_initialized() public view {
        assertTrue(verifier.initialized());
    }

    function test_cannotReinitialize() public {
        bytes memory dummy = new bytes(65536);
        vm.expectRevert("CrystalVerifier: already initialized");
        verifier.initializeHead(0, dummy);
    }

    // ──────────────────────────────────────
    //  Test: Single Fold
    // ──────────────────────────────────────

    function test_foldDeterministic() public view {
        uint8 r1 = verifier.fold(10, 20, 0);
        uint8 r2 = verifier.fold(10, 20, 0);
        assertEq(r1, r2, "fold should be deterministic");
    }

    function test_foldNonCommutative() public view {
        // Non-associative tables should generally not be commutative
        uint8 ab = verifier.fold(42, 99, 0);
        uint8 ba = verifier.fold(99, 42, 0);
        // Not guaranteed to differ for every pair, but should differ for most
        // We test a specific pair that we know differs with our test tables
        // fold(42,99,0) = (42*3 + 99*7 + 0) % 256 = (126 + 693) % 256 = 819 % 256 = 51
        // fold(99,42,0) = (99*3 + 42*7 + 0) % 256 = (297 + 294) % 256 = 591 % 256 = 79
        assertTrue(ab != ba, "fold should be non-commutative");
    }

    function test_foldNonAssociative() public view {
        // The key property: fold(fold(a,b), c) != fold(a, fold(b,c))
        uint8 a = 10;
        uint8 b = 20;
        uint8 c = 30;

        uint8 ab = verifier.fold(a, b, 0);
        uint8 ab_c = verifier.fold(ab, c, 0);

        uint8 bc = verifier.fold(b, c, 0);
        uint8 a_bc = verifier.fold(a, bc, 0);

        assertTrue(ab_c != a_bc, "fold should be non-associative");
    }

    // ──────────────────────────────────────
    //  Test: Tree Verification
    // ──────────────────────────────────────

    function test_leafTreeVerification() public view {
        bytes memory tree = _encodeLeaf(42);

        // Compute expected root: leaf state 42 on all heads
        bytes32 expectedRoot = bytes32(0);
        for (uint256 h = 0; h < 8; h++) {
            expectedRoot |= bytes32(uint256(42)) << (248 - h * 8);
        }

        (bool valid, bytes32 computed) = verifier.verifyTreeRoot(tree, expectedRoot);
        assertTrue(valid, "leaf tree should verify");
        assertEq(computed, expectedRoot);
    }

    function test_simpleInternalTreeVerification() public view {
        // Tree: (leaf_10, leaf_20)
        bytes memory left = _encodeLeaf(10);
        bytes memory right = _encodeLeaf(20);
        bytes memory tree = _encodeInternal(left, right);

        // Compute expected root manually
        bytes32 expectedRoot = bytes32(0);
        for (uint256 h = 0; h < 8; h++) {
            uint8 r = verifier.fold(10, 20, h);
            expectedRoot |= bytes32(uint256(r)) << (248 - h * 8);
        }

        (bool valid, bytes32 computed) = verifier.verifyTreeRoot(tree, expectedRoot);
        assertTrue(valid, "simple internal tree should verify");
        assertEq(computed, expectedRoot);
    }

    function test_wrongRootFails() public view {
        bytes memory tree = _encodeInternal(_encodeLeaf(10), _encodeLeaf(20));
        bytes32 wrongRoot = bytes32(uint256(0xDEADBEEF));

        (bool valid,) = verifier.verifyTreeRoot(tree, wrongRoot);
        assertFalse(valid, "wrong root should not verify");
    }

    // ──────────────────────────────────────
    //  Test: Structure Sensitivity
    // ──────────────────────────────────────

    function test_differentStructureDifferentRoot() public view {
        // Tree A: ((10, 20), 30)  — left-deep
        bytes memory treeA =
            _encodeInternal(_encodeInternal(_encodeLeaf(10), _encodeLeaf(20)), _encodeLeaf(30));

        // Tree B: (10, (20, 30))  — right-deep
        bytes memory treeB =
            _encodeInternal(_encodeLeaf(10), _encodeInternal(_encodeLeaf(20), _encodeLeaf(30)));

        (, bytes32 rootA) = verifier.verifyTreeRoot(treeA, bytes32(0));
        (, bytes32 rootB) = verifier.verifyTreeRoot(treeB, bytes32(0));

        assertTrue(rootA != rootB, "different structure must produce different root");
    }

    function test_subtreeSwapDifferentRoot() public view {
        // Tree A: (10, 20)
        bytes memory treeA = _encodeInternal(_encodeLeaf(10), _encodeLeaf(20));

        // Tree B: (20, 10)  — subtree swap
        bytes memory treeB = _encodeInternal(_encodeLeaf(20), _encodeLeaf(10));

        (, bytes32 rootA) = verifier.verifyTreeRoot(treeA, bytes32(0));
        (, bytes32 rootB) = verifier.verifyTreeRoot(treeB, bytes32(0));

        assertTrue(rootA != rootB, "subtree swap must produce different root");
    }

    // ──────────────────────────────────────
    //  Test: Block Commitment
    // ──────────────────────────────────────

    function test_commitBlock() public {
        bytes32 blockHash = keccak256("block1");
        bytes32 crystalRoot = bytes32(uint256(0x1234));

        vm.prank(sequencer);
        verifier.commitBlock(blockHash, crystalRoot);

        assertTrue(verifier.isCommitted(blockHash));
        assertEq(verifier.getCrystalRoot(blockHash), crystalRoot);
    }

    function test_cannotDoubleCommit() public {
        bytes32 blockHash = keccak256("block1");

        vm.prank(sequencer);
        verifier.commitBlock(blockHash, bytes32(uint256(1)));

        vm.prank(sequencer);
        vm.expectRevert("CrystalVerifier: already committed");
        verifier.commitBlock(blockHash, bytes32(uint256(2)));
    }

    // ──────────────────────────────────────
    //  Test: Fraud Proof
    // ──────────────────────────────────────

    function test_fraudProofAccepted() public {
        bytes32 blockHash = keccak256("block1");
        bytes memory tree = _encodeInternal(_encodeLeaf(10), _encodeLeaf(20));

        // Sequencer commits a WRONG root
        bytes32 wrongRoot = bytes32(uint256(0xBAD));
        vm.prank(sequencer);
        verifier.commitBlock(blockHash, wrongRoot);

        // Sequencer stakes
        vm.deal(sequencer, 10 ether);
        vm.prank(sequencer);
        verifier.depositStake{ value: 10 ether }();

        // Challenger submits fraud proof
        vm.prank(challenger);
        verifier.submitFraudProof(blockHash, 0, tree, sequencer);

        assertTrue(verifier.isChallenged(blockHash));
        assertEq(verifier.stakes(sequencer), 10 ether); // prototype challenge no longer slashes
    }

    function test_fraudProofRejectedWhenCorrect() public {
        bytes32 blockHash = keccak256("block1");
        bytes memory tree = _encodeInternal(_encodeLeaf(10), _encodeLeaf(20));

        // Compute correct root
        (, bytes32 correctRoot) = verifier.verifyTreeRoot(tree, bytes32(0));

        // Sequencer commits correct root
        vm.prank(sequencer);
        verifier.commitBlock(blockHash, correctRoot);

        // Challenger tries to submit fraud proof — should fail
        vm.prank(challenger);
        vm.expectRevert("CrystalVerifier: no fraud detected");
        verifier.submitFraudProof(blockHash, 0, tree, sequencer);
    }

    function test_consistencyChallengeAccepted() public {
        bytes32 blockHash = keccak256("challenge_block");
        bytes memory tree = _encodeInternal(_encodeLeaf(10), _encodeLeaf(20));

        vm.prank(sequencer);
        verifier.commitBlock(blockHash, bytes32(uint256(0xBAD)));

        vm.prank(challenger);
        verifier.submitConsistencyChallenge(blockHash, tree, sequencer);

        assertTrue(verifier.isChallenged(blockHash));
    }

    function test_commitTreeAndChallengeTreeRoot() public {
        bytes32 blockHash = keccak256("tree_block");
        bytes memory tree = _encodeInternal(_encodeLeaf(10), _encodeLeaf(20));
        bytes32 wrongRoot = bytes32(uint256(0xBAD));

        vm.prank(sequencer);
        verifier.commitTree(blockHash, 3, wrongRoot);

        assertTrue(verifier.isTreeCommitted(blockHash, 3));
        assertEq(verifier.getTreeRoot(blockHash, 3), wrongRoot);

        vm.prank(challenger);
        verifier.submitTreeConsistencyChallenge(blockHash, 3, tree);

        assertTrue(verifier.isChallenged(blockHash));
    }

    function test_treeChallengeRejectedWhenCorrect() public {
        bytes32 blockHash = keccak256("tree_correct_block");
        bytes memory tree = _encodeInternal(_encodeLeaf(10), _encodeLeaf(20));
        (, bytes32 correctRoot) = verifier.verifyTreeRoot(tree, bytes32(0));

        vm.prank(sequencer);
        verifier.commitTree(blockHash, 7, correctRoot);

        vm.prank(challenger);
        vm.expectRevert("CrystalVerifier: no mismatch detected");
        verifier.submitTreeConsistencyChallenge(blockHash, 7, tree);
    }

    // ──────────────────────────────────────
    //  Test: MEV Fraud Proof
    // ──────────────────────────────────────

    function test_mevFraudProofDetectsRestructure() public {
        bytes32 blockHash = keccak256("mev_block");

        // Original: ((10, 20), 30)
        bytes memory original =
            _encodeInternal(_encodeInternal(_encodeLeaf(10), _encodeLeaf(20)), _encodeLeaf(30));

        // Tampered: (10, (20, 30))  — same leaves, different structure
        bytes memory tampered =
            _encodeInternal(_encodeLeaf(10), _encodeInternal(_encodeLeaf(20), _encodeLeaf(30)));

        vm.prank(sequencer);
        verifier.commitBlock(blockHash, bytes32(uint256(1)));

        vm.prank(challenger);
        verifier.submitMevFraudProof(blockHash, original, tampered);

        assertTrue(verifier.isChallenged(blockHash));
    }

    function test_mevFraudProofRejectsIdenticalTrees() public {
        bytes32 blockHash = keccak256("legit_block");
        bytes memory tree = _encodeInternal(_encodeLeaf(10), _encodeLeaf(20));

        vm.prank(sequencer);
        verifier.commitBlock(blockHash, bytes32(uint256(1)));

        vm.prank(challenger);
        vm.expectRevert("CrystalVerifier: trees are identical");
        verifier.submitMevFraudProof(blockHash, tree, tree);
    }

    function test_structuralDivergenceChallengeDetectsRestructure() public {
        bytes32 blockHash = keccak256("divergence_block");

        bytes memory original =
            _encodeInternal(_encodeInternal(_encodeLeaf(10), _encodeLeaf(20)), _encodeLeaf(30));
        bytes memory divergent =
            _encodeInternal(_encodeLeaf(10), _encodeInternal(_encodeLeaf(20), _encodeLeaf(30)));

        vm.prank(sequencer);
        verifier.commitBlock(blockHash, bytes32(uint256(1)));

        vm.prank(challenger);
        verifier.submitStructuralDivergenceChallenge(blockHash, original, divergent);

        assertTrue(verifier.isChallenged(blockHash));
    }

    // ──────────────────────────────────────
    //  Test: Block Root Aggregation
    // ──────────────────────────────────────

    function test_blockRootAggregation() public view {
        // Build two trees
        bytes memory tree1 = _encodeInternal(_encodeLeaf(10), _encodeLeaf(20));
        bytes memory tree2 = _encodeInternal(_encodeLeaf(30), _encodeLeaf(40));

        (, bytes32 root1) = verifier.verifyTreeRoot(tree1, bytes32(0));
        (, bytes32 root2) = verifier.verifyTreeRoot(tree2, bytes32(0));

        // Compute aggregate: fold root1 into root2
        bytes32[] memory roots = new bytes32[](2);
        roots[0] = root1;
        roots[1] = root2;

        // Manually compute aggregate
        uint8[8] memory agg;
        for (uint256 h = 0; h < 8; h++) {
            uint8 r1 = uint8(uint256(root1 >> (248 - h * 8)));
            uint8 r2 = uint8(uint256(root2 >> (248 - h * 8)));
            agg[h] = verifier.fold(r1, r2, h);
        }
        bytes32 expectedAgg;
        for (uint256 h = 0; h < 8; h++) {
            expectedAgg |= bytes32(uint256(agg[h])) << (248 - h * 8);
        }

        bool valid = verifier.verifyBlockRoot(roots, expectedAgg);
        assertTrue(valid, "block root aggregation should verify");
    }

    // ──────────────────────────────────────
    //  Test: Gas Benchmark
    // ──────────────────────────────────────

    function test_gasSmallTree() public {
        // 3-node tree: (leaf, leaf)
        bytes memory tree = _encodeInternal(_encodeLeaf(10), _encodeLeaf(20));

        uint256 gasBefore = gasleft();
        verifier.verifyTreeRoot(tree, bytes32(0));
        uint256 gasUsed = gasBefore - gasleft();

        // Log for benchmark visibility
        emit log_named_uint("Gas: 3-node tree verify", gasUsed);
    }

    function test_gasMediumTree() public {
        // 7-node tree: ((10,20),(30,40))
        bytes memory tree = _encodeInternal(
            _encodeInternal(_encodeLeaf(10), _encodeLeaf(20)),
            _encodeInternal(_encodeLeaf(30), _encodeLeaf(40))
        );

        uint256 gasBefore = gasleft();
        verifier.verifyTreeRoot(tree, bytes32(0));
        uint256 gasUsed = gasBefore - gasleft();

        emit log_named_uint("Gas: 7-node tree verify", gasUsed);
    }

    function test_gasDeepTree() public {
        // 9-node right-deep: (10, (20, (30, (40, 50))))
        bytes memory tree = _encodeInternal(
            _encodeLeaf(10),
            _encodeInternal(
                _encodeLeaf(20),
                _encodeInternal(_encodeLeaf(30), _encodeInternal(_encodeLeaf(40), _encodeLeaf(50)))
            )
        );

        uint256 gasBefore = gasleft();
        verifier.verifyTreeRoot(tree, bytes32(0));
        uint256 gasUsed = gasBefore - gasleft();

        emit log_named_uint("Gas: 9-node deep tree verify", gasUsed);
    }
}
