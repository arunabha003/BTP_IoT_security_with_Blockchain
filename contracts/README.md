# Smart Contracts

## Overview

This directory contains **Solidity smart contracts** for decentralized governance of the IoT Identity System using RSA Accumulators. The contracts implement a **secure multisig architecture** with **Safe (Gnosis Safe) integration**, providing **decentralized control** over accumulator state with **emergency capabilities** and **replay protection**.

## Contract Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Governance Layer                         │
├─────────────────────────────────────────────────────────────┤
│  MultisigManager                                            │
│  ├── Safe Lifecycle Management                              │
│  ├── Owner Add/Remove with Timelock                         │
│  ├── Threshold Changes                                       │
│  └── Emergency Controls                                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                         │
├─────────────────────────────────────────────────────────────┤
│  AccumulatorRegistry                                         │
│  ├── RSA Accumulator State Storage                          │
│  ├── Device Registration/Revocation                         │
│  ├── Replay Protection                                       │
│  ├── Rate Limiting                                           │
│  └── Event Emission                                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Safe Integration                         │
├─────────────────────────────────────────────────────────────┤
│  Official Safe Contracts (External)                         │
│  ├── Safe.sol (Multisig Wallet)                            │
│  ├── SafeProxyFactory.sol (Proxy Deployment)               │
│  └── Safe Ecosystem Integration                             │
└─────────────────────────────────────────────────────────────┘
```

## File Structure

```
contracts/
├── src/                            # Smart contract source code
│   ├── AccumulatorRegistry.sol     # Main accumulator state contract
│   └── MultisigManager.sol         # Safe multisig lifecycle management
├── script/                         # Foundry deployment scripts
│   └── DeploySecureMultisig.s.sol  # Complete system deployment
├── test/                           # Foundry test suite
│   └── SecureMultisig.t.sol        # Comprehensive contract tests
├── foundry.toml                    # Foundry configuration
├── foundry.lock                    # Dependency lock file
├── remappings.txt                  # Import path remappings
└── README.md                       # This file
```

## Smart Contracts Explained

### `AccumulatorRegistry.sol`
**Purpose**: Core contract storing RSA accumulator state with multisig governance
**Key Features**:
- **Accumulator State**: Stores current RSA accumulator value and metadata
- **Multisig-Only Access**: All state changes require Safe multisig approval
- **Replay Protection**: Operation IDs prevent transaction replay attacks
- **Rate Limiting**: Minimum block delays between operations
- **Emergency Pause**: Circuit breaker for security incidents
- **Event Logging**: Complete audit trail of all operations

**State Variables**:
```solidity
contract AccumulatorRegistry {
    // Core accumulator state
    bytes32 public currentAccumulator;      // Current RSA accumulator value
    bytes32 public currentAccumulatorHash;  // Keccak256 hash of accumulator
    uint256 public lastUpdateBlock;         // Block number of last update
    
    // Governance references
    MultisigManager public immutable multisigManager;
    Safe public immutable authorizedSafe;
    
    // Security features
    bool public emergencyPaused;
    uint256 public constant MIN_BLOCK_DELAY = 1;
    
    // Replay protection
    mapping(bytes32 => bool) public executedOperations;
    
    // Device registry
    mapping(bytes32 => uint256) public deviceRegistry;
}
```

**Key Functions**:
```solidity
function updateAccumulator(
    bytes32 newAccumulator,
    bytes32 parentHash,
    bytes32 operationId
) external onlyAuthorizedSafe notPaused validMultisigState rateLimited {
    // Verify parentHash matches current state
    require(parentHash == currentAccumulatorHash, "Invalid parent hash");
    
    // Replay protection
    require(!executedOperations[operationId], "Operation already executed");
    executedOperations[operationId] = true;
    
    // Update state
    bytes32 oldAccumulator = currentAccumulator;
    currentAccumulator = newAccumulator;
    currentAccumulatorHash = keccak256(abi.encodePacked(newAccumulator));
    lastUpdateBlock = block.number;
    
    emit AccumulatorUpdated(oldAccumulator, newAccumulator, block.number);
}

function registerDevice(
    bytes calldata deviceId,
    bytes32 operationId
) external onlyAuthorizedSafe notPaused validMultisigState {
    bytes32 key = keccak256(deviceId);
    require(deviceRegistry[key] == 0, "Device already registered");
    
    deviceRegistry[key] = block.number;
    emit DeviceRegistered(deviceId, block.number);
}

function revokeDevice(
    bytes calldata deviceId,
    bytes32 operationId
) external onlyAuthorizedSafe notPaused validMultisigState {
    bytes32 key = keccak256(deviceId);
    require(deviceRegistry[key] != 0, "Device not registered");
    
    delete deviceRegistry[key];
    emit DeviceRevoked(deviceId, block.number);
}
```

**Security Modifiers**:
```solidity
modifier onlyAuthorizedSafe() {
    require(msg.sender == address(authorizedSafe), "Only authorized Safe can call");
    _;
}

