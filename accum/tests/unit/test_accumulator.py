"""
Unit Tests for RSA Accumulator Core Module

Tests the core RSA accumulator operations: add_member, recompute_root, 
membership_witness, and verify_membership.
"""

import os
import pytest
from typing import Set

try:
    from accum.accumulator import (
        add_member, recompute_root, membership_witness, verify_membership,
        remove_member, batch_remove_members, batch_add_members
    )
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from accumulator import (
        add_member, recompute_root, membership_witness, verify_membership,
        remove_member, batch_remove_members, batch_add_members
    )


def generate_demo_params():
    """Generate demo RSA parameters for testing."""
    # Use small primes for testing
    p, q = 11, 19
    N = p * q  # N = 209
    # Use QR base: g = h^2 mod N (h=2 -> g=4)
    g = pow(2, 2, N)  # g = 4, ensuring g is in quadratic residue subgroup
    return N, g


class TestAccumulatorCore:
    """Test core RSA accumulator mathematical operations."""
    
    @pytest.fixture
    def toy_params(self):
        """Provide toy RSA parameters for testing."""
        return generate_demo_params()  # N=209, g=4
    
    def test_add_member_basic(self, toy_params):
        """Test basic member addition to accumulator."""
        N, g = toy_params
        A = g
        p = 13
        
        # Add member
        A_new = add_member(A, p, N)
        
        # Should compute A^p mod N
        expected = pow(A, p, N)
        assert A_new == expected
        assert A_new != A  # Should change the accumulator
    
    def test_add_member_multiple(self, toy_params):
        """Test adding multiple members sequentially."""
        N, g = toy_params
        A = g
        primes = [13, 17, 23]
        
        # Add members one by one
        for p in primes:
            A = add_member(A, p, N)
        
        # Should equal g^(13*17*23) mod N
        product = 1
        for p in primes:
            product *= p
        expected = pow(g, product, N)
        
        assert A == expected
    
    def test_add_member_validation(self, toy_params):
        """Test add_member input validation."""
        N, g = toy_params
        
        # Invalid parameters
        with pytest.raises(ValueError, match="All parameters must be positive"):
            add_member(0, 13, N)

        with pytest.raises(ValueError, match="All parameters must be positive"):
            add_member(-1, 13, N)

        # Invalid prime
        with pytest.raises(ValueError, match="All parameters must be positive"):
            add_member(g, 0, N)

        with pytest.raises(ValueError, match="All parameters must be positive"):
            add_member(g, -1, N)

        # Invalid modulus
        with pytest.raises(ValueError, match="All parameters must be positive"):
            add_member(g, 13, 0)

        with pytest.raises(ValueError, match="All parameters must be positive"):
            add_member(g, 13, -1)
    
    def test_recompute_root_empty_set(self, toy_params):
        """Test recomputing root with empty prime set."""
        N, g = toy_params
        
        root = recompute_root(set(), N, g)
        assert root == g  # Empty set should give generator
    
    def test_recompute_root_single_prime(self, toy_params):
        """Test recomputing root with single prime."""
        N, g = toy_params
        primes = {13}
        
        root = recompute_root(primes, N, g)
        expected = pow(g, 13, N)
        assert root == expected
    
    def test_recompute_root_multiple_primes(self, toy_params):
        """Test recomputing root with multiple primes."""
        N, g = toy_params
        primes = {13, 17, 23}
        
        root = recompute_root(primes, N, g)
        
        # Should equal g^(13*17*23) mod N
        product = 13 * 17 * 23
        expected = pow(g, product, N)
        assert root == expected
    
    def test_recompute_root_order_independence(self, toy_params):
        """Test that recompute_root is independent of prime order."""
        N, g = toy_params
        primes1 = {13, 17, 23}
        primes2 = {23, 13, 17}  # Different order
        
        root1 = recompute_root(primes1, N, g)
        root2 = recompute_root(primes2, N, g)
        
        assert root1 == root2
    
    def test_recompute_root_validation(self, toy_params):
        """Test recompute_root input validation."""
        N, g = toy_params
        
        # Invalid parameters
        with pytest.raises(ValueError, match="N and g must be positive"):
            recompute_root({13}, 0, g)

        # Invalid generator
        with pytest.raises(ValueError, match="N and g must be positive"):
            recompute_root({13}, N, 0)

        # Invalid prime in set
        with pytest.raises(ValueError, match="All primes must be positive"):
            recompute_root({0}, N, g)

        with pytest.raises(ValueError, match="All primes must be positive"):
            recompute_root({13, -1}, N, g)
    
    def test_membership_witness_single_member(self, toy_params):
        """Test witness generation for single member."""
        N, g = toy_params
        current_primes = set()  # No other members
        p = 13
        
        witness = membership_witness(current_primes, p, N, g)
        assert witness == g  # Witness should be generator for single member
    
    def test_membership_witness_multiple_members(self, toy_params):
        """Test witness generation with multiple members."""
        N, g = toy_params
        current_primes = {13, 17, 23}
        p = 17  # Target member
        
        witness = membership_witness(current_primes, p, N, g)
        
        # Witness should be g^(13*23) mod N (product excluding p)
        other_primes_product = 13 * 23
        expected = pow(g, other_primes_product, N)
        assert witness == expected
    
    def test_membership_witness_target_not_in_set(self, toy_params):
        """Test witness generation when target prime is not in current set."""
        N, g = toy_params
        current_primes = {13, 17}
        p = 23  # Not in current_primes
        
        witness = membership_witness(current_primes, p, N, g)
        
        # Should compute witness for all current primes
        product = 13 * 17
        expected = pow(g, product, N)
        assert witness == expected
    
    def test_membership_witness_validation(self, toy_params):
        """Test membership_witness input validation."""
        N, g = toy_params
        
        # Invalid target prime
        with pytest.raises(ValueError, match="Target prime 0 must be greater than 1"):
            membership_witness({13}, 0, N, g)

        # Invalid parameters
        with pytest.raises(ValueError, match="N and g must be positive"):
            membership_witness({13}, 17, 0, g)
        
        # Invalid generator
        with pytest.raises(ValueError, match="N and g must be positive"):
            membership_witness({13}, 17, N, 0)
    
    def test_verify_membership_valid_proof(self, toy_params):
        """Test membership verification with valid proof."""
        N, g = toy_params
        
        # Set up accumulator with primes {13, 17, 23}
        primes = {13, 17, 23}
        A = recompute_root(primes, N, g)
        
        # Generate witness for prime 17
        w = membership_witness(primes, 17, N, g)
        
        # Verify membership
        is_member = verify_membership(w, 17, A, N)
        assert is_member is True
    
    def test_verify_membership_invalid_proof(self, toy_params):
        """Test membership verification with invalid proof."""
        N, g = toy_params
        
        # Set up accumulator with primes {13, 17}
        primes = {13, 17}
        A = recompute_root(primes, N, g)
        
        # Try to verify membership of prime 23 (not in accumulator)
        fake_witness = pow(g, 13 * 17, N)  # Wrong witness
        is_member = verify_membership(fake_witness, 23, A, N)
        assert is_member is False
    
    def test_verify_membership_wrong_witness(self, toy_params):
        """Test membership verification with wrong witness."""
        N, g = toy_params
        
        # Set up accumulator
        primes = {13, 17, 23}
        A = recompute_root(primes, N, g)
        
        # Use wrong witness (for different prime)
        wrong_witness = membership_witness(primes, 13, N, g)
        
        # Try to verify with wrong witness
        is_member = verify_membership(wrong_witness, 17, A, N)
        assert is_member is False
    
    def test_verify_membership_validation(self, toy_params):
        """Test verify_membership input validation."""
        N, g = toy_params
        A = pow(g, 13, N)
        w = g

        # Invalid inputs should return False (not raise exceptions)
        assert verify_membership(0, 13, A, N) == False  # Invalid witness
        assert verify_membership(w, 0, A, N) == False  # Invalid prime
        assert verify_membership(w, 13, 0, N) == False  # Invalid accumulator
        assert verify_membership(w, 13, A, 0) == False  # Invalid modulus
    
    def test_incremental_vs_batch_equivalence(self, toy_params):
        """Test that incremental and batch accumulator computation are equivalent."""
        N, g = toy_params
        primes = [13, 17, 23, 29]
        
        # Incremental computation
        A_incremental = g
        for p in primes:
            A_incremental = add_member(A_incremental, p, N)
        
        # Batch computation
        A_batch = recompute_root(set(primes), N, g)
        
        assert A_incremental == A_batch
    
    def test_accumulator_mathematical_property(self, toy_params):
        """Test fundamental accumulator mathematical property."""
        N, g = toy_params
        primes = {13, 17, 23}
        
        # Compute accumulator
        A = recompute_root(primes, N, g)
        
        # For each prime, verify w^p = A (mod N)
        for p in primes:
            w = membership_witness(primes, p, N, g)
            assert pow(w, p, N) == A
    
    def test_accumulator_commutativity(self, toy_params):
        """Test that accumulator addition is commutative."""
        N, g = toy_params
        
        # Add primes in different orders
        A1 = add_member(add_member(g, 13, N), 17, N)
        A2 = add_member(add_member(g, 17, N), 13, N)
        
        assert A1 == A2
    
    def test_accumulator_associativity(self, toy_params):
        """Test that accumulator addition is associative."""
        N, g = toy_params
        
        # Different groupings should give same result
        A1 = add_member(add_member(add_member(g, 13, N), 17, N), 23, N)
        A2 = batch_add_members(g, [13, 17, 23], N)  # Batch computation

        assert A1 == A2


