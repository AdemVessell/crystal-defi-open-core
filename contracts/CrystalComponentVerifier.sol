// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.20;

/**
 * @title CrystalComponentVerifier
 * @author Arkhē Technologic
 * @notice Compact prototype verifier for Crystal structural roots.
 *
 * @dev This verifier stores the 4x4 component tables used by the Python SDK
 *      instead of storing expanded 256x256 tables. It preserves the same fold
 *      function while reducing table payload from 512 KB to 512 bytes:
 *
 *        8 heads * 4 components * 16 entries = 512 component bytes
 *
 *      Crystal roots are not standalone cryptographic commitments. Production
 *      use should bind these roots to a hash/Merkle/native-chain anchor.
 */
contract CrystalComponentVerifier {
    uint256 public constant STATE_SIZE = 256;
    uint256 public constant N_HEADS = 8;
    uint256 public constant COMPONENTS = 4;
    uint256 public constant COMPONENT_TABLE_SIZE = 64; // 4 * 4 * 4
    uint64 public constant DEFAULT_CHALLENGE_WINDOW_SECONDS = 1 days;
    uint64 public constant DEFAULT_CHALLENGE_RESPONSE_WINDOW_SECONDS = 1 hours;

    /// @notice _componentTables[head][k * 16 + left2 * 4 + right2] = two-bit value.
    bytes[N_HEADS] private _componentTables;

    /// @notice Posted per-tree roots. treeRoots[blockHash][treeIndex] = crystalRoot.
    mapping(bytes32 => mapping(uint256 => bytes32)) public treeRoots;

    /// @notice Posted per-tree Merkle anchors. treeMerkleRoots[blockHash][treeIndex] = merkleRoot.
    mapping(bytes32 => mapping(uint256 => bytes32)) public treeMerkleRoots;

    /// @notice Challenged blocks.
    mapping(bytes32 => bool) public challenged;

    enum AnchoredTreeStatus {
        None,
        Active,
        Challenged,
        Finalized,
        Invalidated
    }

    enum ChallengeStatus {
        None,
        PendingMismatch,
        ResolvedMismatch
    }

    struct AnchoredTreeCommitment {
        AnchoredTreeStatus status;
        bytes32 crystalRoot;
        bytes32 merkleRoot;
        address sequencer;
        uint64 committedAt;
        uint64 challengeDeadline;
    }

    struct LocalizedChallenge {
        ChallengeStatus status;
        bytes32 blockHash;
        uint256 treeIndex;
        address challenger;
        bytes32 postedCrystalRoot;
        bytes32 postedMerkleRoot;
        bytes32 computedCrystalRoot;
        bytes32 computedMerkleRoot;
        bytes32 targetMerkleHash;
        uint64 openedAt;
        uint64 responseDeadline;
    }

    struct LocalizedChallengeRecord {
        bytes32 blockHash;
        uint256 treeIndex;
        address challenger;
        bytes32 postedCrystalRoot;
        bytes32 postedMerkleRoot;
        bytes32 computedCrystalRoot;
        bytes32 computedMerkleRoot;
        bytes32 targetMerkleHash;
    }

    mapping(bytes32 => mapping(uint256 => AnchoredTreeCommitment)) public anchoredTreeCommitments;
    mapping(bytes32 => LocalizedChallenge) public localizedChallenges;

    bool public initialized;
    address public owner;

    event ComponentTablesInitialized(uint256 timestamp);
    event TreeCommitted(
        bytes32 indexed blockHash, uint256 indexed treeIndex, bytes32 crystalRoot, address sequencer
    );
    event AnchoredTreeCommitted(
        bytes32 indexed blockHash,
        uint256 indexed treeIndex,
        bytes32 crystalRoot,
        bytes32 merkleRoot,
        address sequencer
    );
    event AnchoredTreeChallengeWindowOpened(
        bytes32 indexed blockHash, uint256 indexed treeIndex, uint64 challengeDeadline
    );
    event AnchoredTreeFinalized(
        bytes32 indexed blockHash,
        uint256 indexed treeIndex,
        bytes32 crystalRoot,
        bytes32 merkleRoot
    );
    event AnchoredTreeInvalidated(
        bytes32 indexed blockHash, uint256 indexed treeIndex, bytes32 indexed challengeId
    );
    event AnchoredTreeChallenged(
        bytes32 indexed blockHash, uint256 indexed treeIndex, bytes32 indexed challengeId
    );
    event ConsistencyChallengeSubmitted(
        bytes32 indexed blockHash, address challenger, bytes32 expectedRoot, bytes32 computedRoot
    );
    event LocalizedChallengeSubmitted(
        bytes32 indexed challengeId,
        bytes32 indexed blockHash,
        uint256 indexed treeIndex,
        address challenger,
        bytes32 postedCrystalRoot,
        bytes32 postedMerkleRoot,
        bytes32 computedCrystalRoot,
        bytes32 targetMerkleHash,
        uint64 responseDeadline
    );
    event LocalizedChallengeResolved(
        bytes32 indexed challengeId,
        bytes32 indexed blockHash,
        uint256 indexed treeIndex,
        address challenger,
        bytes32 postedCrystalRoot,
        bytes32 postedMerkleRoot,
        bytes32 computedCrystalRoot
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "CrystalComponentVerifier: not owner");
        _;
    }

    modifier onlyInitialized() {
        require(initialized, "CrystalComponentVerifier: tables not initialized");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function initializeHead(uint256 headIndex, bytes calldata componentData) external onlyOwner {
        require(!initialized, "CrystalComponentVerifier: already initialized");
        require(headIndex < N_HEADS, "CrystalComponentVerifier: invalid head");
        require(
            componentData.length == COMPONENT_TABLE_SIZE,
            "CrystalComponentVerifier: invalid component table size"
        );
        _componentTables[headIndex] = componentData;
    }

    function finalizeInitialization() external onlyOwner {
        for (uint256 h = 0; h < N_HEADS; h++) {
            require(
                _componentTables[h].length == COMPONENT_TABLE_SIZE,
                "CrystalComponentVerifier: head not set"
            );
        }
        initialized = true;
        emit ComponentTablesInitialized(block.timestamp);
    }

    function fold(uint8 left, uint8 right, uint256 head)
        public
        view
        onlyInitialized
        returns (uint8 result)
    {
        require(head < N_HEADS, "CrystalComponentVerifier: invalid head");
        bytes storage table = _componentTables[head];

        for (uint256 k = 0; k < COMPONENTS; k++) {
            uint8 left2 = uint8((uint256(left) >> (2 * k)) & 3);
            uint8 right2 = uint8((uint256(right) >> (2 * k)) & 3);
            uint256 index = k * 16 + uint256(left2) * 4 + uint256(right2);
            uint8 component = uint8(table[index]) & 3;
            result = uint8(uint256(result) | (uint256(component) << (2 * k)));
        }
    }

    function foldAllHeads(uint8[N_HEADS] calldata left, uint8[N_HEADS] calldata right)
        external
        view
        onlyInitialized
        returns (uint8[N_HEADS] memory results)
    {
        for (uint256 h = 0; h < N_HEADS; h++) {
            results[h] = fold(left[h], right[h], h);
        }
    }

    function verifyTreeRoot(bytes calldata treeData, bytes32 claimedRoot)
        external
        view
        onlyInitialized
        returns (bool valid, bytes32 computedRoot)
    {
        uint256 offset = 0;
        uint8[N_HEADS] memory roots;
        (roots, offset) = _decodeAndFold(treeData, offset);
        require(offset == treeData.length, "CrystalComponentVerifier: trailing tree data");

        computedRoot = _packRoot(roots);
        valid = (computedRoot == claimedRoot);
    }

    function commitTree(bytes32 blockHash, uint256 treeIndex, bytes32 crystalRoot) external {
        require(
            treeRoots[blockHash][treeIndex] == bytes32(0),
            "CrystalComponentVerifier: tree already committed"
        );
        treeRoots[blockHash][treeIndex] = crystalRoot;
        emit TreeCommitted(blockHash, treeIndex, crystalRoot, msg.sender);
    }

    function commitAnchoredTree(
        bytes32 blockHash,
        uint256 treeIndex,
        bytes32 crystalRoot,
        bytes32 merkleRoot
    ) external {
        _commitAnchoredTree(
            blockHash, treeIndex, crystalRoot, merkleRoot, DEFAULT_CHALLENGE_WINDOW_SECONDS
        );
    }

    function commitAnchoredTreeWithWindow(
        bytes32 blockHash,
        uint256 treeIndex,
        bytes32 crystalRoot,
        bytes32 merkleRoot,
        uint64 challengeWindowSeconds
    ) external {
        _commitAnchoredTree(blockHash, treeIndex, crystalRoot, merkleRoot, challengeWindowSeconds);
    }

    function finalizeAnchoredTree(bytes32 blockHash, uint256 treeIndex) external {
        AnchoredTreeCommitment storage commitment = anchoredTreeCommitments[blockHash][treeIndex];
        require(
            commitment.status == AnchoredTreeStatus.Active,
            "CrystalComponentVerifier: anchored tree not active"
        );
        require(
            block.timestamp >= commitment.challengeDeadline,
            "CrystalComponentVerifier: challenge window open"
        );

        commitment.status = AnchoredTreeStatus.Finalized;
        emit AnchoredTreeFinalized(
            blockHash, treeIndex, commitment.crystalRoot, commitment.merkleRoot
        );
    }

    function _commitAnchoredTree(
        bytes32 blockHash,
        uint256 treeIndex,
        bytes32 crystalRoot,
        bytes32 merkleRoot,
        uint64 challengeWindowSeconds
    ) internal {
        require(crystalRoot != bytes32(0), "CrystalComponentVerifier: empty crystal root");
        require(merkleRoot != bytes32(0), "CrystalComponentVerifier: empty merkle root");
        require(challengeWindowSeconds > 0, "CrystalComponentVerifier: empty challenge window");
        require(
            block.timestamp <= type(uint64).max - challengeWindowSeconds,
            "CrystalComponentVerifier: challenge deadline overflow"
        );
        require(
            treeRoots[blockHash][treeIndex] == bytes32(0),
            "CrystalComponentVerifier: tree already committed"
        );
        require(
            anchoredTreeCommitments[blockHash][treeIndex].status == AnchoredTreeStatus.None,
            "CrystalComponentVerifier: anchored tree already committed"
        );

        uint64 challengeDeadline = uint64(block.timestamp + challengeWindowSeconds);
        treeRoots[blockHash][treeIndex] = crystalRoot;
        treeMerkleRoots[blockHash][treeIndex] = merkleRoot;
        anchoredTreeCommitments[blockHash][treeIndex] = AnchoredTreeCommitment({
            status: AnchoredTreeStatus.Active,
            crystalRoot: crystalRoot,
            merkleRoot: merkleRoot,
            sequencer: msg.sender,
            committedAt: uint64(block.timestamp),
            challengeDeadline: challengeDeadline
        });
        emit AnchoredTreeCommitted(blockHash, treeIndex, crystalRoot, merkleRoot, msg.sender);
        emit AnchoredTreeChallengeWindowOpened(blockHash, treeIndex, challengeDeadline);
    }

    function submitTreeConsistencyChallenge(
        bytes32 blockHash,
        uint256 treeIndex,
        bytes calldata treeData
    ) external onlyInitialized {
        bytes32 postedRoot = treeRoots[blockHash][treeIndex];
        require(postedRoot != bytes32(0), "CrystalComponentVerifier: tree not committed");
        require(!challenged[blockHash], "CrystalComponentVerifier: already challenged");

        uint256 offset = 0;
        uint8[N_HEADS] memory roots;
        (roots, offset) = _decodeAndFold(treeData, offset);
        require(offset == treeData.length, "CrystalComponentVerifier: trailing tree data");
        bytes32 computedRoot = _packRoot(roots);

        require(computedRoot != postedRoot, "CrystalComponentVerifier: no mismatch detected");

        challenged[blockHash] = true;
        _markAnchoredTreeInvalidated(blockHash, treeIndex, bytes32(0));
        emit ConsistencyChallengeSubmitted(blockHash, msg.sender, postedRoot, computedRoot);
    }

    function verifyCrystalPath(bytes calldata witnessData, bytes32 expectedRoot)
        external
        view
        onlyInitialized
        returns (bool valid, bytes32 computedRoot)
    {
        computedRoot = _decodeAndFoldPathWitness(witnessData);
        valid = (computedRoot == expectedRoot);
    }

    function verifyMerklePath(
        bytes32 targetHash,
        bytes calldata proofData,
        bytes32 expectedMerkleRoot
    ) external pure returns (bool valid, bytes32 computedMerkleRoot) {
        computedMerkleRoot = _decodeAndHashMerklePath(targetHash, proofData);
        valid = (computedMerkleRoot == expectedMerkleRoot);
    }

    function verifyLeafMerklePath(
        uint8 leafValue,
        bytes calldata proofData,
        bytes32 expectedMerkleRoot
    ) external pure returns (bool valid, bytes32 computedMerkleRoot) {
        bytes32 leafHash = sha256(bytes.concat(hex"00", bytes1(leafValue)));
        computedMerkleRoot = _decodeAndHashMerklePath(leafHash, proofData);
        valid = (computedMerkleRoot == expectedMerkleRoot);
    }

    function verifyLocalizedPath(
        bytes calldata crystalWitnessData,
        bytes32 expectedCrystalRoot,
        bytes32 targetMerkleHash,
        bytes calldata merkleProofData,
        bytes32 expectedMerkleRoot
    )
        external
        view
        onlyInitialized
        returns (
            bool crystalValid,
            bool merkleValid,
            bytes32 computedCrystalRoot,
            bytes32 computedMerkleRoot
        )
    {
        _requireSameLocalizedPath(crystalWitnessData, merkleProofData);
        computedCrystalRoot = _decodeAndFoldPathWitness(crystalWitnessData);
        computedMerkleRoot = _decodeAndHashMerklePath(targetMerkleHash, merkleProofData);
        crystalValid = (computedCrystalRoot == expectedCrystalRoot);
        merkleValid = (computedMerkleRoot == expectedMerkleRoot);
    }

    function verifyLocalizedPathBinding(
        bytes calldata crystalWitnessData,
        bytes calldata merkleProofData
    ) external pure returns (bool) {
        _requireSameLocalizedPath(crystalWitnessData, merkleProofData);
        return true;
    }

    function submitCrystalPathConsistencyChallenge(
        bytes32 blockHash,
        uint256 treeIndex,
        bytes calldata witnessData
    ) external onlyInitialized {
        bytes32 postedRoot = treeRoots[blockHash][treeIndex];
        require(postedRoot != bytes32(0), "CrystalComponentVerifier: tree not committed");
        require(!challenged[blockHash], "CrystalComponentVerifier: already challenged");

        bytes32 computedRoot = _decodeAndFoldPathWitness(witnessData);
        require(computedRoot != postedRoot, "CrystalComponentVerifier: no mismatch detected");

        challenged[blockHash] = true;
        _markAnchoredTreeInvalidated(blockHash, treeIndex, bytes32(0));
        emit ConsistencyChallengeSubmitted(blockHash, msg.sender, postedRoot, computedRoot);
    }

    function submitAnchoredLocalizedChallenge(
        bytes32 blockHash,
        uint256 treeIndex,
        bytes calldata crystalWitnessData,
        bytes32 targetMerkleHash,
        bytes calldata merkleProofData
    ) external onlyInitialized returns (bytes32 challengeId) {
        bytes32 postedCrystalRoot = treeRoots[blockHash][treeIndex];
        bytes32 postedMerkleRoot = treeMerkleRoots[blockHash][treeIndex];
        AnchoredTreeCommitment storage commitment = anchoredTreeCommitments[blockHash][treeIndex];
        require(postedCrystalRoot != bytes32(0), "CrystalComponentVerifier: tree not committed");
        require(
            postedMerkleRoot != bytes32(0), "CrystalComponentVerifier: merkle root not committed"
        );
        require(
            commitment.status == AnchoredTreeStatus.Active,
            "CrystalComponentVerifier: anchored tree not active"
        );
        require(
            block.timestamp < commitment.challengeDeadline,
            "CrystalComponentVerifier: challenge window closed"
        );

        _requireSameLocalizedPath(crystalWitnessData, merkleProofData);
        bytes32 computedCrystalRoot = _decodeAndFoldPathWitness(crystalWitnessData);
        bytes32 computedMerkleRoot = _decodeAndHashMerklePath(targetMerkleHash, merkleProofData);

        require(
            computedMerkleRoot == postedMerkleRoot,
            "CrystalComponentVerifier: merkle anchor mismatch"
        );
        require(
            computedCrystalRoot != postedCrystalRoot,
            "CrystalComponentVerifier: no mismatch detected"
        );

        challengeId = _recordPendingLocalizedChallenge(
            LocalizedChallengeRecord({
                blockHash: blockHash,
                treeIndex: treeIndex,
                challenger: msg.sender,
                postedCrystalRoot: postedCrystalRoot,
                postedMerkleRoot: postedMerkleRoot,
                computedCrystalRoot: computedCrystalRoot,
                computedMerkleRoot: computedMerkleRoot,
                targetMerkleHash: targetMerkleHash
            })
        );
    }

    function resolveAnchoredLocalizedChallenge(bytes32 challengeId) external {
        LocalizedChallenge storage challenge = localizedChallenges[challengeId];
        require(
            challenge.status == ChallengeStatus.PendingMismatch,
            "CrystalComponentVerifier: challenge not pending"
        );
        require(
            block.timestamp >= challenge.responseDeadline,
            "CrystalComponentVerifier: response window open"
        );

        challenge.status = ChallengeStatus.ResolvedMismatch;
        challenged[challenge.blockHash] = true;
        _markAnchoredTreeInvalidated(challenge.blockHash, challenge.treeIndex, challengeId);
        emit LocalizedChallengeResolved(
            challengeId,
            challenge.blockHash,
            challenge.treeIndex,
            challenge.challenger,
            challenge.postedCrystalRoot,
            challenge.postedMerkleRoot,
            challenge.computedCrystalRoot
        );
    }

    function computeLocalizedChallengeId(
        bytes32 blockHash,
        uint256 treeIndex,
        address challenger,
        bytes32 postedCrystalRoot,
        bytes32 postedMerkleRoot,
        bytes32 computedCrystalRoot,
        bytes32 targetMerkleHash
    ) external pure returns (bytes32) {
        return _localizedChallengeId(
            blockHash,
            treeIndex,
            challenger,
            postedCrystalRoot,
            postedMerkleRoot,
            computedCrystalRoot,
            targetMerkleHash
        );
    }

    function _decodeAndFold(bytes calldata data, uint256 offset)
        internal
        view
        returns (uint8[N_HEADS] memory roots, uint256 newOffset)
    {
        require(offset < data.length, "CrystalComponentVerifier: truncated tree");

        uint8 nodeType = uint8(data[offset]);
        offset++;

        if (nodeType == 0x00) {
            require(offset + N_HEADS <= data.length, "CrystalComponentVerifier: truncated leaf");
            for (uint256 h = 0; h < N_HEADS; h++) {
                roots[h] = uint8(data[offset]);
                offset++;
            }
            newOffset = offset;
        } else if (nodeType == 0x01) {
            uint8[N_HEADS] memory leftRoots;
            uint8[N_HEADS] memory rightRoots;

            (leftRoots, offset) = _decodeAndFold(data, offset);
            (rightRoots, offset) = _decodeAndFold(data, offset);

            for (uint256 h = 0; h < N_HEADS; h++) {
                roots[h] = _foldUnchecked(leftRoots[h], rightRoots[h], h);
            }
            newOffset = offset;
        } else {
            revert("CrystalComponentVerifier: invalid node type");
        }
    }

    function _decodeAndFoldPathWitness(bytes calldata data)
        internal
        view
        returns (bytes32 computedRoot)
    {
        uint256 offset = 0;
        uint8[N_HEADS] memory roots;
        (roots, offset) = _decodeRootVector(data, offset);

        require(offset < data.length, "CrystalComponentVerifier: truncated path witness");
        uint256 stepCount = uint8(data[offset]);
        offset++;
        require(stepCount <= 64, "CrystalComponentVerifier: path witness too deep");

        for (uint256 i = 0; i < stepCount; i++) {
            require(offset < data.length, "CrystalComponentVerifier: truncated path witness");
            uint8 side = uint8(data[offset]);
            offset++;
            require(side <= 1, "CrystalComponentVerifier: invalid path side");

            uint8[N_HEADS] memory sibling;
            (sibling, offset) = _decodeRootVector(data, offset);

            for (uint256 h = 0; h < N_HEADS; h++) {
                if (side == 0) {
                    roots[h] = _foldUnchecked(roots[h], sibling[h], h);
                } else {
                    roots[h] = _foldUnchecked(sibling[h], roots[h], h);
                }
            }
        }

        require(offset == data.length, "CrystalComponentVerifier: trailing path witness data");
        computedRoot = _packRoot(roots);
    }

    function _decodeAndHashMerklePath(bytes32 targetHash, bytes calldata data)
        internal
        pure
        returns (bytes32 computedMerkleRoot)
    {
        uint256 offset = 0;
        require(offset < data.length, "CrystalComponentVerifier: truncated merkle proof");
        uint256 stepCount = uint8(data[offset]);
        offset++;
        require(stepCount <= 64, "CrystalComponentVerifier: merkle proof too deep");

        bytes32 currentHash = targetHash;
        for (uint256 i = 0; i < stepCount; i++) {
            require(offset < data.length, "CrystalComponentVerifier: truncated merkle proof");
            uint8 side = uint8(data[offset]);
            offset++;
            require(side <= 1, "CrystalComponentVerifier: invalid merkle side");
            require(offset + 32 <= data.length, "CrystalComponentVerifier: truncated merkle proof");
            bytes32 siblingHash = bytes32(data[offset:offset + 32]);
            offset += 32;

            if (side == 0) {
                currentHash = sha256(bytes.concat(hex"01", currentHash, siblingHash));
            } else {
                currentHash = sha256(bytes.concat(hex"01", siblingHash, currentHash));
            }
        }

        require(offset == data.length, "CrystalComponentVerifier: trailing merkle proof data");
        computedMerkleRoot = currentHash;
    }

    function _requireSameLocalizedPath(
        bytes calldata crystalWitnessData,
        bytes calldata merkleProofData
    ) internal pure {
        require(
            crystalWitnessData.length >= N_HEADS + 1,
            "CrystalComponentVerifier: truncated path witness"
        );
        require(merkleProofData.length >= 1, "CrystalComponentVerifier: truncated merkle proof");

        uint256 crystalStepCount = uint8(crystalWitnessData[N_HEADS]);
        uint256 merkleStepCount = uint8(merkleProofData[0]);
        require(
            crystalStepCount == merkleStepCount,
            "CrystalComponentVerifier: localized path depth mismatch"
        );
        require(crystalStepCount <= 64, "CrystalComponentVerifier: path witness too deep");
        require(merkleStepCount <= 64, "CrystalComponentVerifier: merkle proof too deep");
        require(
            crystalWitnessData.length == N_HEADS + 1 + crystalStepCount * (1 + N_HEADS),
            "CrystalComponentVerifier: malformed path witness"
        );
        require(
            merkleProofData.length == 1 + merkleStepCount * 33,
            "CrystalComponentVerifier: malformed merkle proof"
        );

        for (uint256 i = 0; i < crystalStepCount; i++) {
            uint8 crystalSide = uint8(crystalWitnessData[N_HEADS + 1 + i * (1 + N_HEADS)]);
            uint8 merkleSide = uint8(merkleProofData[1 + i * 33]);
            require(crystalSide <= 1, "CrystalComponentVerifier: invalid path side");
            require(merkleSide <= 1, "CrystalComponentVerifier: invalid merkle side");
            require(crystalSide == merkleSide, "CrystalComponentVerifier: localized path mismatch");
        }
    }

    function _decodeRootVector(bytes calldata data, uint256 offset)
        internal
        pure
        returns (uint8[N_HEADS] memory roots, uint256 newOffset)
    {
        require(offset + N_HEADS <= data.length, "CrystalComponentVerifier: truncated root vector");
        for (uint256 h = 0; h < N_HEADS; h++) {
            roots[h] = uint8(data[offset]);
            offset++;
        }
        newOffset = offset;
    }

    function _localizedChallengeId(
        bytes32 blockHash,
        uint256 treeIndex,
        address challenger,
        bytes32 postedCrystalRoot,
        bytes32 postedMerkleRoot,
        bytes32 computedCrystalRoot,
        bytes32 targetMerkleHash
    ) internal pure returns (bytes32) {
        return keccak256(
            abi.encodePacked(
                blockHash,
                treeIndex,
                challenger,
                postedCrystalRoot,
                postedMerkleRoot,
                computedCrystalRoot,
                targetMerkleHash
            )
        );
    }

    function _recordPendingLocalizedChallenge(LocalizedChallengeRecord memory record)
        internal
        returns (bytes32 challengeId)
    {
        challengeId = _localizedChallengeId(
            record.blockHash,
            record.treeIndex,
            record.challenger,
            record.postedCrystalRoot,
            record.postedMerkleRoot,
            record.computedCrystalRoot,
            record.targetMerkleHash
        );
        require(
            localizedChallenges[challengeId].status == ChallengeStatus.None,
            "CrystalComponentVerifier: challenge already exists"
        );
        require(
            block.timestamp <= type(uint64).max - DEFAULT_CHALLENGE_RESPONSE_WINDOW_SECONDS,
            "CrystalComponentVerifier: response deadline overflow"
        );

        uint64 openedAt = uint64(block.timestamp);
        uint64 responseDeadline =
            uint64(block.timestamp + DEFAULT_CHALLENGE_RESPONSE_WINDOW_SECONDS);
        localizedChallenges[challengeId] = LocalizedChallenge({
            status: ChallengeStatus.PendingMismatch,
            blockHash: record.blockHash,
            treeIndex: record.treeIndex,
            challenger: record.challenger,
            postedCrystalRoot: record.postedCrystalRoot,
            postedMerkleRoot: record.postedMerkleRoot,
            computedCrystalRoot: record.computedCrystalRoot,
            computedMerkleRoot: record.computedMerkleRoot,
            targetMerkleHash: record.targetMerkleHash,
            openedAt: openedAt,
            responseDeadline: responseDeadline
        });
        _markAnchoredTreeChallenged(record.blockHash, record.treeIndex, challengeId);
        emit LocalizedChallengeSubmitted(
            challengeId,
            record.blockHash,
            record.treeIndex,
            record.challenger,
            record.postedCrystalRoot,
            record.postedMerkleRoot,
            record.computedCrystalRoot,
            record.targetMerkleHash,
            responseDeadline
        );
    }

    function _markAnchoredTreeInvalidated(bytes32 blockHash, uint256 treeIndex, bytes32 challengeId)
        internal
    {
        AnchoredTreeCommitment storage commitment = anchoredTreeCommitments[blockHash][treeIndex];
        if (
            commitment.status == AnchoredTreeStatus.Active
                || commitment.status == AnchoredTreeStatus.Challenged
        ) {
            commitment.status = AnchoredTreeStatus.Invalidated;
            emit AnchoredTreeInvalidated(blockHash, treeIndex, challengeId);
        }
    }

    function _markAnchoredTreeChallenged(bytes32 blockHash, uint256 treeIndex, bytes32 challengeId)
        internal
    {
        AnchoredTreeCommitment storage commitment = anchoredTreeCommitments[blockHash][treeIndex];
        if (commitment.status == AnchoredTreeStatus.Active) {
            commitment.status = AnchoredTreeStatus.Challenged;
            emit AnchoredTreeChallenged(blockHash, treeIndex, challengeId);
        }
    }

    function _foldUnchecked(uint8 left, uint8 right, uint256 head)
        internal
        view
        returns (uint8 result)
    {
        bytes storage table = _componentTables[head];
        for (uint256 k = 0; k < COMPONENTS; k++) {
            uint8 left2 = uint8((uint256(left) >> (2 * k)) & 3);
            uint8 right2 = uint8((uint256(right) >> (2 * k)) & 3);
            uint256 index = k * 16 + uint256(left2) * 4 + uint256(right2);
            uint8 component = uint8(table[index]) & 3;
            result = uint8(uint256(result) | (uint256(component) << (2 * k)));
        }
    }

    function _packRoot(uint8[N_HEADS] memory roots) internal pure returns (bytes32 packed) {
        for (uint256 h = 0; h < N_HEADS; h++) {
            packed |= bytes32(uint256(roots[h])) << (248 - h * 8);
        }
    }

    function componentDataLength(uint256 headIndex) external view returns (uint256) {
        require(headIndex < N_HEADS, "CrystalComponentVerifier: invalid head");
        return _componentTables[headIndex].length;
    }

    function isTreeCommitted(bytes32 blockHash, uint256 treeIndex) external view returns (bool) {
        return treeRoots[blockHash][treeIndex] != bytes32(0);
    }

    function getTreeRoot(bytes32 blockHash, uint256 treeIndex) external view returns (bytes32) {
        return treeRoots[blockHash][treeIndex];
    }

    function getTreeMerkleRoot(bytes32 blockHash, uint256 treeIndex)
        external
        view
        returns (bytes32)
    {
        return treeMerkleRoots[blockHash][treeIndex];
    }

    function getAnchoredTreeStatus(bytes32 blockHash, uint256 treeIndex)
        external
        view
        returns (AnchoredTreeStatus)
    {
        return anchoredTreeCommitments[blockHash][treeIndex].status;
    }

    function getAnchoredTreeChallengeDeadline(bytes32 blockHash, uint256 treeIndex)
        external
        view
        returns (uint64)
    {
        return anchoredTreeCommitments[blockHash][treeIndex].challengeDeadline;
    }

    function isChallenged(bytes32 blockHash) external view returns (bool) {
        return challenged[blockHash];
    }
}