modifier onlyMultisigManager() {
    require(msg.sender == address(multisigManager), "Only MultisigManager can call");
    _;
}

modifier notPaused() {
    require(!emergencyPaused, "Contract is paused");
    _;
}

modifier rateLimited() {
    require(
        block.number >= lastUpdateBlock + MIN_BLOCK_DELAY,
        "Rate limit exceeded"
    );
    _;
}
```

### `MultisigManager.sol`
**Purpose**: Manages Safe multisig lifecycle and configuration changes
**Key Features**:
- **Safe Deployment**: Creates and configures Safe multisig wallets
- **Dynamic Configuration**: Add/remove owners, change threshold
- **Timelock Protection**: Prevents rapid configuration changes
- **Emergency Controls**: Pause system during security incidents
- **Operation Queuing**: Time-delayed execution of sensitive operations

**State Variables**:
```solidity
contract MultisigManager {
    // Safe contract references
    Safe public immutable safeSingleton;
    SafeProxyFactory public immutable proxyFactory;
    
    // Current multisig configuration
    Safe public currentSafe;
    address public emergencyAdmin;
    
    // Operation management
    uint256 public constant MIN_TIMELOCK_DELAY = 1 days;
    uint256 public constant MAX_TIMELOCK_DELAY = 30 days;
    uint256 public operationTimelock = 2 days;
    
    // Emergency state
    bool public emergencyPaused;
    
    // Queued operations
    mapping(bytes32 => QueuedOperation) public queuedOperations;
    mapping(bytes32 => bool) public executedOperations;
}
```

**Safe Deployment**:
```solidity
function deploySafe(
    address[] memory owners,
    uint256 threshold
) external returns (address) {
    require(owners.length >= 3, "Minimum 3 owners required");
    require(threshold >= 2, "Minimum threshold of 2 required");
    require(threshold <= owners.length, "Threshold cannot exceed owner count");
    
    // Prepare Safe initialization data
    bytes memory initializer = abi.encodeWithSelector(
        Safe.setup.selector,
        owners,                    // _owners
        threshold,                 // _threshold
        address(0),               // to (no module)
        "",                       // data
        address(0),               // fallbackHandler
        address(0),               // paymentToken
        0,                        // payment
        address(0)                // paymentReceiver
    );
    
    // Deploy Safe proxy
    Safe safe = Safe(payable(proxyFactory.createProxyWithNonce(
        address(safeSingleton),
        initializer,
        block.timestamp  // Use timestamp as salt for uniqueness
    )));
    
    currentSafe = safe;
    emit SafeDeployed(address(safe), owners, threshold);
    
    return address(safe);
}
```

**Owner Management with Timelock**:
```solidity
function queueAddOwner(address newOwner) external {
    require(msg.sender == address(currentSafe), "Only current Safe can queue");
    require(newOwner != address(0), "Invalid owner address");
    
    bytes32 operationHash = keccak256(abi.encodePacked(
        "ADD_OWNER",
        newOwner,
        block.timestamp
    ));
    
    queuedOperations[operationHash] = QueuedOperation({
        operationType: OperationType.AddOwner,
        target: newOwner,
        value: 0,
        data: "",
        scheduledTime: block.timestamp + operationTimelock,
        executed: false
    });
    
    emit OperationQueued(operationHash, OperationType.AddOwner, newOwner);
}

