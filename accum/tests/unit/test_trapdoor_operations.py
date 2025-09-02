"""
Unit Tests for Trapdoor Operations Module

Tests the trapdoor-based RSA accumulator removal operations.
"""

import os
import pytest
import math

try:
    from accum.trapdoor_operations import (
        extended_gcd, modular_inverse, compute_phi_n, compute_lambda_n,
        trapdoor_remove_member, trapdoor_batch_remove_members,
        verify_trapdoor_removal, validate_prime_for_accumulator
    )
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from trapdoor_operations import (
        extended_gcd, modular_inverse, compute_phi_n, compute_lambda_n,
        trapdoor_remove_member, trapdoor_batch_remove_members,
        verify_trapdoor_removal, validate_prime_for_accumulator
    )


class TestExtendedGCD:
    """Test extended Euclidean algorithm."""
    
    def test_extended_gcd_basic(self):
        """Test basic extended GCD computation."""
        # Test with gcd(35, 15) = 5
        gcd, x, y = extended_gcd(35, 15)
        assert gcd == 5
        assert 35 * x + 15 * y == gcd
    
    def test_extended_gcd_coprime(self):
        """Test extended GCD with coprime numbers."""
        # Test with gcd(7, 3) = 1
        gcd, x, y = extended_gcd(7, 3)
        assert gcd == 1
        assert 7 * x + 3 * y == 1
    
    def test_extended_gcd_zero(self):
        """Test extended GCD with zero."""
        gcd, x, y = extended_gcd(0, 5)
        assert gcd == 5
        assert 0 * x + 5 * y == 5
        
        gcd, x, y = extended_gcd(7, 0)
        assert gcd == 7
        assert 7 * x + 0 * y == 7
    
    def test_extended_gcd_same_numbers(self):
        """Test extended GCD with same numbers."""
        gcd, x, y = extended_gcd(12, 12)
        assert gcd == 12
        assert 12 * x + 12 * y == 12


class TestModularInverse:
    """Test modular inverse computation."""
    
    def test_modular_inverse_basic(self):
        """Test basic modular inverse."""
        # 3^(-1) mod 7 = 5, since 3 * 5 = 15 ≡ 1 (mod 7)
        inv = modular_inverse(3, 7)
        assert inv == 5
        assert (3 * inv) % 7 == 1
    
    def test_modular_inverse_coprime(self):
        """Test modular inverse with various coprime pairs."""
        test_cases = [
            (7, 11),   # 7^(-1) mod 11
            (5, 13),   # 5^(-1) mod 13  
            (2, 9),    # 2^(-1) mod 9
        ]
        
        for a, m in test_cases:
            inv = modular_inverse(a, m)
            assert inv is not None
            assert (a * inv) % m == 1
            assert 0 <= inv < m
    
    def test_modular_inverse_no_inverse(self):
        """Test modular inverse when no inverse exists."""
        # gcd(6, 9) = 3 ≠ 1, so 6^(-1) mod 9 doesn't exist
        inv = modular_inverse(6, 9)
        assert inv is None
        
        # gcd(4, 8) = 4 ≠ 1
        inv = modular_inverse(4, 8)
        assert inv is None
    
    def test_modular_inverse_edge_cases(self):
        """Test edge cases for modular inverse."""
        # a = 1 (inverse is 1)
        inv = modular_inverse(1, 7)
        assert inv == 1
    
    def test_modular_inverse_invalid_input(self):
        """Test modular inverse with invalid inputs."""
        with pytest.raises(ValueError):
            modular_inverse(-1, 7)
        
        with pytest.raises(ValueError):
            modular_inverse(3, -7)
        
        with pytest.raises(ValueError):
            modular_inverse(0, 7)  # a = 0 is invalid
        
        with pytest.raises(ValueError):
            modular_inverse(0, 0)


class TestPhiComputation:
    """Test Euler's totient function computation."""
    
    def test_compute_phi_n_basic(self):
        """Test φ(N) computation with small primes."""
        # φ(15) = φ(3 * 5) = (3-1) * (5-1) = 2 * 4 = 8
        phi = compute_phi_n(3, 5)
        assert phi == 8
        
        # φ(21) = φ(3 * 7) = (3-1) * (7-1) = 2 * 6 = 12
        phi = compute_phi_n(3, 7)
        assert phi == 12
    
    def test_compute_phi_n_larger_primes(self):
        """Test φ(N) computation with larger primes."""
        # φ(209) = φ(11 * 19) = (11-1) * (19-1) = 10 * 18 = 180
        phi = compute_phi_n(11, 19)
        assert phi == 180
    
    def test_compute_phi_n_invalid_input(self):
        """Test φ(N) computation with invalid inputs."""
        with pytest.raises(ValueError):
            compute_phi_n(1, 5)  # p must be > 1
        
        with pytest.raises(ValueError):
            compute_phi_n(5, 1)  # q must be > 1
        
        with pytest.raises(ValueError):
            compute_phi_n(5, 5)  # p and q must be distinct


