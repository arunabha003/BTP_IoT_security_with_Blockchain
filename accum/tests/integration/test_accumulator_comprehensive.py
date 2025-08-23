"""
Comprehensive tests for RSA Accumulator package.

Tests cover both small-prime property tests and realistic 2048-bit operations.
"""

import pytest

from .rsa_params import load_params
from .hash_to_prime import hash_to_prime, is_prime
from .accumulator import (
    add_member,
    recompute_root,
    membership_witness,
    verify_membership,
    batch_add_members,
)
from .witness_refresh import (
    refresh_witness,
    batch_refresh_witnesses,
    update_witness_on_addition,
)


class TestHashToPrime:
    """Test hash-to-prime conversion functionality."""

    def test_hash_to_prime_deterministic(self):
        """Test that hash_to_prime is deterministic."""
        input_bytes = b"test_key_12345678901234567890123456789012"  # 32 bytes

        prime1 = hash_to_prime(input_bytes)
        prime2 = hash_to_prime(input_bytes)

        assert prime1 == prime2, "hash_to_prime should be deterministic"
        assert is_prime(prime1), "Result should be prime"

    def test_hash_to_prime_different_inputs(self):
        """Test that different inputs produce different primes."""
        input1 = b"key1" + b"\x00" * 28
        input2 = b"key2" + b"\x00" * 28

        prime1 = hash_to_prime(input1)
        prime2 = hash_to_prime(input2)

        assert prime1 != prime2, "Different inputs should produce different primes"
        assert is_prime(prime1) and is_prime(prime2), "Both results should be prime"

    def test_hash_to_prime_edge_cases(self):
        """Test hash_to_prime with edge cases."""
        # Test with minimum valid input
        prime = hash_to_prime(b"x")
        assert is_prime(prime)

        # Test with maximum typical Ed25519 key size
        large_key = b"a" * 32
        prime = hash_to_prime(large_key)
        assert is_prime(prime)

    def test_hash_to_prime_errors(self):
        """Test hash_to_prime error conditions."""
        with pytest.raises(TypeError):
            hash_to_prime("not bytes")

        with pytest.raises(ValueError):
            hash_to_prime(b"")


class TestSmallPrimeProperties:
    """Property tests with small primes for verification."""

    @pytest.fixture
    def small_params(self):
        """Small RSA parameters for testing."""
        return 35, 2  # N=35 (5*7), g=2

    def test_add_member_property(self, small_params):
        """Test add_member satisfies basic properties."""
        N, g = small_params

        # Test: adding prime p to accumulator A gives A^p mod N
        A = g
        p = 3

        result = add_member(A, p, N)
        expected = pow(A, p, N)

        assert result == expected

    def test_recompute_root_empty_set(self, small_params):
        """Test recompute_root with empty set."""
        N, g = small_params

        result = recompute_root([], N, g)
        assert result == g, "Empty set should return generator"

    def test_recompute_root_single_prime(self, small_params):
        """Test recompute_root with single prime."""
        N, g = small_params
        p = 3

        result = recompute_root([p], N, g)
        expected = pow(g, p, N)

        assert result == expected

    def test_recompute_root_multiple_primes(self, small_params):
        """Test recompute_root with multiple primes."""
        N, g = small_params
        primes = [3, 11]

        result = recompute_root(primes, N, g)
        expected = pow(g, 3 * 11, N)

        assert result == expected

    def test_membership_verification_property(self, small_params):
        """Test membership verification satisfies w^p ≡ A (mod N)."""
        N, g = small_params
        primes = [3, 11]
        target_prime = 3

        # Compute accumulator for all primes
        A = recompute_root(primes, N, g)

        # Compute witness for target_prime (exclude it)
        other_primes = [p for p in primes if p != target_prime]
        w = membership_witness(other_primes, N, g)

        # Verify: w^target_prime ≡ A (mod N)
        assert pow(w, target_prime, N) == A
        assert verify_membership(w, target_prime, A, N)

    def test_incremental_vs_batch_equivalence(self, small_params):
        """Test that incremental and batch operations are equivalent."""
        N, g = small_params
        primes = [3, 11, 13]

        # Incremental: add one by one
        A_incremental = g
        for p in primes:
            A_incremental = add_member(A_incremental, p, N)

        # Batch: add all at once
        A_batch = batch_add_members(g, primes, N)

        # Recompute: from scratch
        A_recompute = recompute_root(primes, N, g)

        assert A_incremental == A_batch == A_recompute


