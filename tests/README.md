# System Integration Tests

## Overview

This directory contains **comprehensive system integration tests** that verify the complete IoT Identity System working end-to-end. These tests orchestrate all components together: smart contracts on Anvil blockchain, FastAPI gateway service, RSA accumulator mathematics, and database operations.

## Test Architecture

```
System Under Test:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Anvil Chain   │    │    Gateway      │    │ RSA Accumulator │
│                 │    │                 │    │                 │
│ • Smart Contract│◄──►│ • FastAPI API   │◄──►│ • Mathematics   │
│ • Event Logs    │    │ • Database      │    │ • Cryptography  │
│ • Multisig      │    │ • Middleware    │    │ • Witness Mgmt  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                        ▲                        ▲
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                          ┌───────▼───────┐
                          │  Integration  │
                          │     Tests     │
                          └───────────────┘
```

## File Structure

```
tests/
├── conftest.py                     # Pytest fixtures and test infrastructure
├── test_auth_flow.py              # Complete authentication flow testing
├── test_end_to_end_system.py      # Comprehensive system integration
├── test_minimal_integration.py    # Minimal integration with performance
├── test_rsa_math.py               # RSA accumulator mathematics
├── test_simple.py                 # Basic component verification
├── run_tests.py                   # Test runner with reporting
├── requirements.txt               # Test-specific dependencies
├── __init__.py                    # Package marker
└── README.md                      # This file
```

## Core Test Files Explained

### `conftest.py`
**Purpose**: Central test configuration and fixture management for system integration
**Key Fixtures**:
- **`anvil_chain`**: Starts local Anvil blockchain with deterministic accounts
- **`deployed_contract_address`**: Deploys smart contracts using Foundry
- **`gateway_server`**: Starts FastAPI gateway with proper configuration
- **`accumulator_registry_contract`**: Provides Web3 contract instance
- **`admin_account`**: Test account for admin operations

**Infrastructure Management**:
```python
@pytest.fixture(scope="session")
def anvil_chain():
    """Starts Anvil blockchain and yields RPC URL."""
    process = subprocess.Popen(["anvil", "--silent"])
    # Wait for startup and verify connectivity
    yield "http://127.0.0.1:8545"
    # Cleanup process

@pytest.fixture(scope="session") 
def deployed_contract_address(anvil_chain):
    """Deploys contracts using forge script and returns address."""
    deploy_command = [
        "forge", "script", "script/DeploySecureMultisig.s.sol",
        "--rpc-url", anvil_chain,
        "--private-key", DEPLOYER_PRIVATE_KEY,
        "--broadcast"
    ]
    # Parse deployment output for contract address
    return contract_address

@pytest.fixture(scope="session")
def gateway_server(anvil_chain, deployed_contract_address):
    """Starts FastAPI gateway server with test configuration."""
    env = {
        "RPC_URL": anvil_chain,
        "CONTRACT_ADDRESS": deployed_contract_address,
        "ADMIN_KEY": "test-admin-key",
        "DATABASE_URL": "sqlite+aiosqlite:///./test_gateway.db"
    }
    # Start uvicorn process with test environment
    yield "http://127.0.0.1:8000"
    # Cleanup process and database
```

**Key Features**:
- **Session-scoped fixtures**: Shared infrastructure across all tests
- **Proper cleanup**: Processes and resources cleaned up after tests
- **Error handling**: Robust startup verification and timeout handling
- **Isolated environment**: Test database and configuration

### `test_end_to_end_system.py`
**Purpose**: Comprehensive system integration testing covering all major workflows
**Test Categories**:
- **System Health**: Connectivity and component status verification
- **Accumulator Management**: State synchronization and consistency
- **Device Lifecycle**: Complete enrollment → authentication → revocation
- **Performance**: Response times and concurrent request handling
- **Security**: Authentication, rate limiting, input validation
- **Error Handling**: Proper error responses and recovery

**Key Test Methods**:
```python
def test_system_health_and_connectivity(self, anvil_chain, gateway_server):
    """Verify all components are healthy and connected."""
    # Test gateway health endpoint
    # Verify database connectivity
    # Check blockchain connection
    # Validate contract loading

def test_device_enrollment_complete_flow(self, gateway_server):
    """Test complete device enrollment with validation."""
    # Generate Ed25519 keypair
    # Submit enrollment request
    # Verify accumulator update
    # Check database persistence
    # Measure performance

def test_authentication_flow_complete(self, gateway_server):
    """Test complete authentication flow."""
    # Start auth session (get nonce)
    # Sign nonce with device key
    # Submit verification request
    # Validate RSA membership proof
    # Check witness refresh

def test_system_performance_characteristics(self, gateway_server):
    """Measure system performance and scalability."""
    # Test endpoint response times
    # Concurrent request handling
    # Rate limiting behavior
    # Resource utilization
```

