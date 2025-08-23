"""
Test Configuration and Fixtures

Provides fixtures for:
- Anvil blockchain with deployed contracts
- Gateway server with proper configuration
- RSA accumulator parameters and test data
"""

import asyncio
import json
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Generator, AsyncGenerator

import pytest
import httpx
from web3 import Web3


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def anvil_process(project_root: Path) -> Generator[subprocess.Popen, None, None]:
    """Start Anvil blockchain for testing."""
    print("\n🔧 Starting Anvil blockchain...")
    
    # Start Anvil with deterministic accounts
    anvil_cmd = [
        "anvil",
        "--port", "8545",
        "--accounts", "10",
        "--balance", "10000",
        "--gas-limit", "30000000",
        "--code-size-limit", "50000",
        "--chain-id", "31337",
        "--block-time", "1",  # 1 second blocks
    ]
    
    process = subprocess.Popen(
        anvil_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for Anvil to start
    max_wait = 10
    for i in range(max_wait):
        try:
            w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
            if w3.is_connected():
                print(f"   ✅ Anvil started (block: {w3.eth.block_number})")
                break
        except Exception:
            pass
        
        if i == max_wait - 1:
            process.terminate()
            raise RuntimeError("Anvil failed to start within 10 seconds")
        
        time.sleep(1)
    
    yield process
    
    # Cleanup
    print("🛑 Stopping Anvil...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


@pytest.fixture(scope="session")
def deployed_contract(project_root: Path, anvil_process) -> Dict[str, Any]:
    """Deploy smart contracts using Foundry and return deployment info."""
    print("\n📜 Deploying smart contracts...")
    
    contracts_dir = project_root / "contracts"
    
    # Change to contracts directory
    original_cwd = os.getcwd()
    os.chdir(contracts_dir)
    
    try:
        # Deploy using Foundry
        deploy_cmd = [
            "forge", "script", 
            "script/DeploySecureMultisig.s.sol:DeploySecureMultisig",
            "--rpc-url", "http://127.0.0.1:8545",
            "--private-key", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",  # Anvil default
            "--broadcast",
            "--via-ir"
        ]
        
        result = subprocess.run(
            deploy_cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"Deploy stderr: {result.stderr}")
            print(f"Deploy stdout: {result.stdout}")
            raise RuntimeError(f"Contract deployment failed: {result.stderr}")
        
        # Parse deployment output to extract contract address
        output_lines = result.stdout.split('\n')
        registry_address = None
        multisig_address = None
        
        for line in output_lines:
            if "AccumulatorRegistry deployed at:" in line:
                registry_address = line.split(":")[-1].strip()
            elif "Safe deployed at:" in line:
                multisig_address = line.split(":")[-1].strip()
        
        if not registry_address:
            # Try to find address in broadcast artifacts
            broadcast_dir = contracts_dir / "broadcast" / "DeploySecureMultisig.s.sol" / "31337"
            if broadcast_dir.exists():
                for file in broadcast_dir.glob("*.json"):
                    with open(file) as f:
                        data = json.load(f)
                        for tx in data.get("transactions", []):
                            if tx.get("contractName") == "AccumulatorRegistry":
                                registry_address = tx.get("contractAddress")
                                break
        
        if not registry_address:
            raise RuntimeError("Could not extract AccumulatorRegistry address from deployment")
        
        print(f"   ✅ AccumulatorRegistry: {registry_address}")
        if multisig_address:
            print(f"   ✅ Safe Multisig: {multisig_address}")
        
        return {
            "registry_address": registry_address,
            "multisig_address": multisig_address,
            "rpc_url": "http://127.0.0.1:8545"
        }
    
    finally:
        os.chdir(original_cwd)


@pytest.fixture(scope="session")
def gateway_process(project_root: Path, deployed_contract: Dict[str, Any]) -> Generator[subprocess.Popen, None, None]:
    """Start the gateway server with proper configuration."""
    print("\n🚀 Starting Gateway server...")
    
    gateway_dir = project_root / "gateway"
    
    # Environment variables for gateway
    env = os.environ.copy()
    env.update({
        "RPC_URL": deployed_contract["rpc_url"],
        "CONTRACT_ADDRESS": deployed_contract["registry_address"],
        "ADMIN_KEY": "test-admin-key-12345",
        "DATABASE_URL": "sqlite+aiosqlite:///./test_gateway.db",
        "LOG_LEVEL": "INFO"
    })
    
    # Start gateway server
    gateway_cmd = [
        gateway_dir / "venv" / "bin" / "python",
        "-m", "uvicorn", 
        "main:app",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--log-level", "warning"
    ]
    
    process = subprocess.Popen(
        gateway_cmd,
        cwd=gateway_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for gateway to start
    max_wait = 15
    for i in range(max_wait):
        try:
            async def check_health():
                async with httpx.AsyncClient() as client:
                    response = await client.get("http://127.0.0.1:8000/healthz", timeout=2)
                    return response.status_code == 200
            
            if asyncio.run(check_health()):
                print("   ✅ Gateway server started")
                break
        except Exception:
            pass
        
        if i == max_wait - 1:
            process.terminate()
            stdout, stderr = process.communicate(timeout=5)
            print(f"Gateway stdout: {stdout}")
            print(f"Gateway stderr: {stderr}")
            raise RuntimeError("Gateway failed to start within 15 seconds")
        
        time.sleep(1)
    
    yield process
    
    # Cleanup
    print("🛑 Stopping Gateway...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


@pytest.fixture(scope="session")
async def gateway_client(gateway_process) -> AsyncGenerator[httpx.AsyncClient, None]:
    """HTTP client configured for the gateway."""
    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8000",
        timeout=30.0
    ) as client:
        yield client


@pytest.fixture(scope="session")
def admin_headers() -> Dict[str, str]:
    """Headers with admin authentication."""
    return {
        "x-admin-key": "test-admin-key-12345",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="session")
def web3_client(deployed_contract: Dict[str, Any]) -> Web3:
    """Web3 client connected to Anvil."""
    w3 = Web3(Web3.HTTPProvider(deployed_contract["rpc_url"]))
    assert w3.is_connected(), "Failed to connect to Anvil"
    return w3


@pytest.fixture
def rsa_params() -> Dict[str, int]:
    """RSA parameters for testing (small for speed, insecure)."""
    # Using the toy example from the explanation
    return {
        "N": 209,  # 11 * 19
        "g": 4,    # 2^2 mod 209
        "p": 11,
        "q": 19
    }


@pytest.fixture
def device_primes() -> Dict[str, int]:
    """Pre-computed device primes for testing."""
    return {
        "device_001": 13,
        "device_002": 17,
        "device_003": 23,
        "device_004": 29,
        "device_005": 31
    }


@pytest.fixture
def timing_results() -> Dict[str, Any]:
    """Storage for timing and size measurements."""
    return {
        "operations": [],
        "payloads": [],
        "summary": {}
    }


def record_timing(timing_results: Dict[str, Any], operation: str, duration_ms: float, payload_size: int = 0):
    """Record timing and payload size data."""
    timing_results["operations"].append({
        "operation": operation,
        "duration_ms": duration_ms,
        "payload_size_bytes": payload_size
    })


def print_performance_report(timing_results: Dict[str, Any]):
    """Print detailed performance report."""
    print("\n" + "="*60)
    print("📊 PERFORMANCE REPORT")
    print("="*60)
    
    operations = timing_results["operations"]
    if not operations:
        print("No timing data recorded")
        return
    
    # Group by operation type
    by_operation = {}
    for op in operations:
        op_type = op["operation"]
        if op_type not in by_operation:
            by_operation[op_type] = []
        by_operation[op_type].append(op)
    
    # Print detailed results
    for op_type, ops in by_operation.items():
        durations = [op["duration_ms"] for op in ops]
        sizes = [op["payload_size_bytes"] for op in ops if op["payload_size_bytes"] > 0]
        
        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)
        
        print(f"\n🔹 {op_type.upper()}")
        print(f"   Count: {len(ops)}")
        print(f"   Duration: {avg_duration:.2f}ms avg ({min_duration:.2f}-{max_duration:.2f}ms)")
        
        if sizes:
            avg_size = sum(sizes) / len(sizes)
            print(f"   Payload: {avg_size:.0f} bytes avg")
    
    # Summary statistics
    total_duration = sum(op["duration_ms"] for op in operations)
    total_payload = sum(op["payload_size_bytes"] for op in operations)
    
    print(f"\n📈 SUMMARY")
    print(f"   Total operations: {len(operations)}")
    print(f"   Total duration: {total_duration:.2f}ms")
    print(f"   Total payload: {total_payload} bytes")
    print(f"   Avg per operation: {total_duration/len(operations):.2f}ms")
    
    print("="*60)