class TestLambdaComputation:
    """Test Carmichael's lambda function computation."""
    
    def test_compute_lambda_n_basic(self):
        """Test λ(N) computation with small primes."""
        # λ(15) = λ(3 * 5) = lcm(3-1, 5-1) = lcm(2, 4) = 4
        lam = compute_lambda_n(3, 5)
        assert lam == 4
        
        # λ(21) = λ(3 * 7) = lcm(3-1, 7-1) = lcm(2, 6) = 6
        lam = compute_lambda_n(3, 7)
        assert lam == 6
    
    def test_compute_lambda_n_larger_primes(self):
        """Test λ(N) computation with larger primes."""
        # λ(209) = λ(11 * 19) = lcm(11-1, 19-1) = lcm(10, 18) = 90
        lam = compute_lambda_n(11, 19)
        assert lam == 90
    
    def test_compute_lambda_n_vs_phi_n(self):
        """Test that λ(N) divides φ(N)."""
        p, q = 11, 19
        lam = compute_lambda_n(p, q)
        phi = compute_phi_n(p, q)
        
        # λ(N) should divide φ(N)
        assert phi % lam == 0
        assert lam == 90
        assert phi == 180
    
    def test_compute_lambda_n_invalid_input(self):
        """Test λ(N) computation with invalid inputs."""
        with pytest.raises(ValueError):
            compute_lambda_n(1, 5)  # p must be > 1
        
        with pytest.raises(ValueError):
            compute_lambda_n(5, 1)  # q must be > 1
        
        with pytest.raises(ValueError):
            compute_lambda_n(5, 5)  # p and q must be distinct


class TestTrapdoorRemoval:
    """Test trapdoor-based member removal."""
    
    @pytest.fixture
    def toy_rsa_params(self):
        """Provide toy RSA parameters for testing."""
        p, q = 11, 19
        N = p * q  # N = 209
        # Use QR base: g = h^2 mod N (h=2 -> g=4)
        g = pow(2, 2, N)  # g = 4, ensuring g is in quadratic residue subgroup
        return N, g, p, q
    
    def test_trapdoor_remove_member_basic(self, toy_rsa_params):
        """Test basic trapdoor removal."""
        N, g, p, q = toy_rsa_params
        
        # Create accumulator with primes coprime to λ(N) = 90
        primes = [7, 13, 17]  # All coprime to 90 = 2^2 * 3^2 * 5
        A = g
        for prime in primes:
            A = pow(A, prime, N)
        
        # Remove prime 13
        A_new = trapdoor_remove_member(A, 13, N, p, q)
        
        # Verify removal: A_new^13 should equal A
        assert verify_trapdoor_removal(A, A_new, 13, N)
        
        # Double-check by recomputing from remaining primes
        remaining_primes = [7, 17]
        expected_A = g
        for prime in remaining_primes:
            expected_A = pow(expected_A, prime, N)
        assert A_new == expected_A
    
    def test_trapdoor_remove_member_single_prime(self, toy_rsa_params):
        """Test removing single prime from accumulator."""
        N, g, p, q = toy_rsa_params
        
        # Create accumulator with single prime
        prime = 17
        A = pow(g, prime, N)
        
        # Remove the prime
        A_new = trapdoor_remove_member(A, prime, N, p, q)
        
        # Should get back to generator
        assert A_new == g
        assert verify_trapdoor_removal(A, A_new, prime, N)
    
    def test_trapdoor_remove_member_problematic_prime(self, toy_rsa_params):
        """Test removal of prime that shares factors with λ(N)."""
        N, g, p, q = toy_rsa_params
        # λ(N) = 90 = 2 * 3^2 * 5
        
        # Create accumulator with prime 5 (which divides λ(N))
        A = pow(g, 5, N)
        
        # Should fail to remove prime 5
        with pytest.raises(ValueError, match="Cannot compute modular inverse"):
            trapdoor_remove_member(A, 5, N, p, q)
    
    def test_trapdoor_remove_member_invalid_inputs(self, toy_rsa_params):
        """Test trapdoor removal with invalid inputs."""
        N, g, p, q = toy_rsa_params
        A = pow(g, 7, N)
        
        # Invalid A
        with pytest.raises(ValueError):
            trapdoor_remove_member(-1, 7, N, p, q)
        
        # Invalid prime
        with pytest.raises(ValueError):
            trapdoor_remove_member(A, -1, N, p, q)
        
        # Invalid N
        with pytest.raises(ValueError):
            trapdoor_remove_member(A, 7, -1, p, q)
        
        # Wrong factorization
        with pytest.raises(ValueError):
            trapdoor_remove_member(A, 7, N, 5, 7)  # 5 * 7 ≠ 209
        
        # Prime too large
        with pytest.raises(ValueError):
            trapdoor_remove_member(A, N + 1, N, p, q)


