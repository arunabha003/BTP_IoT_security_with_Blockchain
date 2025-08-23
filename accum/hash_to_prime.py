"""
Hash-to-Prime Conversion for RSA Accumulators

Converts arbitrary byte data (like public keys) to prime numbers
suitable for RSA accumulator operations.
"""

import hashlib
import random


def hash_to_prime(pubkey_bytes: bytes, max_attempts: int = 1000) -> int:
    """
    Convert public key bytes to a prime number using SHA-256 and Miller-Rabin.

    This function takes arbitrary bytes (typically a public key) and deterministically
    converts them to a prime number suitable for RSA accumulator operations.

    Args:
        pubkey_bytes: The input bytes to convert (e.g., Ed25519 public key)
        max_attempts: Maximum number of attempts to find a prime (default: 1000)

    Returns:
        int: A prime number derived from the input bytes

    Raises:
        ValueError: If no prime is found within max_attempts
        TypeError: If pubkey_bytes is not bytes

    Example:
        >>> pubkey = b"\\x12\\x34\\x56\\x78" * 8  # 32-byte Ed25519 key
        >>> prime = hash_to_prime(pubkey)
        >>> assert is_prime(prime)  # Verify it's actually prime
    """
    if not isinstance(pubkey_bytes, bytes):
        raise TypeError("pubkey_bytes must be bytes")

    if len(pubkey_bytes) == 0:
        raise ValueError("pubkey_bytes cannot be empty")

    # Start with SHA-256 hash of the input
    base_hash = hashlib.sha256(pubkey_bytes).digest()

    for attempt in range(max_attempts):
        # Create a candidate by hashing base_hash + attempt counter
        candidate_bytes = hashlib.sha256(
            base_hash + attempt.to_bytes(4, "big")
        ).digest()

        # Convert to integer (ensure it's odd for primality)
        candidate = int.from_bytes(candidate_bytes, "big")

        # Ensure it's odd (even numbers > 2 can't be prime)
        if candidate % 2 == 0:
            candidate += 1

        # Ensure it's at least 3 (smallest odd prime)
        if candidate < 3:
            candidate = 3

        # Test for primality using Miller-Rabin
        if is_prime(candidate):
            return candidate

    raise ValueError(f"Could not find prime within {max_attempts} attempts")


def is_prime(n: int, k: int = 10) -> bool:
    """
    Miller-Rabin primality test.

    Args:
        n: Number to test for primality
        k: Number of rounds (higher = more accurate, default: 10)

    Returns:
        bool: True if n is probably prime, False if definitely composite

    Note:
        This is a probabilistic test. With k=10, the probability of
        incorrectly identifying a composite as prime is < 2^(-20).
    """
    if n < 2:
        return False
    if n == 2 or n == 3:
        return True
    if n % 2 == 0:
        return False

    # Write n-1 as d * 2^r
    r = 0
    d = n - 1
    while d % 2 == 0:
        d //= 2
        r += 1

    # Miller-Rabin test
    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)

        if x == 1 or x == n - 1:
            continue

        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False  # Definitely composite

    return True  # Probably prime


def _test_hash_to_prime() -> None:
    """Test the hash_to_prime function with various inputs."""
    test_cases = [
        b"test_key_1",
        b"a" * 32,  # 32-byte key
        b"\x00" * 32,  # All zeros
        b"\xff" * 32,  # All ones
        b"Ed25519_public_key_example_12345678"[:32],  # Realistic Ed25519 key
    ]

    print("Testing hash_to_prime function:")
    for i, test_input in enumerate(test_cases):
        try:
            prime = hash_to_prime(test_input)
            print(
                f"  Test {i+1}: {test_input[:16]}... -> Prime: {prime} ({prime.bit_length()} bits)"
            )
            assert is_prime(prime), f"Result {prime} is not prime!"
        except Exception as e:
            print(f"  Test {i+1}: FAILED - {e}")

    # Test error cases
    print("\nTesting error cases:")
    try:
        hash_to_prime("not bytes")  # Should raise TypeError
        print("  ERROR: Should have raised TypeError")
    except TypeError:
        print("  ✓ Correctly raised TypeError for non-bytes input")

    try:
        hash_to_prime(b"")  # Should raise ValueError
        print("  ERROR: Should have raised ValueError")
    except ValueError:
        print("  ✓ Correctly raised ValueError for empty input")


if __name__ == "__main__":
    _test_hash_to_prime()
