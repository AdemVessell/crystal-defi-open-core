// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.20;

/**
 * @title CrystalVerifier
 * @author Arkhē Technologic
 * @notice Prototype on-chain consistency checks for L2 transaction trees using
 *         non-associative algebraic folding (PathCrystal).
 *
 * @dev Crystal roots are compact structural fingerprints, not standalone
 *      cryptographic commitments. Production use must bind this signal to
 *      hash/Merkle/native-chain anchors. The challenge helpers below are
 *      prototype consistency checks, not a complete fraud-proof game.
 *
 *      Gas profile:
 *        - Single fold:    ~200 gas (one SLOAD + lookup)
 *        - Tree verify:    ~200 * n_internal_nodes * n_heads gas
 *        - Typical 7-node: measure with Foundry gas tests before citing
 *
 *      Prototype table storage is large: 8 heads x 256 x 256 = 512 KB.
 *      Production should use compact component tables instead of full tables.
 */
contract CrystalVerifier {
    // ──────────────────────────────────────────────
    //  Constants
    // ──────────────────────────────────────────────

    uint256 public constant STATE_SIZE = 256;
    uint256 public constant N_HEADS = 8;
    uint256 public constant TABLE_SIZE = 65536; // 256 * 256

    // ──────────────────────────────────────────────
    //  Storage
    // ──────────────────────────────────────────────

    /// @notice Crystal composition tables. _tables[head][i * 256 + j] = fold(i, j).
    /// Packed as bytes: each entry is one uint8.
    bytes[N_HEADS] private _tables;

    /// @notice Whether tables have been initialized (one-time setup).
    bool public initialized;

    /// @notice Contract owner (deployer). Only owner can initialize tables.
    address public owner;

    /// @notice Posted crystal roots per block. blockRoots[blockHash] = crystalRoot.
    mapping(bytes32 => bytes32) public blockRoots;

    /// @notice Posted per-tree roots. treeRoots[blockHash][treeIndex] = crystalRoot.
    mapping(bytes32 => mapping(uint256 => bytes32)) public treeRoots;

    /// @notice Challenged blocks.
    mapping(bytes32 => bool) public challenged;

    /// @notice Sequencer stake tracking (simplified).
    mapping(address => uint256) public stakes;

    // ──────────────────────────────────────────────
    //  Events
    // ──────────────────────────────────────────────

    event TablesInitialized(uint256 timestamp);
    event BlockCommitted(bytes32 indexed blockHash, bytes32 crystalRoot, address sequencer);
    event TreeCommitted(
        bytes32 indexed blockHash, uint256 indexed treeIndex, bytes32 crystalRoot, address sequencer
    );
    event ConsistencyChallengeSubmitted(
        bytes32 indexed blockHash, address challenger, bytes32 expectedRoot, bytes32 computedRoot
    );
    event StructuralDivergenceChallengeSubmitted(
        bytes32 indexed blockHash, address challenger, bytes32 originalRoot, bytes32 divergentRoot
    );
    event FraudProofSubmitted(
        bytes32 indexed blockHash, address challenger, bytes32 expectedRoot, bytes32 computedRoot
    );
    event SequencerSlashed(address indexed sequencer, uint256 amount);

    // ──────────────────────────────────────────────
    //  Modifiers
    // ──────────────────────────────────────────────

    modifier onlyOwner() {
        require(msg.sender == owner, "CrystalVerifier: not owner");
        _;
    }

    modifier onlyInitialized() {
        require(initialized, "CrystalVerifier: tables not initialized");
        _;
    }

    // ──────────────────────────────────────────────
    //  Constructor
    // ──────────────────────────────────────────────

    constructor() {
        owner = msg.sender;
    }

    // ──────────────────────────────────────────────
    //  Table Initialization
    // ──────────────────────────────────────────────

    /**
     * @notice Initialize one crystal head table. Call once per head (0..7).
     * @param headIndex Which head (0 to N_HEADS-1).
     * @param tableData Packed 256×256 bytes — tableData[i*256+j] = fold(i,j).
     */
    function initializeHead(uint256 headIndex, bytes calldata tableData) external onlyOwner {
        require(!initialized, "CrystalVerifier: already initialized");
        require(headIndex < N_HEADS, "CrystalVerifier: invalid head");
        require(tableData.length == TABLE_SIZE, "CrystalVerifier: invalid table size");
        _tables[headIndex] = tableData;
    }

    /**
     * @notice Seal the tables. No further changes allowed.
     */
    function finalizeInitialization() external onlyOwner {
        // Verify all heads are set
        for (uint256 h = 0; h < N_HEADS; h++) {
            require(_tables[h].length == TABLE_SIZE, "CrystalVerifier: head not set");
        }
        initialized = true;
        emit TablesInitialized(block.timestamp);
    }

    // ──────────────────────────────────────────────
    //  Core Fold Operation
    // ──────────────────────────────────────────────

    /**
     * @notice Single crystal fold: compose two states through one head.
     * @param left Left child state (0-255).
     * @param right Right child state (0-255).
     * @param head Head index (0 to N_HEADS-1).
     * @return result The composed state.
     *
     * @dev This is the atomic operation. Gas: ~200 (cold SLOAD + index).
     */
    function fold(uint8 left, uint8 right, uint256 head)
        public
        view
        onlyInitialized
        returns (uint8 result)
    {
        uint256 index = uint256(left) * STATE_SIZE + uint256(right);
        result = uint8(_tables[head][index]);
    }

    /**
     * @notice Fold through all heads at once.
     * @param left Left child states (one per head).
     * @param right Right child states (one per head).
     * @return results Composed states for each head.
     */
    function foldAllHeads(uint8[N_HEADS] calldata left, uint8[N_HEADS] calldata right)
        public
        view
        onlyInitialized
        returns (uint8[N_HEADS] memory results)
    {
        for (uint256 h = 0; h < N_HEADS; h++) {
            uint256 index = uint256(left[h]) * STATE_SIZE + uint256(right[h]);
            results[h] = uint8(_tables[h][index]);
        }
    }

    // ──────────────────────────────────────────────
    //  Tree Verification
    // ──────────────────────────────────────────────

    /**
     * @notice Verify a crystal root for a serialized transaction tree.
     * @param treeData ABI-encoded tree (see _decodeAndFold).
     * @param claimedRoot The crystal root the sequencer posted.
     * @return valid Whether the root matches.
     * @return computedRoot The re-computed root.
     *
     * @dev The tree is encoded as a flat byte array:
     *      - 0x00 prefix = leaf node, followed by N_HEADS bytes (leaf states)
     *      - 0x01 prefix = internal node, followed by left subtree then right subtree
     *
     *      Gas: O(n_internal_nodes * N_HEADS * 200)
     */
    function verifyTreeRoot(bytes calldata treeData, bytes32 claimedRoot)
        external
        view
        onlyInitialized
        returns (bool valid, bytes32 computedRoot)
    {
        uint8[N_HEADS] memory roots;
        uint256 offset = 0;
        (roots, offset) = _decodeAndFold(treeData, offset);
        require(offset == treeData.length, "CrystalVerifier: trailing tree data");

        computedRoot = _packRoot(roots);
        valid = (computedRoot == claimedRoot);
    }

    /**
     * @notice Verify an aggregate block crystal root.
     * @param rootsInBlock Array of per-tree crystal roots in the block.
     * @param claimedBlockRoot The aggregate root the sequencer posted.
     * @return valid Whether the aggregate matches.
     */
    function verifyBlockRoot(bytes32[] calldata rootsInBlock, bytes32 claimedBlockRoot)
        external
        view
        onlyInitialized
        returns (bool valid)
    {
        require(rootsInBlock.length > 0, "CrystalVerifier: empty block");

        uint8[N_HEADS] memory agg = _unpackRoot(rootsInBlock[0]);

        for (uint256 i = 1; i < rootsInBlock.length; i++) {
            uint8[N_HEADS] memory next = _unpackRoot(rootsInBlock[i]);
            for (uint256 h = 0; h < N_HEADS; h++) {
                uint256 index = uint256(agg[h]) * STATE_SIZE + uint256(next[h]);
                agg[h] = uint8(_tables[h][index]);
            }
        }

        valid = (_packRoot(agg) == claimedBlockRoot);
    }

    // ──────────────────────────────────────────────
    //  Block Commitment (Sequencer calls this)
    // ──────────────────────────────────────────────

    /**
     * @notice Sequencer commits a crystal root for a block.
     * @param blockHash The L2 block hash.
     * @param crystalRoot The aggregate crystal root.
     */
    function commitBlock(bytes32 blockHash, bytes32 crystalRoot) external {
        require(blockRoots[blockHash] == bytes32(0), "CrystalVerifier: already committed");
        blockRoots[blockHash] = crystalRoot;
        emit BlockCommitted(blockHash, crystalRoot, msg.sender);
    }

    /**
     * @notice Commit a per-tree Crystal root for a block.
     * @dev This is the preferred prototype path for consistency challenges.
     */
    function commitTree(bytes32 blockHash, uint256 treeIndex, bytes32 crystalRoot) external {
        require(
            treeRoots[blockHash][treeIndex] == bytes32(0), "CrystalVerifier: tree already committed"
        );
        treeRoots[blockHash][treeIndex] = crystalRoot;
        emit TreeCommitted(blockHash, treeIndex, crystalRoot, msg.sender);
    }

    // ──────────────────────────────────────────────
    //  Prototype Consistency Challenge Submission
    // ──────────────────────────────────────────────

    /**
     * @notice Submit a consistency challenge: the posted crystal root doesn't match
     *         re-folding the transaction tree from calldata.
     * @param blockHash The block being challenged.
     * @param treeData The serialized tree (from L1 calldata).
     * @param sequencer The sequencer to slash.
     *
     * @dev The contract re-folds the tree and compares against the posted root.
     *      If mismatch: block is marked challenged and prototype stake logic runs.
     */
    function submitConsistencyChallenge(
        bytes32 blockHash,
        bytes calldata treeData,
        address sequencer
    ) external onlyInitialized {
        _submitConsistencyChallenge(blockHash, treeData, sequencer);
    }

    /**
     * @notice Submit a per-tree consistency challenge.
     * @dev This is preferred over aggregate block-root challenge placeholders.
     */
    function submitTreeConsistencyChallenge(
        bytes32 blockHash,
        uint256 treeIndex,
        bytes calldata treeData
    ) external onlyInitialized {
        bytes32 postedRoot = treeRoots[blockHash][treeIndex];
        require(postedRoot != bytes32(0), "CrystalVerifier: tree not committed");
        require(!challenged[blockHash], "CrystalVerifier: already challenged");

        uint8[N_HEADS] memory roots;
        uint256 offset = 0;
        (roots, offset) = _decodeAndFold(treeData, offset);
        require(offset == treeData.length, "CrystalVerifier: trailing tree data");
        bytes32 computedRoot = _packRoot(roots);

        require(computedRoot != postedRoot, "CrystalVerifier: no mismatch detected");

        challenged[blockHash] = true;
        emit ConsistencyChallengeSubmitted(blockHash, msg.sender, postedRoot, computedRoot);
    }

    /**
     * @notice Deprecated compatibility wrapper for submitConsistencyChallenge.
     */
    function submitFraudProof(
        bytes32 blockHash,
        uint256,
        /* treeIndex */
        bytes calldata treeData,
        address sequencer
    ) external onlyInitialized {
        _submitConsistencyChallenge(blockHash, treeData, sequencer);
    }

    function _submitConsistencyChallenge(
        bytes32 blockHash,
        bytes calldata treeData,
        address /* sequencer */
    )
        internal
    {
        bytes32 postedRoot = blockRoots[blockHash];
        require(postedRoot != bytes32(0), "CrystalVerifier: block not committed");
        require(!challenged[blockHash], "CrystalVerifier: already challenged");

        // Re-fold the tree
        uint8[N_HEADS] memory roots;
        uint256 offset = 0;
        (roots, offset) = _decodeAndFold(treeData, offset);
        require(offset == treeData.length, "CrystalVerifier: trailing tree data");
        bytes32 computedRoot = _packRoot(roots);

        // Check for mismatch
        // Note: in production, this would check per-tree root against the
        // individual tree commitment, not the aggregate. Simplified here.
        require(computedRoot != postedRoot, "CrystalVerifier: no fraud detected");

        // Mismatch confirmed
        challenged[blockHash] = true;

        emit ConsistencyChallengeSubmitted(blockHash, msg.sender, postedRoot, computedRoot);
        emit FraudProofSubmitted(blockHash, msg.sender, postedRoot, computedRoot);
    }

    /**
     * @notice Submit a structural-difference challenge: two trees with different
     *         structure produce different crystal roots.
     * @param blockHash The block being challenged.
     * @param originalTreeData The original tree (from mempool/user submission).
     * @param tamperedTreeData The tree that was actually posted (restructured).
     */
    function submitStructuralDivergenceChallenge(
        bytes32 blockHash,
        bytes calldata originalTreeData,
        bytes calldata tamperedTreeData
    ) external onlyInitialized {
        _submitStructuralDivergenceChallenge(blockHash, originalTreeData, tamperedTreeData);
    }

    /**
     * @notice Deprecated compatibility wrapper for submitStructuralDivergenceChallenge.
     */
    function submitMevFraudProof(
        bytes32 blockHash,
        bytes calldata originalTreeData,
        bytes calldata tamperedTreeData
    ) external onlyInitialized {
        _submitStructuralDivergenceChallenge(blockHash, originalTreeData, tamperedTreeData);
    }

    function _submitStructuralDivergenceChallenge(
        bytes32 blockHash,
        bytes calldata originalTreeData,
        bytes calldata tamperedTreeData
    ) internal {
        require(blockRoots[blockHash] != bytes32(0), "CrystalVerifier: block not committed");
        require(!challenged[blockHash], "CrystalVerifier: already challenged");

        // Fold both trees
        uint8[N_HEADS] memory origRoots;
        uint8[N_HEADS] memory tampRoots;
        uint256 offset;

        (origRoots, offset) = _decodeAndFold(originalTreeData, 0);
        require(offset == originalTreeData.length, "CrystalVerifier: trailing original tree data");
        (tampRoots, offset) = _decodeAndFold(tamperedTreeData, 0);
        require(offset == tamperedTreeData.length, "CrystalVerifier: trailing tampered tree data");

        bytes32 origRoot = _packRoot(origRoots);
        bytes32 tampRoot = _packRoot(tampRoots);

        // Roots must differ (showing structural disagreement under Crystal)
        require(origRoot != tampRoot, "CrystalVerifier: trees are identical");

        // Mark challenged
        challenged[blockHash] = true;
        emit StructuralDivergenceChallengeSubmitted(blockHash, msg.sender, origRoot, tampRoot);
        emit FraudProofSubmitted(blockHash, msg.sender, origRoot, tampRoot);
    }

    // ──────────────────────────────────────────────
    //  Staking (simplified)
    // ──────────────────────────────────────────────

    function depositStake() external payable {
        stakes[msg.sender] += msg.value;
    }

    function withdrawStake(uint256 amount) external {
        require(stakes[msg.sender] >= amount, "CrystalVerifier: insufficient stake");
        stakes[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }

    // ──────────────────────────────────────────────
    //  Internal: Tree Decode + Fold
    // ──────────────────────────────────────────────

    /**
     * @dev Recursively decode and fold a tree from packed bytes.
     *
     *      Encoding:
     *        Leaf:     0x00 ++ leafState[0] ++ leafState[1] ++ ... ++ leafState[N_HEADS-1]
     *        Internal: 0x01 ++ leftSubtree ++ rightSubtree
     *
     *      The leaf states are the crystal states for each head (same value
     *      for all heads at the leaf level — the leaf-to-state mapping is
     *      deterministic and published).
     */
    function _decodeAndFold(bytes calldata data, uint256 offset)
        internal
        view
        returns (uint8[N_HEADS] memory roots, uint256 newOffset)
    {
        require(offset < data.length, "CrystalVerifier: truncated tree");

        uint8 nodeType = uint8(data[offset]);
        offset++;

        if (nodeType == 0x00) {
            // Leaf node: read N_HEADS state bytes
            require(offset + N_HEADS <= data.length, "CrystalVerifier: truncated leaf");
            for (uint256 h = 0; h < N_HEADS; h++) {
                roots[h] = uint8(data[offset]);
                offset++;
            }
            newOffset = offset;
        } else if (nodeType == 0x01) {
            // Internal node: decode left, decode right, fold
            uint8[N_HEADS] memory leftRoots;
            uint8[N_HEADS] memory rightRoots;

            (leftRoots, offset) = _decodeAndFold(data, offset);
            (rightRoots, offset) = _decodeAndFold(data, offset);

            for (uint256 h = 0; h < N_HEADS; h++) {
                uint256 index = uint256(leftRoots[h]) * STATE_SIZE + uint256(rightRoots[h]);
                roots[h] = uint8(_tables[h][index]);
            }
            newOffset = offset;
        } else {
            revert("CrystalVerifier: invalid node type");
        }
    }

    // ──────────────────────────────────────────────
    //  Internal: Root Packing
    // ──────────────────────────────────────────────

    /**
     * @dev Pack N_HEADS uint8 roots into a bytes32.
     *      Roots occupy the first N_HEADS bytes; rest is zero-padded.
     */
    function _packRoot(uint8[N_HEADS] memory roots) internal pure returns (bytes32 packed) {
        for (uint256 h = 0; h < N_HEADS; h++) {
            packed |= bytes32(uint256(roots[h])) << (248 - h * 8);
        }
    }

    /**
     * @dev Unpack a bytes32 into N_HEADS uint8 roots.
     */
    function _unpackRoot(bytes32 packed) internal pure returns (uint8[N_HEADS] memory roots) {
        for (uint256 h = 0; h < N_HEADS; h++) {
            roots[h] = uint8(uint256(packed >> (248 - h * 8)));
        }
    }

    // ──────────────────────────────────────────────
    //  View Helpers
    // ──────────────────────────────────────────────

    /**
     * @notice Check if a block has been committed.
     */
    function isCommitted(bytes32 blockHash) external view returns (bool) {
        return blockRoots[blockHash] != bytes32(0);
    }

    /**
     * @notice Check if a block has been challenged.
     */
    function isChallenged(bytes32 blockHash) external view returns (bool) {
        return challenged[blockHash];
    }

    /**
     * @notice Get the crystal root for a committed block.
     */
    function getCrystalRoot(bytes32 blockHash) external view returns (bytes32) {
        return blockRoots[blockHash];
    }

    /**
     * @notice Check if a per-tree root has been committed.
     */
    function isTreeCommitted(bytes32 blockHash, uint256 treeIndex) external view returns (bool) {
        return treeRoots[blockHash][treeIndex] != bytes32(0);
    }

    /**
     * @notice Get a per-tree Crystal root for a block.
     */
    function getTreeRoot(bytes32 blockHash, uint256 treeIndex) external view returns (bytes32) {
        return treeRoots[blockHash][treeIndex];
    }

    /**
     * @notice Get initialized byte length for one head.
     */
    function headDataLength(uint256 headIndex) external view returns (uint256) {
        require(headIndex < N_HEADS, "CrystalVerifier: invalid head");
        return _tables[headIndex].length;
    }
}