**Comprehensive Integration Test**:
```python
def test_system_integration_comprehensive(self, anvil_chain, gateway_server, accumulator_registry_contract):
    """Master integration test running all components."""
    test_results = {
        'health_check': False,
        'accumulator_state': False, 
        'device_enrollment': False,
        'authentication': False,
        'revocation': False,
        'performance': {},
        'security': False,
        'error_handling': False
    }
    
    # Run all test components and collect results
    # Generate comprehensive report
    # Assert core functionality requirements
    return test_results
```

### `test_auth_flow.py`
**Purpose**: Focused testing of the complete authentication workflow
**Test Scenario**:
1. **Ed25519 Keypair Generation**: Create cryptographically secure device keys
2. **Device Enrollment**: Register device with RSA accumulator
3. **Authentication Challenge**: Request nonce from gateway
4. **Signature Generation**: Sign nonce with device private key
5. **Proof Verification**: Submit Ed25519 signature + RSA membership proof
6. **Device Revocation**: Remove device from accumulator
7. **Revocation Verification**: Confirm revoked device fails authentication

**Key Features**:
```python
@pytest.fixture(scope="module")
def device_keypair():
    """Generate Ed25519 keypair for testing."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    # Return keys in multiple formats for testing

def test_end_to_end_auth_flow(gateway_server, device_keypair):
    """Complete authentication flow test."""
    # 1. Enroll device
    enroll_payload = {
        "device_id": device_id,
        "pubkey_pem": device_keypair["public_pem"].decode('utf-8')
    }
    response = requests.post(f"{base_url}/enroll", json=enroll_payload, headers=admin_headers)
    
    # 2. Start auth session
    response = requests.get(f"{base_url}/auth/start?device_id={device_id}")
    nonce = response.json()['nonce']
    
    # 3. Sign nonce and verify
    signature = device_keypair["private_key"].sign(nonce_bytes)
    verify_payload = {
        "device_id": device_id,
        "p_hex": p_hex,
        "witness_hex": witness_hex,
        "signature_base64": Web3.to_hex(signature),
        "nonce": nonce
    }
    response = requests.post(f"{base_url}/auth/verify", json=verify_payload)
    assert response.json()['ok'] is True
    
    # 4. Revoke and verify failure
    # ...
```

### `test_rsa_math.py`
**Purpose**: Verification of RSA accumulator mathematical correctness
**Mathematical Properties Tested**:
- **Accumulator Construction**: A = g^(∏ primes) mod N
- **Membership Witnesses**: w = g^(∏ other_primes) mod N  
- **Verification Equation**: w^p ≡ A (mod N)
- **Incremental Updates**: A' = A^p mod N
- **Order Independence**: Different enrollment orders → same result
- **Witness Refresh**: Correct witness updates on accumulator changes

**Test Structure**:
```python
def test_rsa_accumulator_math_walkthrough(toy_rsa_params, toy_device_primes):
    """Step-by-step verification of RSA accumulator math."""
    N, g = toy_rsa_params  # N=209, g=4
    
    # Test exact values from protocol specification
    A0 = 4
    A1 = pow(A0, 13, N)  # Should equal 9
    assert A1 == 9
    
    A2 = pow(A1, 17, N)  # Should equal 169  
    assert A2 == 169
    
    # Test witness generation and verification
    w13 = pow(g, 17 * 23, N)  # Witness for prime 13
    assert pow(w13, 13, N) == A_final
    
    # Test all mathematical properties
```

### `test_minimal_integration.py`
**Purpose**: Lightweight integration test with performance measurement
**Key Features**:
- **Self-contained**: No external dependencies (Anvil, Gateway)
- **Performance focused**: Detailed timing measurements
- **Mathematical verification**: Step-by-step accumulator operations
- **Complete workflow**: Device enrollment → authentication → revocation

**Performance Measurement**:
```python
def test_complete_auth_flow():
    """Test complete flow with performance measurement."""
    timings = {
        "enrollment": [],
        "authentication": [],
        "revocation": [],
        "signature_verification": []
    }
    
    # Measure each operation
    start_time = time.time()
    # ... perform operation
    operation_time = (time.time() - start_time) * 1000
    timings["operation"].append(operation_time)
    
    # Generate performance report
    print("📊 PERFORMANCE REPORT")
    for operation, times in timings.items():
        avg_time = sum(times) / len(times)
        print(f"{operation}: {avg_time:.2f}ms avg")
```

### `test_simple.py`
**Purpose**: Basic component verification and smoke tests
**Component Tests**:
- **Anvil startup**: Blockchain starts and responds
- **Foundry tools**: forge, cast, anvil commands work
- **Gateway imports**: FastAPI app can be imported
- **RSA math**: Basic modular exponentiation works

### `run_tests.py`
**Purpose**: Test runner with comprehensive reporting and orchestration
**Features**:
- **Test discovery**: Automatically finds and runs all tests
- **Performance reporting**: Detailed timing and resource usage
- **Error collection**: Comprehensive error reporting
- **Environment setup**: Automatic dependency checking
- **CI/CD integration**: Machine-readable output formats

## Test Execution