class TestAccumulatorRemoval:
    """Test RSA accumulator removal operations with trapdoor."""
    
    @pytest.fixture
    def toy_params_with_trapdoor(self):
        """Provide toy RSA parameters with trapdoor information."""
        p, q = 11, 19  # Small primes for testing
        N = p * q  # N = 209
        g = 2
        trapdoor = (p, q)
        return N, g, trapdoor
    
    def test_remove_member_basic(self, toy_params_with_trapdoor):
        """Test basic member removal with trapdoor."""
        N, g, trapdoor = toy_params_with_trapdoor
        
        # Create accumulator with primes coprime to λ(N) = 90
        primes = [7, 13, 17]  # All coprime to 90 = 2 * 3^2 * 5
        A = g
        for prime in primes:
            A = add_member(A, prime, N)
        
        # Remove prime 13
        A_new = remove_member(A, 13, N, trapdoor)
        
        # Verify by recomputing from remaining primes
        remaining_primes = [7, 17]
        expected_A = recompute_root(remaining_primes, N, g)
        assert A_new == expected_A
        
        # Verify removal property: A_new^13 ≡ A (mod N)
        assert pow(A_new, 13, N) == A
    
    def test_remove_member_single_prime(self, toy_params_with_trapdoor):
        """Test removing single prime from accumulator."""
        N, g, trapdoor = toy_params_with_trapdoor
        
        # Create accumulator with single prime
        prime = 17
        A = add_member(g, prime, N)
        
        # Remove the prime
        A_new = remove_member(A, prime, N, trapdoor)
        
        # Should get back to generator
        assert A_new == g
    
    def test_remove_member_without_trapdoor(self, toy_params_with_trapdoor):
        """Test that removal without trapdoor raises NotImplementedError."""
        N, g, _ = toy_params_with_trapdoor
        A = add_member(g, 7, N)
        
        with pytest.raises(NotImplementedError, match="Direct removal requires trapdoor"):
            remove_member(A, 7, N)  # No trapdoor provided
    
    def test_remove_member_problematic_prime(self, toy_params_with_trapdoor):
        """Test removal of prime that shares factors with λ(N)."""
        N, g, trapdoor = toy_params_with_trapdoor
        # λ(N) = 90 = 2 * 3^2 * 5
        
        # Create accumulator with prime 5 (which divides λ(N))
        A = add_member(g, 5, N)
        
        # Should fail to remove prime 5
        with pytest.raises(ValueError, match="Cannot compute modular inverse"):
            remove_member(A, 5, N, trapdoor)
    
    def test_remove_member_invalid_inputs(self, toy_params_with_trapdoor):
        """Test removal with invalid inputs."""
        N, g, trapdoor = toy_params_with_trapdoor
        A = add_member(g, 7, N)
        
        # Invalid A
        with pytest.raises(ValueError):
            remove_member(-1, 7, N, trapdoor)
        
        # Invalid prime
        with pytest.raises(ValueError):
            remove_member(A, -1, N, trapdoor)
        
        # Invalid N
        with pytest.raises(ValueError):
            remove_member(A, 7, -1, trapdoor)
        
        # Prime too large
        with pytest.raises(ValueError):
            remove_member(A, N + 1, N, trapdoor)


