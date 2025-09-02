"""
Integration Tests for Trapdoor Operations

End-to-end testing of trapdoor-based device removal in RSA accumulators.
Tests the complete workflow from enrollment through removal to verification.
"""

import pytest
import math

try:
    from accum.accumulator import (
        add_member, recompute_root, membership_witness, verify_membership,
        batch_add_members
    )
    from accum.trapdoor_operations import (
        trapdoor_remove_member,
        trapdoor_batch_remove_members,
        trapdoor_remove_member_with_lambda,
        trapdoor_batch_remove_members_with_lambda,
        compute_lambda_n,
        verify_trapdoor_removal
    )
    from accum.hash_to_prime import hash_to_prime_coprime_lambda
    from accum.witness_refresh import batch_refresh_witnesses
except ImportError:
    import sys
    sys.path.append('..')
    from accumulator import (
        add_member, recompute_root, membership_witness, verify_membership,
        batch_add_members
    )
    from trapdoor_operations import (
        trapdoor_remove_member,
        trapdoor_batch_remove_members,
        trapdoor_remove_member_with_lambda,
        trapdoor_batch_remove_members_with_lambda,
        compute_lambda_n,
        verify_trapdoor_removal
    )
    from hash_to_prime import hash_to_prime_coprime_lambda
    from witness_refresh import batch_refresh_witnesses


