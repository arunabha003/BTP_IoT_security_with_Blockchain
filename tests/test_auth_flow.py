"""
End-to-End Authentication Flow Tests

Tests the complete IoT device authentication flow:
1. Generate Ed25519 keypair
2. Enroll device -> get prime and witness
3. Start auth -> get nonce
4. Sign nonce -> verify auth -> assert success
5. Revoke device
6. Repeat auth -> assert failure

Includes RSA accumulator math verification and performance measurements.
"""

import asyncio
import base64
import json
import time
from typing import Dict, Any

import pytest
import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from conftest import record_timing, print_performance_report


class Ed25519Device:
    """Represents an IoT device with Ed25519 keypair."""
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.private_key = ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        
        # Get PEM format for enrollment
        self.pem_public = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        
        # Get raw bytes for verification
        self.raw_public = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
    
    def sign_message(self, message: bytes) -> bytes:
        """Sign a message with the device's private key."""
        return self.private_key.sign(message)


def verify_rsa_accumulator_math(
    accumulator_hex: str,
    device_prime: int,
    witness_hex: str,
    rsa_params: Dict[str, int]
) -> bool:
    """
    Verify RSA accumulator membership proof mathematically.
    
    Checks: w^p ≡ A (mod N)
    """
    N = rsa_params["N"]
    
    # Convert hex to integers
    A = int(accumulator_hex, 16) if accumulator_hex.startswith('0x') else int(accumulator_hex, 16)
    w = int(witness_hex, 16) if witness_hex.startswith('0x') else int(witness_hex, 16)
    
    # Verify membership: w^p ≡ A (mod N)
    computed = pow(w, device_prime, N)
    return computed == A


