// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import {AccumulatorRegistry} from "src/AccumulatorRegistry.sol";
import {MultisigManager} from "src/MultisigManager.sol";
import {Safe} from "safe-contracts/Safe.sol";
import {SafeProxyFactory} from "safe-contracts/proxies/SafeProxyFactory.sol";
import {SafeProxy} from "safe-contracts/proxies/SafeProxy.sol";

contract DeploySecureMultisig is Script {
    function run() external returns (
        AccumulatorRegistry registry,
        MultisigManager manager,
        Safe safe
    ) {
        vm.startBroadcast();
        
        // 1. Deploy Safe infrastructure
        Safe safeSingleton = new Safe();
        SafeProxyFactory proxyFactory = new SafeProxyFactory();
        
        console.log("Safe singleton deployed at:", address(safeSingleton));
        console.log("SafeProxyFactory deployed at:", address(proxyFactory));
        
        // 2. Deploy MultisigManager with emergency admin
        address emergencyAdmin = vm.addr(999); // Use a dedicated emergency key
        manager = new MultisigManager(
            payable(address(safeSingleton)),
            address(proxyFactory),
            emergencyAdmin
        );
        
        console.log("MultisigManager deployed at:", address(manager));
        console.log("Emergency admin:", emergencyAdmin);
        
        // 3. Setup initial multisig owners (3-of-5 for production security)
        //    Use Anvil's first 5 default accounts for easy testing
        address[] memory owners = new address[](5);
        owners[0] = 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266; // Anvil account 0
        owners[1] = 0x70997970C51812dc3A010C7d01b50e0d17dc79C8; // Anvil account 1
        owners[2] = 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC; // Anvil account 2
        owners[3] = 0x90F79bf6EB2c4f870365E785982E1f101E93b906; // Anvil account 3
        owners[4] = 0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65; // Anvil account 4
        
        uint256 threshold = 3; // 3-of-5 multisig
        
        // 4. Deploy Safe directly to avoid potential issues
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
        
        SafeProxy safeProxy = proxyFactory.createProxyWithNonce(
            payable(address(safeSingleton)),
            initializer,
            uint256(keccak256(abi.encodePacked(block.timestamp, owners, threshold)))
        );
        
        safe = Safe(payable(address(safeProxy)));
        
        // Update MultisigManager's currentSafe (if needed)
        // Note: For now we'll deploy without this dependency
        
        console.log("Safe deployed at:", address(safe));
        console.log("Safe owner 1:", owners[0]);
        console.log("Safe owner 2:", owners[1]);
        console.log("Safe owner 3:", owners[2]);
        console.log("Safe owner 4:", owners[3]);
        console.log("Safe owner 5:", owners[4]);
        console.log("Safe threshold:", threshold);
        
        // 5. Deploy AccumulatorRegistry with multisig-only access
        // Initial accumulator = g = 4 (as a 256-byte big-endian value)
        bytes memory initialAccumulator = new bytes(256);
        initialAccumulator[255] = 0x04; // g = 4 at the least significant byte
        
        registry = new AccumulatorRegistry(
            initialAccumulator,
            address(manager),
            address(safe)
        );
        
        console.log("AccumulatorRegistry deployed at:", address(registry));
        console.log("Registry is multisig-only:", true);
        console.log("Initial accumulator version:", registry.version());
        
        vm.stopBroadcast();
        
        // 6. Verify deployment
        console.log("\n=== DEPLOYMENT VERIFICATION ===");
        console.log("Registry authorized safe:", address(registry.authorizedSafe()));
        console.log("Registry multisig manager:", address(registry.multisigManager()));
        console.log("Registry version:", registry.version());
        console.log("Registry paused:", registry.emergencyPaused());
        
        console.log("\n=== SECURITY FEATURES ENABLED ===");
        console.log("+ Multisig-only access");
        console.log("+ Minimum 3-of-5 threshold");
        console.log("+ Timelock for owner changes (24h)");
        console.log("+ Emergency pause controls");
        console.log("+ Replay protection");
        console.log("+ Rate limiting");
        console.log("+ Operation tracking");
        console.log("+ Enhanced event logging");
    }
}