class TestTrapdoorBatchRemoval:
    """Test trapdoor-based batch member removal."""
    
    @pytest.fixture
    def toy_rsa_params(self):
        """Provide toy RSA parameters for testing."""
        p, q = 11, 19
        N = p * q  # N = 209
        # Use QR base: g = h^2 mod N (h=2 -> g=4)
        g = pow(2, 2, N)  # g = 4, ensuring g is in quadratic residue subgroup
        return N, g, p, q
    
    def test_trapdoor_batch_remove_basic(self, toy_rsa_params):
        """Test basic batch removal."""
        N, g, p, q = toy_rsa_params
        
        # Create accumulator with multiple primes
        primes = [7, 11, 13, 17]  # All coprime to λ(N) = 90
        A = g
        for prime in primes:
            A = pow(A, prime, N)
        
        # Remove multiple primes
        primes_to_remove = [11, 17]
        A_new = trapdoor_batch_remove_members(A, primes_to_remove, N, p, q)
        
        # Verify by recomputing from remaining primes
        remaining_primes = [7, 13]
        expected_A = g
        for prime in remaining_primes:
            expected_A = pow(expected_A, prime, N)
        assert A_new == expected_A
    
    def test_trapdoor_batch_remove_empty_list(self, toy_rsa_params):
        """Test batch removal with empty list."""
        N, g, p, q = toy_rsa_params
        A = pow(g, 7, N)
        
        # Remove nothing
        A_new = trapdoor_batch_remove_members(A, [], N, p, q)
        assert A_new == A
    
    def test_trapdoor_batch_remove_all_primes(self, toy_rsa_params):
        """Test removing all primes from accumulator."""
        N, g, p, q = toy_rsa_params
        
        # Create accumulator with primes
        primes = [7, 13]
        A = g
        for prime in primes:
            A = pow(A, prime, N)
        
        # Remove all primes
        A_new = trapdoor_batch_remove_members(A, primes, N, p, q)
        
        # Should get back to generator
        assert A_new == g


class TestVerifyTrapdoorRemoval:
    """Test verification of trapdoor removal operations."""
    
    def test_verify_trapdoor_removal_valid(self):
        """Test verification of valid removal."""
        # Use small numbers for testing - create a simple valid case
        N = 35  # 5 * 7  
        A_old = 8
        removed_prime = 7  # Use a prime coprime to φ(N) = 24
        
        # For verification, we just need A_new such that A_new^removed_prime ≡ A_old (mod N)
        # Let's use A_new = 2, then check if 2^7 ≡ 8 (mod 35)
        A_new = 2
        
        # Test the verification function logic
        result = verify_trapdoor_removal(A_old, A_new, removed_prime, N)
        expected = (pow(A_new, removed_prime, N) == A_old)
        assert result == expected
    
    def test_verify_trapdoor_removal_invalid_inputs(self):
        """Test verification with invalid inputs."""
        # All parameters must be positive
        assert not verify_trapdoor_removal(-1, 5, 3, 35)
        assert not verify_trapdoor_removal(12, -1, 3, 35)
        assert not verify_trapdoor_removal(12, 5, -1, 35)
        assert not verify_trapdoor_removal(12, 5, 3, -1)
        assert not verify_trapdoor_removal(0, 5, 3, 35)


class TestPrimeValidation:
    """Test prime validation for accumulator use."""
    
    def test_validate_prime_for_accumulator_valid(self):
        """Test validation of valid primes."""
        p, q = 11, 19
        N = p * q  # N = 209, λ(N) = 90 = 2 * 3^2 * 5
        
        # These primes should be valid (coprime to λ(N) = 90)
        valid_primes = [7, 11, 13, 17, 19, 23, 29]
        
        for prime in valid_primes:
            # Should not raise any exception
            validate_prime_for_accumulator(prime, N, p, q)
    
    def test_validate_prime_for_accumulator_invalid(self):
        """Test validation of invalid primes."""
        p, q = 11, 19
        N = p * q  # N = 209, λ(N) = 90 = 2 * 3^2 * 5
        
        # These primes should be invalid (not coprime to λ(N) = 90)
        invalid_primes = [2, 3, 5, 6, 9, 10, 15, 18, 30, 45, 90]
        
        for prime in invalid_primes:
            with pytest.raises(ValueError, match="not coprime with λ\\(N\\)"):
                validate_prime_for_accumulator(prime, N, p, q)
    
    def test_validate_prime_for_accumulator_edge_cases(self):
        """Test prime validation edge cases."""
        p, q = 11, 19
        N = p * q
        
        # Invalid inputs
        with pytest.raises(ValueError, match="Prime must be positive"):
            validate_prime_for_accumulator(0, N, p, q)
        
        with pytest.raises(ValueError, match="Prime must be positive"):
            validate_prime_for_accumulator(-1, N, p, q)
        
        # Note: p >= N constraint removed - these should now pass
        # validate_prime_for_accumulator(N, N, p, q)  # Would pass now
        # validate_prime_for_accumulator(N + 1, N, p, q)  # Would pass now
        
        # Wrong factorization
        with pytest.raises(ValueError, match="N must equal p \\* q"):
            validate_prime_for_accumulator(7, N, 5, 7)  # 5 * 7 ≠ 209


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
