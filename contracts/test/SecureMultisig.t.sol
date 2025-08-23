// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {AccumulatorRegistry} from "src/AccumulatorRegistry.sol";
import {MultisigManager} from "src/MultisigManager.sol";
import {Safe} from "safe-contracts/Safe.sol";
import {SafeProxyFactory} from "safe-contracts/proxies/SafeProxyFactory.sol";
// SafeProxy import removed as unused in tests
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
        
        // Deploy AccumulatorRegistry
        bytes memory initialAccumulator = abi.encodePacked(bytes32(uint256(1)));
        registry = new AccumulatorRegistry(
            initialAccumulator,
            address(manager),
            safeAddr
        );
    }
    
    function testInitialState() public {
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
    
    // Helper function to execute Safe transactions
    function executeSafeTransaction(
        address to,
        bytes memory data
    ) internal returns (bool success) {
        uint256 nonce = safe.nonce();
        
        // Build transaction hash for signing
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
        // Sort signatures by signer address
        address[] memory signers = new address[](3);
        signers[0] = owner1;
        signers[1] = owner2;
        signers[2] = owner3;
        
        // Sort signers
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