class TestAccumulatorBatchRemoval:
    """Test RSA accumulator batch removal operations."""
    
    @pytest.fixture
    def toy_params_with_trapdoor(self):
        """Provide toy RSA parameters with trapdoor information."""
        p, q = 11, 19  # Small primes for testing
        N = p * q  # N = 209
        g = 2
        trapdoor = (p, q)
        return N, g, trapdoor
    
    def test_batch_remove_members_basic(self, toy_params_with_trapdoor):
        """Test basic batch removal."""
        N, g, trapdoor = toy_params_with_trapdoor
        
        # Create accumulator with multiple primes
        primes = [7, 11, 13, 17]  # All coprime to λ(N) = 90
        A = g
        for prime in primes:
            A = add_member(A, prime, N)
        
        # Remove multiple primes
        primes_to_remove = [11, 17]
        A_new = batch_remove_members(A, primes_to_remove, N, trapdoor)
        
        # Verify by recomputing from remaining primes
        remaining_primes = [7, 13]
        expected_A = recompute_root(remaining_primes, N, g)
        assert A_new == expected_A
    
    def test_batch_remove_members_empty_list(self, toy_params_with_trapdoor):
        """Test batch removal with empty list."""
        N, g, trapdoor = toy_params_with_trapdoor
        A = add_member(g, 7, N)
        
        # Remove nothing
        A_new = batch_remove_members(A, [], N, trapdoor)
        assert A_new == A
    
    def test_batch_remove_members_all_primes(self, toy_params_with_trapdoor):
        """Test removing all primes from accumulator."""
        N, g, trapdoor = toy_params_with_trapdoor
        
        # Create accumulator with primes
        primes = [7, 13]
        A = g
        for prime in primes:
            A = add_member(A, prime, N)
        
        # Remove all primes
        A_new = batch_remove_members(A, primes, N, trapdoor)
        
        # Should get back to generator
        assert A_new == g
    
    def test_batch_remove_members_without_trapdoor(self, toy_params_with_trapdoor):
        """Test that batch removal without trapdoor raises NotImplementedError."""
        N, g, _ = toy_params_with_trapdoor
        A = add_member(add_member(g, 7, N), 13, N)
        
        with pytest.raises(NotImplementedError, match="Batch removal requires trapdoor"):
            batch_remove_members(A, [7, 13], N)  # No trapdoor provided
    
    def test_batch_remove_vs_sequential_equivalence(self, toy_params_with_trapdoor):
        """Test that batch removal equals sequential removal."""
        N, g, trapdoor = toy_params_with_trapdoor
        
        # Create accumulator with multiple primes
        primes = [7, 13, 17, 23]  # All coprime to λ(N) = 90
        A = g
        for prime in primes:
            A = add_member(A, prime, N)
        
        primes_to_remove = [13, 23]
        
        # Method 1: Batch removal
        A_batch = batch_remove_members(A, primes_to_remove, N, trapdoor)
        
        # Method 2: Sequential removal
        A_sequential = A
        for prime in primes_to_remove:
            A_sequential = remove_member(A_sequential, prime, N, trapdoor)
        
        assert A_batch == A_sequential


