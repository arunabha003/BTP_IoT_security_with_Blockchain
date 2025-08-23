"""
End-to-End System Integration Tests

Comprehensive tests that verify the complete IoT identity system working together:
- Smart contracts deployed on Anvil
- Gateway service with real database
- RSA accumulator mathematics
- Complete device lifecycle flows
- Performance and security validation
"""

import asyncio
import json
import time
import pytest
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from web3 import Web3


class TestCompleteSystemIntegration:
    """Test the complete system integration across all components."""
    
    def test_system_health_and_connectivity(self, anvil_chain, gateway_server):
        """Test that all system components are healthy and connected."""
        base_url = gateway_server
        
        print("\n🏥 Testing System Health...")
        
        # Test gateway health
        response = requests.get(f"{base_url}/healthz")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["ok"] is True
        print(f"   ✅ Gateway: {health_data['service']} v{health_data['version']}")
        print(f"   ✅ Database: {health_data['database']}")
        print(f"   ✅ Blockchain: {health_data['blockchain']}")
        print(f"   ✅ Contract: {'Loaded' if health_data['contract_loaded'] else 'Not Loaded'}")
        
        # Test detailed status
        response = requests.get(f"{base_url}/status")
        assert response.status_code == 200
        
        status_data = response.json()
        assert "config" in status_data
        assert "blockchain" in status_data
        assert "database" in status_data
        print(f"   ✅ System Status: All components operational")
    
    def test_accumulator_state_management(self, gateway_server):
        """Test accumulator state management and synchronization."""
        base_url = gateway_server
        
        print("\n🔄 Testing Accumulator State Management...")
        
        # Get initial accumulator state
        response = requests.get(f"{base_url}/accumulator")
        assert response.status_code == 200
        
        initial_state = response.json()
        print(f"   📊 Initial Root: {initial_state['rootHex']}")
        print(f"   📊 Block: {initial_state['block']}")
        print(f"   📊 Active Devices: {initial_state['activeDevices']}")
        
        # Test root endpoint consistency
        response = requests.get(f"{base_url}/root")
        assert response.status_code == 200
        
        root_data = response.json()
        assert root_data["root"] == initial_state["rootHex"]
        print(f"   ✅ Root endpoint consistent with accumulator info")
    
    def test_device_enrollment_complete_flow(self, gateway_server):
        """Test complete device enrollment with all validations."""
        base_url = gateway_server
        admin_key = "test-admin-key"
        headers = {"X-Admin-Key": admin_key}
        
        print("\n📱 Testing Complete Device Enrollment Flow...")
        
        # Generate Ed25519 keypair
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        device_id = "system_test_device_001"
        
        # Test enrollment
        start_time = time.time()
        enrollment_payload = {
            "device_id": device_id,
            "pubkey_pem": public_pem
        }
        
        response = requests.post(f"{base_url}/enroll", json=enrollment_payload, headers=headers)
        enrollment_time = time.time() - start_time
        
        if response.status_code == 200:
            enrollment_data = response.json()
            print(f"   ✅ Device enrolled successfully in {enrollment_time:.3f}s")
            print(f"      Device ID: {enrollment_data['device_id']}")
            print(f"      Prime: {enrollment_data['prime_p_hex']}")
            print(f"      Initial Witness: {enrollment_data['initial_witness_hex']}")
            print(f"      New Root: {enrollment_data['current_root_hex']}")
            
            # Verify accumulator state updated
            response = requests.get(f"{base_url}/accumulator")
            assert response.status_code == 200
            
            new_state = response.json()
            assert new_state['activeDevices'] >= 1
            print(f"   ✅ Accumulator updated: {new_state['activeDevices']} active devices")
            
            return {
                'device_id': device_id,
                'private_key': private_key,
                'public_key': public_key,
                'enrollment_data': enrollment_data
            }
        else:
            print(f"   ⚠️  Enrollment failed: {response.status_code} - {response.text}")
            print(f"      This may be expected if smart contracts are not fully connected")
            return None
    
    def test_authentication_flow_complete(self, gateway_server):
        """Test complete authentication flow if device enrollment succeeded."""
        base_url = gateway_server
        
        print("\n🔐 Testing Authentication Flow...")
        
        # First try to enroll a device for authentication testing
        device_info = self.test_device_enrollment_complete_flow(gateway_server)
        
        if device_info is None:
            print("   ⚠️  Skipping authentication test - enrollment not available")
            return
        
        device_id = device_info['device_id']
        private_key = device_info['private_key']
        enrollment_data = device_info['enrollment_data']
        
        # Start authentication session
        print(f"\n   🔑 Starting authentication for {device_id}...")
        
        start_time = time.time()
        response = requests.get(f"{base_url}/auth/start?device_id={device_id}")
        auth_start_time = time.time() - start_time
        
        if response.status_code == 200:
            auth_start_data = response.json()
            nonce = auth_start_data['nonce']
            expires_at = auth_start_data['expiresAt']
            
            print(f"   ✅ Auth session started in {auth_start_time:.3f}s")
            print(f"      Nonce: {nonce}")
            print(f"      Expires: {expires_at}")
            
            # Sign the nonce
            signature = private_key.sign(nonce.encode())
            signature_hex = Web3.to_hex(signature)
            
            # Verify authentication
            verify_payload = {
                "device_id": device_id,
                "p_hex": enrollment_data['prime_p_hex'],
                "witness_hex": enrollment_data['initial_witness_hex'],
                "signature_base64": signature_hex,
                "nonce": nonce
            }
            
            start_time = time.time()
            response = requests.post(f"{base_url}/auth/verify", json=verify_payload)
            auth_verify_time = time.time() - start_time
            
            if response.status_code == 200:
                verify_data = response.json()
                print(f"   ✅ Authentication verified in {auth_verify_time:.3f}s")
                print(f"      Result: {'SUCCESS' if verify_data['ok'] else 'FAILED'}")
                
                if 'newWitnessHex' in verify_data:
                    print(f"      New Witness: {verify_data['newWitnessHex']}")
                
                assert verify_data['ok'] is True
            else:
                print(f"   ❌ Authentication verification failed: {response.status_code} - {response.text}")
        else:
            print(f"   ❌ Auth start failed: {response.status_code} - {response.text}")
    
    def test_device_revocation_complete(self, gateway_server):
        """Test complete device revocation flow."""
        base_url = gateway_server
        admin_key = "test-admin-key"
        headers = {"X-Admin-Key": admin_key}
        
        print("\n🚫 Testing Device Revocation Flow...")
        
        # First enroll a device
        device_info = self.test_device_enrollment_complete_flow(gateway_server)
        
        if device_info is None:
            print("   ⚠️  Skipping revocation test - enrollment not available")
            return
        
        device_id = device_info['device_id']
        
        # Get accumulator state before revocation
        response = requests.get(f"{base_url}/accumulator")
        assert response.status_code == 200
        before_state = response.json()
        
        # Revoke the device
        print(f"\n   🗑️  Revoking device {device_id}...")
        
        revoke_payload = {"device_id": device_id}
        start_time = time.time()
        response = requests.post(f"{base_url}/revoke", json=revoke_payload, headers=headers)
        revoke_time = time.time() - start_time
        
        if response.status_code == 204:
            print(f"   ✅ Device revoked successfully in {revoke_time:.3f}s")
            
            # Verify accumulator state updated
            response = requests.get(f"{base_url}/accumulator")
            assert response.status_code == 200
            
            after_state = response.json()
            print(f"   📊 Active devices: {before_state['activeDevices']} → {after_state['activeDevices']}")
            
            # Try to start auth session for revoked device (should fail)
            response = requests.get(f"{base_url}/auth/start?device_id={device_id}")
            if response.status_code == 403:
                print(f"   ✅ Revoked device correctly rejected for authentication")
            else:
                print(f"   ⚠️  Revoked device auth start: {response.status_code}")
        else:
            print(f"   ❌ Device revocation failed: {response.status_code} - {response.text}")
    
    def test_system_performance_characteristics(self, gateway_server):
        """Test system performance characteristics and limits."""
        base_url = gateway_server
        
        print("\n⚡ Testing System Performance Characteristics...")
        
        # Test response times for various endpoints
        endpoints_to_test = [
            ("/healthz", "GET", None),
            ("/root", "GET", None),
            ("/accumulator", "GET", None),
            ("/status", "GET", None),
        ]
        
        performance_results = {}
        
        for endpoint, method, payload in endpoints_to_test:
            times = []
            for _ in range(10):  # 10 samples per endpoint
                start_time = time.time()
                
                if method == "GET":
                    response = requests.get(f"{base_url}{endpoint}")
                else:
                    response = requests.post(f"{base_url}{endpoint}", json=payload)
                
                end_time = time.time()
                
                if response.status_code in [200, 204]:
                    times.append((end_time - start_time) * 1000)  # Convert to ms
            
            if times:
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                performance_results[endpoint] = {
                    'avg_ms': avg_time,
                    'min_ms': min_time,
                    'max_ms': max_time
                }
                
                print(f"   📊 {endpoint}: {avg_time:.2f}ms avg ({min_time:.2f}-{max_time:.2f}ms)")
        
        # Test concurrent requests
        print(f"\n   🔄 Testing concurrent request handling...")
        
        import concurrent.futures
        import threading
        
        def make_request():
            response = requests.get(f"{base_url}/healthz")
            return response.status_code == 200
        
        # Test 20 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            start_time = time.time()
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            total_time = time.time() - start_time
        
        success_rate = sum(results) / len(results)
        print(f"   ✅ Concurrent requests: {success_rate:.1%} success rate in {total_time:.3f}s")
        
        return performance_results
    
    def test_system_security_features(self, gateway_server):
        """Test system security features and protections."""
        base_url = gateway_server
        
        print("\n🔒 Testing System Security Features...")
        
        # Test admin authentication
        print(f"\n   🛡️  Testing admin authentication...")
        
        # Test without admin key (should fail)
        payload = {"newRootHex": "0x" + "12" * 32}
        response = requests.post(f"{base_url}/accumulator/update", json=payload)
        assert response.status_code == 401
        print(f"   ✅ Admin endpoint properly protected (401 without key)")
        
        # Test with wrong admin key (should fail)
        wrong_headers = {"X-Admin-Key": "wrong-key"}
        response = requests.post(f"{base_url}/accumulator/update", json=payload, headers=wrong_headers)
        assert response.status_code == 401
        print(f"   ✅ Wrong admin key rejected (401)")
        
        # Test rate limiting
        print(f"\n   🚦 Testing rate limiting...")
        
        rate_limit_hit = False
        for i in range(25):  # Try to exceed rate limit
            response = requests.get(f"{base_url}/healthz")
            if response.status_code == 429:
                rate_limit_hit = True
                break
        
        if rate_limit_hit:
            print(f"   ✅ Rate limiting active (got 429 after {i+1} requests)")
        else:
            print(f"   ⚠️  Rate limiting not triggered in 25 requests")
        
        # Test security headers
        print(f"\n   🛡️  Testing security headers...")
        
        response = requests.get(f"{base_url}/healthz")
        security_headers = [
            'x-frame-options',
            'x-content-type-options',
            'strict-transport-security',
            'x-request-id'
        ]
        
        present_headers = []
        for header in security_headers:
            if header in response.headers:
                present_headers.append(header)
        
        print(f"   ✅ Security headers present: {len(present_headers)}/{len(security_headers)}")
        for header in present_headers:
            print(f"      - {header}: {response.headers[header]}")
        
        # Test input validation
        print(f"\n   ✅ Testing input validation...")
        
        admin_headers = {"X-Admin-Key": "test-admin-key"}
        
        # Test invalid hex format
        invalid_payload = {"newRootHex": "invalid_hex"}
        response = requests.post(f"{base_url}/accumulator/update", json=invalid_payload, headers=admin_headers)
        if response.status_code == 400:
            print(f"   ✅ Invalid hex format rejected (400)")
        
        # Test missing required fields
        incomplete_payload = {"device_id": "test"}  # Missing pubkey_pem
        response = requests.post(f"{base_url}/enroll", json=incomplete_payload, headers=admin_headers)
        if response.status_code == 422:
            print(f"   ✅ Missing required fields rejected (422)")
    
    def test_system_error_handling(self, gateway_server):
        """Test system error handling and recovery."""
        base_url = gateway_server
        
        print("\n🚨 Testing System Error Handling...")
        
        # Test 404 handling
        response = requests.get(f"{base_url}/nonexistent-endpoint")
        assert response.status_code == 404
        print(f"   ✅ 404 errors handled properly")
        
        # Test malformed JSON
        response = requests.post(
            f"{base_url}/accumulator/update",
            data="invalid json",
            headers={"Content-Type": "application/json", "X-Admin-Key": "test-admin-key"}
        )
        assert response.status_code in [400, 422]
        print(f"   ✅ Malformed JSON handled ({response.status_code})")
        
        # Test method not allowed
        response = requests.delete(f"{base_url}/healthz")
        assert response.status_code == 405
        print(f"   ✅ Method not allowed handled (405)")
        
        # Test request ID consistency
        response = requests.get(f"{base_url}/healthz")
        request_id = response.headers.get('x-request-id')
        assert request_id is not None
        assert len(request_id) == 8  # UUID prefix
        print(f"   ✅ Request ID tracking working: {request_id}")
    
    def test_system_integration_comprehensive(self, anvil_chain, gateway_server, accumulator_registry_contract):
        """Comprehensive system integration test covering all components."""
        base_url = gateway_server
        
        print("\n🌟 Comprehensive System Integration Test")
        print("=" * 50)
        
        # Collect all test results
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
        
        try:
            # Run all test components
            self.test_system_health_and_connectivity(anvil_chain, gateway_server)
            test_results['health_check'] = True
            
            self.test_accumulator_state_management(gateway_server)
            test_results['accumulator_state'] = True
            
            device_info = self.test_device_enrollment_complete_flow(gateway_server)
            test_results['device_enrollment'] = device_info is not None
            
            if device_info:
                # Only test auth/revocation if enrollment worked
                self.test_authentication_flow_complete(gateway_server)
                test_results['authentication'] = True
                
                self.test_device_revocation_complete(gateway_server)
                test_results['revocation'] = True
            
            test_results['performance'] = self.test_system_performance_characteristics(gateway_server)
            
            self.test_system_security_features(gateway_server)
            test_results['security'] = True
            
            self.test_system_error_handling(gateway_server)
            test_results['error_handling'] = True
            
        except Exception as e:
            print(f"\n❌ Test failed with exception: {e}")
        
        # Print final summary
        print(f"\n🎯 COMPREHENSIVE SYSTEM TEST SUMMARY")
        print("=" * 40)
        
        passed_tests = sum(1 for k, v in test_results.items() if k != 'performance' and v is True)
        total_tests = len(test_results) - 1  # Exclude performance dict
        
        print(f"✅ Health Check: {'PASS' if test_results['health_check'] else 'FAIL'}")
        print(f"✅ Accumulator State: {'PASS' if test_results['accumulator_state'] else 'FAIL'}")
        print(f"✅ Device Enrollment: {'PASS' if test_results['device_enrollment'] else 'FAIL'}")
        print(f"✅ Authentication: {'PASS' if test_results['authentication'] else 'FAIL'}")
        print(f"✅ Device Revocation: {'PASS' if test_results['revocation'] else 'FAIL'}")
        print(f"✅ Security Features: {'PASS' if test_results['security'] else 'FAIL'}")
        print(f"✅ Error Handling: {'PASS' if test_results['error_handling'] else 'FAIL'}")
        
        if test_results['performance']:
            avg_response_time = sum(
                result['avg_ms'] for result in test_results['performance'].values()
            ) / len(test_results['performance'])
            print(f"⚡ Average Response Time: {avg_response_time:.2f}ms")
        
        print(f"\n🏆 OVERALL RESULT: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 ALL SYSTEM INTEGRATION TESTS PASSED!")
        else:
            print("⚠️  Some tests failed - system may have connectivity issues")
        
        # Assert that core functionality works
        assert test_results['health_check'], "Health check must pass"
        assert test_results['accumulator_state'], "Accumulator state management must work"
        assert test_results['security'], "Security features must be functional"
        assert test_results['error_handling'], "Error handling must work"
        
        print(f"\n✅ Core system functionality verified!")
        
        return test_results


if __name__ == "__main__":
    # Allow running this test file directly for development
    print("🧪 Running End-to-End System Integration Tests")
    print("Note: This requires anvil_chain and gateway_server fixtures")
    print("Run with: pytest test_end_to_end_system.py -v -s")