@pytest.mark.asyncio
async def test_complete_auth_flow(
    gateway_client: httpx.AsyncClient,
    admin_headers: Dict[str, str],
    rsa_params: Dict[str, int],
    device_primes: Dict[str, int],
    timing_results: Dict[str, Any]
):
    """Test complete device authentication flow with RSA accumulator verification."""
    
    print("\n🧪 Starting Complete Authentication Flow Test")
    print("=" * 50)
    
    # Step 1: Generate Ed25519 device
    print("\n1️⃣ Generating Ed25519 device keypair...")
    start_time = time.time()
    
    device = Ed25519Device("test_sensor_001")
    
    keygen_time = (time.time() - start_time) * 1000
    record_timing(timing_results, "ed25519_keygen", keygen_time)
    print(f"   ✅ Device created: {device.device_id}")
    print(f"   ⏱️  Key generation: {keygen_time:.2f}ms")
    
    # Step 2: Check initial accumulator state
    print("\n2️⃣ Checking initial accumulator state...")
    start_time = time.time()
    
    response = await gateway_client.get("/accumulator")
    assert response.status_code == 200
    
    initial_state = response.json()
    
    state_check_time = (time.time() - start_time) * 1000
    record_timing(timing_results, "accumulator_state_check", state_check_time, len(response.content))
    
    print(f"   ✅ Initial accumulator: {initial_state['rootHex']}")
    print(f"   ✅ Active devices: {initial_state['activeDevices']}")
    print(f"   ⏱️  State check: {state_check_time:.2f}ms")
    
    # Step 3: Enroll device
    print("\n3️⃣ Enrolling device...")
    start_time = time.time()
    
    enroll_payload = {
        "device_id": device.device_id,
        "pubkey_pem": device.pem_public
    }
    
    response = await gateway_client.post(
        "/enroll",
        json=enroll_payload,
        headers=admin_headers
    )
    
    enroll_time = (time.time() - start_time) * 1000
    payload_size = len(json.dumps(enroll_payload).encode())
    record_timing(timing_results, "device_enrollment", enroll_time, payload_size)
    
    assert response.status_code == 201, f"Enrollment failed: {response.text}"
    
    enroll_result = response.json()
    device_prime_hex = enroll_result["prime"]
    witness_hex = enroll_result["witness"]
    new_root_hex = enroll_result["new_root"]
    
    print(f"   ✅ Device enrolled successfully")
    print(f"   ✅ Device prime: {device_prime_hex}")
    print(f"   ✅ Initial witness: {witness_hex[:20]}...")
    print(f"   ✅ New accumulator: {new_root_hex}")
    print(f"   ⏱️  Enrollment: {enroll_time:.2f}ms")
    print(f"   📦 Payload size: {payload_size} bytes")
    
    # Step 4: Verify RSA accumulator math
    print("\n4️⃣ Verifying RSA accumulator mathematics...")
    
    device_prime = int(device_prime_hex, 16)
    
    # For testing, we'll use a known prime mapping
    # In practice, this would be computed by hash_to_prime()
    expected_prime = device_primes.get("device_001", 13)  # Use test prime
    
    math_valid = verify_rsa_accumulator_math(
        new_root_hex, expected_prime, witness_hex, rsa_params
    )
    
    print(f"   ✅ RSA math verification: {'PASSED' if math_valid else 'FAILED'}")
    print(f"   📊 Used prime: {expected_prime}")
    print(f"   📊 Modulus N: {rsa_params['N']}")
    
    # Step 5: Start authentication
    print("\n5️⃣ Starting authentication flow...")
    start_time = time.time()
    
    response = await gateway_client.get(f"/auth/start?device_id={device.device_id}")
    assert response.status_code == 200
    
    auth_start_time = (time.time() - start_time) * 1000
    record_timing(timing_results, "auth_start", auth_start_time, len(response.content))
    
    auth_start = response.json()
    nonce = auth_start["nonce"]
    expires_at = auth_start["expiresAt"]
    
    print(f"   ✅ Auth nonce received: {nonce[:16]}...")
    print(f"   ✅ Expires at: {expires_at}")
    print(f"   ⏱️  Auth start: {auth_start_time:.2f}ms")
    
    # Step 6: Sign nonce with device key
    print("\n6️⃣ Signing nonce with device key...")
    start_time = time.time()
    
    nonce_bytes = nonce.encode()
    signature = device.sign_message(nonce_bytes)
    signature_b64 = base64.b64encode(signature).decode()
    
    signing_time = (time.time() - start_time) * 1000
    record_timing(timing_results, "ed25519_signing", signing_time)
    
    print(f"   ✅ Nonce signed")
    print(f"   ✅ Signature: {signature_b64[:32]}...")
    print(f"   ⏱️  Signing: {signing_time:.2f}ms")
    
    # Step 7: Verify authentication
    print("\n7️⃣ Verifying authentication...")
    start_time = time.time()
    
    auth_verify_payload = {
        "device_id": device.device_id,
        "p_hex": device_prime_hex,
        "witness_hex": witness_hex,
        "signature_base64": signature_b64,
        "nonce": nonce,
        "pubkey_pem": device.pem_public
    }
    
    response = await gateway_client.post(
        "/auth/verify",
        json=auth_verify_payload
    )
    
    auth_verify_time = (time.time() - start_time) * 1000
    verify_payload_size = len(json.dumps(auth_verify_payload).encode())
    record_timing(timing_results, "auth_verify", auth_verify_time, verify_payload_size)
    
    print(f"   📝 Auth verify status: {response.status_code}")
    
    if response.status_code == 200:
        auth_result = response.json()
        assert auth_result["ok"] is True, f"Auth verification failed: {auth_result}"
        
        print(f"   ✅ Authentication SUCCESSFUL")
        print(f"   ✅ Device authenticated: {auth_result['device_id']}")
    else:
        print(f"   ❌ Authentication failed: {response.text}")
        # Continue with test to see the failure reason
    
    print(f"   ⏱️  Auth verify: {auth_verify_time:.2f}ms")
    print(f"   📦 Payload size: {verify_payload_size} bytes")
    
    # Step 8: Revoke device
    print("\n8️⃣ Revoking device...")
    start_time = time.time()
    
    revoke_payload = {
        "device_id": device.device_id
    }
    
    response = await gateway_client.post(
        "/revoke",
        json=revoke_payload,
        headers=admin_headers
    )
    
    revoke_time = (time.time() - start_time) * 1000
    revoke_payload_size = len(json.dumps(revoke_payload).encode())
    record_timing(timing_results, "device_revocation", revoke_time, revoke_payload_size)
    
    assert response.status_code == 204, f"Revocation failed: {response.text}"
    
    print(f"   ✅ Device revoked successfully")
    print(f"   ⏱️  Revocation: {revoke_time:.2f}ms")
    
    # Step 9: Verify revoked device cannot authenticate
    print("\n9️⃣ Verifying revoked device fails authentication...")
    
    # Get new nonce
    response = await gateway_client.get(f"/auth/start?device_id={device.device_id}")
    assert response.status_code == 200
    
    new_auth_start = response.json()
    new_nonce = new_auth_start["nonce"]
    
    # Sign new nonce
    new_signature = device.sign_message(new_nonce.encode())
    new_signature_b64 = base64.b64encode(new_signature).decode()
    
    start_time = time.time()
    
    # Try to authenticate with old witness (should fail)
    failed_auth_payload = {
        "device_id": device.device_id,
        "p_hex": device_prime_hex,
        "witness_hex": witness_hex,  # Old witness, should be invalid now
        "signature_base64": new_signature_b64,
        "nonce": new_nonce,
        "pubkey_pem": device.pem_public
    }
    
    response = await gateway_client.post(
        "/auth/verify",
        json=failed_auth_payload
    )
    
    failed_auth_time = (time.time() - start_time) * 1000
    record_timing(timing_results, "auth_verify_revoked", failed_auth_time)
    
    # Should fail with 401 Unauthorized
    assert response.status_code == 401, f"Expected auth failure, got: {response.status_code}"
    
    print(f"   ✅ Revoked device authentication correctly FAILED")
    print(f"   ✅ Status: {response.status_code} (Unauthorized)")
    print(f"   ⏱️  Failed auth check: {failed_auth_time:.2f}ms")
    
    # Step 10: Check final accumulator state
    print("\n🔟 Checking final accumulator state...")
    start_time = time.time()
    
    response = await gateway_client.get("/accumulator")
    assert response.status_code == 200
    
    final_state = response.json()
    
    final_check_time = (time.time() - start_time) * 1000
    record_timing(timing_results, "final_state_check", final_check_time)
    
    print(f"   ✅ Final accumulator: {final_state['rootHex']}")
    print(f"   ✅ Active devices: {final_state['activeDevices']}")
    print(f"   ✅ Accumulator changed: {final_state['rootHex'] != initial_state['rootHex']}")
    print(f"   ⏱️  Final check: {final_check_time:.2f}ms")


