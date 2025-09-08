// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "forge-std/Script.sol";
import "forge-std/console.sol";
import "../src/RegistryMock.sol";

/**
 * @title DeployRegistryMock
 * @dev Deployment script for RegistryMock contract on Anvil
 * 
 * Usage:
 *   forge script script/DeployRegistryMock.s.sol --broadcast --rpc-url $RPC_URL --private-key $PRIVATE_KEY_ADMIN
 */
contract DeployRegistryMock is Script {
    // Initial accumulator value (256 bytes, big-endian)
    // This represents g where g=4 from params.json
    // 4 encoded as 256-byte big-endian number
    bytes constant INITIAL_ACCUMULATOR = 
        hex"0000000000000000000000000000000000000000000000000000000000000000"
        hex"0000000000000000000000000000000000000000000000000000000000000000"
        hex"0000000000000000000000000000000000000000000000000000000000000000"
        hex"0000000000000000000000000000000000000000000000000000000000000000"
        hex"0000000000000000000000000000000000000000000000000000000000000000"
        hex"0000000000000000000000000000000000000000000000000000000000000000"
        hex"0000000000000000000000000000000000000000000000000000000000000000"
        hex"0000000000000000000000000000000000000000000000000000000000000004";
    
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY_ADMIN");
        
        console.log("=== Deploying RegistryMock ===");
        console.log("Deployer:", vm.addr(deployerPrivateKey));
        console.log("Chain ID:", block.chainid);
        console.log("Block number:", block.number);
        
        // Validate initial accumulator
        require(INITIAL_ACCUMULATOR.length == 256, "Initial accumulator must be 256 bytes");
        console.log("Initial accumulator length:", INITIAL_ACCUMULATOR.length);
        
        vm.startBroadcast(deployerPrivateKey);
        
        // Deploy RegistryMock with initial accumulator
        RegistryMock registry = new RegistryMock(INITIAL_ACCUMULATOR);
        
        vm.stopBroadcast();
        
        // Verify deployment
        (bytes memory accumulator, bytes32 hash, uint256 version) = registry.getCurrentState();
        
        console.log("=== Deployment Successful ===");
        console.log("RegistryMock address:", address(registry));
        console.log("Owner:", registry.owner());
        console.log("Initial version:", version);
        console.log("Initial accumulator hash:", vm.toString(hash));
        console.log("Accumulator length:", accumulator.length);
        
        console.log("\n=== Copy this to your .env file ===");
        console.log("REGISTRY_ADDRESS=%s", address(registry));
        console.log("Owner=%s", registry.owner());
        console.log("Version=%s", version);
        console.log("Hash=%s", vm.toString(hash));
    }
}
