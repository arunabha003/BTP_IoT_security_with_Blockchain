// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Safe} from "safe-contracts/Safe.sol";
import {SafeProxyFactory} from "safe-contracts/proxies/SafeProxyFactory.sol";
import {SafeProxy} from "safe-contracts/proxies/SafeProxy.sol";

/**
 * @title MultisigManager
 * @dev Advanced multisig management contract for AccumulatorRegistry
 * Provides flexible owner management, threshold changes, and security controls
 */
contract MultisigManager {
    // Immutable references
    Safe public immutable safeSingleton;
    SafeProxyFactory public immutable proxyFactory;
    
    // Current active Safe
    Safe public currentSafe;
    
    // Security parameters
    uint256 public constant MIN_THRESHOLD = 2;
    uint256 public constant MAX_OWNERS = 10;
    uint256 public constant MIN_OWNERS = 3;
    
    // Timelock for critical operations (24 hours)
    uint256 public constant TIMELOCK_DELAY = 24 hours;
    
    // Emergency controls
    address public emergencyAdmin;
    bool public emergencyPaused;
    
    // Pending operations for timelock
    struct PendingOperation {
        bytes32 operationHash;
        uint256 executeAfter;
        bool executed;
        OperationType opType;
    }
    
    enum OperationType {
        ADD_OWNER,
        REMOVE_OWNER,
        CHANGE_THRESHOLD,
        REPLACE_SAFE,
        EMERGENCY_PAUSE,
        EMERGENCY_UNPAUSE
    }
    
    mapping(bytes32 => PendingOperation) public pendingOperations;
    
    // Events
    event SafeDeployed(address indexed safe, address[] owners, uint256 threshold);
    event OwnerAdditionQueued(bytes32 indexed operationHash, address indexed newOwner, uint256 executeAfter);
    event OwnerRemovalQueued(bytes32 indexed operationHash, address indexed owner, uint256 executeAfter);
    event ThresholdChangeQueued(bytes32 indexed operationHash, uint256 newThreshold, uint256 executeAfter);
    event SafeReplacementQueued(bytes32 indexed operationHash, address indexed newSafe, uint256 executeAfter);
    event OperationExecuted(bytes32 indexed operationHash, OperationType opType);
    event OperationCancelled(bytes32 indexed operationHash);
    event EmergencyPauseToggled(bool paused);
    event EmergencyAdminChanged(address indexed oldAdmin, address indexed newAdmin);
    
    // Custom errors
    error InvalidThreshold();
    error InvalidOwnerCount();
    error OwnerAlreadyExists();
    error OwnerNotFound();
    error InvalidSafe();
    error OperationNotReady();
    error OperationAlreadyExecuted();
    error OperationNotFound();
    error NotAuthorized();
    error EmergencyPaused();
    error InvalidTimelock();
    
    modifier onlySafe() {
        if (msg.sender != address(currentSafe)) revert NotAuthorized();
        _;
    }
    
    modifier onlyEmergencyAdmin() {
        if (msg.sender != emergencyAdmin) revert NotAuthorized();
        _;
    }
    
    modifier notPaused() {
        if (emergencyPaused) revert EmergencyPaused();
        _;
    }
    
    constructor(
        address payable _safeSingleton,
        address _proxyFactory,
        address _emergencyAdmin
    ) {
        safeSingleton = Safe(_safeSingleton);
        proxyFactory = SafeProxyFactory(_proxyFactory);
        emergencyAdmin = _emergencyAdmin;
    }
    
    /**
     * @dev Deploy initial Safe with specified owners and threshold
     */
    function deploySafe(
        address[] memory owners,
        uint256 threshold
    ) external returns (address) {
        if (owners.length < MIN_OWNERS || owners.length > MAX_OWNERS) revert InvalidOwnerCount();
        if (threshold < MIN_THRESHOLD || threshold > owners.length) revert InvalidThreshold();
        
        // Validate owners
        for (uint256 i = 0; i < owners.length; i++) {
            if (owners[i] == address(0)) revert InvalidSafe();
            for (uint256 j = i + 1; j < owners.length; j++) {
                if (owners[i] == owners[j]) revert OwnerAlreadyExists();
            }
        }
        
        // Prepare Safe initialization
        bytes memory initializer = abi.encodeCall(
            Safe.setup,
            (
                owners,
                threshold,
                address(0),
                "",
                address(0),
                address(0),
                0,
                payable(address(0))
            )
        );
        
        // Deploy Safe proxy
        SafeProxy proxy = proxyFactory.createProxyWithNonce(
            address(safeSingleton),
            initializer,
            uint256(keccak256(abi.encodePacked(block.timestamp, owners, threshold)))
        );
        
        currentSafe = Safe(payable(address(proxy)));
        
        emit SafeDeployed(address(currentSafe), owners, threshold);
        return address(currentSafe);
    }
    
    /**
     * @dev Queue addition of new owner (requires timelock)
     */
    function queueAddOwner(address newOwner, uint256 newThreshold) external onlySafe notPaused {
        address[] memory currentOwners = currentSafe.getOwners();
        if (currentOwners.length >= MAX_OWNERS) revert InvalidOwnerCount();
        if (newThreshold < MIN_THRESHOLD || newThreshold > currentOwners.length + 1) revert InvalidThreshold();
        
        // Check if owner already exists
        for (uint256 i = 0; i < currentOwners.length; i++) {
            if (currentOwners[i] == newOwner) revert OwnerAlreadyExists();
        }
        
        bytes32 operationHash = keccak256(abi.encodePacked(
            "ADD_OWNER",
            newOwner,
            newThreshold,
            block.timestamp
        ));
        
        uint256 executeAfter = block.timestamp + TIMELOCK_DELAY;
        pendingOperations[operationHash] = PendingOperation({
            operationHash: operationHash,
            executeAfter: executeAfter,
            executed: false,
            opType: OperationType.ADD_OWNER
        });
        
        emit OwnerAdditionQueued(operationHash, newOwner, executeAfter);
    }
    
    /**
     * @dev Queue removal of owner (requires timelock)
     */
    function queueRemoveOwner(address ownerToRemove, uint256 newThreshold) external onlySafe notPaused {
        address[] memory currentOwners = currentSafe.getOwners();
        if (currentOwners.length <= MIN_OWNERS) revert InvalidOwnerCount();
        if (newThreshold < MIN_THRESHOLD || newThreshold >= currentOwners.length) revert InvalidThreshold();
        
        // Check if owner exists
        bool ownerFound = false;
        for (uint256 i = 0; i < currentOwners.length; i++) {
            if (currentOwners[i] == ownerToRemove) {
                ownerFound = true;
                break;
            }
        }
        if (!ownerFound) revert OwnerNotFound();
        
        bytes32 operationHash = keccak256(abi.encodePacked(
            "REMOVE_OWNER",
            ownerToRemove,
            newThreshold,
            block.timestamp
        ));
        
        uint256 executeAfter = block.timestamp + TIMELOCK_DELAY;
        pendingOperations[operationHash] = PendingOperation({
            operationHash: operationHash,
            executeAfter: executeAfter,
            executed: false,
            opType: OperationType.REMOVE_OWNER
        });
        
        emit OwnerRemovalQueued(operationHash, ownerToRemove, executeAfter);
    }
    
    /**
     * @dev Queue threshold change (requires timelock)
     */
    function queueChangeThreshold(uint256 newThreshold) external onlySafe notPaused {
        uint256 ownerCount = currentSafe.getOwners().length;
        if (newThreshold < MIN_THRESHOLD || newThreshold > ownerCount) revert InvalidThreshold();
        
        bytes32 operationHash = keccak256(abi.encodePacked(
            "CHANGE_THRESHOLD",
            newThreshold,
            block.timestamp
        ));
        
        uint256 executeAfter = block.timestamp + TIMELOCK_DELAY;
        pendingOperations[operationHash] = PendingOperation({
            operationHash: operationHash,
            executeAfter: executeAfter,
            executed: false,
            opType: OperationType.CHANGE_THRESHOLD
        });
        
        emit ThresholdChangeQueued(operationHash, newThreshold, executeAfter);
    }
    
    /**
     * @dev Execute a pending operation after timelock
     */
    function executeOperation(
        bytes32 operationHash,
        bytes memory operationData
    ) external onlySafe notPaused {
        PendingOperation storage op = pendingOperations[operationHash];
        if (op.operationHash == bytes32(0)) revert OperationNotFound();
        if (block.timestamp < op.executeAfter) revert OperationNotReady();
        if (op.executed) revert OperationAlreadyExecuted();
        
        op.executed = true;
        
        if (op.opType == OperationType.ADD_OWNER) {
            (address newOwner, uint256 newThreshold) = abi.decode(operationData, (address, uint256));
            _executeAddOwner(newOwner, newThreshold);
        } else if (op.opType == OperationType.REMOVE_OWNER) {
            (address ownerToRemove, uint256 newThreshold) = abi.decode(operationData, (address, uint256));
            _executeRemoveOwner(ownerToRemove, newThreshold);
        } else if (op.opType == OperationType.CHANGE_THRESHOLD) {
            uint256 newThreshold = abi.decode(operationData, (uint256));
            _executeChangeThreshold(newThreshold);
        }
        
        emit OperationExecuted(operationHash, op.opType);
    }
    
    /**
     * @dev Cancel a pending operation (emergency only)
     */
    function cancelOperation(bytes32 operationHash) external onlyEmergencyAdmin {
        PendingOperation storage op = pendingOperations[operationHash];
        if (op.operationHash == bytes32(0)) revert OperationNotFound();
        if (op.executed) revert OperationAlreadyExecuted();
        
        delete pendingOperations[operationHash];
        emit OperationCancelled(operationHash);
    }
    
    /**
     * @dev Emergency pause/unpause
     */
    function toggleEmergencyPause() external onlyEmergencyAdmin {
        emergencyPaused = !emergencyPaused;
        emit EmergencyPauseToggled(emergencyPaused);
    }
    
    /**
     * @dev Change emergency admin
     */
    function changeEmergencyAdmin(address newAdmin) external onlyEmergencyAdmin {
        address oldAdmin = emergencyAdmin;
        emergencyAdmin = newAdmin;
        emit EmergencyAdminChanged(oldAdmin, newAdmin);
    }
    
    // Internal execution functions
    function _executeAddOwner(address newOwner, uint256 /* newThreshold */) internal {
        // This would call Safe's addOwnerWithThreshold
        // Implementation depends on specific Safe version
        // For now, we emit the event - actual implementation would interact with Safe
        emit OperationExecuted(keccak256(abi.encodePacked("ADD_OWNER", newOwner)), OperationType.ADD_OWNER);
    }
    
    function _executeRemoveOwner(address ownerToRemove, uint256 /* newThreshold */) internal {
        // This would call Safe's removeOwner and changeThreshold
        emit OperationExecuted(keccak256(abi.encodePacked("REMOVE_OWNER", ownerToRemove)), OperationType.REMOVE_OWNER);
    }
    
    function _executeChangeThreshold(uint256 newThreshold) internal {
        // This would call Safe's changeThreshold
        emit OperationExecuted(keccak256(abi.encodePacked("CHANGE_THRESHOLD", newThreshold)), OperationType.CHANGE_THRESHOLD);
    }
    
    // View functions
    function getCurrentOwners() external view returns (address[] memory) {
        return currentSafe.getOwners();
    }
    
    function getCurrentThreshold() external view returns (uint256) {
        return currentSafe.getThreshold();
    }
    
    function isOperationPending(bytes32 operationHash) external view returns (bool) {
        PendingOperation storage op = pendingOperations[operationHash];
        return op.operationHash != bytes32(0) && !op.executed && block.timestamp >= op.executeAfter;
    }
    
    function getOperationStatus(bytes32 operationHash) external view returns (
        bool exists,
        bool executed,
        bool ready,
        uint256 executeAfter,
        OperationType opType
    ) {
        PendingOperation storage op = pendingOperations[operationHash];
        exists = op.operationHash != bytes32(0);
        executed = op.executed;
        ready = block.timestamp >= op.executeAfter;
        executeAfter = op.executeAfter;
        opType = op.opType;
    }
}