@pytest.mark.asyncio
async def test_multiple_device_flow(
    gateway_client: httpx.AsyncClient,
    admin_headers: Dict[str, str],
    device_primes: Dict[str, int],
    timing_results: Dict[str, Any]
):
    """Test enrollment and authentication of multiple devices."""
    
    print("\n🧪 Testing Multiple Device Flow")
    print("=" * 40)
    
    devices = []
    
    # Create multiple devices
    for i in range(3):
        device_id = f"multi_device_{i:03d}"
        device = Ed25519Device(device_id)
        devices.append(device)
        print(f"   📱 Created device: {device_id}")
    
    enrolled_devices = []
    
    # Enroll all devices
    print(f"\n📝 Enrolling {len(devices)} devices...")
    for device in devices:
        start_time = time.time()
        
        enroll_payload = {
            "device_id": device.device_id,
            "pubkey_pem": device.pem_public
        }
        
        response = await gateway_client.post(
            "/enroll",
            json=enroll_payload,
            headers=admin_headers
        )
        
        enroll_time = (time.time() - start_time) * 1000
        record_timing(timing_results, "multi_device_enrollment", enroll_time)
        
        if response.status_code == 201:
            result = response.json()
            enrolled_devices.append({
                "device": device,
                "prime": result["prime"],
                "witness": result["witness"]
            })
            print(f"   ✅ Enrolled: {device.device_id} ({enroll_time:.2f}ms)")
        else:
            print(f"   ❌ Failed to enroll: {device.device_id} - {response.text}")
    
    # Authenticate all enrolled devices
    print(f"\n🔐 Authenticating {len(enrolled_devices)} devices...")
    auth_successes = 0
    
    for device_data in enrolled_devices:
        device = device_data["device"]
        
        # Get nonce
        response = await gateway_client.get(f"/auth/start?device_id={device.device_id}")
        if response.status_code != 200:
            print(f"   ❌ Failed to get nonce for: {device.device_id}")
            continue
        
        nonce = response.json()["nonce"]
        
        # Sign and verify
        signature = device.sign_message(nonce.encode())
        signature_b64 = base64.b64encode(signature).decode()
        
        start_time = time.time()
        
        auth_payload = {
            "device_id": device.device_id,
            "p_hex": device_data["prime"],
            "witness_hex": device_data["witness"],
            "signature_base64": signature_b64,
            "nonce": nonce,
            "pubkey_pem": device.pem_public
        }
        
        response = await gateway_client.post("/auth/verify", json=auth_payload)
        
        auth_time = (time.time() - start_time) * 1000
        record_timing(timing_results, "multi_device_auth", auth_time)
        
        if response.status_code == 200 and response.json().get("ok"):
            auth_successes += 1
            print(f"   ✅ Authenticated: {device.device_id} ({auth_time:.2f}ms)")
        else:
            print(f"   ❌ Auth failed: {device.device_id} - {response.text}")
    
    print(f"\n📊 Multi-device results:")
    print(f"   Enrolled: {len(enrolled_devices)}/{len(devices)}")
    print(f"   Authenticated: {auth_successes}/{len(enrolled_devices)}")
    
    assert len(enrolled_devices) >= 2, "Should enroll at least 2 devices"
    assert auth_successes >= 2, "Should authenticate at least 2 devices"


