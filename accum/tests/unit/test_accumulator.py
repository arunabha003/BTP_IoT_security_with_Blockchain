"""
Unit Tests for RSA Accumulator Core Module

Tests the core RSA accumulator operations: add_member, recompute_root, 
membership_witness, and verify_membership.
"""

import os
import pytest
from typing import Set

try:
    from accum.accumulator import add_member, recompute_root, membership_witness, verify_membership
    from accum.rsa_params import generate_demo_params
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from accumulator import add_member, recompute_root, membership_witness, verify_membership
    from rsa_params import generate_demo_params


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
        
        # Invalid accumulator
        with pytest.raises(ValueError, match="Accumulator must be positive"):
            add_member(0, 13, N)
        
        with pytest.raises(ValueError, match="Accumulator must be positive"):
            add_member(-1, 13, N)
        
        # Invalid prime
        with pytest.raises(ValueError, match="Prime must be positive"):
            add_member(g, 0, N)
        
        with pytest.raises(ValueError, match="Prime must be positive"):
            add_member(g, -1, N)
        
        # Invalid modulus
        with pytest.raises(ValueError, match="Modulus must be positive"):
            add_member(g, 13, 0)
        
        with pytest.raises(ValueError, match="Modulus must be positive"):
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
        
        # Invalid modulus
        with pytest.raises(ValueError, match="Modulus must be positive"):
            recompute_root({13}, 0, g)
        
        # Invalid generator
        with pytest.raises(ValueError, match="Generator must be positive"):
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
        with pytest.raises(ValueError, match="Target prime must be positive"):
            membership_witness({13}, 0, N, g)
        
        # Invalid modulus
        with pytest.raises(ValueError, match="Modulus must be positive"):
            membership_witness({13}, 17, 0, g)
        
        # Invalid generator
        with pytest.raises(ValueError, match="Generator must be positive"):
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
        
        # Invalid witness
        with pytest.raises(ValueError, match="Witness must be positive"):
            verify_membership(0, 13, A, N)
        
        # Invalid prime
        with pytest.raises(ValueError, match="Prime must be positive"):
            verify_membership(w, 0, A, N)
        
        # Invalid accumulator
        with pytest.raises(ValueError, match="Accumulator must be positive"):
            verify_membership(w, 13, 0, N)
        
        # Invalid modulus
        with pytest.raises(ValueError, match="Modulus must be positive"):
            verify_membership(w, 13, A, 0)
    
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
        A2 = add_member(g, 13 * 17 * 23, N)  # Direct computation
        
        assert A1 == A2