class TestRealWorldScenario:
    """Test with realistic 2048-bit parameters."""

    @pytest.fixture
    def real_params(self):
        """Load real 2048-bit RSA parameters."""
        return load_params()

    def test_load_params_validity(self, real_params):
        """Test that loaded parameters are valid."""
        N, g = real_params

        assert N > 0, "N must be positive"
        assert g > 0, "g must be positive"
        assert g < N, "g must be less than N"
        assert N.bit_length() >= 2040, f"N should be ~2048 bits, got {N.bit_length()}"

    def test_two_member_scenario(self, real_params):
        """Test adding 2-3 members, verify witness, remove one, verify failure."""
        N, g = real_params

        # Generate device keys and convert to primes
        device1_key = b"device1_ed25519_key_" + b"\x01" * 12  # 32 bytes
        device2_key = b"device2_ed25519_key_" + b"\x02" * 12  # 32 bytes
        device3_key = b"device3_ed25519_key_" + b"\x03" * 12  # 32 bytes

        p1 = hash_to_prime(device1_key)
        p2 = hash_to_prime(device2_key)
        p3 = hash_to_prime(device3_key)

        print(
            f"Device primes: p1={p1.bit_length()}bits, p2={p2.bit_length()}bits, p3={p3.bit_length()}bits"
        )

        # Step 1: Add 2 members
        primes_set = {p1, p2}
        A = recompute_root(primes_set, N, g)

        # Step 2: Verify both members
        w1 = membership_witness([p2], N, g)  # Witness for p1
        w2 = membership_witness([p1], N, g)  # Witness for p2

        assert verify_membership(w1, p1, A, N), "Device 1 should be verified"
        assert verify_membership(w2, p2, A, N), "Device 2 should be verified"

        # Step 3: Add third member
        primes_set.add(p3)
        A_new = recompute_root(primes_set, N, g)

        # Step 4: Verify all three members with new accumulator
        witnesses = batch_refresh_witnesses(primes_set, N, g)

        for prime in primes_set:
            assert verify_membership(
                witnesses[prime], prime, A_new, N
            ), f"Prime {prime} should verify with new accumulator"

        # Step 5: Remove one member (simulate revocation)
        revoked_prime = p2
        primes_after_revocation = primes_set - {revoked_prime}
        A_after_revocation = recompute_root(primes_after_revocation, N, g)

        # Step 6: Verify remaining members still work
        witnesses_after = batch_refresh_witnesses(primes_after_revocation, N, g)

        for prime in primes_after_revocation:
            assert verify_membership(
                witnesses_after[prime], prime, A_after_revocation, N
            ), f"Prime {prime} should verify after revocation"

        # Step 7: Verify revoked member fails with new accumulator
        old_witness_revoked = witnesses[revoked_prime]  # Old witness

        # Old witness should NOT verify with new accumulator
        assert not verify_membership(
            old_witness_revoked, revoked_prime, A_after_revocation, N
        ), "Revoked device should fail verification with new accumulator"

    def test_witness_refresh_after_addition(self, real_params):
        """Test witness refresh when new members are added."""
        N, g = real_params

        # Initial set
        device1_key = b"refresh_test_device1_" + b"\x00" * 12
        device2_key = b"refresh_test_device2_" + b"\x00" * 12

        p1 = hash_to_prime(device1_key)
        p2 = hash_to_prime(device2_key)

        initial_set = {p1, p2}
        initial_witnesses = batch_refresh_witnesses(initial_set, N, g)

        # Add new member
        device3_key = b"refresh_test_device3_" + b"\x00" * 12
        p3 = hash_to_prime(device3_key)

        updated_set = initial_set | {p3}

        # Method 1: Full refresh
        new_witnesses_full = batch_refresh_witnesses(updated_set, N, g)

        # Method 2: Incremental update
        new_witnesses_incremental = {}
        for prime in initial_set:
            old_witness = initial_witnesses[prime]
            new_witnesses_incremental[prime] = update_witness_on_addition(
                old_witness, p3, N
            )

        # Both methods should give same result
        for prime in initial_set:
            assert (
                new_witnesses_full[prime] == new_witnesses_incremental[prime]
            ), f"Full refresh and incremental update should match for prime {prime}"

        # Verify all witnesses work
        new_accumulator = recompute_root(updated_set, N, g)
        for prime in updated_set:
            witness = new_witnesses_full[prime]
            assert verify_membership(
                witness, prime, new_accumulator, N
            ), f"Witness for prime {prime} should verify"


class TestWitnessRefresh:
    """Test witness refresh functionality."""

    @pytest.fixture
    def small_params(self):
        return 35, 2  # N=35, g=2

    def test_refresh_witness_basic(self, small_params):
        """Test basic witness refresh functionality."""
        N, g = small_params
        primes_set = {3, 11, 13}
        target_prime = 11

        witness = refresh_witness(target_prime, primes_set, N, g)

        # Verify the witness
        accumulator = recompute_root(primes_set, N, g)
        assert verify_membership(witness, target_prime, accumulator, N)

    def test_refresh_witness_errors(self, small_params):
        """Test refresh_witness error conditions."""
        N, g = small_params
        primes_set = {3, 11}

        with pytest.raises(ValueError, match="not found in set_primes"):
            refresh_witness(13, primes_set, N, g)  # 13 not in set

    def test_batch_refresh_witnesses(self, small_params):
        """Test batch witness refresh."""
        N, g = small_params
        primes_set = {3, 11, 13}

        witnesses = batch_refresh_witnesses(primes_set, N, g)

        assert len(witnesses) == len(primes_set)

        accumulator = recompute_root(primes_set, N, g)
        for prime, witness in witnesses.items():
            assert verify_membership(witness, prime, accumulator, N)


class TestErrorConditions:
    """Test error handling and edge cases."""

    def test_invalid_parameters(self):
        """Test functions with invalid parameters."""
        # Test add_member with invalid params
        with pytest.raises(ValueError):
            add_member(0, 3, 35)  # A <= 0

        with pytest.raises(ValueError):
            add_member(2, 0, 35)  # p <= 0

        with pytest.raises(ValueError):
            add_member(2, 40, 35)  # p >= N

        # Test recompute_root with invalid params
        with pytest.raises(ValueError):
            recompute_root([3, 5], 0, 2)  # N <= 0

        with pytest.raises(ValueError):
            recompute_root([3, 5], 35, 40)  # g >= N

    def test_verify_membership_edge_cases(self):
        """Test verify_membership with edge cases."""
        # All parameters must be positive
        assert not verify_membership(0, 3, 8, 35)  # w <= 0
        assert not verify_membership(2, 0, 8, 35)  # p <= 0
        assert not verify_membership(2, 3, 0, 35)  # A <= 0
        assert not verify_membership(2, 3, 8, 0)  # N <= 0

        # Parameters must be less than N
        assert not verify_membership(40, 3, 8, 35)  # w >= N
        assert not verify_membership(2, 40, 8, 35)  # p >= N
        assert not verify_membership(2, 3, 40, 35)  # A >= N


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