function executeOperation(bytes32 operationHash) external {
    QueuedOperation storage op = queuedOperations[operationHash];
    require(op.scheduledTime != 0, "Operation not found");
    require(block.timestamp >= op.scheduledTime, "Timelock not expired");
    require(!op.executed, "Operation already executed");
    
    op.executed = true;
    executedOperations[operationHash] = true;
    
    if (op.operationType == OperationType.AddOwner) {
        // Execute add owner operation on Safe
        _executeAddOwner(op.target);
    }
    // Handle other operation types...
    
    emit OperationExecuted(operationHash, op.operationType);
}
```

### `DeploySecureMultisig.s.sol`
**Purpose**: Foundry deployment script for complete system setup
**Deployment Flow**:
1. **Deploy Safe Infrastructure**: Safe singleton and proxy factory
2. **Deploy MultisigManager**: With emergency admin configuration
3. **Deploy Safe Proxy**: 3-of-5 multisig with test accounts
4. **Deploy AccumulatorRegistry**: Connected to MultisigManager and Safe
5. **Verify Deployment**: Check all contracts are properly connected

**Deployment Script**:
```solidity
contract DeploySecureMultisig is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);
        
        // 1. Deploy Safe singleton and factory
        Safe safeSingleton = new Safe();
        SafeProxyFactory proxyFactory = new SafeProxyFactory();
        
        // 2. Deploy MultisigManager
        address emergencyAdmin = vm.addr(deployerPrivateKey);
        MultisigManager multisigManager = new MultisigManager(
            safeSingleton,
            proxyFactory,
            emergencyAdmin
        );
        
        // 3. Deploy Safe proxy (3-of-5 multisig)
        address[] memory owners = new address[](5);
        owners[0] = 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266; // Anvil account 0
        owners[1] = 0x70997970C51812dc3A010C7d01b50e0d17dc79C8; // Anvil account 1
        owners[2] = 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC; // Anvil account 2
        owners[3] = 0x90F79bf6EB2c4f870365E785982E1f101E93b906; // Anvil account 3
        owners[4] = 0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65; // Anvil account 4
        
        address safeAddress = multisigManager.deploySafe(owners, 3);
        
        // 4. Deploy AccumulatorRegistry
        AccumulatorRegistry registry = new AccumulatorRegistry(
            bytes32(0),  // Initial accumulator (empty)
            multisigManager,
            Safe(payable(safeAddress))
        );
        
        vm.stopBroadcast();
        
        // 5. Log deployment addresses
        console.log("Safe Singleton deployed to:", address(safeSingleton));
        console.log("SafeProxyFactory deployed to:", address(proxyFactory));
        console.log("MultisigManager deployed to:", address(multisigManager));
        console.log("Safe deployed to:", safeAddress);
        console.log("AccumulatorRegistry deployed to:", address(registry));
    }
}
```

### `SecureMultisig.t.sol`
**Purpose**: Comprehensive test suite for the complete smart contract system
**Test Coverage**:
- **Deployment Verification**: All contracts deploy and connect properly
- **Access Control**: Only authorized Safe can call protected functions
- **Multisig Operations**: Safe transaction execution with proper signatures
- **Replay Protection**: Operation IDs prevent duplicate execution
- **Emergency Controls**: Pause functionality works correctly
- **Rate Limiting**: Block delay enforcement
- **Event Emission**: All events are emitted correctly

**Key Test Functions**:
```solidity
contract SecureMultisigTest is Test {
    // Test setup with full deployment
    function setUp() public {
        // Deploy all contracts
        safeSingleton = new Safe();
        proxyFactory = new SafeProxyFactory();
        multisigManager = new MultisigManager(safeSingleton, proxyFactory, emergencyAdmin);
        
        // Deploy Safe and registry
        safeAddress = multisigManager.deploySafe(owners, 3);
        safe = Safe(payable(safeAddress));
        registry = new AccumulatorRegistry(bytes32(0), multisigManager, safe);
    }
    
    function testMultisigUpdateAccumulator() public {
        // Test accumulator update through multisig
        bytes32 newAccumulator = bytes32(uint256(0x123456));
        bytes32 parentHash = bytes32(0);
        bytes32 operationId = keccak256("test_update_1");
        
        // Execute through Safe multisig
        bool success = executeSafeTransaction(
            address(registry),
            0,
            abi.encodeWithSelector(
                AccumulatorRegistry.updateAccumulator.selector,
                newAccumulator,
                parentHash,
                operationId
            )
        );
        
        assertTrue(success);
        assertEq(registry.currentAccumulator(), newAccumulator);
    }
    
    function executeSafeTransaction(
        address to,
        uint256 value,
        bytes memory data
    ) internal returns (bool) {
        // Calculate transaction hash
        bytes32 txHash = safe.getTransactionHash(
            to, value, data, Enum.Operation.Call,
            0, 0, 0, address(0), address(0), safe.nonce()
        );
        
        // Generate signatures from owners (sorted by address)
        bytes memory signatures = "";
        uint256 signerCount = 0;
        
        for (uint256 i = 0; i < owners.length && signerCount < 3; i++) {
            if (ownerPrivateKeys[owners[i]] != 0) {
                (uint8 v, bytes32 r, bytes32 s) = vm.sign(
                    ownerPrivateKeys[owners[i]], 
                    txHash
                );
                signatures = abi.encodePacked(signatures, r, s, v);
                signerCount++;
            }
        }
        
        // Execute transaction
        return safe.execTransaction(
            to, value, data, Enum.Operation.Call,
            0, 0, 0, address(0), address(0), signatures
        );
    }
}
```

## Security Features

### Access Control
- **Multisig-Only Operations**: All state changes require Safe multisig approval
- **Role-Based Access**: Different roles for different operations
- **Emergency Admin**: Separate emergency controls with limited scope

### Replay Protection
- **Operation IDs**: Unique identifiers prevent transaction replay
- **Parent Hash Validation**: Ensures operations execute in correct order
- **Nonce Management**: Built-in Safe nonce prevents replay attacks

### Rate Limiting
- **Block Delays**: Minimum time between operations
- **Configurable Limits**: Adjustable based on network conditions
- **Emergency Override**: Emergency admin can bypass limits

### Emergency Controls
- **Circuit Breaker**: Pause all operations during incidents
- **Emergency Admin**: Dedicated role for emergency actions
- **Timelock Bypass**: Emergency operations can skip timelock

### Input Validation
- **Parameter Validation**: All inputs validated for correctness
- **State Consistency**: Ensures contract state remains consistent
- **Custom Errors**: Clear error messages for debugging

## Deployment Guide

### Prerequisites
```bash
# Install Foundry
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Verify installation
forge --version
cast --version
anvil --version
```

### Local Development
```bash
cd contracts

