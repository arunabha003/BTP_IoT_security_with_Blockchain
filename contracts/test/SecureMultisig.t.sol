// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {AccumulatorRegistry} from "../src/AccumulatorRegistry.sol";
import {MultisigManager} from "../src/MultisigManager.sol";
import {Safe} from "safe-contracts/Safe.sol";
import {SafeProxyFactory} from "safe-contracts/proxies/SafeProxyFactory.sol";
import {Enum} from "safe-contracts/libraries/Enum.sol";

contract SecureMultisigTest is Test {
    AccumulatorRegistry registry;
    MultisigManager manager;
    Safe safe;
    SafeProxyFactory proxyFactory;
    
    // Test accounts
    uint256 owner1Key = 1;
    uint256 owner2Key = 2;
    uint256 owner3Key = 3;
    uint256 owner4Key = 4;
    uint256 owner5Key = 5;
    uint256 emergencyAdminKey = 999;
    
    address owner1 = vm.addr(owner1Key);
    address owner2 = vm.addr(owner2Key);
    address owner3 = vm.addr(owner3Key);
    address owner4 = vm.addr(owner4Key);
    address owner5 = vm.addr(owner5Key);
    address emergencyAdmin = vm.addr(emergencyAdminKey);
    
    address[] owners;
    
    // Events to test
    event SafeDeployed(address indexed safe, address[] owners, uint256 threshold);
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
    event OwnerAdditionQueued(bytes32 indexed operationHash, address indexed newOwner, uint256 executeAfter);
    event OwnerRemovalQueued(bytes32 indexed operationHash, address indexed owner, uint256 executeAfter);
    event ThresholdChangeQueued(bytes32 indexed operationHash, uint256 newThreshold, uint256 executeAfter);
    event OperationExecuted(bytes32 indexed operationHash, MultisigManager.OperationType opType);
    
    function setUp() public {
        // Setup owners array
        owners.push(owner1);
        owners.push(owner2);
        owners.push(owner3);
        owners.push(owner4);
        owners.push(owner5);
        
        // Deploy Safe infrastructure
        Safe safeSingleton = new Safe();
        proxyFactory = new SafeProxyFactory();
        
        // Deploy MultisigManager
        manager = new MultisigManager(
            payable(address(safeSingleton)),
            address(proxyFactory),
            emergencyAdmin
        );
        
        // Deploy Safe via manager (3-of-5)
        address safeAddr = manager.deploySafe(owners, 3);
        safe = Safe(payable(safeAddr));
        
        // Enable MultisigManager as a module on the Safe
        bytes memory enableModuleData = abi.encodeWithSignature(
            "enableModule(address)",
            address(manager)
        );

        bool moduleEnabled = executeSafeTransaction(safeAddr, enableModuleData);
        assertTrue(moduleEnabled, "Failed to enable MultisigManager as module");
        
        // Deploy AccumulatorRegistry
        bytes memory initialAccumulator = abi.encodePacked(bytes32(uint256(1)));
        registry = new AccumulatorRegistry(
            initialAccumulator,
            address(manager),
            safeAddr
        );
    }
    
    function testInitialState() public view {
        // Test registry state
        assertEq(address(registry.authorizedSafe()), address(safe));
        assertEq(address(registry.multisigManager()), address(manager));
        assertEq(registry.version(), 1);
        assertEq(registry.emergencyPaused(), false);
        
        // Test safe state
        assertEq(safe.getThreshold(), 3);
        assertEq(safe.getOwners().length, 5);
        
        // Test security info
        (
            address multisigManagerAddr,
            address authorizedSafeAddr,
            uint256 threshold,
            address[] memory safeOwners,
            bool paused,
            uint256 lastUpdate
        ) = registry.getSecurityInfo();
        
        assertEq(multisigManagerAddr, address(manager));
        assertEq(authorizedSafeAddr, address(safe));
        assertEq(threshold, 3);
        assertEq(safeOwners.length, 5);
        assertEq(paused, false);
        assertTrue(lastUpdate > 0);
    }
    
    function testOnlyMultisigCanCallRegistry() public {
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(42)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("test", block.timestamp));
        
        // Direct call should fail
        vm.expectRevert(AccumulatorRegistry.NotAuthorizedSafe.selector);
        registry.updateAccumulator(newAcc, currentHash, operationId);
        
        // Call from wrong address should fail
        vm.prank(owner1);
        vm.expectRevert(AccumulatorRegistry.NotAuthorizedSafe.selector);
        registry.updateAccumulator(newAcc, currentHash, operationId);
        
        // Call from unauthorized contract should fail
        vm.prank(address(manager));
        vm.expectRevert(AccumulatorRegistry.NotAuthorizedSafe.selector);
        registry.updateAccumulator(newAcc, currentHash, operationId);
    }
    
    function testMultisigUpdateAccumulator() public {
        // Advance block to avoid rate limiting
        vm.roll(block.number + 1);
        
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(42)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("update", block.timestamp));
        
        // Prepare transaction data
        bytes memory txData = abi.encodeWithSignature(
            "updateAccumulator(bytes,bytes32,bytes32)",
            newAcc, currentHash, operationId
        );
        
        // Execute via Safe multisig
        vm.expectEmit(true, true, true, true);
        emit AccumulatorUpdated(newAcc, keccak256(newAcc), 2, tx.origin, block.number);
        
        bool success = executeSafeTransaction(address(registry), txData);
        assertTrue(success);
        
        // Verify state
        assertEq(registry.currentAccumulator(), newAcc);
        assertEq(registry.version(), 2);
        assertEq(registry.storedHash(), keccak256(newAcc));
        assertTrue(registry.executedOperations(operationId));
    }
    
    function testMultisigDeviceOperations() public {
        // Advance block to avoid rate limiting
        vm.roll(block.number + 1);
        
        bytes memory deviceId = abi.encodePacked(bytes32(uint256(0xDEADBEEF)));
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(100)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("register", block.timestamp));
        
        // Register device
        bytes memory registerData = abi.encodeWithSignature(
            "registerDevice(bytes,bytes,bytes32,bytes32)",
            deviceId, newAcc, currentHash, operationId
        );
        
        vm.expectEmit(true, true, true, true);
        emit DeviceRegistered(deviceId, newAcc, keccak256(newAcc), 2, tx.origin);
        
        bool success = executeSafeTransaction(address(registry), registerData);
        assertTrue(success);
        
        // Verify device is registered
        assertEq(registry.deviceStatus(deviceId), 1);
        assertEq(registry.version(), 2);
        
        // Advance block for revocation to avoid rate limiting
        vm.roll(block.number + 1);
        
        // Revoke device
        bytes memory revokeAcc = abi.encodePacked(bytes32(uint256(200)));
        currentHash = registry.storedHash();
        bytes32 revokeOpId = keccak256(abi.encodePacked("revoke", block.timestamp));
        
        bytes memory revokeData = abi.encodeWithSignature(
            "revokeDevice(bytes,bytes,bytes32,bytes32)",
            deviceId, revokeAcc, currentHash, revokeOpId
        );
        
        vm.expectEmit(true, true, true, true);
        emit DeviceRevoked(deviceId, revokeAcc, keccak256(revokeAcc), 3, tx.origin);
        
        success = executeSafeTransaction(address(registry), revokeData);
        assertTrue(success);
        
        // Verify device is revoked
        assertEq(registry.deviceStatus(deviceId), 2);
        assertEq(registry.version(), 3);
    }
    
    function testReplayProtection() public {
        // Advance block to avoid rate limiting
        vm.roll(block.number + 1);
        
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(42)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("test", block.timestamp));
        
        bytes memory txData = abi.encodeWithSignature(
            "updateAccumulator(bytes,bytes32,bytes32)",
            newAcc, currentHash, operationId
        );
        
        // First execution should succeed
        bool success1 = executeSafeTransaction(address(registry), txData);
        assertTrue(success1);
        
        // Second execution with same operationId should fail
        bool success2 = executeSafeTransaction(address(registry), txData);
        assertFalse(success2);
    }
    
    function testInvalidParentHashProtection() public {
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(42)));
        bytes32 wrongHash = bytes32(uint256(999));
        bytes32 operationId = keccak256(abi.encodePacked("test", block.timestamp));
        
        bytes memory txData = abi.encodeWithSignature(
            "updateAccumulator(bytes,bytes32,bytes32)",
            newAcc, wrongHash, operationId
        );
        
        // Should fail due to invalid parent hash
        bool success = executeSafeTransaction(address(registry), txData);
        assertFalse(success);
    }
    
    function testEmergencyPause() public {
        // Only MultisigManager can pause
        vm.prank(emergencyAdmin);
        vm.expectRevert(AccumulatorRegistry.NotMultisigManager.selector);
        registry.toggleEmergencyPause();
        
        // Manager can pause via emergency admin
        vm.prank(emergencyAdmin);
        manager.toggleEmergencyPause();
        assertTrue(manager.emergencyPaused());
        
        // Registry operations should fail when paused
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(42)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("test", block.timestamp));
        
        bytes memory txData = abi.encodeWithSignature(
            "updateAccumulator(bytes,bytes32,bytes32)",
            newAcc, currentHash, operationId
        );
        
        bool success = executeSafeTransaction(address(registry), txData);
        assertFalse(success);
    }
    
    function testMultisigValidation() public {
        // Test that registry validates Safe configuration
        assertEq(safe.getThreshold(), 3);
        assertEq(safe.getOwners().length, 5);
        
        // Advance block to avoid rate limiting
        vm.roll(block.number + 1);
        
        // Registry should accept calls only from properly configured Safe
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(42)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("test", block.timestamp));
        
        bytes memory txData = abi.encodeWithSignature(
            "updateAccumulator(bytes,bytes32,bytes32)",
            newAcc, currentHash, operationId
        );
        
        bool success = executeSafeTransaction(address(registry), txData);
        assertTrue(success);
    }
    
    function testBatchOperations() public {
        // Advance block to avoid rate limiting
        vm.roll(block.number + 1);
        
        bytes[] memory deviceIds = new bytes[](3);
        deviceIds[0] = abi.encodePacked(bytes32(uint256(0x111)));
        deviceIds[1] = abi.encodePacked(bytes32(uint256(0x222)));
        deviceIds[2] = abi.encodePacked(bytes32(uint256(0x333)));
        
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(999)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("batch", block.timestamp));
        
        // Batch register
        bytes memory batchData = abi.encodeWithSignature(
            "batchRegisterDevices(bytes[],bytes,bytes32,bytes32)",
            deviceIds, newAcc, currentHash, operationId
        );
        
        bool success = executeSafeTransaction(address(registry), batchData);
        assertTrue(success);
        
        // Verify all devices are registered
        for (uint256 i = 0; i < deviceIds.length; i++) {
            assertEq(registry.deviceStatus(deviceIds[i]), 1);
        }
        assertEq(registry.version(), 2);
    }
    
    function testMultisigManagerTimelockedOperations() public {
        // Test queueing and executing owner addition
        address newOwner = vm.addr(100);
        uint256 newThreshold = 4;
        
        // Queue add owner operation
        bytes memory queueData = abi.encodeWithSignature(
            "queueAddOwner(address,uint256)",
            newOwner,
            newThreshold
        );
        
        // Calculate expected operation hash
        bytes memory params = abi.encode(newOwner, newThreshold);
        bytes32 expectedHash = keccak256(abi.encode(
            MultisigManager.OperationType.ADD_OWNER,
            params,
            block.chainid,
            address(manager),
            1 // This will be the first operation, so nonce = 1
        ));
        
        vm.expectEmit(true, true, false, true);
        emit OwnerAdditionQueued(expectedHash, newOwner, block.timestamp + 24 hours);
        
        bool success = executeSafeTransaction(address(manager), queueData);
        assertTrue(success, "Failed to queue add owner operation");
        
        // Verify operation nonce incremented
        assertEq(manager.opNonce(), 1);
        
        // Try to execute before timelock expires (should fail)
        bytes memory executeData = abi.encodeWithSignature(
            "executeOperation(bytes32)",
            expectedHash
        );
        
        success = executeSafeTransaction(address(manager), executeData);
        assertFalse(success, "Should not execute before timelock expires");
        
        // Fast forward time past timelock
        vm.warp(block.timestamp + 24 hours + 1);
        
        // Now execution should succeed
        vm.expectEmit(true, false, false, true);
        emit OperationExecuted(expectedHash, MultisigManager.OperationType.ADD_OWNER);
        
        success = executeSafeTransaction(address(manager), executeData);
        assertTrue(success, "Failed to execute add owner operation after timelock");
        
        // Verify the owner was added and threshold changed
        address[] memory updatedOwners = safe.getOwners();
        assertEq(updatedOwners.length, 6, "Owner count should be 6");
        assertEq(safe.getThreshold(), 4, "Threshold should be 4");
        
        // Verify new owner is in the list
        bool newOwnerFound = false;
        for (uint256 i = 0; i < updatedOwners.length; i++) {
            if (updatedOwners[i] == newOwner) {
                newOwnerFound = true;
                break;
            }
        }
        assertTrue(newOwnerFound, "New owner should be in owners list");
    }
    
    function testMultisigManagerChangeThreshold() public {
        // Test threshold change
        uint256 newThreshold = 4;
        
        // Queue threshold change
        bytes memory queueData = abi.encodeWithSignature(
            "queueChangeThreshold(uint256)",
            newThreshold
        );
        
        // Calculate expected operation hash
        bytes memory params = abi.encode(newThreshold);
        bytes32 expectedHash = keccak256(abi.encode(
            MultisigManager.OperationType.CHANGE_THRESHOLD,
            params,
            block.chainid,
            address(manager),
            1 // First operation
        ));
        
        vm.expectEmit(true, false, false, true);
        emit ThresholdChangeQueued(expectedHash, newThreshold, block.timestamp + 24 hours);
        
        bool success = executeSafeTransaction(address(manager), queueData);
        assertTrue(success, "Failed to queue threshold change");
        
        // Execute after timelock
        vm.warp(block.timestamp + 24 hours + 1);
        
        bytes memory executeData = abi.encodeWithSignature(
            "executeOperation(bytes32)",
            expectedHash
        );
        
        vm.expectEmit(true, false, false, true);
        emit OperationExecuted(expectedHash, MultisigManager.OperationType.CHANGE_THRESHOLD);
        
        success = executeSafeTransaction(address(manager), executeData);
        assertTrue(success, "Failed to execute threshold change");
        
        // Verify threshold changed
        assertEq(safe.getThreshold(), newThreshold, "Threshold should be updated");
    }
    
    function testMultisigManagerEmergencyControls() public {
        // Test emergency pause
        vm.prank(emergencyAdmin);
        manager.toggleEmergencyPause();
        assertTrue(manager.emergencyPaused(), "Should be paused");
        
        // Test that queuing operations fails when paused
        bytes memory queueData = abi.encodeWithSignature(
            "queueChangeThreshold(uint256)",
            4
        );
        
        // Should fail due to emergency pause (the helper catches reverts and returns false)
        bool success = executeSafeTransaction(address(manager), queueData);
        assertFalse(success, "Should fail when paused");
        
        // Test emergency operation cancellation
        vm.prank(emergencyAdmin);
        manager.toggleEmergencyPause(); // Unpause
        
        // Queue an operation
        bool success2 = executeSafeTransaction(address(manager), queueData);
        assertTrue(success2, "Should be able to queue when unpaused");
        
        // Calculate operation hash to cancel
        bytes memory params = abi.encode(uint256(4));
        bytes32 operationHash = keccak256(abi.encode(
            MultisigManager.OperationType.CHANGE_THRESHOLD,
            params,
            block.chainid,
            address(manager),
            1
        ));
        
        // Emergency admin can cancel
        vm.prank(emergencyAdmin);
        manager.cancelOperation(operationHash);
        
        // Verify operation was cancelled
        (bool exists,,,, ) = manager.getOperationStatus(operationHash);
        assertFalse(exists, "Operation should be cancelled");
    }
    
    function testMultisigManagerDomainSeparation() public {
        // Test that operation hashes include domain separation
        uint256 initialNonce = manager.opNonce();
        
        // Queue two identical operations
        bytes memory queueData = abi.encodeWithSignature(
            "queueChangeThreshold(uint256)",
            4
        );
        
        executeSafeTransaction(address(manager), queueData);
        uint256 firstNonce = manager.opNonce();
        
        executeSafeTransaction(address(manager), queueData);
        uint256 secondNonce = manager.opNonce();
        
        // Nonces should be different
        assertEq(firstNonce, initialNonce + 1, "First nonce should increment");
        assertEq(secondNonce, initialNonce + 2, "Second nonce should increment");
        
        // Operation hashes should be different due to nonce
        bytes memory params = abi.encode(uint256(4));
        
        bytes32 firstHash = keccak256(abi.encode(
            MultisigManager.OperationType.CHANGE_THRESHOLD,
            params,
            block.chainid,
            address(manager),
            firstNonce
        ));
        
        bytes32 secondHash = keccak256(abi.encode(
            MultisigManager.OperationType.CHANGE_THRESHOLD,
            params,
            block.chainid,
            address(manager),
            secondNonce
        ));
        
        assertTrue(firstHash != secondHash, "Operation hashes should be different");
    }
    
    // Helper function to execute Safe transactions with proper signature handling
    function executeSafeTransaction(
        address to,
        bytes memory data
    ) internal returns (bool success) {
        uint256 nonce = safe.nonce();
        
        // Build transaction hash for signing //EIP712 hash
        bytes32 txHash = safe.getTransactionHash(
            to,
            0,
            data,
            Enum.Operation.Call,
            0,
            0,
            0,
            address(0),
            address(0),
            nonce
        );
        
        // Generate signatures from 3 owners (meets threshold)
        // Sort signers by address for Safe compatibility
        address[] memory signers = new address[](3);
        signers[0] = owner1;
        signers[1] = owner2;
        signers[2] = owner3;
        
        // Sort signers by address
        for (uint256 i = 0; i < signers.length - 1; i++) {
            for (uint256 j = i + 1; j < signers.length; j++) {
                if (signers[i] > signers[j]) {
                    address temp = signers[i];
                    signers[i] = signers[j];
                    signers[j] = temp;
                }
            }
        }
        
        bytes memory signatures;
        for (uint256 i = 0; i < signers.length; i++) {
            uint256 key;
            if (signers[i] == owner1) key = owner1Key;
            else if (signers[i] == owner2) key = owner2Key;
            else if (signers[i] == owner3) key = owner3Key;
            else if (signers[i] == owner4) key = owner4Key;
            else if (signers[i] == owner5) key = owner5Key;
            
            (uint8 v, bytes32 r, bytes32 s) = vm.sign(key, txHash);
            signatures = abi.encodePacked(signatures, r, s, v);
        }
        
        // Execute transaction (catch reverts)
        try safe.execTransaction(
            to,
            0,
            data,
            Enum.Operation.Call,
            0,
            0,
            0,
            address(0),
            payable(address(0)),
            signatures
        ) returns (bool result) {
            return result;
        } catch {
            return false;
        }
    }
}