### Prerequisites
```bash
# Install test dependencies
cd tests
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt setuptools

# Ensure Foundry is available
forge --version
anvil --version

# Ensure gateway dependencies are installed
cd ../gateway
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Ensure accum package is available
cd ../accum
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

### Running Tests

**All integration tests**:
```bash
cd tests
source venv/bin/activate
pytest -v -s
```

**Specific test files**:
```bash
# Comprehensive system integration
pytest test_end_to_end_system.py -v -s

# Authentication flow only
pytest test_auth_flow.py -v -s

# Mathematical verification
pytest test_rsa_math.py -v -s

# Performance testing
pytest test_minimal_integration.py -v -s
```

**Test runner with reporting**:
```bash
python run_tests.py
```

**With coverage reporting**:
```bash
pytest --cov=gateway --cov=accum tests/ --cov-report=html
```

### Test Output Example

```
🧪 System Integration Tests
=============================

🏥 Testing System Health...
   ✅ Gateway: iot-identity-gateway v1.0.0
   ✅ Database: healthy
   ✅ Blockchain: connected
   ✅ Contract: Loaded

📱 Testing Complete Device Enrollment Flow...
   ✅ Device enrolled successfully in 0.156s
      Device ID: system_test_device_001
      Prime: 0xabc123...
      New Root: 0xdef456...
   ✅ Accumulator updated: 1 active devices

🔐 Testing Authentication Flow...
   ✅ Auth session started in 0.003s
   ✅ Authentication verified in 0.012s
      Result: SUCCESS

🚫 Testing Device Revocation Flow...
   ✅ Device revoked successfully in 0.089s
   ✅ Revoked device correctly rejected

⚡ Testing System Performance...
   📊 /healthz: 2.34ms avg (1.89-3.45ms)
   📊 /accumulator: 5.67ms avg (4.23-7.89ms)

🔒 Testing System Security...
   ✅ Admin endpoint properly protected
   ✅ Rate limiting active
   ✅ Security headers present: 4/4

🎯 COMPREHENSIVE SYSTEM TEST SUMMARY
====================================
✅ Health Check: PASS
✅ Device Enrollment: PASS  
✅ Authentication: PASS
✅ Device Revocation: PASS
✅ Security Features: PASS
⚡ Average Response Time: 3.45ms

🏆 OVERALL RESULT: 7/7 tests passed
🎉 ALL SYSTEM INTEGRATION TESTS PASSED!
```

## Test Configuration

### Environment Variables
```bash
# Test configuration
RPC_URL=http://127.0.0.1:8545
CONTRACT_ADDRESS=0x1234...  # Set by deployment fixture
ADMIN_KEY=test-admin-key
DATABASE_URL=sqlite+aiosqlite:///./test_gateway.db
LOG_LEVEL=DEBUG

# Performance tuning
ANVIL_ACCOUNTS=10
ANVIL_BALANCE=10000
GATEWAY_PORT=8000
TEST_TIMEOUT=120
```

### Pytest Configuration
```ini
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --color=yes
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

## Performance Benchmarks

**Expected Performance** (on MacBook Pro M1):
- **Health Check**: < 5ms
- **Authentication**: < 20ms  
- **Enrollment**: < 100ms (including blockchain tx)
- **Revocation**: < 150ms (including recomputation)
- **Concurrent Requests**: 95%+ success rate with 20 parallel requests

**Resource Usage**:
- **Memory**: ~200MB for full test suite
- **Disk**: ~50MB for test databases and logs
- **Network**: Local only (Anvil + Gateway)
- **CPU**: Moderate during RSA operations

## Troubleshooting

### Common Issues

**Anvil not starting**:
```bash
# Check Foundry installation
forge --version
anvil --version

# Try manual start
anvil --port 8545 --accounts 10
```

**Gateway connection failed**:
```bash
# Check dependencies
cd gateway
source venv/bin/activate
pip install -r requirements.txt

# Check configuration
echo $RPC_URL
echo $CONTRACT_ADDRESS
```

**Contract deployment failed**:
```bash
# Check contracts compile
cd contracts
forge build

# Test deployment manually
forge script script/DeploySecureMultisig.s.sol --rpc-url http://127.0.0.1:8545
```

**Test timeouts**:
```bash
# Increase timeout
pytest --timeout=300 test_end_to_end_system.py

# Run with more verbose output
pytest -v -s --capture=no test_end_to_end_system.py
```

### Debug Mode
```bash
# Run with debug logging
LOG_LEVEL=DEBUG pytest test_end_to_end_system.py -v -s

# Keep test environment running
pytest --pdb test_end_to_end_system.py

# Manual testing
python -c "
import requests
print(requests.get('http://127.0.0.1:8000/healthz').json())
"
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: System Integration Tests
on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install Foundry
        uses: foundry-rs/foundry-toolchain@v1
      
      - name: Run Integration Tests
        run: |
          cd tests
          python -m venv venv
          source venv/bin/activate
          pip install -r requirements.txt
          pytest test_end_to_end_system.py -v --junitxml=results.xml
      
      - name: Upload Test Results
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: tests/results.xml
```

This comprehensive integration test suite ensures that the complete IoT Identity System works correctly across all components, providing confidence for production deployment and ongoing development.
