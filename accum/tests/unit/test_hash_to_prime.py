"""
Unit Tests for Hash-to-Prime Module

Tests the conversion of byte strings to prime numbers using SHA-256 and Miller-Rabin.
"""

import hashlib
import os
import pytest

try:
    from accum.hash_to_prime import hash_to_prime
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from hash_to_prime import hash_to_prime


class TestHashToPrime:
    """Test hash-to-prime conversion functionality."""
    
    def test_hash_to_prime_basic(self):
        """Test basic hash-to-prime conversion."""
        test_data = b"test data"
        prime = hash_to_prime(test_data)
        
        # Result should be a prime number
        assert isinstance(prime, int)
        assert prime > 1
        assert self._is_prime_simple(prime)
    
    def test_hash_to_prime_deterministic(self):
        """Test that hash-to-prime is deterministic."""
        test_data = b"deterministic test"
        
        prime1 = hash_to_prime(test_data)
        prime2 = hash_to_prime(test_data)
        
        # Should always return the same prime for same input
        assert prime1 == prime2
    
    def test_hash_to_prime_different_inputs(self):
        """Test that different inputs produce different primes."""
        data1 = b"input one"
        data2 = b"input two"
        
        prime1 = hash_to_prime(data1)
        prime2 = hash_to_prime(data2)
        
        # Different inputs should produce different primes
        assert prime1 != prime2
        assert self._is_prime_simple(prime1)
        assert self._is_prime_simple(prime2)
    
    def test_hash_to_prime_empty_input(self):
        """Test hash-to-prime with empty input."""
        prime = hash_to_prime(b"")
        
        assert isinstance(prime, int)
        assert prime > 1
        assert self._is_prime_simple(prime)
    
    def test_hash_to_prime_large_input(self):
        """Test hash-to-prime with large input data."""
        large_data = b"x" * 10000
        prime = hash_to_prime(large_data)
        
        assert isinstance(prime, int)
        assert prime > 1
        assert self._is_prime_simple(prime)
    
    def test_hash_to_prime_binary_data(self):
        """Test hash-to-prime with binary data."""
        binary_data = bytes(range(256))
        prime = hash_to_prime(binary_data)
        
        assert isinstance(prime, int)
        assert prime > 1
        assert self._is_prime_simple(prime)
    
    def test_hash_to_prime_unicode_encoded(self):
        """Test hash-to-prime with Unicode data encoded as bytes."""
        unicode_text = "Hello 世界 🌍".encode('utf-8')
        prime = hash_to_prime(unicode_text)
        
        assert isinstance(prime, int)
        assert prime > 1
        assert self._is_prime_simple(prime)
    
    def test_hash_to_prime_max_attempts(self):
        """Test hash-to-prime with limited max attempts."""
        test_data = b"test with max attempts"
        
        # Should work with reasonable max_attempts
        prime = hash_to_prime(test_data, max_attempts=100)
        assert self._is_prime_simple(prime)
        
        # Should raise error with very low max_attempts
        with pytest.raises(ValueError, match="Could not find prime"):
            hash_to_prime(test_data, max_attempts=1)
    
    def test_hash_to_prime_type_validation(self):
        """Test hash-to-prime input type validation."""
        # Should raise TypeError for non-bytes input
        with pytest.raises(TypeError, match="Input must be bytes"):
            hash_to_prime("string input")
        
        with pytest.raises(TypeError, match="Input must be bytes"):
            hash_to_prime(123)
        
        with pytest.raises(TypeError, match="Input must be bytes"):
            hash_to_prime(None)
    
    def test_hash_to_prime_max_attempts_validation(self):
        """Test hash-to-prime max_attempts parameter validation."""
        test_data = b"test data"
        
        # Should raise ValueError for invalid max_attempts
        with pytest.raises(ValueError, match="max_attempts must be positive"):
            hash_to_prime(test_data, max_attempts=0)
        
        with pytest.raises(ValueError, match="max_attempts must be positive"):
            hash_to_prime(test_data, max_attempts=-1)
    
    def test_hash_to_prime_distribution(self):
        """Test that hash-to-prime produces well-distributed primes."""
        primes = []
        
        # Generate primes from different inputs
        for i in range(20):
            data = f"test input {i}".encode('utf-8')
            prime = hash_to_prime(data)
            primes.append(prime)
            assert self._is_prime_simple(prime)
        
        # All primes should be different
        assert len(set(primes)) == len(primes)
        
        # Primes should be reasonably large (> 2^16)
        assert all(p > 65536 for p in primes)
    
    def test_hash_to_prime_consistency_with_sha256(self):
        """Test that hash-to-prime uses SHA-256 correctly."""
        test_data = b"consistency test"
        
        # Calculate expected hash
        expected_hash = hashlib.sha256(test_data).digest()
        expected_int = int.from_bytes(expected_hash, 'big')
        
        # The prime should be >= the hash value (since we search upward)
        prime = hash_to_prime(test_data)
        assert prime >= expected_int
        
        # The prime should be odd (since we make hash odd and increment by 2)
        assert prime % 2 == 1
    
    def test_hash_to_prime_known_vectors(self):
        """Test hash-to-prime with known test vectors."""
        # These are deterministic test cases
        test_vectors = [
            (b"", None),  # We'll check this produces a consistent prime
            (b"test", None),
            (b"hello world", None),
            (b"\x00\x01\x02\x03", None),
        ]
        
        for data, expected in test_vectors:
            prime = hash_to_prime(data)
            assert self._is_prime_simple(prime)
            
            # Test consistency
            prime2 = hash_to_prime(data)
            assert prime == prime2
    
    def _is_prime_simple(self, n):
        """Simple primality test for verification."""
        if n < 2:
            return False
        if n == 2:
            return True
        if n % 2 == 0:
            return False
        
        # Check odd divisors up to sqrt(n)
        i = 3
        while i * i <= n:
            if n % i == 0:
                return False
            i += 2
        
        return True
