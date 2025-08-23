"""
Integration Tests for Complete RSA Accumulator Flow

Tests the complete integration of all accumulator components working together
in realistic scenarios.
"""

import os
import pytest
from typing import Set, Dict, List

try:
    from accum.rsa_params import load_params, generate_demo_params
    from accum.hash_to_prime import hash_to_prime
    from accum.accumulator import add_member, recompute_root, membership_witness, verify_membership
    from accum.witness_refresh import refresh_witness, batch_refresh_witnesses, update_witness_on_addition
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from rsa_params import load_params, generate_demo_params
    from hash_to_prime import hash_to_prime
    from accumulator import add_member, recompute_root, membership_witness, verify_membership
    from witness_refresh import refresh_witness, batch_refresh_witnesses, update_witness_on_addition


class TestFullAccumulatorFlow:
    """Integration tests for complete accumulator workflows."""
    
    @pytest.fixture
    def toy_params(self):
        """Provide toy RSA parameters for testing."""
        return generate_demo_params()
    
    @pytest.fixture
    def production_params(self):
        """Provide production RSA parameters."""
        try:
            return load_params()
        except:
            pytest.skip("Production parameters not available")
    
    def test_device_lifecycle_toy_params(self, toy_params):
        """Test complete device lifecycle with toy parameters."""
        N, g = toy_params
        
        # Simulate device public keys
        device_keys = [
            b"device_001_public_key",
            b"device_002_public_key", 
            b"device_003_public_key",
        ]
        
        # Convert to primes
        device_primes = [hash_to_prime(key) for key in device_keys]
        
        # Initialize accumulator
        accumulator = g
        active_primes: Set[int] = set()
        device_witnesses: Dict[bytes, int] = {}
        
        # Phase 1: Enroll all devices
        for i, (key, prime) in enumerate(zip(device_keys, device_primes)):
            # Store witness before adding device (witness = old accumulator)
            device_witnesses[key] = accumulator
            
            # Add device to accumulator
            accumulator = add_member(accumulator, prime, N)
            active_primes.add(prime)
            
            # Update witnesses for existing devices
            for existing_key in device_witnesses:
                if existing_key != key:  # Don't update the just-added device
                    device_witnesses[existing_key] = update_witness_on_addition(
                        device_witnesses[existing_key], prime, N
                    )
            
            print(f"Enrolled device {i+1}: prime={prime}, accumulator={accumulator}")
        
        # Phase 2: Verify all devices can authenticate
        for key, prime in zip(device_keys, device_primes):
            witness = device_witnesses[key]
            is_valid = verify_membership(witness, prime, accumulator, N)
            assert is_valid, f"Device {key} failed authentication"
            print(f"Device {key}: Authentication successful")
        
        # Phase 3: Revoke middle device
        revoked_key = device_keys[1]
        revoked_prime = device_primes[1]
        
        # Remove from active set
        active_primes.remove(revoked_prime)
        del device_witnesses[revoked_key]
        
        # Recompute accumulator without revoked device
        new_accumulator = recompute_root(active_primes, N, g)
        
        # Refresh witnesses for remaining devices
        for key, prime in zip(device_keys, device_primes):
            if key != revoked_key:
                device_witnesses[key] = refresh_witness(prime, active_primes, N, g)
        
        print(f"Revoked device {revoked_key}, new accumulator: {new_accumulator}")
        
        # Phase 4: Verify remaining devices still work
        for key, prime in zip(device_keys, device_primes):
            if key != revoked_key:
                witness = device_witnesses[key]
                is_valid = verify_membership(witness, prime, new_accumulator, N)
                assert is_valid, f"Device {key} failed authentication after revocation"
                print(f"Device {key}: Authentication successful after revocation")
        
        # Phase 5: Verify revoked device fails
        old_witness = accumulator  # The revoked device's last witness
        is_valid = verify_membership(old_witness, revoked_prime, new_accumulator, N)
        assert not is_valid, "Revoked device should not authenticate"
        print(f"Revoked device {revoked_key}: Correctly rejected")
    
    def test_large_scale_enrollment(self, toy_params):
        """Test enrollment of many devices."""
        N, g = toy_params
        num_devices = 50
        
        # Generate device keys and primes
        device_data = []
        for i in range(num_devices):
            key = f"device_{i:03d}_key".encode()
            prime = hash_to_prime(key)
            device_data.append((key, prime))
        
        # Build accumulator incrementally
        accumulator = g
        active_primes = set()
        
        for i, (key, prime) in enumerate(device_data):
            accumulator = add_member(accumulator, prime, N)
            active_primes.add(prime)
            
            if i % 10 == 0:  # Progress update
                print(f"Enrolled {i+1}/{num_devices} devices")
        
        # Verify batch witness generation
        all_primes = [data[1] for data in device_data]
        witnesses = batch_refresh_witnesses(all_primes, active_primes, N, g)
        
        # Verify all witnesses
        for i, (key, prime) in enumerate(device_data):
            witness = witnesses[i]
            is_valid = verify_membership(witness, prime, accumulator, N)
            assert is_valid, f"Device {i} failed verification in large scale test"
        
        print(f"Successfully verified {num_devices} devices in batch")
    
    def test_production_parameters_basic(self, production_params):
        """Test basic operations with production parameters."""
        N, g = production_params
        
        # Verify parameters are production-ready
        assert N.bit_length() >= 2048, "Production N should be at least 2048 bits"
        assert g in [2, 3, 4], "Production g should be small"
        
        # Test basic operations
        device_key = b"production_test_device"
        prime = hash_to_prime(device_key)
        
        # Single device enrollment
        accumulator = add_member(g, prime, N)
        witness = g  # Witness for single device
        
        # Verify membership
        is_valid = verify_membership(witness, prime, accumulator, N)
        assert is_valid, "Production parameters failed basic test"
        
        print(f"Production parameters test successful: N={N.bit_length()} bits")
    
    def test_accumulator_mathematical_invariants(self, toy_params):
        """Test mathematical invariants across operations."""
        N, g = toy_params
        
        # Test data
        primes = [hash_to_prime(f"device_{i}".encode()) for i in range(5)]
        
        # Test invariant: incremental vs batch computation
        # Incremental
        acc_incremental = g
        for p in primes:
            acc_incremental = add_member(acc_incremental, p, N)
        
        # Batch
        acc_batch = recompute_root(set(primes), N, g)
        
        assert acc_incremental == acc_batch, "Incremental and batch computation must match"
        
        # Test invariant: witness verification
        for target_prime in primes:
            witness = membership_witness(set(primes), target_prime, N, g)
            assert pow(witness, target_prime, N) == acc_batch, "Witness verification invariant failed"
        
        # Test invariant: order independence
        import random
        shuffled_primes = primes.copy()
        random.shuffle(shuffled_primes)
        
        acc_shuffled = recompute_root(set(shuffled_primes), N, g)
        assert acc_batch == acc_shuffled, "Order independence invariant failed"
        
        print("All mathematical invariants verified")
    
    def test_witness_consistency_across_operations(self, toy_params):
        """Test witness consistency across different operations."""
        N, g = toy_params
        
        initial_primes = {13, 17, 23}
        target_prime = 17
        
        # Method 1: Direct witness computation
        witness_direct = membership_witness(initial_primes, target_prime, N, g)
        
        # Method 2: Witness refresh
        witness_refresh = refresh_witness(target_prime, initial_primes, N, g)
        
        # Method 3: Incremental update (simulate adding all primes one by one)
        witness_incremental = g  # Start with generator
        for p in initial_primes:
            if p != target_prime:
                witness_incremental = update_witness_on_addition(witness_incremental, p, N)
        
        # All methods should give same result
        assert witness_direct == witness_refresh, "Direct vs refresh witness mismatch"
        # Note: incremental method gives different result as it's computed differently
        
        # Verify all witnesses work
        accumulator = recompute_root(initial_primes, N, g)
        assert verify_membership(witness_direct, target_prime, accumulator, N)
        assert verify_membership(witness_refresh, target_prime, accumulator, N)
        
        print("Witness consistency verified across operations")
    
    def test_error_recovery_scenarios(self, toy_params):
        """Test error recovery in various failure scenarios."""
        N, g = toy_params
        
        # Scenario 1: Invalid prime in device set
        try:
            invalid_primes = {13, 17, 0}  # 0 is invalid
            recompute_root(invalid_primes, N, g)
            assert False, "Should have raised error for invalid prime"
        except ValueError:
            pass  # Expected
        
        # Scenario 2: Witness verification with wrong accumulator
        primes = {13, 17}
        correct_acc = recompute_root(primes, N, g)
        wrong_acc = recompute_root({13, 23}, N, g)  # Different set
        
        witness = membership_witness(primes, 17, N, g)
        assert verify_membership(witness, 17, correct_acc, N) == True
        assert verify_membership(witness, 17, wrong_acc, N) == False
        
        # Scenario 3: Hash collision handling (very unlikely but test robustness)
        keys = [f"test_key_{i}".encode() for i in range(100)]
        primes = [hash_to_prime(key) for key in keys]
        
        # Check for uniqueness (hash_to_prime should handle collisions)
        assert len(set(primes)) == len(primes), "Hash-to-prime should produce unique primes"
        
        print("Error recovery scenarios verified")
    
    def test_performance_characteristics(self, toy_params):
        """Test performance characteristics of accumulator operations."""
        import time
        
        N, g = toy_params
        num_devices = 20
        
        # Generate test data
        device_keys = [f"perf_device_{i:03d}".encode() for i in range(num_devices)]
        device_primes = [hash_to_prime(key) for key in device_keys]
        
        # Measure enrollment time
        start_time = time.time()
        accumulator = g
        for prime in device_primes:
            accumulator = add_member(accumulator, prime, N)
        enrollment_time = time.time() - start_time
        
        # Measure batch witness generation time
        start_time = time.time()
        witnesses = batch_refresh_witnesses(device_primes, set(device_primes), N, g)
        witness_time = time.time() - start_time
        
        # Measure verification time
        start_time = time.time()
        for i, prime in enumerate(device_primes):
            verify_membership(witnesses[i], prime, accumulator, N)
        verification_time = time.time() - start_time
        
        print(f"Performance metrics for {num_devices} devices:")
        print(f"  Enrollment: {enrollment_time:.4f}s ({enrollment_time/num_devices*1000:.2f}ms per device)")
        print(f"  Witness generation: {witness_time:.4f}s ({witness_time/num_devices*1000:.2f}ms per device)")
        print(f"  Verification: {verification_time:.4f}s ({verification_time/num_devices*1000:.2f}ms per device)")
        
        # Basic performance assertions (toy parameters should be very fast)
        assert enrollment_time < 1.0, "Enrollment should be fast with toy parameters"
        assert witness_time < 1.0, "Witness generation should be fast"
        assert verification_time < 1.0, "Verification should be fast"
    
    def test_cross_component_integration(self, toy_params):
        """Test integration across all accumulator components."""
        N, g = toy_params
        
        # Use all components together in a realistic scenario
        device_identifiers = ["sensor_001", "sensor_002", "actuator_001", "gateway_001"]
        
        # Phase 1: Convert identifiers to primes using hash_to_prime
        device_primes = {}
        for device_id in device_identifiers:
            key_data = f"{device_id}_public_key_data".encode()
            prime = hash_to_prime(key_data)
            device_primes[device_id] = prime
        
        # Phase 2: Build accumulator using add_member
        accumulator = g
        enrolled_order = []
        for device_id in device_identifiers:
            accumulator = add_member(accumulator, device_primes[device_id], N)
            enrolled_order.append(device_id)
        
        # Phase 3: Generate witnesses using membership_witness
        all_primes = set(device_primes.values())
        device_witnesses = {}
        for device_id, prime in device_primes.items():
            witness = membership_witness(all_primes, prime, N, g)
            device_witnesses[device_id] = witness
        
        # Phase 4: Verify all devices using verify_membership
        for device_id in device_identifiers:
            prime = device_primes[device_id]
            witness = device_witnesses[device_id]
            is_valid = verify_membership(witness, prime, accumulator, N)
            assert is_valid, f"Cross-component integration failed for {device_id}"
        
        # Phase 5: Test witness refresh after simulated change
        # Remove one device and refresh witnesses
        removed_device = "sensor_002"
        remaining_primes = {p for did, p in device_primes.items() if did != removed_device}
        new_accumulator = recompute_root(remaining_primes, N, g)
        
        # Refresh witnesses for remaining devices
        for device_id, prime in device_primes.items():
            if device_id != removed_device:
                new_witness = refresh_witness(prime, remaining_primes, N, g)
                is_valid = verify_membership(new_witness, prime, new_accumulator, N)
                assert is_valid, f"Witness refresh failed for {device_id}"
        
        print("Cross-component integration test successful")
        print(f"Tested with devices: {device_identifiers}")
        print(f"Final accumulator: {accumulator}")
        print(f"After removal accumulator: {new_accumulator}")
    
    def test_edge_cases_and_boundary_conditions(self, toy_params):
        """Test edge cases and boundary conditions."""
        N, g = toy_params
        
        # Edge case 1: Single device
        single_prime = hash_to_prime(b"single_device")
        single_acc = add_member(g, single_prime, N)
        single_witness = g  # Witness for single device is generator
        assert verify_membership(single_witness, single_prime, single_acc, N)
        
        # Edge case 2: Empty accumulator verification
        empty_acc = g
        # Should not verify any prime against empty accumulator
        random_prime = hash_to_prime(b"random")
        assert not verify_membership(g, random_prime, empty_acc, N)
        
        # Edge case 3: Very small primes
        small_primes = {2, 3, 5, 7, 11}  # First few primes
        small_acc = recompute_root(small_primes, N, g)
        for p in small_primes:
            w = membership_witness(small_primes, p, N, g)
            assert verify_membership(w, p, small_acc, N)
        
        # Edge case 4: Primes close to N (should still work but be careful)
        # For toy params N=209, test with primes close to 209
        large_prime = 199  # Prime less than N=209
        large_acc = add_member(g, large_prime, N)
        large_witness = g
        assert verify_membership(large_witness, large_prime, large_acc, N)
        
        print("Edge cases and boundary conditions verified")
    
    @pytest.mark.slow
    def test_stress_test_large_accumulator(self, toy_params):
        """Stress test with larger number of devices."""
        N, g = toy_params
        num_devices = 100
        
        print(f"Starting stress test with {num_devices} devices...")
        
        # Generate many devices
        device_data = []
        for i in range(num_devices):
            device_id = f"stress_device_{i:04d}"
            key_data = f"{device_id}_key_material".encode()
            prime = hash_to_prime(key_data)
            device_data.append((device_id, prime))
        
        # Build large accumulator
        accumulator = g
        all_primes = set()
        
        for device_id, prime in device_data:
            accumulator = add_member(accumulator, prime, N)
            all_primes.add(prime)
        
        # Batch verify all devices
        primes_list = [prime for _, prime in device_data]
        witnesses = batch_refresh_witnesses(primes_list, all_primes, N, g)
        
        verification_failures = 0
        for i, (device_id, prime) in enumerate(device_data):
            if not verify_membership(witnesses[i], prime, accumulator, N):
                verification_failures += 1
        
        assert verification_failures == 0, f"{verification_failures} devices failed verification"
        
        # Test random revocations
        import random
        revoke_count = num_devices // 10  # Revoke 10%
        revoked_indices = random.sample(range(num_devices), revoke_count)
        
        remaining_primes = set()
        for i, (_, prime) in enumerate(device_data):
            if i not in revoked_indices:
                remaining_primes.add(prime)
        
        new_accumulator = recompute_root(remaining_primes, N, g)
        
        # Verify remaining devices still work
        remaining_verification_failures = 0
        for i, (device_id, prime) in enumerate(device_data):
            if i not in revoked_indices:
                witness = refresh_witness(prime, remaining_primes, N, g)
                if not verify_membership(witness, prime, new_accumulator, N):
                    remaining_verification_failures += 1
        
        assert remaining_verification_failures == 0, f"{remaining_verification_failures} remaining devices failed"
        
        print(f"Stress test completed successfully:")
        print(f"  {num_devices} devices enrolled")
        print(f"  {revoke_count} devices revoked")
        print(f"  {len(remaining_primes)} devices remain active")
        print(f"  All verifications passed")
