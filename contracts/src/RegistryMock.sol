// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title RegistryMock
 * @dev Simplified owner-only registry for IoT identity accumulator MVP
 * 
 * This contract stores the current accumulator state and provides owner-only
 * functions for device registration, revocation, and accumulator updates.
 * It's designed for MVP testing on Anvil - NOT for production use.
 */
contract RegistryMock {
    // Owner of the contract (authorized to make all updates)
    address public owner;
    
    // Current accumulator state (256-byte big-endian encoded)
    bytes public currentAccumulator;
    
    // Hash of the current accumulator for integrity checking
    bytes32 public storedHash;
    
    // Version counter for accumulator updates
    uint256 public version;
    
    // Events for logging operations
    event AccumulatorUpdated(
        bytes indexed newAccumulator,
        bytes32 indexed parentHash,
        bytes32 indexed operationId,
        uint256 version
    );
    
    event DeviceRegistered(
        bytes indexed deviceId,
        bytes indexed newAccumulator, 
        bytes32 indexed parentHash,
        bytes32 operationId,
        uint256 version
    );
    
    event DeviceRevoked(
        bytes indexed deviceId,
        bytes indexed newAccumulator,
        bytes32 indexed parentHash, 
        bytes32 operationId,
        uint256 version
    );
    
    event OwnershipTransferred(
        address indexed previousOwner,
        address indexed newOwner
    );
    
    modifier onlyOwner() {
        require(msg.sender == owner, "RegistryMock: caller is not the owner");
        _;
    }
    
    modifier validParentHash(bytes32 parentHash) {
        require(parentHash == storedHash, "RegistryMock: invalid parent hash");
        _;
    }
    
    constructor(bytes memory initialAccumulator) {
        require(initialAccumulator.length == 256, "RegistryMock: accumulator must be 256 bytes");
        
        owner = msg.sender;
        currentAccumulator = initialAccumulator;
        storedHash = keccak256(initialAccumulator);
        version = 1;
        
        emit AccumulatorUpdated(
            initialAccumulator,
            bytes32(0), // No parent for initial state
            keccak256(abi.encodePacked(block.timestamp, initialAccumulator, bytes32(0))),
            version
        );
    }
    
    /**
     * @dev Get current accumulator state
     * @return accumulator Current accumulator value (256 bytes)
     * @return hash Current accumulator hash  
     * @return ver Current version number
     */
    function getCurrentState() external view returns (
        bytes memory accumulator,
        bytes32 hash,
        uint256 ver
    ) {
        return (currentAccumulator, storedHash, version);
    }
    
    /**
     * @dev Update accumulator value (owner only)
     * @param newAccumulator New accumulator value (must be 256 bytes)
     * @param parentHash Hash of previous accumulator (must match storedHash)
     * @param operationId Unique identifier for this operation
     */
    function updateAccumulator(
        bytes calldata newAccumulator,
        bytes32 parentHash,
        bytes32 operationId
    ) external onlyOwner validParentHash(parentHash) {
        require(newAccumulator.length == 256, "RegistryMock: accumulator must be 256 bytes");
        require(operationId != bytes32(0), "RegistryMock: operationId cannot be zero");
        
        currentAccumulator = newAccumulator;
        storedHash = keccak256(newAccumulator);
        version++;
        
        emit AccumulatorUpdated(newAccumulator, parentHash, operationId, version);
    }
    
    /**
     * @dev Register a new device (owner only)
     * @param deviceId Device identifier (typically keccak256 of public key DER)
     * @param newAccumulator Updated accumulator after adding device
     * @param parentHash Hash of previous accumulator  
     * @param operationId Unique identifier for this operation
     */
    function registerDevice(
        bytes calldata deviceId,
        bytes calldata newAccumulator,
        bytes32 parentHash,
        bytes32 operationId
    ) external onlyOwner validParentHash(parentHash) {
        require(deviceId.length == 32, "RegistryMock: deviceId must be 32 bytes");
        require(newAccumulator.length == 256, "RegistryMock: accumulator must be 256 bytes");
        require(operationId != bytes32(0), "RegistryMock: operationId cannot be zero");
        
        currentAccumulator = newAccumulator;
        storedHash = keccak256(newAccumulator);
        version++;
        
        emit DeviceRegistered(deviceId, newAccumulator, parentHash, operationId, version);
    }
    
    /**
     * @dev Revoke a device (owner only)
     * @param deviceId Device identifier to revoke
     * @param newAccumulator Updated accumulator after removing device
     * @param parentHash Hash of previous accumulator
     * @param operationId Unique identifier for this operation  
     */
    function revokeDevice(
        bytes calldata deviceId,
        bytes calldata newAccumulator,
        bytes32 parentHash,
        bytes32 operationId
    ) external onlyOwner validParentHash(parentHash) {
        require(deviceId.length == 32, "RegistryMock: deviceId must be 32 bytes");
        require(newAccumulator.length == 256, "RegistryMock: accumulator must be 256 bytes");
        require(operationId != bytes32(0), "RegistryMock: operationId cannot be zero");
        
        currentAccumulator = newAccumulator;
        storedHash = keccak256(newAccumulator);
        version++;
        
        emit DeviceRevoked(deviceId, newAccumulator, parentHash, operationId, version);
    }
    
    /**
     * @dev Transfer ownership of the contract (owner only)
     * @param newOwner Address of the new owner
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "RegistryMock: new owner is the zero address");
        require(newOwner != owner, "RegistryMock: new owner is the current owner");
        
        address oldOwner = owner;
        owner = newOwner;
        
        emit OwnershipTransferred(oldOwner, newOwner);
    }
    
    /**
     * @dev Emergency function to pause the contract (owner only)
     * This is a placeholder for production safety - not used in MVP
     */
    function emergencyStop() external onlyOwner {
        // In a real implementation, this would pause all operations
        // For MVP, we just emit an event
        emit AccumulatorUpdated(
            currentAccumulator,
            storedHash, 
            keccak256(abi.encodePacked("EMERGENCY_STOP", block.timestamp)),
            version
        );
    }
}