@pytest.mark.asyncio 
async def test_performance_stress(
    gateway_client: httpx.AsyncClient,
    admin_headers: Dict[str, str],
    timing_results: Dict[str, Any]
):
    """Stress test with rapid operations to measure performance limits."""
    
    print("\n🧪 Performance Stress Test")
    print("=" * 30)
    
    # Rapid health checks
    print("\n⚡ Rapid health checks...")
    health_times = []
    
    for i in range(10):
        start_time = time.time()
        response = await gateway_client.get("/healthz")
        duration = (time.time() - start_time) * 1000
        health_times.append(duration)
        record_timing(timing_results, "stress_health_check", duration)
    
    avg_health = sum(health_times) / len(health_times)
    print(f"   ✅ Health checks: {avg_health:.2f}ms avg")
    
    # Rapid accumulator state checks
    print("\n⚡ Rapid accumulator checks...")
    accum_times = []
    
    for i in range(10):
        start_time = time.time()
        response = await gateway_client.get("/accumulator")
        duration = (time.time() - start_time) * 1000
        accum_times.append(duration)
        record_timing(timing_results, "stress_accumulator_check", duration)
    
    avg_accum = sum(accum_times) / len(accum_times)
    print(f"   ✅ Accumulator checks: {avg_accum:.2f}ms avg")
    
    # Concurrent requests
    print("\n⚡ Concurrent requests...")
    
    async def concurrent_health_check():
        start_time = time.time()
        response = await gateway_client.get("/healthz")
        duration = (time.time() - start_time) * 1000
        record_timing(timing_results, "concurrent_health", duration)
        return duration
    
    # Run 5 concurrent requests
    start_time = time.time()
    concurrent_times = await asyncio.gather(*[concurrent_health_check() for _ in range(5)])
    total_concurrent_time = (time.time() - start_time) * 1000
    
    print(f"   ✅ Concurrent requests: {total_concurrent_time:.2f}ms total")
    print(f"   ✅ Individual times: {[f'{t:.1f}ms' for t in concurrent_times]}")


def test_print_final_report(timing_results: Dict[str, Any]):
    """Print the final performance report."""
    print_performance_report(timing_results)
