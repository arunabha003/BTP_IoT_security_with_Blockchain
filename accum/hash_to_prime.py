"""
Hash-to-Prime Conversion for RSA Accumulators

Converts arbitrary byte data (like public keys) to prime numbers
suitable for RSA accumulator operations.
"""

import hashlib
import math
from typing import Optional


def _mr_is_probable_prime(n: int, rounds: int = 64) -> bool:
    """Deterministic Miller-Rabin primality test."""
    if n < 2:
        return False
    small = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
    for p in small:
        if n == p:
            return True
        if n % p == 0:
            return False
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    seed = n.to_bytes((n.bit_length() + 7) // 8, "big")
    for i in range(rounds):
        h = hashlib.sha256(seed + i.to_bytes(4, "big")).digest()
        a = 2 + (int.from_bytes(h, "big") % (n - 3))
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = (x * x) % n
            if x == n - 1:
                break
        else:
            return False
    return True


def hash_to_prime(pubkey_bytes: bytes, *, min_bits: int = 256, max_attempts: int = 100_000, mr_rounds: int = 64) -> int:
    """
    Convert public key bytes to a prime number using deterministic SHA-256 and Miller-Rabin.

    This function takes arbitrary bytes (typically a public key) and deterministically
    converts them to a prime number suitable for RSA accumulator operations.

    Args:
        pubkey_bytes: The input bytes to convert (e.g., Ed25519 public key)
        min_bits: Minimum bit length for the prime (default: 256)
        max_attempts: Maximum number of attempts to find a prime (default: 100_000)
        mr_rounds: Number of Miller-Rabin rounds (default: 64)

    Returns:
        int: A prime number derived from the input bytes

    Raises:
        ValueError: If no prime is found within max_attempts
        TypeError: If pubkey_bytes is not bytes

    Example:
        >>> pubkey = b"\\x12\\x34\\x56\\x78" * 8  # 32-byte Ed25519 key
        >>> prime = hash_to_prime(pubkey)
        >>> assert _mr_is_probable_prime(prime)  # Verify it's actually prime
    """
    if not isinstance(pubkey_bytes, bytes):
        raise TypeError("pubkey_bytes must be bytes")
    if not pubkey_bytes:
        raise ValueError("pubkey_bytes cannot be empty")
    if max_attempts <= 0:
        raise ValueError("max_attempts must be positive")
    if min_bits < 64:
        raise ValueError("min_bits should be >= 64")

    base = int.from_bytes(hashlib.sha256(pubkey_bytes).digest(), "big")
    if base.bit_length() < min_bits:
        base |= (1 << (min_bits - 1))
    if base % 2 == 0:
        base += 1

    cand = base
    for _ in range(max_attempts):
        if _mr_is_probable_prime(cand, mr_rounds):
            return cand
        cand += 2

    raise ValueError("Could not find prime within max_attempts")


def hash_to_prime_coprime_lambda(pubkey_bytes: bytes, lambda_n: int, *, min_bits: int = 256, max_attempts: int = 200_000, mr_rounds: int = 64) -> int:
    """
    Convert public key bytes to a prime number coprime to λ(N).

    This is useful for trapdoor operations where primes need to be coprime to λ(N).

    Args:
        pubkey_bytes: The input bytes to convert
        lambda_n: Carmichael's lambda function value λ(N)
        min_bits: Minimum bit length for the prime (default: 256)
        max_attempts: Maximum number of attempts to find a prime (default: 200_000)
        mr_rounds: Number of Miller-Rabin rounds (default: 64)

    Returns:
        int: A prime number coprime to λ(N)

    Raises:
        ValueError: If no suitable prime is found within max_attempts
    """
    if not isinstance(lambda_n, int) or lambda_n <= 0:
        raise ValueError("lambda_n must be a positive integer")

    x = hash_to_prime(pubkey_bytes, min_bits=min_bits, max_attempts=max_attempts, mr_rounds=mr_rounds)
    tries = 0
    while tries < max_attempts and math.gcd(x, lambda_n) != 1:
        x += 2
        while not _mr_is_probable_prime(x, mr_rounds):
            x += 2
        tries += 1
    if math.gcd(x, lambda_n) != 1:
        raise ValueError("Failed to find prime coprime to λ(N) within max_attempts")
    return x


def _test_hash_to_prime() -> None:
    """Test the hash_to_prime function with various inputs."""
    test_cases = [
        b"test_key_1",
        b"a" * 32,  # 32-byte key
        b"\x00" * 32,  # All zeros
        b"\xff" * 32,  # All ones
        b"Ed25519_public_key_example_12345678"[:32],  # Realistic Ed25519 key
        # Real 2048-bit RSA public key in PEM format (base64 decoded)
        b'''-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2aGRQGPK2KJvMBoaprhM
0v90365hdh/wgjV8WQ4XnFgsjMDRUKg1ySIH6e2vP2IXoMfcePVXFZdBRAftCm/V
XF9WJR6u43Xh5a2ehZBZuqAqb4EmdeAcpQRG7vgLyKrYfJVA1awVEKMvzkpgW3Sj
uXr91CyKS/UI6Key0g/DfUKHA8yP/PxEclF05QE+IXpXBdrVt6CCGY+gTG+u+r3W
G0NoS5JidNuCcKGpNVa8qnq+sdm4zGB9SyfzE4wb6B57rni/dTy0L1bZ+I/3eW7h
xL3JO/UhrpjKJG/Diuj2KmDAdTJzBMjb2HIt+QMfJKY6u4/r7myHvF6BE4UM2Bqe
fQIDAQAB
-----END PUBLIC KEY-----''',
    ]

    print("Testing hash_to_prime function:")
    for i, test_input in enumerate(test_cases):
        try:
            prime = hash_to_prime(test_input)
            print(
                f"  Test {i+1}: {test_input[:16]}... -> Prime: {prime} ({prime.bit_length()} bits)"
            )
            assert _mr_is_probable_prime(prime), f"Result {prime} is not prime!"
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
