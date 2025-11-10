// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {AccumulatorRegistry} from "../src/AccumulatorRegistry.sol";
import {Safe} from "safe-contracts/Safe.sol";
import {SafeProxyFactory} from "safe-contracts/proxies/SafeProxyFactory.sol";
import {Enum} from "safe-contracts/libraries/Enum.sol";

/**
 * @title SafeSignatureDebug
 * @notice Test to debug EIP-712 signature verification in Gnosis Safe
 * @dev Simulates the exact multi-sig flow with Anvil accounts
 */
contract SafeSignatureDebugTest is Test {
    AccumulatorRegistry registry;
    Safe safe;
    SafeProxyFactory proxyFactory;
    Safe safeSingleton;
    
    // Anvil default accounts (first 5)
    uint256 constant ANVIL_KEY_0 = 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80;
    uint256 constant ANVIL_KEY_1 = 0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d;
    uint256 constant ANVIL_KEY_2 = 0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a;
    uint256 constant ANVIL_KEY_3 = 0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6;
    uint256 constant ANVIL_KEY_4 = 0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a;
    
    address owner0 = vm.addr(ANVIL_KEY_0);
    address owner1 = vm.addr(ANVIL_KEY_1);
    address owner2 = vm.addr(ANVIL_KEY_2);
    address owner3 = vm.addr(ANVIL_KEY_3);
    address owner4 = vm.addr(ANVIL_KEY_4);
    
    address[] owners;
    uint256 constant THRESHOLD = 3;
    
    // Test data
    bytes32 testDeviceId = bytes32(uint256(0x5f29bfc920ed7c15e4a7ffadcc762ee6a65adaedaf5716371bddb3841783ba42));
    bytes testAccumulator;
    bytes32 testParentHash; // Will be set to initial accumulator hash in setUp
    bytes32 testOperationId = bytes32(uint256(0x60f124701419bda11d23f768876d2f8f7f88d7ea1e1c2c1964418129c853ecdc));
    
    function setUp() public {
        console.log("\n=== SETUP ===");
        
        // Setup owners (Anvil accounts 0-4)
        owners = new address[](5);
        owners[0] = owner0;
        owners[1] = owner1;
        owners[2] = owner2;
        owners[3] = owner3;
        owners[4] = owner4;
        
        console.log("Owner 0:", owner0);
        console.log("Owner 1:", owner1);
        console.log("Owner 2:", owner2);
        console.log("Owner 3:", owner3);
        console.log("Owner 4:", owner4);
        
        // Deploy Safe infrastructure
        safeSingleton = new Safe();
        proxyFactory = new SafeProxyFactory();
        
        // Deploy Safe proxy with Anvil accounts as owners
        bytes memory initializer = abi.encodeCall(
            Safe.setup,
            (
                owners,
                THRESHOLD,
                address(0),
                "",
                address(0),
                address(0),
                0,
                payable(address(0))
            )
        );
        
        address safeProxyAddress = address(proxyFactory.createProxyWithNonce(
            address(safeSingleton),
            initializer,
            uint256(keccak256(abi.encodePacked(block.timestamp, owners, THRESHOLD)))
        ));
        
        safe = Safe(payable(safeProxyAddress));
        
        console.log("\nSafe deployed at:", address(safe));
        console.log("Safe threshold:", safe.getThreshold());
        console.log("Safe nonce:", safe.nonce());
        
        // Deploy AccumulatorRegistry with initial accumulator
        // For this test, we'll use the test contract address as multisigManager
        // since we only need to test the Safe signature verification
        bytes memory initialAccumulator = _generateTestAccumulator();
        testParentHash = keccak256(initialAccumulator); // Set parent hash for test
        vm.prank(address(safe));
        registry = new AccumulatorRegistry(initialAccumulator, address(this), address(safe));
        
        console.log("Registry deployed at:", address(registry));
        
        // Setup test accumulator (256 bytes) - different from initial for the update
        testAccumulator = _generateTestAccumulator();
        
        console.log("\n=== SETUP COMPLETE ===\n");
    }
    
    function test_SafeEIP712Signature() public {
        console.log("\n=== TEST: EIP-712 Signature Verification ===\n");
        
        // Roll forward blocks to avoid rate limiting
        vm.roll(block.number + 10);
        console.log("Current block number:", block.number);
        
        // Convert testDeviceId from bytes32 to bytes for registerDevice
        bytes memory deviceIdBytes = abi.encodePacked(testDeviceId);
        
        // 1. Prepare registerDevice call data
        bytes memory callData = abi.encodeCall(
            AccumulatorRegistry.registerDevice,
            (deviceIdBytes, testAccumulator, testParentHash, testOperationId)
        );
        
        console.log("Call data length:", callData.length);
        console.log("Function selector:", vm.toString(bytes4(callData)));
        
        console.log("\nSafe Transaction Parameters:");
        console.log("  to:", address(registry));
        console.log("  value:", uint256(0));
        console.log("  operation:", uint8(Enum.Operation.Call));
        console.log("  nonce:", safe.nonce());
        
        // 2. Compute Safe transaction hash (EIP-712)
        bytes32 safeTxHash = safe.getTransactionHash(
            address(registry),    // to
            0,                    // value
            callData,             // data
            Enum.Operation.Call,  // operation
            0,                    // safeTxGas
            0,                    // baseGas
            0,                    // gasPrice
            address(0),           // gasToken
            address(0),           // refundReceiver
            safe.nonce()          // nonce
        );
        
        console.log("\nSafe TX Hash:", vm.toString(safeTxHash));
        
        // 4. Get domain separator
        bytes32 domainSeparator = safe.domainSeparator();
        console.log("Domain Separator:", vm.toString(domainSeparator));
        
        // 5. Manually compute the hash to verify
        bytes32 DOMAIN_TYPEHASH = keccak256("EIP712Domain(uint256 chainId,address verifyingContract)");
        bytes32 SAFE_TX_TYPEHASH = keccak256(
            "SafeTx(address to,uint256 value,bytes data,uint8 operation,uint256 safeTxGas,uint256 baseGas,uint256 gasPrice,address gasToken,address refundReceiver,uint256 nonce)"
        );
        
        bytes32 computedDomainSeparator = keccak256(
            abi.encode(DOMAIN_TYPEHASH, block.chainid, address(safe))
        );
        
        console.log("\nVerification:");
        console.log("  Chain ID:", block.chainid);
        console.log("  Computed Domain Separator:", vm.toString(computedDomainSeparator));
        console.log("  Domain Separator Match:", computedDomainSeparator == domainSeparator);
        
        bytes32 safeTxHashData = keccak256(
            abi.encode(
                SAFE_TX_TYPEHASH,
                address(registry),     // to
                uint256(0),           // value
                keccak256(callData),  // keccak256(data)
                uint8(Enum.Operation.Call), // operation
                uint256(0),           // safeTxGas
                uint256(0),           // baseGas
                uint256(0),           // gasPrice
                address(0),           // gasToken
                address(0),           // refundReceiver
                safe.nonce()          // nonce
            )
        );
        
        bytes32 computedSafeTxHash = keccak256(
            abi.encodePacked(bytes1(0x19), bytes1(0x01), domainSeparator, safeTxHashData)
        );
        
        console.log("  Computed Safe TX Hash:", vm.toString(computedSafeTxHash));
        console.log("  Safe TX Hash Match:", computedSafeTxHash == safeTxHash);
        
        // 6. Sign with 3 owners (owners 0, 1, 2)
        console.log("\n=== Signing ===");
        
        (uint8 v0, bytes32 r0, bytes32 s0) = vm.sign(ANVIL_KEY_0, safeTxHash);
        (uint8 v1, bytes32 r1, bytes32 s1) = vm.sign(ANVIL_KEY_1, safeTxHash);
        (uint8 v2, bytes32 r2, bytes32 s2) = vm.sign(ANVIL_KEY_2, safeTxHash);
        
        console.log("\nSignature 0 (owner", owner0, "):");
        console.log("  v:", v0);
        console.log("  r:", vm.toString(r0));
        console.log("  s:", vm.toString(s0));
        
        console.log("\nSignature 1 (owner", owner1, "):");
        console.log("  v:", v1);
        console.log("  r:", vm.toString(r1));
        console.log("  s:", vm.toString(s1));
        
        console.log("\nSignature 2 (owner", owner2, "):");
        console.log("  v:", v2);
        console.log("  r:", vm.toString(r2));
        console.log("  s:", vm.toString(s2));
        
        // 7. Verify signature recovery
        address recovered0 = ecrecover(safeTxHash, v0, r0, s0);
        address recovered1 = ecrecover(safeTxHash, v1, r1, s1);
        address recovered2 = ecrecover(safeTxHash, v2, r2, s2);
        
        console.log("\n=== Signature Recovery ===");
        console.log("Recovered 0:", recovered0, "Match:", recovered0 == owner0);
        console.log("Recovered 1:", recovered1, "Match:", recovered1 == owner1);
        console.log("Recovered 2:", recovered2, "Match:", recovered2 == owner2);
        
        // 8. Combine signatures (sorted by signer address)
        // Addresses in ascending order: owner2 < owner1 < owner0
        // 0x3C44C... < 0x70997... < 0xf39Fd...
        bytes memory signatures;
        
        if (owner2 < owner1 && owner1 < owner0) {
            // Order: 2, 1, 0
            signatures = abi.encodePacked(r2, s2, v2, r1, s1, v1, r0, s0, v0);
            console.log("\nSignature order: owner2, owner1, owner0");
        } else if (owner0 < owner1 && owner1 < owner2) {
            // Order: 0, 1, 2
            signatures = abi.encodePacked(r0, s0, v0, r1, s1, v1, r2, s2, v2);
            console.log("\nSignature order: owner0, owner1, owner2");
        } else {
            // Find correct order
            address[] memory signers = new address[](3);
            signers[0] = owner0;
            signers[1] = owner1;
            signers[2] = owner2;
            
            // Bubble sort
            for (uint i = 0; i < 2; i++) {
                for (uint j = 0; j < 2 - i; j++) {
                    if (signers[j] > signers[j + 1]) {
                        address temp = signers[j];
                        signers[j] = signers[j + 1];
                        signers[j + 1] = temp;
                    }
                }
            }
            
            console.log("\nSorted signer order:");
            console.log("  0:", signers[0]);
            console.log("  1:", signers[1]);
            console.log("  2:", signers[2]);
            
            // Build signatures in sorted order
            for (uint i = 0; i < 3; i++) {
                if (signers[i] == owner0) {
                    signatures = abi.encodePacked(signatures, r0, s0, v0);
                } else if (signers[i] == owner1) {
                    signatures = abi.encodePacked(signatures, r1, s1, v1);
                } else if (signers[i] == owner2) {
                    signatures = abi.encodePacked(signatures, r2, s2, v2);
                }
            }
        }
        
        console.log("\nCombined signatures length:", signatures.length, "(should be 195 = 3 * 65)");
        console.log("Signatures:", vm.toString(signatures));
        
        // 9. Execute transaction through Safe
        console.log("\n=== Executing Transaction ===");
        
        vm.prank(owner1); // Can be called by anyone
        bool success = safe.execTransaction(
            address(registry),    // to
            0,                    // value
            callData,             // data
            Enum.Operation.Call,  // operation
            0,                    // safeTxGas
            0,                    // baseGas
            0,                    // gasPrice
            address(0),           // gasToken
            payable(address(0)),  // refundReceiver
            signatures
        );
        
        console.log("\nExecution success:", success);
        
        if (success) {
            console.log("New Safe nonce:", safe.nonce());
            console.log("\n[PASS] Multi-sig transaction executed successfully!");
        } else {
            console.log("\n[FAIL] Transaction reverted");
            revert("execTransaction failed");
        }
    }
    
    function _generateTestAccumulator() internal pure returns (bytes memory) {
        // Generate 256 bytes of test data
        bytes memory acc = new bytes(256);
        for (uint i = 0; i < 256; i++) {
            acc[i] = bytes1(uint8(i));
        }
        return acc;
    }
}

// Minimal SafeProxy interface for createProxyWithNonce
interface SafeProxy {
    function masterCopy() external view returns (address);
}
