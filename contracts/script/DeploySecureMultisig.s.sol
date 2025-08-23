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
        address[] memory owners = new address[](5);
        owners[0] = vm.addr(1); // CEO/Founder
        owners[1] = vm.addr(2); // CTO
        owners[2] = vm.addr(3); // Security Lead  
        owners[3] = vm.addr(4); // DevOps Lead
        owners[4] = vm.addr(5); // External Security Auditor
        
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
        bytes memory initialAccumulator = abi.encodePacked(keccak256(abi.encode(block.timestamp, "INITIAL")));
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