class TestTrapdoorIntegration:
    """Integration tests for trapdoor-based device removal."""

    @pytest.fixture
    def trapdoor_params(self):
        """Fixture providing RSA trapdoor parameters for testing."""
        # Use small primes for testing: N = 11 * 19 = 209
        p, q = 11, 19
        N = p * q
        g = pow(2, 2, N)  # QR subgroup generator
        lambda_n = compute_lambda_n(p, q)

        return {
            'p': p,
            'q': q,
            'N': N,
            'g': g,
            'lambda_n': lambda_n
        }

    @pytest.fixture
    def real_trapdoor_params(self):
        """Fixture providing real cryptographic RSA trapdoor parameters for testing."""
        # Real 2048-bit RSA parameters provided by user
        N_hex = "0xc09f09d858a2037ca76e7b1c52543a002213c8f1086a587f41f9616ac4fd8d6ecbec8852fd95adaec50c34cde7f0e676059896c2be9f2e479297a7507f1d1e58afe26be99489b798a704f1627b8e6b09b9a88b01ce697c4197bbeec134bb41aac0579c8026deec542c6965b0b8d39e77405a65110af3774f88cd463c6c304483c6f0a802f288c8ba4f071b6afcefa2b9395e2fe71aaea8e277c06b5d2724153c4a20209c06f2e0f523fb96b576a37937fb340478e86bbbfa8914c50f0f33a8948836caf99ca5f7f6983787a25e091d9591204dbb8c14e473d172f4e7a0b5164cf9ee97f838ded82fd2357a51a6f495850ef268009e7ecc19047f8e99a91a4d9b"
        p_hex = "0xdf22790cd88f9990d0a35fbb128adc6f0a4702c9cd9a1956aa5b54bd223105c78d23feff9cd95b67acf71355468304fa5f5673cb7bead0c24b45dbc934b63029b0f0261b6aba63b315fbfb112075987c00f9976cd5b0bc5378704fb1f734f4e9defbfe047c279c9cd4a62a7fbd8cdd85a4292cfe520d975fcf344a1c20b8181b"
        q_hex = "0xdcfe0670e3010b530afa4de7bd17f9b2829464cb5b1f2b8e0712e585d6ef0852ddfc4b50bb133a09247887788f0e6496cfdee573672b486662374e4d88fb6d1c707aa50c765b99c1c8dad9e47452cf95e5f839fb747bb746be625e9078ca3bf3b357abaa4e683c03f74c61a34f52da82ca604d1bbe50d19621a92c3fc6b4f881"

        p = int(p_hex, 16)
        q = int(q_hex, 16)
        N = int(N_hex, 16)

        # Verify N = p * q
        assert N == p * q, "N should equal p * q"

        # Use safe generator (typically 2 or 4 work well for RSA accumulators)
        g = 4  # Fixed small generator for real parameters

        lambda_n = compute_lambda_n(p, q)

        return {
            'p': p,
            'q': q,
            'N': N,
            'g': g,
            'lambda_n': lambda_n
        }

    def test_single_device_trapdoor_removal_end_to_end(self, trapdoor_params):
        """Test complete workflow: enroll devices → remove one via trapdoor → verify."""
        p, q, N, g, lambda_n = trapdoor_params['p'], trapdoor_params['q'], trapdoor_params['N'], trapdoor_params['g'], trapdoor_params['lambda_n']

        # Step 1: Enroll devices and build accumulator
        device_ids = [b'device_1', b'device_2', b'device_3', b'device_4']
        # Use hardcoded primes that are coprime to λ(N)=90 for reliable testing
        # λ(N)=90 = 2*3^2*5, so avoid primes 2, 3, 5 and their multiples
        device_primes = [7, 13, 17, 19]  # All coprime to 90

        # Build accumulator incrementally
        A = g
        for prime in device_primes:
            A = add_member(A, prime, N)

        # Step 2: Remove one device using trapdoor (p,q method)
        device_to_remove = 1  # Remove device_2
        prime_to_remove = device_primes[device_to_remove]
        A_old = A

        A_new = trapdoor_remove_member(A_old, prime_to_remove, N, p, q)

        # Step 3: Verify removal correctness
        # 3a. Use verify_trapdoor_removal
        assert verify_trapdoor_removal(A_old, A_new, prime_to_remove, N), \
            "Trapdoor removal verification failed"

        # 3b. Compare with recomputation
        remaining_primes = device_primes[:device_to_remove] + device_primes[device_to_remove + 1:]
        A_recomputed = recompute_root(remaining_primes, N, g)
        assert A_new == A_recomputed, \
            f"A_new ({A_new}) != A_recomputed ({A_recomputed})"

        # Step 4: Verify witnesses for remaining devices
        remaining_device_ids = device_ids[:device_to_remove] + device_ids[device_to_remove + 1:]
        remaining_device_primes = device_primes[:device_to_remove] + device_primes[device_to_remove + 1:]

        for i, (device_id, prime) in enumerate(zip(remaining_device_ids, remaining_device_primes)):
            # Generate witness for this device
            witness = membership_witness(set(remaining_device_primes), prime, N, g)

            # Verify membership
            is_member = verify_membership(witness, prime, A_new, N)
            assert is_member, f"Device {device_id} witness verification failed after removal"

    def test_batch_trapdoor_removal_end_to_end(self, trapdoor_params):
        """Test batch removal workflow using trapdoor operations."""
        p, q, N, g, lambda_n = trapdoor_params['p'], trapdoor_params['q'], trapdoor_params['N'], trapdoor_params['g'], trapdoor_params['lambda_n']

        # Step 1: Enroll devices
        device_ids = [b'device_1', b'device_2', b'device_3', b'device_4', b'device_5']
        # Use hardcoded primes that are coprime to λ(N)=90
        device_primes = [7, 11, 13, 17, 19]  # All coprime to 90

        # Build accumulator
        A = g
        for prime in device_primes:
            A = add_member(A, prime, N)

        # Step 2: Remove multiple devices using trapdoor batch removal
        devices_to_remove_indices = [1, 3]  # Remove device_2 and device_4
        primes_to_remove = [device_primes[i] for i in devices_to_remove_indices]
        A_old = A

        A_new = trapdoor_batch_remove_members(A_old, primes_to_remove, N, p, q)

        # Step 3: Verify batch removal
        remaining_indices = [i for i in range(len(device_primes)) if i not in devices_to_remove_indices]
        remaining_primes = [device_primes[i] for i in remaining_indices]

        # Verify via recomputation
        A_recomputed = recompute_root(remaining_primes, N, g)
        assert A_new == A_recomputed, \
            f"Batch removal failed: A_new ({A_new}) != A_recomputed ({A_recomputed})"

        # Step 4: Verify remaining device witnesses
        remaining_device_ids = [device_ids[i] for i in remaining_indices]

        for i, (device_id, prime) in enumerate(zip(remaining_device_ids, remaining_primes)):
            witness = membership_witness(set(remaining_primes), prime, N, g)
            is_member = verify_membership(witness, prime, A_new, N)
            assert is_member, f"Device {device_id} witness verification failed after batch removal"

    def test_lambda_only_trapdoor_removal(self, trapdoor_params):
        """Test trapdoor removal using λ(N)-only convenience functions."""
        p, q, N, g, lambda_n = trapdoor_params['p'], trapdoor_params['q'], trapdoor_params['N'], trapdoor_params['g'], trapdoor_params['lambda_n']

        # Step 1: Setup devices
        device_ids = [b'device_alpha', b'device_beta', b'device_gamma']
        # Use hardcoded primes that are coprime to λ(N)=90
        device_primes = [7, 13, 17]  # All coprime to 90

        # Build accumulator
        A = g
        for prime in device_primes:
            A = add_member(A, prime, N)

        # Step 2: Remove using λ(N)-only function
        prime_to_remove = device_primes[1]  # Remove device_beta
        A_old = A

        A_new = trapdoor_remove_member_with_lambda(A_old, prime_to_remove, N, lambda_n)

        # Step 3: Verify removal
        remaining_primes = device_primes[:1] + device_primes[2:]
        A_recomputed = recompute_root(remaining_primes, N, g)

        assert A_new == A_recomputed, \
            f"λ(N)-only removal failed: A_new ({A_new}) != A_recomputed ({A_recomputed})"

        # Verify trapdoor removal verification
        assert verify_trapdoor_removal(A_old, A_new, prime_to_remove, N), \
            "Trapdoor removal verification failed for λ(N)-only method"

    def test_batch_lambda_only_trapdoor_removal(self, trapdoor_params):
        """Test batch removal using λ(N)-only convenience functions."""
        p, q, N, g, lambda_n = trapdoor_params['p'], trapdoor_params['q'], trapdoor_params['N'], trapdoor_params['g'], trapdoor_params['lambda_n']

        # Step 1: Setup devices
        device_ids = [b'device_A', b'device_B', b'device_C', b'device_D']
        # Use hardcoded primes that are coprime to λ(N)=90
        device_primes = [7, 11, 13, 17]  # All coprime to 90

        # Build accumulator
        A = batch_add_members(g, device_primes, N)

        # Step 2: Batch remove using λ(N)-only function
        primes_to_remove = [device_primes[0], device_primes[2]]  # Remove A and C
        A_old = A

        A_new = trapdoor_batch_remove_members_with_lambda(A_old, primes_to_remove, N, lambda_n)

        # Step 3: Verify batch removal
        remaining_primes = [device_primes[1], device_primes[3]]  # B and D remain
        A_recomputed = recompute_root(remaining_primes, N, g)

        assert A_new == A_recomputed, \
            f"λ(N)-only batch removal failed: A_new ({A_new}) != A_recomputed ({A_recomputed})"

    def test_trapdoor_removal_negative_case(self, trapdoor_params):
        """Test that trapdoor removal fails for primes that share factors with λ(N)."""
        p, q, N, g, lambda_n = trapdoor_params['p'], trapdoor_params['q'], trapdoor_params['N'], trapdoor_params['g'], trapdoor_params['lambda_n']

        # λ(N) = lcm(p-1, q-1) = lcm(10, 18) = 90 = 2 * 3^2 * 5
        # So primes that share factors with 90 (2, 3, 5) should fail

        # Step 1: Setup a valid accumulator
        valid_prime = 7  # Coprime to λ(N)=90
        A = add_member(g, valid_prime, N)

        # Step 2: Try to remove a prime that shares a factor with λ(N)
        # Try prime 5 (shares factor 5 with λ(N) = 90)
        problematic_prime = 5

        # This should fail because 5 shares a factor with λ(N)
        with pytest.raises(ValueError, match="Cannot compute modular inverse"):
            trapdoor_remove_member(A, problematic_prime, N, p, q)

        # Also test with λ(N)-only function
        with pytest.raises(ValueError, match="Cannot compute modular inverse"):
            trapdoor_remove_member_with_lambda(A, problematic_prime, N, lambda_n)

        # Step 3: Verify that a prime coprime to λ(N) works
        # valid_prime was generated to be coprime to λ(N), so removal should work
        A_new = trapdoor_remove_member_with_lambda(A, valid_prime, N, lambda_n)

        # Verify removal
        A_empty = g  # Should be back to generator
        assert A_new == A_empty, "Removal of valid prime should restore to generator"

    def test_witness_consistency_after_trapdoor_removal(self, trapdoor_params):
        """Test that witnesses remain consistent after trapdoor removal."""
        p, q, N, g, lambda_n = trapdoor_params['p'], trapdoor_params['q'], trapdoor_params['N'], trapdoor_params['g'], trapdoor_params['lambda_n']

        # Step 1: Setup multiple devices
        device_ids = [f'device_{i}'.encode() for i in range(5)]
        # Use hardcoded primes that are coprime to λ(N)=90
        device_primes = [7, 11, 13, 17, 19]  # All coprime to 90

        # Build accumulator
        A = batch_add_members(g, device_primes, N)

        # Generate initial witnesses
        initial_witnesses = batch_refresh_witnesses(set(device_primes), N, g)

        # Step 2: Remove one device via trapdoor
        device_to_remove = 2  # Remove device_2
        prime_to_remove = device_primes[device_to_remove]

        A_new = trapdoor_remove_member_with_lambda(A, prime_to_remove, N, lambda_n)

        # Step 3: Generate new witnesses for remaining devices
        remaining_primes = device_primes[:device_to_remove] + device_primes[device_to_remove + 1:]
        new_witnesses = batch_refresh_witnesses(set(remaining_primes), N, g)

        # Step 4: Verify all remaining witnesses work with new accumulator
        for i, prime in enumerate(remaining_primes):
            # Get witness from batch refresh
            witness_from_batch = new_witnesses[prime]

            # Verify membership
            is_member = verify_membership(witness_from_batch, prime, A_new, N)
            assert is_member, f"Witness verification failed for remaining prime {prime}"

            # Also verify that the new witness is different from the old one (should be updated)
            old_witness = initial_witnesses[prime]
            assert old_witness != witness_from_batch, \
                f"Witness for prime {prime} was not updated after removal"

    def test_trapdoor_vs_recomputation_equivalence(self, trapdoor_params):
        """Test that trapdoor removal gives same result as recomputation."""
        p, q, N, g, lambda_n = trapdoor_params['p'], trapdoor_params['q'], trapdoor_params['N'], trapdoor_params['g'], trapdoor_params['lambda_n']

        # Step 1: Setup devices
        device_ids = [f'test_device_{i}'.encode() for i in range(10)]
        # Use hardcoded primes that are coprime to λ(N)=90
        device_primes = [7, 11, 13, 17, 19, 23, 29, 31, 37, 41]  # All coprime to 90

        # Build accumulator
        A = batch_add_members(g, device_primes, N)

        # Step 2: Remove devices using both methods and compare
        for remove_count in [1, 2, 3]:
            primes_to_remove = device_primes[:remove_count]
            remaining_primes = device_primes[remove_count:]

            # Method 1: Trapdoor batch removal
            A_trapdoor = trapdoor_batch_remove_members_with_lambda(A, primes_to_remove, N, lambda_n)

            # Method 2: Recomputation from scratch
            A_recomputed = recompute_root(remaining_primes, N, g)

            # They should be identical
            assert A_trapdoor == A_recomputed, \
                f"Trapdoor and recomputation differ for {remove_count} removals: {A_trapdoor} != {A_recomputed}"

            # Verify via trapdoor verification for the batch operation
            # For batch removal, we verify that A_trapdoor^(product of removed primes) ≡ A (mod N)
            if primes_to_remove:
                from functools import reduce
                product_removed = reduce(lambda x, y: x * y, primes_to_remove)
                assert verify_trapdoor_removal(A, A_trapdoor, product_removed, N), \
                    f"Trapdoor verification failed for batch removal of primes {primes_to_remove}"

    @pytest.mark.slow
    def test_single_device_trapdoor_removal_real_params(self, real_trapdoor_params):
        """Test trapdoor removal with real 2048-bit cryptographic parameters."""
        p, q, N, g, lambda_n = real_trapdoor_params['p'], real_trapdoor_params['q'], real_trapdoor_params['N'], real_trapdoor_params['g'], real_trapdoor_params['lambda_n']

        # Use smaller device set for real parameters (computationally expensive)
        device_ids = [b'device_real_1', b'device_real_2', b'device_real_3']
        device_primes = [7, 13, 17]  # Small primes coprime to λ(N)

        # Build accumulator
        A = g
        for prime in device_primes:
            A = add_member(A, prime, N)

        # Remove one device using trapdoor
        prime_to_remove = device_primes[1]  # Remove device_real_2
        A_old = A

        A_new = trapdoor_remove_member(A_old, prime_to_remove, N, p, q)

        # Verify removal
        remaining_primes = [device_primes[0], device_primes[2]]
        A_recomputed = recompute_root(remaining_primes, N, g)

        assert A_new == A_recomputed, \
            f"Real params trapdoor removal failed: A_new != A_recomputed"

        # Verify trapdoor removal verification
        assert verify_trapdoor_removal(A_old, A_new, prime_to_remove, N), \
            "Trapdoor verification failed for real parameters"

        # Verify remaining device witnesses
        for prime in remaining_primes:
            witness = membership_witness(set(remaining_primes), prime, N, g)
            is_member = verify_membership(witness, prime, A_new, N)
            assert is_member, f"Witness verification failed for prime {prime} with real parameters"

    @pytest.mark.slow
    def test_batch_trapdoor_removal_real_params(self, real_trapdoor_params):
        """Test batch trapdoor removal with real 2048-bit cryptographic parameters."""
        p, q, N, g, lambda_n = real_trapdoor_params['p'], real_trapdoor_params['q'], real_trapdoor_params['N'], real_trapdoor_params['g'], real_trapdoor_params['lambda_n']

        # Use small device set for real parameters
        device_primes = [7, 11, 13, 17]  # All coprime to λ(N)

        # Build accumulator
        A = batch_add_members(g, device_primes, N)

        # Remove multiple devices using trapdoor batch removal
        primes_to_remove = [device_primes[0], device_primes[2]]  # Remove first and third
        A_old = A

        A_new = trapdoor_batch_remove_members(A_old, primes_to_remove, N, p, q)

        # Verify batch removal
        remaining_primes = [device_primes[1], device_primes[3]]
        A_recomputed = recompute_root(remaining_primes, N, g)

        assert A_new == A_recomputed, \
            f"Real params batch trapdoor removal failed: A_new != A_recomputed"

    @pytest.mark.slow
    def test_lambda_trapdoor_removal_real_params(self, real_trapdoor_params):
        """Test λ(N)-only trapdoor removal with real 2048-bit cryptographic parameters."""
        p, q, N, g, lambda_n = real_trapdoor_params['p'], real_trapdoor_params['q'], real_trapdoor_params['N'], real_trapdoor_params['g'], real_trapdoor_params['lambda_n']

        # Use small device set for real parameters
        device_primes = [7, 13, 17]  # All coprime to λ(N)

        # Build accumulator
        A = batch_add_members(g, device_primes, N)

        # Remove using λ(N)-only function
        prime_to_remove = device_primes[1]
        A_old = A

        A_new = trapdoor_remove_member_with_lambda(A_old, prime_to_remove, N, lambda_n)

        # Verify removal
        remaining_primes = [device_primes[0], device_primes[2]]
        A_recomputed = recompute_root(remaining_primes, N, g)

        assert A_new == A_recomputed, \
            f"Real params λ(N) trapdoor removal failed: A_new != A_recomputed"

        # Verify trapdoor removal verification
        assert verify_trapdoor_removal(A_old, A_new, prime_to_remove, N), \
            "Trapdoor verification failed for λ(N) method with real parameters"

    @pytest.mark.slow
    def test_trapdoor_negative_case_real_params(self, real_trapdoor_params):
        """Test trapdoor removal failure cases with real 2048-bit parameters."""
        p, q, N, g, lambda_n = real_trapdoor_params['p'], real_trapdoor_params['q'], real_trapdoor_params['N'], real_trapdoor_params['g'], real_trapdoor_params['lambda_n']

        # Setup valid accumulator
        valid_prime = 7  # Coprime to λ(N)
        A = add_member(g, valid_prime, N)

        # Test removal of prime that shares factors with λ(N)
        # λ(N) = lcm(p-1, q-1) will definitely have factors that divide many numbers
        problematic_prime = p - 1  # This will share factors with λ(N)

        # This should fail
        with pytest.raises(ValueError, match="Cannot compute modular inverse"):
            trapdoor_remove_member(A, problematic_prime, N, p, q)

        # Also test with λ(N)-only function
        with pytest.raises(ValueError, match="Cannot compute modular inverse"):
            trapdoor_remove_member_with_lambda(A, problematic_prime, N, lambda_n)

    @pytest.mark.slow
    def test_accumulator_properties_real_params(self, real_trapdoor_params):
        """Test fundamental accumulator properties with real 2048-bit parameters."""
        p, q, N, g, lambda_n = real_trapdoor_params['p'], real_trapdoor_params['q'], real_trapdoor_params['N'], real_trapdoor_params['g'], real_trapdoor_params['lambda_n']

        # Test basic accumulator operations
        device_primes = [7, 13, 17, 19]  # Small primes coprime to λ(N)

        # Test incremental vs batch addition
        A_incremental = g
        for prime in device_primes:
            A_incremental = add_member(A_incremental, prime, N)

        A_batch = batch_add_members(g, device_primes, N)

        assert A_incremental == A_batch, \
            "Incremental and batch addition should produce same result with real parameters"

        # Test recomputation
        A_recomputed = recompute_root(device_primes, N, g)

        assert A_incremental == A_recomputed, \
            "Incremental and recomputed accumulators should match with real parameters"

        # Test witness properties
        for i, prime in enumerate(device_primes):
            witness = membership_witness(set(device_primes), prime, N, g)
            is_member = verify_membership(witness, prime, A_incremental, N)
            assert is_member, f"Witness verification failed for prime {prime} with real parameters"