class TestAccumulatorAddRemoveCycle:
    """Test add/remove cycles maintain mathematical correctness."""
    
    @pytest.fixture
    def toy_params_with_trapdoor(self):
        """Provide toy RSA parameters with trapdoor information."""
        p, q = 11, 19  # Small primes for testing
        N = p * q  # N = 209
        g = 2
        trapdoor = (p, q)
        return N, g, trapdoor
    
    def test_add_remove_cycle(self, toy_params_with_trapdoor):
        """Test that adding then removing a prime returns to original state."""
        N, g, trapdoor = toy_params_with_trapdoor
        
        # Start with some primes
        initial_primes = [7, 17]
        A_initial = recompute_root(initial_primes, N, g)
        
        # Add a prime
        new_prime = 13
        A_after_add = add_member(A_initial, new_prime, N)
        
        # Remove the same prime
        A_after_remove = remove_member(A_after_add, new_prime, N, trapdoor)
        
        # Should return to initial state
        assert A_after_remove == A_initial
    
    def test_remove_add_cycle(self, toy_params_with_trapdoor):
        """Test that removing then adding a prime returns to original state."""
        N, g, trapdoor = toy_params_with_trapdoor
        
        # Start with some primes
        initial_primes = [7, 13, 17]
        A_initial = recompute_root(initial_primes, N, g)
        
        # Remove a prime
        prime_to_remove = 13
        A_after_remove = remove_member(A_initial, prime_to_remove, N, trapdoor)
        
        # Add the same prime back
        A_after_add = add_member(A_after_remove, prime_to_remove, N)
        
        # Should return to initial state
        assert A_after_add == A_initial
    
    def test_batch_add_remove_cycle(self, toy_params_with_trapdoor):
        """Test batch add/remove cycle maintains correctness."""
        N, g, trapdoor = toy_params_with_trapdoor
        
        # Start with some primes
        initial_primes = [7, 17]
        A_initial = recompute_root(initial_primes, N, g)
        
        # Add multiple primes
        primes_to_add = [13, 23]
        A_after_batch_add = A_initial
        for prime in primes_to_add:
            A_after_batch_add = add_member(A_after_batch_add, prime, N)
        
        # Remove the same primes
        A_after_batch_remove = batch_remove_members(A_after_batch_add, primes_to_add, N, trapdoor)
        
        # Should return to initial state
        assert A_after_batch_remove == A_initial
