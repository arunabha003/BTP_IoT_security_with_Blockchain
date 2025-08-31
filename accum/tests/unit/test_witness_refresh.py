"""
Unit Tests for Witness Refresh Module

Tests witness update algorithms for RSA accumulator operations.
"""

import os
import pytest
from typing import Set

try:
    from accum.witness_refresh import (
        refresh_witness, batch_refresh_witnesses, 
        update_witness_on_addition, update_witness_on_removal
    )
    from accum.accumulator import recompute_root, membership_witness, verify_membership

except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from witness_refresh import (
        refresh_witness, batch_refresh_witnesses,
        update_witness_on_addition, update_witness_on_removal
    )
    from accumulator import recompute_root, membership_witness, verify_membership



def generate_demo_params():
    """Generate demo RSA parameters for testing."""
    # Use small primes for testing
    p, q = 11, 19
    N = p * q  # N = 209
    # Use QR base: g = h^2 mod N (h=2 -> g=4)
    g = pow(2, 2, N)  # g = 4, ensuring g is in quadratic residue subgroup
    return N, g


class TestWitnessRefresh:
    """Test witness refresh and update algorithms."""
    
    @pytest.fixture
    def toy_params(self):
        """Provide toy RSA parameters for testing."""
        return generate_demo_params()  # N=209, g=2
    
    def test_refresh_witness_basic(self, toy_params):
        """Test basic witness refresh for a single prime."""
        N, g = toy_params
        target_p = 13
        set_primes = {13, 17, 23}
        
        # Refresh witness for target prime
        witness = refresh_witness(target_p, set_primes, N, g)
        
        # Verify the witness is correct
        A = recompute_root(set_primes, N, g)
        assert verify_membership(witness, target_p, A, N)
    
    def test_refresh_witness_target_not_in_set(self, toy_params):
        """Test witness refresh when target prime is not in current set."""
        N, g = toy_params
        target_p = 29  # Not in set
        set_primes = {13, 17, 23}
        
        # Should still compute a witness (for potential addition)
        witness = refresh_witness(target_p, set_primes, N, g)
        
        # Witness should be g^(product of all primes in set) mod N
        expected = recompute_root(set_primes, N, g)
        assert witness == expected
    
    def test_refresh_witness_empty_set(self, toy_params):
        """Test witness refresh with empty prime set."""
        N, g = toy_params
        target_p = 13
        set_primes = set()
        
        witness = refresh_witness(target_p, set_primes, N, g)
        assert witness == g  # Should be generator for empty set
    
    def test_refresh_witness_single_member(self, toy_params):
        """Test witness refresh when only target prime is in set."""
        N, g = toy_params
        target_p = 13
        set_primes = {13}
        
        witness = refresh_witness(target_p, set_primes, N, g)
        assert witness == g  # Witness for single member is generator
    
    def test_refresh_witness_validation(self, toy_params):
        """Test refresh_witness input validation."""
        N, g = toy_params
        
        # Invalid target prime
        with pytest.raises(ValueError, match="Target prime must be positive"):
            refresh_witness(0, {13, 17}, N, g)
        
        # Invalid modulus
        with pytest.raises(ValueError, match="Modulus must be positive"):
            refresh_witness(13, {17}, 0, g)
        
        # Invalid generator
        with pytest.raises(ValueError, match="Generator must be positive"):
            refresh_witness(13, {17}, N, 0)
        
        # Invalid prime in set
        with pytest.raises(ValueError, match="All primes must be positive"):
            refresh_witness(13, {0, 17}, N, g)
    
    def test_batch_refresh_witnesses(self, toy_params):
        """Test batch witness refresh for multiple primes."""
        N, g = toy_params
        target_primes = [13, 17, 23]
        set_primes = {13, 17, 23, 29}
        
        witnesses = batch_refresh_witnesses(target_primes, set_primes, N, g)
        
        # Verify all witnesses
        A = recompute_root(set_primes, N, g)
        for i, p in enumerate(target_primes):
            assert verify_membership(witnesses[i], p, A, N)
    
    def test_batch_refresh_witnesses_empty_targets(self, toy_params):
        """Test batch witness refresh with empty target list."""
        N, g = toy_params
        target_primes = []
        set_primes = {13, 17, 23}
        
        witnesses = batch_refresh_witnesses(target_primes, set_primes, N, g)
        assert witnesses == []
    
    def test_batch_refresh_witnesses_validation(self, toy_params):
        """Test batch_refresh_witnesses input validation."""
        N, g = toy_params
        
        # Invalid target prime
        with pytest.raises(ValueError, match="All target primes must be positive"):
            batch_refresh_witnesses([13, 0, 17], {13, 17}, N, g)
        
        # Invalid modulus
        with pytest.raises(ValueError, match="Modulus must be positive"):
            batch_refresh_witnesses([13], {17}, 0, g)
    
    def test_update_witness_on_addition(self, toy_params):
        """Test witness update when a new member is added."""
        N, g = toy_params
        
        # Initial state: accumulator has {13, 17}
        initial_primes = {13, 17}
        old_witness_13 = membership_witness(initial_primes, 13, N, g)
        
        # Add new prime 23
        new_prime = 23
        
        # Update witness for prime 13
        new_witness_13 = update_witness_on_addition(old_witness_13, new_prime, N)
        
        # Verify the updated witness is correct
        new_primes = {13, 17, 23}
        A_new = recompute_root(new_primes, N, g)
        assert verify_membership(new_witness_13, 13, A_new, N)
        
        # Should equal w^new_prime mod N
        expected = pow(old_witness_13, new_prime, N)
        assert new_witness_13 == expected
    
    def test_update_witness_on_addition_validation(self, toy_params):
        """Test update_witness_on_addition input validation."""
        N, g = toy_params
        
        # Invalid old witness
        with pytest.raises(ValueError, match="Old witness must be positive"):
            update_witness_on_addition(0, 13, N)
        
        # Invalid new prime
        with pytest.raises(ValueError, match="New prime must be positive"):
            update_witness_on_addition(g, 0, N)
        
        # Invalid modulus
        with pytest.raises(ValueError, match="Modulus must be positive"):
            update_witness_on_addition(g, 13, 0)
    
    def test_update_witness_on_removal_not_implemented(self, toy_params):
        """Test that witness update on removal raises NotImplementedError."""
        N, g = toy_params
        
        with pytest.raises(NotImplementedError, match="Witness update on removal"):
            update_witness_on_removal(g, 13, {17, 23}, N, g)
    
    def test_witness_consistency_after_refresh(self, toy_params):
        """Test that refreshed witnesses are consistent with direct computation."""
        N, g = toy_params
        primes = {13, 17, 23, 29}
        
        # Direct witness computation
        direct_witness = membership_witness(primes, 17, N, g)
        
        # Refreshed witness computation
        refreshed_witness = refresh_witness(17, primes, N, g)
        
        assert direct_witness == refreshed_witness
    
    def test_witness_refresh_after_addition(self, toy_params):
        """Test complete witness refresh scenario after member addition."""
        N, g = toy_params
        
        # Initial state
        initial_primes = {13, 17}
        A_initial = recompute_root(initial_primes, N, g)
        
        # Initial witnesses
        w13_initial = membership_witness(initial_primes, 13, N, g)
        w17_initial = membership_witness(initial_primes, 17, N, g)
        
        # Verify initial witnesses
        assert verify_membership(w13_initial, 13, A_initial, N)
        assert verify_membership(w17_initial, 17, A_initial, N)
        
        # Add new member
        new_prime = 23
        new_primes = initial_primes | {new_prime}
        A_new = recompute_root(new_primes, N, g)
        
        # Refresh witnesses for existing members
        w13_refreshed = refresh_witness(13, new_primes, N, g)
        w17_refreshed = refresh_witness(17, new_primes, N, g)
        
        # Generate witness for new member
        w23_new = refresh_witness(23, new_primes, N, g)
        
        # Verify all witnesses work with new accumulator
        assert verify_membership(w13_refreshed, 13, A_new, N)
        assert verify_membership(w17_refreshed, 17, A_new, N)
        assert verify_membership(w23_new, 23, A_new, N)
    
    def test_witness_refresh_mathematical_property(self, toy_params):
        """Test mathematical property of witness refresh."""
        N, g = toy_params
        primes = {13, 17, 23}
        target_p = 17
        
        # Refreshed witness should satisfy w^p ≡ A (mod N)
        witness = refresh_witness(target_p, primes, N, g)
        A = recompute_root(primes, N, g)
        
        assert pow(witness, target_p, N) == A
    
    def test_batch_witness_efficiency(self, toy_params):
        """Test that batch witness refresh is more efficient than individual calls."""
        N, g = toy_params
        target_primes = [13, 17, 23, 29, 31]
        set_primes = {13, 17, 23, 29, 31, 37}
        
        # Batch refresh
        batch_witnesses = batch_refresh_witnesses(target_primes, set_primes, N, g)
        
        # Individual refresh
        individual_witnesses = []
        for p in target_primes:
            w = refresh_witness(p, set_primes, N, g)
            individual_witnesses.append(w)
        
        # Results should be identical
        assert batch_witnesses == individual_witnesses
        
        # Verify all witnesses
        A = recompute_root(set_primes, N, g)
        for i, p in enumerate(target_primes):
            assert verify_membership(batch_witnesses[i], p, A, N)
    
    def test_witness_update_incremental_consistency(self, toy_params):
        """Test that incremental witness updates are consistent."""
        N, g = toy_params
        
        # Start with single prime
        primes = {13}
        A = recompute_root(primes, N, g)
        w13 = membership_witness(primes, 13, N, g)
        
        # Add primes incrementally and update witness
        new_primes = [17, 23, 29]
        current_witness = w13
        
        for new_p in new_primes:
            # Update witness incrementally
            current_witness = update_witness_on_addition(current_witness, new_p, N)
            primes.add(new_p)
            
            # Verify witness is still valid
            A = recompute_root(primes, N, g)
            assert verify_membership(current_witness, 13, A, N)
        
        # Final witness should match direct computation
        final_witness_direct = membership_witness(primes, 13, N, g)
        assert current_witness == final_witness_direct


