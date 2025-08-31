// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Safe} from "safe-contracts/Safe.sol";
import {MultisigManager} from "./MultisigManager.sol";

/**
 * @title AccumulatorRegistry
 * @dev Secure RSA accumulator registry that ONLY accepts calls from authorized multisig
 * Integrates with MultisigManager for advanced multisig operations
 */
contract AccumulatorRegistry {
    // Multisig management
    MultisigManager public immutable multisigManager;
    Safe public authorizedSafe;
    
    // Core accumulator state
    bytes public currentAccumulator;
    bytes32 public storedHash;
    uint256 public version;
    
    // Security controls
    bool public emergencyPaused;
    uint256 public lastUpdateBlock;
    uint256 public constant MIN_BLOCK_DELAY = 1; // Minimum blocks between updates
    
    // Device status mapping by hashed id
    // 0 = None, 1 = Active, 2 = Revoked
    mapping(bytes32 => uint8) private _deviceStatus;
    
    // Operation tracking for audit
    mapping(bytes32 => bool) public executedOperations;
    
    // Events with enhanced security information
    event SafeAuthorized(address indexed safe, address indexed multisigManager);
    event AccumulatorUpdated(
        bytes newAccumulator, 
        bytes32 indexed newHash, 
        uint256 indexed newVersion,
        address indexed executor,
        uint256 blockNumber
    );
    event DeviceRegistered(
        bytes deviceId, 
        bytes newAccumulator, 
        bytes32 indexed newHash, 
        uint256 indexed newVersion,
        address indexed executor
    );
    event DeviceRevoked(
        bytes deviceId, 
        bytes newAccumulator, 
        bytes32 indexed newHash, 
        uint256 indexed newVersion,
        address indexed executor
    );
    event EmergencyPauseToggled(bool paused, address indexed admin);
    event SafeChanged(address indexed oldSafe, address indexed newSafe);
    
    // Enhanced custom errors
    error NotAuthorizedSafe();
    error NotMultisigManager();
    error InvalidParentHash();
    error DeviceAlreadyActive();
    error DeviceAlreadyRevoked();
    error DeviceNotActive();
    error EmergencyPaused();
    error InvalidSafe();
    error OperationAlreadyExecuted();
    error UpdateTooFrequent();
    error InvalidMultisigThreshold();
    error InvalidMultisigOwnerCount();
    
    // Security modifiers
    modifier onlyAuthorizedSafe() {
        if (msg.sender != address(authorizedSafe)) revert NotAuthorizedSafe();
        _;
    }
    
    modifier onlyMultisigManager() {
        if (msg.sender != address(multisigManager)) revert NotMultisigManager();
        _;
    }
    
    modifier notPaused() {
        if (emergencyPaused) revert EmergencyPaused();
        _;
    }
    
    modifier validMultisigState() {
        // Ensure the Safe has proper configuration
        uint256 threshold = authorizedSafe.getThreshold();
        uint256 ownerCount = authorizedSafe.getOwners().length;
        
        if (threshold < 2) revert InvalidMultisigThreshold();
        if (ownerCount < 3 || ownerCount > 10) revert InvalidMultisigOwnerCount();
        if (threshold > ownerCount) revert InvalidMultisigThreshold();
        _;
    }
    
    modifier rateLimited() {
        if (block.number < lastUpdateBlock + MIN_BLOCK_DELAY) revert UpdateTooFrequent();
        _;
    }
    
    constructor(
        bytes memory initialAccumulator,
        address _multisigManager,
        address _authorizedSafe
    ) {
        if (_multisigManager == address(0) || _authorizedSafe == address(0)) revert InvalidSafe();
        
        multisigManager = MultisigManager(_multisigManager);
        authorizedSafe = Safe(payable(_authorizedSafe));
        
        // Validate initial Safe configuration
        uint256 threshold = authorizedSafe.getThreshold();
        uint256 ownerCount = authorizedSafe.getOwners().length;
        if (threshold < 2) revert InvalidMultisigThreshold();
        if (ownerCount < 3) revert InvalidMultisigOwnerCount();
        
        currentAccumulator = initialAccumulator;
        storedHash = keccak256(initialAccumulator);
        version = 1;
        lastUpdateBlock = block.number;
        
        emit SafeAuthorized(_authorizedSafe, _multisigManager);
        emit AccumulatorUpdated(initialAccumulator, storedHash, version, address(0), block.number);
    }
    
    /**
     * @dev Change authorized Safe (only MultisigManager can do this)
     */
    function changeAuthorizedSafe(address newSafe) external onlyMultisigManager {
        if (newSafe == address(0)) revert InvalidSafe();
        
        address oldSafe = address(authorizedSafe);
        authorizedSafe = Safe(payable(newSafe));
        
        // Validate new Safe configuration
        uint256 threshold = authorizedSafe.getThreshold();
        uint256 ownerCount = authorizedSafe.getOwners().length;
        if (threshold < 2) revert InvalidMultisigThreshold();
        if (ownerCount < 3) revert InvalidMultisigOwnerCount();
        
        emit SafeChanged(oldSafe, newSafe);
    }
    
    /**
     * @dev Emergency pause (only MultisigManager can do this)
     */
    function toggleEmergencyPause() external onlyMultisigManager {
        emergencyPaused = !emergencyPaused;
        emit EmergencyPauseToggled(emergencyPaused, msg.sender);
    }

    /**
     * @dev Update accumulator with enhanced security checks (MULTISIG ONLY)
     */
    
    function updateAccumulator(
        bytes calldata newAccumulator, 
        bytes32 parentHash,
        bytes32 operationId
    ) external 
        onlyAuthorizedSafe 
        notPaused 
        validMultisigState 
        rateLimited 
    {
        if (parentHash != storedHash) revert InvalidParentHash();
        if (executedOperations[operationId]) revert OperationAlreadyExecuted();
        
        executedOperations[operationId] = true;
        currentAccumulator = newAccumulator;
        storedHash = keccak256(newAccumulator);
        version++;
        lastUpdateBlock = block.number;
        
        emit AccumulatorUpdated(newAccumulator, storedHash, version, tx.origin, block.number);
    }

    /**
     * @dev Register device with enhanced security (MULTISIG ONLY)
     */
    function registerDevice(
        bytes calldata deviceId, 
        bytes calldata newAccumulator,
        bytes32 parentHash,
        bytes32 operationId
    ) external 
        onlyAuthorizedSafe 
        notPaused 
        validMultisigState 
        rateLimited 
    {
        if (parentHash != storedHash) revert InvalidParentHash();
        if (executedOperations[operationId]) revert OperationAlreadyExecuted();
        
        bytes32 key = keccak256(deviceId);
        uint8 st = _deviceStatus[key];
        if (st == 1) revert DeviceAlreadyActive();
        if (st == 2) revert DeviceAlreadyRevoked();
        
        executedOperations[operationId] = true;
        _deviceStatus[key] = 1; // Active
        currentAccumulator = newAccumulator;
        storedHash = keccak256(newAccumulator);
        version++;
        lastUpdateBlock = block.number;
        
        emit DeviceRegistered(deviceId, newAccumulator, storedHash, version, tx.origin);
        emit AccumulatorUpdated(newAccumulator, storedHash, version, tx.origin, block.number);
    }

    /**
     * @dev Revoke device with enhanced security (MULTISIG ONLY)
     */
    function revokeDevice(
        bytes calldata deviceId, 
        bytes calldata newAccumulator,
        bytes32 parentHash,
        bytes32 operationId
    ) external 
        onlyAuthorizedSafe 
        notPaused 
        validMultisigState 
        rateLimited 
    {
        if (parentHash != storedHash) revert InvalidParentHash();
        if (executedOperations[operationId]) revert OperationAlreadyExecuted();
        
        bytes32 key = keccak256(deviceId);
        if (_deviceStatus[key] != 1) revert DeviceNotActive();
        
        executedOperations[operationId] = true;
        _deviceStatus[key] = 2; // Revoked
        currentAccumulator = newAccumulator;
        storedHash = keccak256(newAccumulator);
        version++;
        lastUpdateBlock = block.number;
        
        emit DeviceRevoked(deviceId, newAccumulator, storedHash, version, tx.origin);
        emit AccumulatorUpdated(newAccumulator, storedHash, version, tx.origin, block.number);
    }

    /**
     * @dev Batch register devices with enhanced security (MULTISIG ONLY)
     */
    function batchRegisterDevices(
        bytes[] calldata deviceIds,
        bytes calldata newAccumulator,
        bytes32 parentHash,
        bytes32 operationId
    ) external 
        onlyAuthorizedSafe 
        notPaused 
        validMultisigState 
        rateLimited 
    {
        if (parentHash != storedHash) revert InvalidParentHash();
        if (executedOperations[operationId]) revert OperationAlreadyExecuted();
        if (deviceIds.length == 0 || deviceIds.length > 50) revert InvalidMultisigOwnerCount(); // Reuse error for batch limit
        
        executedOperations[operationId] = true;
        
        for (uint256 i = 0; i < deviceIds.length; i++) {
            bytes32 key = keccak256(deviceIds[i]);
            uint8 st = _deviceStatus[key];
            if (st == 1) revert DeviceAlreadyActive();
            if (st == 2) revert DeviceAlreadyRevoked();
            _deviceStatus[key] = 1;
            emit DeviceRegistered(deviceIds[i], newAccumulator, keccak256(newAccumulator), version + 1, tx.origin);
        }
        
        currentAccumulator = newAccumulator;
        storedHash = keccak256(newAccumulator);
        version++;
        lastUpdateBlock = block.number;
        
        emit AccumulatorUpdated(newAccumulator, storedHash, version, tx.origin, block.number);
    }

    /**
     * @dev Batch revoke devices with enhanced security (MULTISIG ONLY)
     */
    function batchRevokeDevices(
        bytes[] calldata deviceIds,
        bytes calldata newAccumulator,
        bytes32 parentHash,
        bytes32 operationId
    ) external 
        onlyAuthorizedSafe 
        notPaused 
        validMultisigState 
        rateLimited 
    {
        if (parentHash != storedHash) revert InvalidParentHash();
        if (executedOperations[operationId]) revert OperationAlreadyExecuted();
        if (deviceIds.length == 0 || deviceIds.length > 50) revert InvalidMultisigOwnerCount(); // Reuse error for batch limit
        
        executedOperations[operationId] = true;
        
        for (uint256 i = 0; i < deviceIds.length; i++) {
            bytes32 key = keccak256(deviceIds[i]);
            if (_deviceStatus[key] != 1) revert DeviceNotActive();
            _deviceStatus[key] = 2;
            emit DeviceRevoked(deviceIds[i], newAccumulator, keccak256(newAccumulator), version + 1, tx.origin);
        }
        
        currentAccumulator = newAccumulator;
        storedHash = keccak256(newAccumulator);
        version++;
        lastUpdateBlock = block.number;
        
        emit AccumulatorUpdated(newAccumulator, storedHash, version, tx.origin, block.number);
    }

    // View helpers with enhanced security information
    function deviceStatus(bytes calldata deviceId) external view returns (uint8) {
        return _deviceStatus[keccak256(deviceId)];
    }

    function getCurrentState() external view returns (
        bytes memory accumulator, 
        bytes32 hash, 
        uint256 ver,
        address currentSafe,
        uint256 safeThreshold,
        uint256 safeOwnerCount,
        bool paused
    ) {
        return (
            currentAccumulator, 
            storedHash, 
            version,
            address(authorizedSafe),
            authorizedSafe.getThreshold(),
            authorizedSafe.getOwners().length,
            emergencyPaused
        );
    }
    
    function getSecurityInfo() external view returns (
        address multisigManagerAddr,
        address authorizedSafeAddr,
        uint256 threshold,
        address[] memory owners,
        bool paused,
        uint256 lastUpdate
    ) {
        return (
            address(multisigManager),
            address(authorizedSafe),
            authorizedSafe.getThreshold(),
            authorizedSafe.getOwners(),
            emergencyPaused,
            lastUpdateBlock
        );
    }
}