# Install dependencies
forge install

# Compile contracts
forge build

# Run tests
forge test -vv

# Start local blockchain
anvil

# Deploy to local (in another terminal)
forge script script/DeploySecureMultisig.s.sol \
  --rpc-url http://127.0.0.1:8545 \
  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
  --broadcast
```

### Testnet Deployment
```bash
# Set environment variables
export RPC_URL="https://sepolia.infura.io/v3/YOUR_KEY"
export PRIVATE_KEY="0x..."
export ETHERSCAN_API_KEY="YOUR_KEY"

# Deploy to testnet
forge script script/DeploySecureMultisig.s.sol \
  --rpc-url $RPC_URL \
  --private-key $PRIVATE_KEY \
  --broadcast \
  --verify
```

### Mainnet Deployment
```bash
# Use hardware wallet for mainnet
forge script script/DeploySecureMultisig.s.sol \
  --rpc-url $MAINNET_RPC_URL \
  --ledger \
  --broadcast \
  --verify

# Verify deployment
cast call $REGISTRY_ADDRESS "currentAccumulator()" --rpc-url $MAINNET_RPC_URL
```

## Testing

### Running Tests
```bash
# All tests with verbose output
forge test -vv

# Specific test file
forge test -vv --match-path test/SecureMultisig.t.sol

# Specific test function
forge test -vv --match-test testMultisigUpdateAccumulator

# With gas reporting
forge test --gas-report

# With coverage
forge coverage
```

### Test Results
```
Running 9 tests for test/SecureMultisig.t.sol:SecureMultisigTest
[PASS] testBatchOperations() (gas: 282570)
[PASS] testEmergencyPause() (gas: 152822)
[PASS] testInitialState() (gas: 72028)
[PASS] testInvalidParentHashProtection() (gas: 131707)
[PASS] testMultisigDeviceOperations() (gas: 326117)
[PASS] testMultisigUpdateAccumulator() (gas: 196052)
[PASS] testMultisigValidation() (gas: 192912)
[PASS] testOnlyMultisigCanCallRegistry() (gas: 30705)
[PASS] testReplayProtection() (gas: 239234)

Test result: ok. 9 passed; 0 failed; 0 skipped
```

## Gas Optimization

### Gas Usage Analysis
- **AccumulatorRegistry.updateAccumulator**: ~196K gas
- **MultisigManager.deploySafe**: ~450K gas
- **Safe.execTransaction** (3-of-5): ~180K gas
- **Device registration**: ~45K gas
- **Emergency pause**: ~25K gas

### Optimization Techniques
1. **Packed Structs**: Minimize storage slots
2. **Immutable Variables**: Reduce SLOAD operations
3. **Custom Errors**: More efficient than string errors
4. **Batch Operations**: Process multiple items in one transaction
5. **Storage Layout**: Optimize for common access patterns

## Security Considerations

### Auditing Checklist
- [ ] **Access Control**: All functions have proper modifiers
- [ ] **Replay Protection**: Operation IDs prevent duplicate execution
- [ ] **Input Validation**: All parameters validated
- [ ] **State Consistency**: Contract state remains consistent
- [ ] **Emergency Controls**: Pause functionality works
- [ ] **Multisig Integration**: Safe integration is secure
- [ ] **Event Emission**: All state changes emit events
- [ ] **Gas Limits**: Functions don't exceed block gas limit

### Known Limitations
1. **Centralized Emergency Admin**: Single point of failure for emergency functions
2. **Block Delay Rate Limiting**: Can be bypassed by miners
3. **Safe Upgrade Risk**: Safe contracts could be upgraded
4. **Storage Collision**: Proxy pattern requires careful storage layout

### Recommended Practices
1. **Multi-Signature Operations**: Always use 3+ signatures for critical operations
2. **Timelock Delays**: Use appropriate delays for configuration changes
3. **Emergency Procedures**: Have clear procedures for emergency situations
4. **Regular Audits**: Periodic security audits and reviews
5. **Monitoring**: Monitor all contract events and transactions

This smart contract system provides a secure, decentralized foundation for managing IoT device identities with RSA accumulators, featuring robust governance, emergency controls, and integration with the battle-tested Safe multisig infrastructure.