class TestWitnessRemovalUpdates:
    """Test witness updates during member removal operations."""
    
    @pytest.fixture
    def toy_params_with_trapdoor(self):
        """Provide toy RSA parameters with trapdoor information."""
        p, q = 11, 19  # Small primes for testing
        N = p * q  # N = 209
        g = 2
        trapdoor = (p, q)
        return N, g, trapdoor
    
    def test_update_witness_on_removal_basic(self, toy_params_with_trapdoor):
        """Test basic witness update on removal with trapdoor."""
        N, g, trapdoor = toy_params_with_trapdoor
        
        # Create accumulator with primes coprime to λ(N) = 90
        primes = {7, 13, 17, 23}  # All coprime to 90 = 2 * 3^2 * 5
        A = recompute_root(primes, N, g)
        
        # Get witness for prime 7 before removal
        primes_without_7 = primes - {7}
        old_witness = membership_witness(primes_without_7, N, g)
        assert verify_membership(old_witness, 7, A, N)
        
        # Remove prime 13 from the set
        removed_prime = 13
        new_primes = primes - {removed_prime}
        A_new = recompute_root(new_primes, N, g)
        
        # Update witness using trapdoor method
        new_witness = update_witness_on_removal(old_witness, removed_prime, N, trapdoor)
        
        # Verify updated witness is correct
        assert verify_membership(new_witness, 7, A_new, N)
        
        # Compare with direct computation
        new_primes_without_7 = new_primes - {7}
        expected_witness = membership_witness(new_primes_without_7, N, g)
        assert new_witness == expected_witness
    
    def test_update_witness_on_removal_without_trapdoor(self, toy_params_with_trapdoor):
        """Test that witness update without trapdoor raises NotImplementedError."""
        N, g, _ = toy_params_with_trapdoor
        
        old_witness = 42  # Some witness value
        removed_prime = 13
        
        with pytest.raises(NotImplementedError, match="Efficient witness update on removal requires trapdoor"):
            update_witness_on_removal(old_witness, removed_prime, N)  # No trapdoor
    
    def test_update_witness_on_removal_problematic_prime(self, toy_params_with_trapdoor):
        """Test witness update when removing prime that shares factors with λ(N)."""
        N, g, trapdoor = toy_params_with_trapdoor
        # λ(N) = 90 = 2 * 3^2 * 5
        
        old_witness = 42  # Some witness value
        removed_prime = 5  # Shares factor with λ(N)
        
        # Should fail due to modular inverse not existing
        with pytest.raises(ValueError, match="Cannot compute modular inverse"):
            update_witness_on_removal(old_witness, removed_prime, N, trapdoor)
    
    def test_witness_update_consistency_across_operations(self, toy_params_with_trapdoor):
        """Test that witness updates are consistent across add/remove operations."""
        N, g, trapdoor = toy_params_with_trapdoor
        
        # Start with initial set
        initial_primes = {7, 17, 23}
        A_initial = recompute_root(initial_primes, N, g)
        
        # Get witness for prime 7
        initial_primes_without_7 = initial_primes - {7}
        witness_7 = membership_witness(initial_primes_without_7, N, g)
        assert verify_membership(witness_7, 7, A_initial, N)
        
        # Add a prime and update witness
        added_prime = 13
        witness_7_after_add = update_witness_on_addition(witness_7, added_prime, N)
        primes_after_add = initial_primes | {added_prime}
        A_after_add = recompute_root(primes_after_add, N, g)
        assert verify_membership(witness_7_after_add, 7, A_after_add, N)
        
        # Remove the same prime and update witness back
        witness_7_after_remove = update_witness_on_removal(witness_7_after_add, added_prime, N, trapdoor)
        A_after_remove = recompute_root(initial_primes, N, g)
        assert verify_membership(witness_7_after_remove, 7, A_after_remove, N)
        
        # Should be back to original witness
        assert witness_7_after_remove == witness_7
        assert A_after_remove == A_initial
    
    def test_multiple_witness_updates_on_removal(self, toy_params_with_trapdoor):
        """Test multiple consecutive witness updates on removal."""
        N, g, trapdoor = toy_params_with_trapdoor
        
        # Start with larger set
        initial_primes = {7, 11, 13, 17, 23}
        target_prime = 7
        
        # Get initial witness for target prime
        initial_primes_without_target = initial_primes - {target_prime}
        current_witness = membership_witness(initial_primes_without_target, N, g)
        current_primes = initial_primes.copy()
        
        # Remove primes one by one and update witness
        primes_to_remove = [13, 23, 11]
        
        for prime_to_remove in primes_to_remove:
            # Update witness using trapdoor method
            current_witness = update_witness_on_removal(current_witness, prime_to_remove, N, trapdoor)
            current_primes.remove(prime_to_remove)
            
            # Verify witness is still valid
            A_current = recompute_root(current_primes, N, g)
            assert verify_membership(current_witness, target_prime, A_current, N)
        
        # Final witness should match direct computation
        final_primes_without_target = current_primes - {target_prime}
        final_witness_direct = membership_witness(final_primes_without_target, N, g)
        assert current_witness == final_witness_direct
    
    def test_witness_update_invalid_inputs(self, toy_params_with_trapdoor):
        """Test witness update with invalid inputs."""
        N, g, trapdoor = toy_params_with_trapdoor
        
        # Invalid witness
        with pytest.raises(ValueError):
            update_witness_on_removal(-1, 13, N, trapdoor)
        
        # Invalid prime
        with pytest.raises(ValueError):
            update_witness_on_removal(42, -1, N, trapdoor)
        
        # Invalid N
        with pytest.raises(ValueError):
            update_witness_on_removal(42, 13, -1, trapdoor)
        
        # Wrong trapdoor factorization
        wrong_trapdoor = (5, 7)  # 5 * 7 = 35 ≠ 209
        with pytest.raises(ValueError):
            update_witness_on_removal(42, 13, N, wrong_trapdoor)
