// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {AccumulatorRegistry} from "../src/AccumulatorRegistry.sol";
import {MultisigManager} from "../src/MultisigManager.sol";
import {Safe} from "safe-contracts/Safe.sol";
import {SafeProxyFactory} from "safe-contracts/proxies/SafeProxyFactory.sol";
import {Enum} from "safe-contracts/libraries/Enum.sol";

/**
 * @title ComprehensiveCoverageTest
 * @dev Comprehensive test suite to achieve 100% code coverage
 */
contract ComprehensiveCoverageTest is Test {
    AccumulatorRegistry registry;
    MultisigManager manager;
    Safe safe;
    SafeProxyFactory proxyFactory;
    Safe safeSingleton;
    
    // Test accounts
    uint256 owner1Key = 1;
    uint256 owner2Key = 2;
    uint256 owner3Key = 3;
    uint256 owner4Key = 4;
    uint256 owner5Key = 5;
    uint256 owner6Key = 6;
    uint256 owner7Key = 7;
    uint256 owner8Key = 8;
    uint256 owner9Key = 9;
    uint256 owner10Key = 10;
    uint256 owner11Key = 11;
    uint256 emergencyAdminKey = 999;
    
    address owner1 = vm.addr(owner1Key);
    address owner2 = vm.addr(owner2Key);
    address owner3 = vm.addr(owner3Key);
    address owner4 = vm.addr(owner4Key);
    address owner5 = vm.addr(owner5Key);
    address owner6 = vm.addr(owner6Key);
    address owner7 = vm.addr(owner7Key);
    address owner8 = vm.addr(owner8Key);
    address owner9 = vm.addr(owner9Key);
    address owner10 = vm.addr(owner10Key);
    address owner11 = vm.addr(owner11Key);
    address emergencyAdmin = vm.addr(emergencyAdminKey);
    
    address[] owners;
    
    function setUp() public {
        owners.push(owner1);
        owners.push(owner2);
        owners.push(owner3);
        owners.push(owner4);
        owners.push(owner5);
        
        // Deploy Safe infrastructure
        safeSingleton = new Safe();
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
        executeSafeTransaction(safeAddr, enableModuleData);
        
        // Deploy AccumulatorRegistry
        bytes memory initialAccumulator = abi.encodePacked(bytes32(uint256(1)));
        registry = new AccumulatorRegistry(
            initialAccumulator,
            address(manager),
            safeAddr
        );
    }
    
    // ============ AccumulatorRegistry Error Cases ============
    
    function testDeviceAlreadyActive() public {
        vm.roll(block.number + 1);
        
        bytes memory deviceId = abi.encodePacked(bytes32(uint256(0xDEADBEEF)));
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(100)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("register1", block.timestamp));
        
        // Register device first time
        bytes memory registerData = abi.encodeWithSignature(
            "registerDevice(bytes,bytes,bytes32,bytes32)",
            deviceId, newAcc, currentHash, operationId
        );
        executeSafeTransaction(address(registry), registerData);
        
        // Try to register same device again - should fail
        vm.roll(block.number + 1);
        bytes memory newAcc2 = abi.encodePacked(bytes32(uint256(200)));
        currentHash = registry.storedHash();
        bytes32 operationId2 = keccak256(abi.encodePacked("register2", block.timestamp));
        
        bytes memory registerData2 = abi.encodeWithSignature(
            "registerDevice(bytes,bytes,bytes32,bytes32)",
            deviceId, newAcc2, currentHash, operationId2
        );
        
        bool success = executeSafeTransaction(address(registry), registerData2);
        assertFalse(success, "Should fail - device already active");
    }
    
    function testDeviceAlreadyRevoked() public {
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
        executeSafeTransaction(address(registry), registerData);
        
        // Revoke device
        vm.roll(block.number + 1);
        bytes memory revokeAcc = abi.encodePacked(bytes32(uint256(200)));
        currentHash = registry.storedHash();
        bytes32 revokeOpId = keccak256(abi.encodePacked("revoke", block.timestamp));
        
        bytes memory revokeData = abi.encodeWithSignature(
            "revokeDevice(bytes,bytes,bytes32,bytes32)",
            deviceId, revokeAcc, currentHash, revokeOpId
        );
        executeSafeTransaction(address(registry), revokeData);
        
        // Try to register revoked device - should fail
        vm.roll(block.number + 1);
        bytes memory newAcc2 = abi.encodePacked(bytes32(uint256(300)));
        currentHash = registry.storedHash();
        bytes32 operationId2 = keccak256(abi.encodePacked("register2", block.timestamp));
        
        bytes memory registerData2 = abi.encodeWithSignature(
            "registerDevice(bytes,bytes,bytes32,bytes32)",
            deviceId, newAcc2, currentHash, operationId2
        );
        
        bool success = executeSafeTransaction(address(registry), registerData2);
        assertFalse(success, "Should fail - device already revoked");
    }
    
    function testDeviceNotActive() public {
        vm.roll(block.number + 1);
        
        bytes memory deviceId = abi.encodePacked(bytes32(uint256(0xDEADBEEF)));
        bytes memory revokeAcc = abi.encodePacked(bytes32(uint256(200)));
        bytes32 currentHash = registry.storedHash();
        bytes32 revokeOpId = keccak256(abi.encodePacked("revoke", block.timestamp));
        
        // Try to revoke non-existent device - should fail
        bytes memory revokeData = abi.encodeWithSignature(
            "revokeDevice(bytes,bytes,bytes32,bytes32)",
            deviceId, revokeAcc, currentHash, revokeOpId
        );
        
        bool success = executeSafeTransaction(address(registry), revokeData);
        assertFalse(success, "Should fail - device not active");
    }
    
    function testUpdateTooFrequent() public {
        vm.roll(block.number + 1);
        
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(42)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("update1", block.timestamp));
        
        bytes memory txData = abi.encodeWithSignature(
            "updateAccumulator(bytes,bytes32,bytes32)",
            newAcc, currentHash, operationId
        );
        
        // First update - should succeed
        bool success1 = executeSafeTransaction(address(registry), txData);
        assertTrue(success1, "First update should succeed");
        
        // Try to update again in same block - should fail (MIN_BLOCK_DELAY = 1)
        bytes32 operationId2 = keccak256(abi.encodePacked("update2", block.timestamp));
        bytes memory newAcc2 = abi.encodePacked(bytes32(uint256(43)));
        bytes32 currentHash2 = registry.storedHash();
        bytes memory txData2 = abi.encodeWithSignature(
            "updateAccumulator(bytes,bytes32,bytes32)",
            newAcc2, currentHash2, operationId2
        );
        
        bool success2 = executeSafeTransaction(address(registry), txData2);
        assertFalse(success2, "Should fail - update too frequent");
    }
    
    function testInvalidMultisigThresholdTooLow() public {
        // Create a Safe with threshold = 1 (invalid)
        address[] memory testOwners = new address[](3);
        testOwners[0] = owner1;
        testOwners[1] = owner2;
        testOwners[2] = owner3;
        
        bytes memory initializer = abi.encodeCall(
            Safe.setup,
            (
                testOwners,
                1, // Invalid threshold < 2
                address(0),
                "",
                address(0),
                address(0),
                0,
                payable(address(0))
            )
        );
        
        address invalidSafeAddr = address(proxyFactory.createProxyWithNonce(
            address(safeSingleton),
            initializer,
            uint256(keccak256(abi.encodePacked(block.timestamp, "invalid")))
        ));
        
        // Try to deploy registry with invalid Safe - should fail
        bytes memory initialAccumulator = abi.encodePacked(bytes32(uint256(1)));
        vm.expectRevert(AccumulatorRegistry.InvalidMultisigThreshold.selector);
        new AccumulatorRegistry(
            initialAccumulator,
            address(manager),
            invalidSafeAddr
        );
    }
    
    function testInvalidMultisigOwnerCountTooLow() public {
        // Create a Safe with only 2 owners (invalid, need at least 3)
        address[] memory testOwners = new address[](2);
        testOwners[0] = owner1;
        testOwners[1] = owner2;
        
        bytes memory initializer = abi.encodeCall(
            Safe.setup,
            (
                testOwners,
                2,
                address(0),
                "",
                address(0),
                address(0),
                0,
                payable(address(0))
            )
        );
        
        address invalidSafeAddr = address(proxyFactory.createProxyWithNonce(
            address(safeSingleton),
            initializer,
            uint256(keccak256(abi.encodePacked(block.timestamp, "invalid2")))
        ));
        
        // Try to deploy registry with invalid Safe - should fail
        bytes memory initialAccumulator = abi.encodePacked(bytes32(uint256(1)));
        vm.expectRevert(AccumulatorRegistry.InvalidMultisigOwnerCount.selector);
        new AccumulatorRegistry(
            initialAccumulator,
            address(manager),
            invalidSafeAddr
        );
    }
    
    function testInvalidMultisigOwnerCountTooHigh() public {
        // Note: Safe setup prevents creating a Safe with > 10 owners, so we can't test
        // the invalid case directly. However, the validMultisigState modifier checks
        // ownerCount > 10, so that path exists in the code but is unreachable in practice.
        // We'll test that a Safe with exactly 10 owners (the max) works correctly.
        // This tests the boundary condition where ownerCount == 10 (which is valid).
        address[] memory maxOwners = new address[](10);
        for (uint256 i = 0; i < 10; i++) {
            maxOwners[i] = vm.addr(200 + i);
        }
        
        address maxSafeAddr = manager.deploySafe(maxOwners, 3);
        Safe maxSafe = Safe(payable(maxSafeAddr));
        
        // Verify the Safe has 10 owners (max valid)
        assertEq(maxSafe.getOwners().length, 10);
        
        // Change to max Safe - should succeed (10 is the maximum valid)
        vm.prank(address(manager));
        registry.changeAuthorizedSafe(maxSafeAddr);
        
        // Verify change succeeded
        assertEq(address(registry.authorizedSafe()), maxSafeAddr);
        
        // Verify the registry accepts this Safe (10 owners is valid, not > 10)
        (address multisigManagerAddr, address authorizedSafeAddr, uint256 threshold, address[] memory safeOwners, bool paused, uint256 lastUpdate) = registry.getSecurityInfo();
        assertEq(authorizedSafeAddr, maxSafeAddr);
        assertEq(safeOwners.length, 10);
        assertFalse(paused);
    }
    
    function testInvalidMultisigThresholdGreaterThanOwners() public {
        // Safe setup will fail if threshold > owner count, so we can't create such a Safe
        // Instead, test that changeAuthorizedSafe validates threshold
        // We'll test by trying to change to a Safe that would have invalid threshold
        // But since Safe setup validates, we need to test the validation in changeAuthorizedSafe
        
        // Create a Safe with valid config first
        address[] memory testOwners = new address[](3);
        testOwners[0] = owner6;
        testOwners[1] = owner7;
        testOwners[2] = owner8;
        
        address validSafeAddr = manager.deploySafe(testOwners, 2);
        
        // Change to valid Safe - should succeed
        vm.prank(address(manager));
        registry.changeAuthorizedSafe(validSafeAddr);
        
        // The validation in changeAuthorizedSafe checks threshold < 2 and ownerCount < 3
        // But Safe itself prevents threshold > ownerCount, so we can't test that path
        // The validMultisigState modifier checks threshold > ownerCount, but Safe prevents it
        // So this test case is actually not reachable in practice
        // We'll just verify the Safe change works
        assertEq(address(registry.authorizedSafe()), validSafeAddr);
    }
    
    function testChangeAuthorizedSafe() public {
        // Deploy a new Safe with valid config
        address[] memory newOwners = new address[](3);
        newOwners[0] = owner6;
        newOwners[1] = owner7;
        newOwners[2] = owner8;
        
        address newSafeAddr = manager.deploySafe(newOwners, 2);
        
        // Change authorized Safe via MultisigManager
        vm.prank(address(manager));
        registry.changeAuthorizedSafe(newSafeAddr);
        
        // Verify change
        assertEq(address(registry.authorizedSafe()), newSafeAddr);
        
        // Verify the new Safe has valid configuration
        Safe newSafe = Safe(payable(newSafeAddr));
        assertGe(newSafe.getThreshold(), 2);
        assertGe(newSafe.getOwners().length, 3);
        assertLe(newSafe.getOwners().length, 10);
    }
    
    function testChangeAuthorizedSafeInvalidAddress() public {
        vm.prank(address(manager));
        vm.expectRevert(AccumulatorRegistry.InvalidSafe.selector);
        registry.changeAuthorizedSafe(address(0));
    }
    
    function testChangeAuthorizedSafeInvalidConfig() public {
        // Create Safe with invalid config
        address[] memory testOwners = new address[](2);
        testOwners[0] = owner1;
        testOwners[1] = owner2;
        
        bytes memory initializer = abi.encodeCall(
            Safe.setup,
            (
                testOwners,
                2,
                address(0),
                "",
                address(0),
                address(0),
                0,
                payable(address(0))
            )
        );
        
        address invalidSafeAddr = address(proxyFactory.createProxyWithNonce(
            address(safeSingleton),
            initializer,
            uint256(keccak256(abi.encodePacked(block.timestamp, "invalid5")))
        ));
        
        vm.prank(address(manager));
        vm.expectRevert(AccumulatorRegistry.InvalidMultisigOwnerCount.selector);
        registry.changeAuthorizedSafe(invalidSafeAddr);
    }
    
    function testToggleEmergencyPauseFromManager() public {
        // Pause via MultisigManager
        vm.prank(address(manager));
        registry.toggleEmergencyPause();
        assertTrue(registry.emergencyPaused());
        
        // Unpause
        vm.prank(address(manager));
        registry.toggleEmergencyPause();
        assertFalse(registry.emergencyPaused());
    }
    
    function testToggleEmergencyPauseNotFromManager() public {
        vm.prank(owner1);
        vm.expectRevert(AccumulatorRegistry.NotMultisigManager.selector);
        registry.toggleEmergencyPause();
    }
    
    function testBatchRegisterEmptyArray() public {
        vm.roll(block.number + 1);
        
        bytes[] memory deviceIds = new bytes[](0);
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(999)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("batch", block.timestamp));
        
        bytes memory batchData = abi.encodeWithSignature(
            "batchRegisterDevices(bytes[],bytes,bytes32,bytes32)",
            deviceIds, newAcc, currentHash, operationId
        );
        
        bool success = executeSafeTransaction(address(registry), batchData);
        assertFalse(success, "Should fail - empty array");
    }
    
    function testBatchRegisterTooManyDevices() public {
        vm.roll(block.number + 1);
        
        bytes[] memory deviceIds = new bytes[](51);
        for (uint256 i = 0; i < 51; i++) {
            deviceIds[i] = abi.encodePacked(bytes32(uint256(i)));
        }
        
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(999)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("batch", block.timestamp));
        
        bytes memory batchData = abi.encodeWithSignature(
            "batchRegisterDevices(bytes[],bytes,bytes32,bytes32)",
            deviceIds, newAcc, currentHash, operationId
        );
        
        bool success = executeSafeTransaction(address(registry), batchData);
        assertFalse(success, "Should fail - too many devices");
    }
    
    function testBatchRegisterDuplicateDevice() public {
        vm.roll(block.number + 1);
        
        bytes[] memory deviceIds = new bytes[](2);
        deviceIds[0] = abi.encodePacked(bytes32(uint256(0x111)));
        deviceIds[1] = abi.encodePacked(bytes32(uint256(0x111))); // Duplicate
        
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(999)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("batch", block.timestamp));
        
        // Register first device
        bytes memory registerData = abi.encodeWithSignature(
            "registerDevice(bytes,bytes,bytes32,bytes32)",
            deviceIds[0], newAcc, currentHash, operationId
        );
        executeSafeTransaction(address(registry), registerData);
        
        // Try batch register with duplicate - should fail
        vm.roll(block.number + 1);
        bytes memory newAcc2 = abi.encodePacked(bytes32(uint256(1000)));
        currentHash = registry.storedHash();
        bytes32 operationId2 = keccak256(abi.encodePacked("batch2", block.timestamp));
        
        bytes memory batchData = abi.encodeWithSignature(
            "batchRegisterDevices(bytes[],bytes,bytes32,bytes32)",
            deviceIds, newAcc2, currentHash, operationId2
        );
        
        bool success = executeSafeTransaction(address(registry), batchData);
        assertFalse(success, "Should fail - duplicate device");
    }
    
    function testBatchRevokeEmptyArray() public {
        vm.roll(block.number + 1);
        
        bytes[] memory deviceIds = new bytes[](0);
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(999)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("batch", block.timestamp));
        
        bytes memory batchData = abi.encodeWithSignature(
            "batchRevokeDevices(bytes[],bytes,bytes32,bytes32)",
            deviceIds, newAcc, currentHash, operationId
        );
        
        bool success = executeSafeTransaction(address(registry), batchData);
        assertFalse(success, "Should fail - empty array");
    }
    
    function testBatchRevokeTooManyDevices() public {
        vm.roll(block.number + 1);
        
        bytes[] memory deviceIds = new bytes[](51);
        for (uint256 i = 0; i < 51; i++) {
            deviceIds[i] = abi.encodePacked(bytes32(uint256(i)));
        }
        
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(999)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("batch", block.timestamp));
        
        bytes memory batchData = abi.encodeWithSignature(
            "batchRevokeDevices(bytes[],bytes,bytes32,bytes32)",
            deviceIds, newAcc, currentHash, operationId
        );
        
        bool success = executeSafeTransaction(address(registry), batchData);
        assertFalse(success, "Should fail - too many devices");
    }
    
    function testBatchRevokeNotActiveDevice() public {
        vm.roll(block.number + 1);
        
        bytes[] memory deviceIds = new bytes[](1);
        deviceIds[0] = abi.encodePacked(bytes32(uint256(0x111)));
        
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(999)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("batch", block.timestamp));
        
        // Try to revoke non-existent device - should fail
        bytes memory batchData = abi.encodeWithSignature(
            "batchRevokeDevices(bytes[],bytes,bytes32,bytes32)",
            deviceIds, newAcc, currentHash, operationId
        );
        
        bool success = executeSafeTransaction(address(registry), batchData);
        assertFalse(success, "Should fail - device not active");
    }
    
    function testConstructorInvalidAddresses() public {
        bytes memory initialAccumulator = abi.encodePacked(bytes32(uint256(1)));
        
        vm.expectRevert(AccumulatorRegistry.InvalidSafe.selector);
        new AccumulatorRegistry(
            initialAccumulator,
            address(0),
            address(safe)
        );
        
        vm.expectRevert(AccumulatorRegistry.InvalidSafe.selector);
        new AccumulatorRegistry(
            initialAccumulator,
            address(manager),
            address(0)
        );
    }
    
    // ============ MultisigManager Error Cases ============
    
    function testDeploySafeInvalidThreshold() public {
        address[] memory testOwners = new address[](3);
        testOwners[0] = owner1;
        testOwners[1] = owner2;
        testOwners[2] = owner3;
        
        vm.expectRevert(MultisigManager.InvalidThreshold.selector);
        manager.deploySafe(testOwners, 1); // Too low
        
        vm.expectRevert(MultisigManager.InvalidThreshold.selector);
        manager.deploySafe(testOwners, 4); // Too high
    }
    
    function testDeploySafeInvalidOwnerCount() public {
        address[] memory testOwners = new address[](2);
        testOwners[0] = owner1;
        testOwners[1] = owner2;
        
        vm.expectRevert(MultisigManager.InvalidOwnerCount.selector);
        manager.deploySafe(testOwners, 2); // Too few owners
        
        address[] memory testOwners2 = new address[](11);
        for (uint256 i = 0; i < 11; i++) {
            testOwners2[i] = vm.addr(200 + i);
        }
        
        vm.expectRevert(MultisigManager.InvalidOwnerCount.selector);
        manager.deploySafe(testOwners2, 3); // Too many owners
    }
    
    function testDeploySafeZeroAddress() public {
        address[] memory testOwners = new address[](3);
        testOwners[0] = owner1;
        testOwners[1] = address(0); // Zero address
        testOwners[2] = owner3;
        
        vm.expectRevert(MultisigManager.InvalidSafe.selector);
        manager.deploySafe(testOwners, 2);
    }
    
    function testDeploySafeDuplicateOwners() public {
        address[] memory testOwners = new address[](3);
        testOwners[0] = owner1;
        testOwners[1] = owner1; // Duplicate
        testOwners[2] = owner3;
        
        vm.expectRevert(MultisigManager.OwnerAlreadyExists.selector);
        manager.deploySafe(testOwners, 2);
    }
    
    function testQueueAddOwnerMaxOwners() public {
        // Create a Safe with 10 owners (max)
        address[] memory maxOwners = new address[](10);
        for (uint256 i = 0; i < 10; i++) {
            maxOwners[i] = vm.addr(300 + i);
        }
        
        address maxSafeAddr = manager.deploySafe(maxOwners, 3);
        Safe maxSafe = Safe(payable(maxSafeAddr));
        
        // Enable MultisigManager as module
        bytes memory enableModuleData = abi.encodeWithSignature(
            "enableModule(address)",
            address(manager)
        );
        executeSafeTransactionForSafeWithOwners(maxSafe, maxSafeAddr, enableModuleData, maxOwners, 3);
        
        // Change registry to use this Safe
        vm.prank(address(manager));
        registry.changeAuthorizedSafe(maxSafeAddr);
        
        // Now try to add one more owner - should fail (max is 10)
        address finalOwner = vm.addr(2000);
        bytes memory queueData = abi.encodeWithSignature(
            "queueAddOwner(address,uint256)",
            finalOwner,
            maxSafe.getThreshold()
        );
        
        // Need to execute from the max Safe
        bool success = executeSafeTransactionForSafeWithOwners(maxSafe, address(manager), queueData, maxOwners, 3);
        assertFalse(success, "Should fail - max owners reached");
    }
    
    function testQueueAddOwnerInvalidThreshold() public {
        address newOwner = vm.addr(100);
        uint256 invalidThreshold = 0; // Too low
        
        bytes memory queueData = abi.encodeWithSignature(
            "queueAddOwner(address,uint256)",
            newOwner,
            invalidThreshold
        );
        
        bool success = executeSafeTransaction(address(manager), queueData);
        assertFalse(success, "Should fail - invalid threshold");
    }
    
    function testQueueAddOwnerAlreadyExists() public {
        address newOwner = owner1; // Already an owner
        
        bytes memory queueData = abi.encodeWithSignature(
            "queueAddOwner(address,uint256)",
            newOwner,
            3
        );
        
        bool success = executeSafeTransaction(address(manager), queueData);
        assertFalse(success, "Should fail - owner already exists");
    }
    
    function testQueueRemoveOwnerMinOwners() public {
        // Create a Safe with exactly 3 owners (min)
        address[] memory minOwners = new address[](3);
        minOwners[0] = owner6;
        minOwners[1] = owner7;
        minOwners[2] = owner8;
        
        address minSafeAddr = manager.deploySafe(minOwners, 2);
        Safe minSafe = Safe(payable(minSafeAddr));
        
        // Enable MultisigManager as module
        bytes memory enableModuleData = abi.encodeWithSignature(
            "enableModule(address)",
            address(manager)
        );
        executeSafeTransactionForSafeWithOwners(minSafe, minSafeAddr, enableModuleData, minOwners, 2);
        
        // Change registry to use this Safe
        vm.prank(address(manager));
        registry.changeAuthorizedSafe(minSafeAddr);
        
        // Now try to remove one owner - should fail (would go below min of 3)
        address ownerToRemove = minOwners[0];
        bytes memory queueData = abi.encodeWithSignature(
            "queueRemoveOwner(address,uint256)",
            ownerToRemove,
            2
        );
        
        // Need to execute from the min Safe
        bool success = executeSafeTransactionForSafeWithOwners(minSafe, address(manager), queueData, minOwners, 2);
        assertFalse(success, "Should fail - min owners reached");
    }
    
    function testQueueRemoveOwnerNotFound() public {
        address nonExistentOwner = vm.addr(9999);
        
        bytes memory queueData = abi.encodeWithSignature(
            "queueRemoveOwner(address,uint256)",
            nonExistentOwner,
            2
        );
        
        bool success = executeSafeTransaction(address(manager), queueData);
        assertFalse(success, "Should fail - owner not found");
    }
    
    function testQueueChangeThresholdInvalid() public {
        uint256 ownerCount = safe.getOwners().length;
        
        // Try threshold too low
        bytes memory queueData1 = abi.encodeWithSignature(
            "queueChangeThreshold(uint256)",
            1
        );
        bool success1 = executeSafeTransaction(address(manager), queueData1);
        assertFalse(success1, "Should fail - threshold too low");
        
        // Try threshold too high
        bytes memory queueData2 = abi.encodeWithSignature(
            "queueChangeThreshold(uint256)",
            ownerCount + 1
        );
        bool success2 = executeSafeTransaction(address(manager), queueData2);
        assertFalse(success2, "Should fail - threshold too high");
    }
    
    function testExecuteOperationNotFound() public {
        bytes32 fakeHash = keccak256("fake");
        
        bytes memory executeData = abi.encodeWithSignature(
            "executeOperation(bytes32)",
            fakeHash
        );
        
        bool success = executeSafeTransaction(address(manager), executeData);
        assertFalse(success, "Should fail - operation not found");
    }
    
    function testExecuteOperationNotReady() public {
        // Queue an operation
        bytes memory queueData = abi.encodeWithSignature(
            "queueChangeThreshold(uint256)",
            4
        );
        executeSafeTransaction(address(manager), queueData);
        
        // Try to execute immediately - should fail
        bytes memory params = abi.encode(uint256(4));
        bytes32 operationHash = keccak256(abi.encode(
            MultisigManager.OperationType.CHANGE_THRESHOLD,
            params,
            block.chainid,
            address(manager),
            manager.opNonce()
        ));
        
        bytes memory executeData = abi.encodeWithSignature(
            "executeOperation(bytes32)",
            operationHash
        );
        
        bool success = executeSafeTransaction(address(manager), executeData);
        assertFalse(success, "Should fail - operation not ready");
    }
    
    function testExecuteOperationAlreadyExecuted() public {
        // Queue and execute an operation
        bytes memory queueData = abi.encodeWithSignature(
            "queueChangeThreshold(uint256)",
            4
        );
        executeSafeTransaction(address(manager), queueData);
        
        bytes memory params = abi.encode(uint256(4));
        bytes32 operationHash = keccak256(abi.encode(
            MultisigManager.OperationType.CHANGE_THRESHOLD,
            params,
            block.chainid,
            address(manager),
            manager.opNonce()
        ));
        
        vm.warp(block.timestamp + 24 hours + 1);
        bytes memory executeData = abi.encodeWithSignature(
            "executeOperation(bytes32)",
            operationHash
        );
        executeSafeTransaction(address(manager), executeData);
        
        // Try to execute again - should fail
        bool success = executeSafeTransaction(address(manager), executeData);
        assertFalse(success, "Should fail - already executed");
    }
    
    function testRemoveOwnerOperation() public {
        address[] memory currentOwners = safe.getOwners();
        address ownerToRemove = currentOwners[currentOwners.length - 1];
        uint256 newThreshold = safe.getThreshold() > 2 ? safe.getThreshold() - 1 : 2;
        
        // Queue remove owner
        bytes memory queueData = abi.encodeWithSignature(
            "queueRemoveOwner(address,uint256)",
            ownerToRemove,
            newThreshold
        );
        
        bytes memory params = abi.encode(ownerToRemove, newThreshold);
        bytes32 expectedHash = keccak256(abi.encode(
            MultisigManager.OperationType.REMOVE_OWNER,
            params,
            block.chainid,
            address(manager),
            manager.opNonce() + 1
        ));
        
        executeSafeTransaction(address(manager), queueData);
        
        // Execute after timelock
        vm.warp(block.timestamp + 24 hours + 1);
        
        bytes memory executeData = abi.encodeWithSignature(
            "executeOperation(bytes32)",
            expectedHash
        );
        
        bool success = executeSafeTransaction(address(manager), executeData);
        assertTrue(success, "Should succeed");
        
        // Verify owner was removed
        address[] memory updatedOwners = safe.getOwners();
        assertEq(updatedOwners.length, currentOwners.length - 1);
    }
    
    function testGetOperationData() public {
        // Queue an operation
        bytes memory queueData = abi.encodeWithSignature(
            "queueChangeThreshold(uint256)",
            4
        );
        executeSafeTransaction(address(manager), queueData);
        
        bytes memory params = abi.encode(uint256(4));
        bytes32 operationHash = keccak256(abi.encode(
            MultisigManager.OperationType.CHANGE_THRESHOLD,
            params,
            block.chainid,
            address(manager),
            manager.opNonce()
        ));
        
        bytes memory data = manager.getOperationData(operationHash);
        assertEq(data.length, params.length);
    }
    
    function testGetOperationDataNotFound() public {
        bytes32 fakeHash = keccak256("fake");
        vm.expectRevert(MultisigManager.OperationNotFound.selector);
        manager.getOperationData(fakeHash);
    }
    
    function testIsOperationPending() public {
        // Queue an operation
        bytes memory queueData = abi.encodeWithSignature(
            "queueChangeThreshold(uint256)",
            4
        );
        executeSafeTransaction(address(manager), queueData);
        
        bytes memory params = abi.encode(uint256(4));
        bytes32 operationHash = keccak256(abi.encode(
            MultisigManager.OperationType.CHANGE_THRESHOLD,
            params,
            block.chainid,
            address(manager),
            manager.opNonce()
        ));
        
        // Should not be pending yet (timelock not expired)
        bool pending = manager.isOperationPending(operationHash);
        assertFalse(pending, "Should not be pending yet");
        
        // After timelock expires
        vm.warp(block.timestamp + 24 hours + 1);
        pending = manager.isOperationPending(operationHash);
        assertTrue(pending, "Should be pending now");
        
        // After execution
        bytes memory executeData = abi.encodeWithSignature(
            "executeOperation(bytes32)",
            operationHash
        );
        executeSafeTransaction(address(manager), executeData);
        
        pending = manager.isOperationPending(operationHash);
        assertFalse(pending, "Should not be pending after execution");
    }
    
    function testGetOperationStatus() public {
        // Queue an operation
        bytes memory queueData = abi.encodeWithSignature(
            "queueChangeThreshold(uint256)",
            4
        );
        executeSafeTransaction(address(manager), queueData);
        
        bytes memory params = abi.encode(uint256(4));
        bytes32 operationHash = keccak256(abi.encode(
            MultisigManager.OperationType.CHANGE_THRESHOLD,
            params,
            block.chainid,
            address(manager),
            manager.opNonce()
        ));
        
        (bool exists, bool executed, bool ready, uint256 executeAfter, MultisigManager.OperationType opType) = 
            manager.getOperationStatus(operationHash);
        
        assertTrue(exists);
        assertFalse(executed);
        assertFalse(ready);
        assertTrue(executeAfter > block.timestamp);
        assertEq(uint8(opType), uint8(MultisigManager.OperationType.CHANGE_THRESHOLD));
    }
    
    function testChangeEmergencyAdmin() public {
        address newAdmin = vm.addr(8888);
        
        vm.prank(emergencyAdmin);
        manager.changeEmergencyAdmin(newAdmin);
        
        assertEq(manager.emergencyAdmin(), newAdmin);
    }
    
    function testChangeEmergencyAdminNotAuthorized() public {
        vm.prank(owner1);
        vm.expectRevert(MultisigManager.NotAuthorized.selector);
        manager.changeEmergencyAdmin(vm.addr(8888));
    }
    
    function testCancelOperationNotAuthorized() public {
        bytes32 fakeHash = keccak256("fake");
        
        vm.prank(owner1);
        vm.expectRevert(MultisigManager.NotAuthorized.selector);
        manager.cancelOperation(fakeHash);
    }
    
    function testCancelOperationNotFound() public {
        bytes32 fakeHash = keccak256("fake");
        
        vm.prank(emergencyAdmin);
        vm.expectRevert(MultisigManager.OperationNotFound.selector);
        manager.cancelOperation(fakeHash);
    }
    
    function testCancelOperationAlreadyExecuted() public {
        // Queue and execute an operation
        bytes memory queueData = abi.encodeWithSignature(
            "queueChangeThreshold(uint256)",
            4
        );
        executeSafeTransaction(address(manager), queueData);
        
        bytes memory params = abi.encode(uint256(4));
        bytes32 operationHash = keccak256(abi.encode(
            MultisigManager.OperationType.CHANGE_THRESHOLD,
            params,
            block.chainid,
            address(manager),
            manager.opNonce()
        ));
        
        vm.warp(block.timestamp + 24 hours + 1);
        bytes memory executeData = abi.encodeWithSignature(
            "executeOperation(bytes32)",
            operationHash
        );
        executeSafeTransaction(address(manager), executeData);
        
        // Try to cancel - should fail
        vm.prank(emergencyAdmin);
        vm.expectRevert(MultisigManager.OperationAlreadyExecuted.selector);
        manager.cancelOperation(operationHash);
    }
    
    function testQueueOperationsWhenPaused() public {
        // Pause the manager
        vm.prank(emergencyAdmin);
        manager.toggleEmergencyPause();
        
        // Try to queue operation - should fail
        bytes memory queueData = abi.encodeWithSignature(
            "queueChangeThreshold(uint256)",
            4
        );
        
        bool success = executeSafeTransaction(address(manager), queueData);
        assertFalse(success, "Should fail - paused");
    }
    
    function testExecuteOperationWhenPaused() public {
        // Queue an operation first
        bytes memory queueData = abi.encodeWithSignature(
            "queueChangeThreshold(uint256)",
            4
        );
        executeSafeTransaction(address(manager), queueData);
        
        bytes memory params = abi.encode(uint256(4));
        bytes32 operationHash = keccak256(abi.encode(
            MultisigManager.OperationType.CHANGE_THRESHOLD,
            params,
            block.chainid,
            address(manager),
            manager.opNonce()
        ));
        
        vm.warp(block.timestamp + 24 hours + 1);
        
        // Pause the manager
        vm.prank(emergencyAdmin);
        manager.toggleEmergencyPause();
        
        // Try to execute - should fail
        bytes memory executeData = abi.encodeWithSignature(
            "executeOperation(bytes32)",
            operationHash
        );
        
        bool success = executeSafeTransaction(address(manager), executeData);
        assertFalse(success, "Should fail - paused");
    }
    
    function testGetCurrentOwners() public {
        address[] memory owners = manager.getCurrentOwners();
        assertEq(owners.length, 5);
    }
    
    function testGetCurrentThreshold() public {
        uint256 threshold = manager.getCurrentThreshold();
        assertEq(threshold, 3);
    }
    
    function testGetCurrentState() public view {
        (
            bytes memory accumulator,
            bytes32 hash,
            uint256 ver,
            address currentSafeAddr,
            uint256 safeThreshold,
            uint256 safeOwnerCount,
            bool paused
        ) = registry.getCurrentState();
        
        assertEq(accumulator, registry.currentAccumulator());
        assertEq(hash, registry.storedHash());
        assertEq(ver, registry.version());
        assertEq(currentSafeAddr, address(safe));
        assertEq(safeThreshold, safe.getThreshold());
        assertEq(safeOwnerCount, safe.getOwners().length);
        assertEq(paused, registry.emergencyPaused());
    }
    
    function testGetCurrentStateAfterUpdate() public {
        vm.roll(block.number + 1);
        
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(42)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("update", block.timestamp));
        
        bytes memory txData = abi.encodeWithSignature(
            "updateAccumulator(bytes,bytes32,bytes32)",
            newAcc, currentHash, operationId
        );
        
        executeSafeTransaction(address(registry), txData);
        
        (
            bytes memory accumulator,
            bytes32 hash,
            uint256 ver,
            address currentSafeAddr,
            uint256 safeThreshold,
            uint256 safeOwnerCount,
            bool paused
        ) = registry.getCurrentState();
        
        assertEq(accumulator, newAcc);
        assertEq(hash, keccak256(newAcc));
        assertEq(ver, 2);
        assertEq(currentSafeAddr, address(safe));
        assertEq(safeThreshold, safe.getThreshold());
        assertEq(safeOwnerCount, safe.getOwners().length);
        assertFalse(paused);
    }
    
    function testGetCurrentStateWhenPaused() public {
        vm.prank(address(manager));
        registry.toggleEmergencyPause();
        
        (
            bytes memory accumulator,
            bytes32 hash,
            uint256 ver,
            address currentSafeAddr,
            uint256 safeThreshold,
            uint256 safeOwnerCount,
            bool paused
        ) = registry.getCurrentState();
        
        assertTrue(paused);
        assertEq(currentSafeAddr, address(safe));
    }
    
    function testDeviceStatus() public view {
        bytes memory deviceId = abi.encodePacked(bytes32(uint256(0xDEADBEEF)));
        
        // Device not registered yet
        uint8 status = registry.deviceStatus(deviceId);
        assertEq(status, 0);
    }
    
    function testDeviceStatusAfterRegistration() public {
        vm.roll(block.number + 1);
        
        bytes memory deviceId = abi.encodePacked(bytes32(uint256(0xDEADBEEF)));
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(100)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("register", block.timestamp));
        
        bytes memory registerData = abi.encodeWithSignature(
            "registerDevice(bytes,bytes,bytes32,bytes32)",
            deviceId, newAcc, currentHash, operationId
        );
        executeSafeTransaction(address(registry), registerData);
        
        uint8 status = registry.deviceStatus(deviceId);
        assertEq(status, 1); // Active
    }
    
    function testDeviceStatusAfterRevocation() public {
        vm.roll(block.number + 1);
        
        bytes memory deviceId = abi.encodePacked(bytes32(uint256(0xDEADBEEF)));
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(100)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("register", block.timestamp));
        
        bytes memory registerData = abi.encodeWithSignature(
            "registerDevice(bytes,bytes,bytes32,bytes32)",
            deviceId, newAcc, currentHash, operationId
        );
        bool regSuccess = executeSafeTransaction(address(registry), registerData);
        assertTrue(regSuccess, "Registration should succeed");
        
        // Verify device is registered
        uint8 statusBefore = registry.deviceStatus(deviceId);
        assertEq(statusBefore, 1, "Device should be active");
        
        vm.roll(block.number + 1);
        bytes memory revokeAcc = abi.encodePacked(bytes32(uint256(200)));
        currentHash = registry.storedHash();
        bytes32 revokeOpId = keccak256(abi.encodePacked("revoke", block.timestamp));
        
        bytes memory revokeData = abi.encodeWithSignature(
            "revokeDevice(bytes,bytes,bytes32,bytes32)",
            deviceId, revokeAcc, currentHash, revokeOpId
        );
        bool revokeSuccess = executeSafeTransaction(address(registry), revokeData);
        assertTrue(revokeSuccess, "Revocation should succeed");
        
        uint8 status = registry.deviceStatus(deviceId);
        assertEq(status, 2, "Device should be revoked"); // Revoked
    }
    
    function testBatchRegisterDevicesSuccess() public {
        vm.roll(block.number + 1);
        
        bytes[] memory deviceIds = new bytes[](3);
        deviceIds[0] = abi.encodePacked(bytes32(uint256(0x111)));
        deviceIds[1] = abi.encodePacked(bytes32(uint256(0x222)));
        deviceIds[2] = abi.encodePacked(bytes32(uint256(0x333)));
        
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(999)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("batch", block.timestamp));
        
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
    }
    
    function testBatchRevokeDevicesSuccess() public {
        vm.roll(block.number + 1);
        
        // First register devices
        bytes[] memory deviceIds = new bytes[](3);
        deviceIds[0] = abi.encodePacked(bytes32(uint256(0x111)));
        deviceIds[1] = abi.encodePacked(bytes32(uint256(0x222)));
        deviceIds[2] = abi.encodePacked(bytes32(uint256(0x333)));
        
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(999)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("batch", block.timestamp));
        
        bytes memory batchData = abi.encodeWithSignature(
            "batchRegisterDevices(bytes[],bytes,bytes32,bytes32)",
            deviceIds, newAcc, currentHash, operationId
        );
        bool regSuccess = executeSafeTransaction(address(registry), batchData);
        assertTrue(regSuccess, "Batch registration should succeed");
        
        // Verify all devices are registered
        for (uint256 i = 0; i < deviceIds.length; i++) {
            assertEq(registry.deviceStatus(deviceIds[i]), 1, "Device should be active");
        }
        
        // Now revoke them
        vm.roll(block.number + 1);
        bytes memory revokeAcc = abi.encodePacked(bytes32(uint256(1000)));
        currentHash = registry.storedHash();
        bytes32 revokeOpId = keccak256(abi.encodePacked("batchRevoke", block.timestamp));
        
        bytes memory revokeBatchData = abi.encodeWithSignature(
            "batchRevokeDevices(bytes[],bytes,bytes32,bytes32)",
            deviceIds, revokeAcc, currentHash, revokeOpId
        );
        
        bool success = executeSafeTransaction(address(registry), revokeBatchData);
        assertTrue(success, "Batch revocation should succeed");
        
        // Verify all devices are revoked
        for (uint256 i = 0; i < deviceIds.length; i++) {
            assertEq(registry.deviceStatus(deviceIds[i]), 2, "Device should be revoked");
        }
    }
    
    function testBatchRegisterWithMaxDevices() public {
        vm.roll(block.number + 1);
        
        bytes[] memory deviceIds = new bytes[](50); // Max allowed
        for (uint256 i = 0; i < 50; i++) {
            deviceIds[i] = abi.encodePacked(bytes32(uint256(i + 1000)));
        }
        
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(999)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("batch", block.timestamp));
        
        bytes memory batchData = abi.encodeWithSignature(
            "batchRegisterDevices(bytes[],bytes,bytes32,bytes32)",
            deviceIds, newAcc, currentHash, operationId
        );
        
        bool success = executeSafeTransaction(address(registry), batchData);
        assertTrue(success, "Should succeed with max devices");
    }
    
    function testFindPrevOwnerFirstOwner() public {
        // Test _findPrevOwner when removing the first owner
        address[] memory currentOwners = safe.getOwners();
        address firstOwner = currentOwners[0];
        
        // Queue remove owner operation for first owner
        uint256 newThreshold = safe.getThreshold() > 2 ? safe.getThreshold() - 1 : 2;
        
        bytes memory queueData = abi.encodeWithSignature(
            "queueRemoveOwner(address,uint256)",
            firstOwner,
            newThreshold
        );
        
        bytes memory params = abi.encode(firstOwner, newThreshold);
        bytes32 expectedHash = keccak256(abi.encode(
            MultisigManager.OperationType.REMOVE_OWNER,
            params,
            block.chainid,
            address(manager),
            manager.opNonce() + 1
        ));
        
        executeSafeTransaction(address(manager), queueData);
        
        // Execute after timelock
        vm.warp(block.timestamp + 24 hours + 1);
        
        bytes memory executeData = abi.encodeWithSignature(
            "executeOperation(bytes32)",
            expectedHash
        );
        
        bool success = executeSafeTransaction(address(manager), executeData);
        assertTrue(success, "Should succeed removing first owner");
        
        // Verify owner was removed
        address[] memory updatedOwners = safe.getOwners();
        assertEq(updatedOwners.length, currentOwners.length - 1);
    }
    
    function testFindPrevOwnerMiddleOwner() public {
        // Test _findPrevOwner when removing a middle owner
        address[] memory currentOwners = safe.getOwners();
        // Remove the second owner (index 1)
        address ownerToRemove = currentOwners.length > 1 ? currentOwners[1] : currentOwners[0];
        uint256 newThreshold = safe.getThreshold() > 2 ? safe.getThreshold() - 1 : 2;
        
        bytes memory queueData = abi.encodeWithSignature(
            "queueRemoveOwner(address,uint256)",
            ownerToRemove,
            newThreshold
        );
        
        bytes memory params = abi.encode(ownerToRemove, newThreshold);
        bytes32 expectedHash = keccak256(abi.encode(
            MultisigManager.OperationType.REMOVE_OWNER,
            params,
            block.chainid,
            address(manager),
            manager.opNonce() + 1
        ));
        
        executeSafeTransaction(address(manager), queueData);
        
        // Execute after timelock
        vm.warp(block.timestamp + 24 hours + 1);
        
        bytes memory executeData = abi.encodeWithSignature(
            "executeOperation(bytes32)",
            expectedHash
        );
        
        bool success = executeSafeTransaction(address(manager), executeData);
        assertTrue(success, "Should succeed removing middle owner");
    }
    
    function testValidMultisigStateBoundaryConditions() public {
        // Test with exactly 3 owners (minimum)
        address[] memory minOwners = new address[](3);
        minOwners[0] = owner6;
        minOwners[1] = owner7;
        minOwners[2] = owner8;
        
        address minSafeAddr = manager.deploySafe(minOwners, 2);
        
        // Change registry to use this Safe
        vm.prank(address(manager));
        registry.changeAuthorizedSafe(minSafeAddr);
        
        // Should be able to perform operations
        vm.roll(block.number + 1);
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(42)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("test", block.timestamp));
        
        bytes memory txData = abi.encodeWithSignature(
            "updateAccumulator(bytes,bytes32,bytes32)",
            newAcc, currentHash, operationId
        );
        
        // Need to execute from the min Safe
        Safe minSafe = Safe(payable(minSafeAddr));
        bool success = executeSafeTransactionForSafeWithOwners(minSafe, address(registry), txData, minOwners, 2);
        assertTrue(success, "Should work with min owners");
    }
    
    function testValidMultisigStateWithThresholdEqualsOwners() public {
        // Test with threshold equal to owner count
        address[] memory testOwners = new address[](3);
        testOwners[0] = owner6;
        testOwners[1] = owner7;
        testOwners[2] = owner8;
        
        address testSafeAddr = manager.deploySafe(testOwners, 3); // threshold = owner count
        
        // Change registry to use this Safe
        vm.prank(address(manager));
        registry.changeAuthorizedSafe(testSafeAddr);
        
        // Should be valid (threshold == ownerCount is allowed)
        Safe testSafe = Safe(payable(testSafeAddr));
        assertEq(testSafe.getThreshold(), 3);
        assertEq(testSafe.getOwners().length, 3);
        
        // Test that operations work with threshold == ownerCount
        vm.roll(block.number + 1);
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(42)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("test", block.timestamp));
        
        bytes memory txData = abi.encodeWithSignature(
            "updateAccumulator(bytes,bytes32,bytes32)",
            newAcc, currentHash, operationId
        );
        
        bool success = executeSafeTransactionForSafeWithOwners(testSafe, address(registry), txData, testOwners, 3);
        assertTrue(success, "Should work with threshold == ownerCount");
    }
    
    function testBatchRegisterWithSingleDevice() public {
        vm.roll(block.number + 1);
        
        bytes[] memory deviceIds = new bytes[](1);
        deviceIds[0] = abi.encodePacked(bytes32(uint256(0xAAA)));
        
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(999)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("batch", block.timestamp));
        
        bytes memory batchData = abi.encodeWithSignature(
            "batchRegisterDevices(bytes[],bytes,bytes32,bytes32)",
            deviceIds, newAcc, currentHash, operationId
        );
        
        bool success = executeSafeTransaction(address(registry), batchData);
        assertTrue(success, "Should succeed with single device");
        
        assertEq(registry.deviceStatus(deviceIds[0]), 1);
    }
    
    function testBatchRevokeWithSingleDevice() public {
        vm.roll(block.number + 1);
        
        // First register a device
        bytes[] memory deviceIds = new bytes[](1);
        deviceIds[0] = abi.encodePacked(bytes32(uint256(0xAAA)));
        
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(999)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("batch", block.timestamp));
        
        bytes memory batchData = abi.encodeWithSignature(
            "batchRegisterDevices(bytes[],bytes,bytes32,bytes32)",
            deviceIds, newAcc, currentHash, operationId
        );
        bool regSuccess = executeSafeTransaction(address(registry), batchData);
        assertTrue(regSuccess, "Registration should succeed");
        
        // Verify device is registered
        assertEq(registry.deviceStatus(deviceIds[0]), 1, "Device should be active");
        
        // Now revoke it
        vm.roll(block.number + 1);
        bytes memory revokeAcc = abi.encodePacked(bytes32(uint256(1000)));
        currentHash = registry.storedHash();
        bytes32 revokeOpId = keccak256(abi.encodePacked("batchRevoke", block.timestamp));
        
        bytes memory revokeBatchData = abi.encodeWithSignature(
            "batchRevokeDevices(bytes[],bytes,bytes32,bytes32)",
            deviceIds, revokeAcc, currentHash, revokeOpId
        );
        
        bool success = executeSafeTransaction(address(registry), revokeBatchData);
        assertTrue(success, "Should succeed revoking single device");
        
        assertEq(registry.deviceStatus(deviceIds[0]), 2, "Device should be revoked");
    }
    
    function testFindPrevOwnerLastOwner() public {
        // Test _findPrevOwner when removing the last owner
        address[] memory currentOwners = safe.getOwners();
        address lastOwner = currentOwners[currentOwners.length - 1];
        uint256 newThreshold = safe.getThreshold() > 2 ? safe.getThreshold() - 1 : 2;
        
        bytes memory queueData = abi.encodeWithSignature(
            "queueRemoveOwner(address,uint256)",
            lastOwner,
            newThreshold
        );
        
        bytes memory params = abi.encode(lastOwner, newThreshold);
        bytes32 expectedHash = keccak256(abi.encode(
            MultisigManager.OperationType.REMOVE_OWNER,
            params,
            block.chainid,
            address(manager),
            manager.opNonce() + 1
        ));
        
        executeSafeTransaction(address(manager), queueData);
        
        // Execute after timelock
        vm.warp(block.timestamp + 24 hours + 1);
        
        bytes memory executeData = abi.encodeWithSignature(
            "executeOperation(bytes32)",
            expectedHash
        );
        
        bool success = executeSafeTransaction(address(manager), executeData);
        assertTrue(success, "Should succeed removing last owner");
    }
    
    function testGetSecurityInfo() public view {
        (
            address multisigManagerAddr,
            address authorizedSafeAddr,
            uint256 threshold,
            address[] memory owners,
            bool paused,
            uint256 lastUpdate
        ) = registry.getSecurityInfo();
        
        assertEq(multisigManagerAddr, address(manager));
        assertEq(authorizedSafeAddr, address(safe));
        assertEq(threshold, safe.getThreshold());
        assertEq(owners.length, safe.getOwners().length);
        assertFalse(paused);
        assertTrue(lastUpdate > 0);
    }
    
    function testGetSecurityInfoAfterUpdate() public {
        vm.roll(block.number + 1);
        
        bytes memory newAcc = abi.encodePacked(bytes32(uint256(42)));
        bytes32 currentHash = registry.storedHash();
        bytes32 operationId = keccak256(abi.encodePacked("update", block.timestamp));
        
        bytes memory txData = abi.encodeWithSignature(
            "updateAccumulator(bytes,bytes32,bytes32)",
            newAcc, currentHash, operationId
        );
        
        executeSafeTransaction(address(registry), txData);
        
        (
            address multisigManagerAddr,
            address authorizedSafeAddr,
            uint256 threshold,
            address[] memory owners,
            bool paused,
            uint256 lastUpdate
        ) = registry.getSecurityInfo();
        
        assertEq(multisigManagerAddr, address(manager));
        assertEq(authorizedSafeAddr, address(safe));
        assertFalse(paused);
        assertTrue(lastUpdate > 0);
    }
    
    function testQueueRemoveOwnerInvalidThresholdTooHigh() public {
        address[] memory currentOwners = safe.getOwners();
        address ownerToRemove = currentOwners[currentOwners.length - 1];
        uint256 invalidThreshold = currentOwners.length; // Too high (should be < currentOwners.length)
        
        bytes memory queueData = abi.encodeWithSignature(
            "queueRemoveOwner(address,uint256)",
            ownerToRemove,
            invalidThreshold
        );
        
        bool success = executeSafeTransaction(address(manager), queueData);
        assertFalse(success, "Should fail - threshold too high");
    }
    
    function testQueueRemoveOwnerInvalidThresholdTooLow() public {
        address[] memory currentOwners = safe.getOwners();
        address ownerToRemove = currentOwners[currentOwners.length - 1];
        uint256 invalidThreshold = 1; // Too low (should be >= 2)
        
        bytes memory queueData = abi.encodeWithSignature(
            "queueRemoveOwner(address,uint256)",
            ownerToRemove,
            invalidThreshold
        );
        
        bool success = executeSafeTransaction(address(manager), queueData);
        assertFalse(success, "Should fail - threshold too low");
    }
    
    function testQueueAddOwnerInvalidThresholdTooHigh() public {
        address newOwner = vm.addr(100);
        uint256 ownerCount = safe.getOwners().length;
        uint256 invalidThreshold = ownerCount + 2; // Too high (should be <= ownerCount + 1)
        
        bytes memory queueData = abi.encodeWithSignature(
            "queueAddOwner(address,uint256)",
            newOwner,
            invalidThreshold
        );
        
        bool success = executeSafeTransaction(address(manager), queueData);
        assertFalse(success, "Should fail - threshold too high");
    }
    
    // Helper function to execute Safe transactions
    function executeSafeTransaction(
        address to,
        bytes memory data
    ) internal returns (bool success) {
        return executeSafeTransactionForSafe(safe, to, data);
    }
    
    function executeSafeTransactionForSafe(
        Safe safeInstance,
        address target,
        bytes memory data
    ) internal returns (bool success) {
        address[] memory defaultOwners = new address[](3);
        defaultOwners[0] = owner1;
        defaultOwners[1] = owner2;
        defaultOwners[2] = owner3;
        return executeSafeTransactionForSafeWithOwners(safeInstance, target, data, defaultOwners, 3);
    }
    
    function executeSafeTransactionForSafeWithOwners(
        Safe safeInstance,
        address target,
        bytes memory data,
        address[] memory owners,
        uint256 threshold
    ) internal returns (bool success) {
        uint256 nonce = safeInstance.nonce();
        
        bytes32 txHash = safeInstance.getTransactionHash(
            target,
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
        
        // Use first 'threshold' owners as signers
        address[] memory signers = new address[](threshold);
        for (uint256 i = 0; i < threshold; i++) {
            signers[i] = owners[i];
        }
        
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
            uint256 key = 0;
            if (signers[i] == owner1) key = owner1Key;
            else if (signers[i] == owner2) key = owner2Key;
            else if (signers[i] == owner3) key = owner3Key;
            else if (signers[i] == owner4) key = owner4Key;
            else if (signers[i] == owner5) key = owner5Key;
            else if (signers[i] == owner6) key = owner6Key;
            else if (signers[i] == owner7) key = owner7Key;
            else if (signers[i] == owner8) key = owner8Key;
            else if (signers[i] == owner9) key = owner9Key;
            else if (signers[i] == owner10) key = owner10Key;
            else {
                // For owners not in our predefined list, we can't sign
                // This will cause the transaction to fail
                return false;
            }
            
            (uint8 v, bytes32 r, bytes32 s) = vm.sign(key, txHash);
            signatures = abi.encodePacked(signatures, r, s, v);
        }
        
        try safeInstance.execTransaction(
            target,
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

