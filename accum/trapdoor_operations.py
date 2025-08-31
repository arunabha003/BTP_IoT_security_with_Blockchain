"""
Trapdoor Operations for RSA Accumulators

This module implements efficient RSA accumulator operations that require
knowledge of the factorization of N (the trapdoor information).

The main operation is removal of members from the accumulator, which requires
computing modular inverse (p-th root) operations efficiently.
"""

import math
from typing import Tuple, Optional


def extended_gcd(a: int, b: int) -> Tuple[int, int, int]:
    """
    Extended Euclidean Algorithm.
    
    Computes gcd(a, b) and coefficients x, y such that ax + by = gcd(a, b).
    
    Args:
        a: First integer
        b: Second integer
        
    Returns:
        Tuple[int, int, int]: (gcd, x, y) where ax + by = gcd
        
    Example:
        >>> gcd, x, y = extended_gcd(35, 15)
        >>> assert gcd == 5
        >>> assert 35 * x + 15 * y == 5
    """
    if a == 0:
        return b, 0, 1
    
    gcd, x1, y1 = extended_gcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    
    return gcd, x, y


def modular_inverse(a: int, m: int) -> Optional[int]:
    """
    Compute modular inverse of a modulo m.
    
    Finds x such that (a * x) ≡ 1 (mod m), if it exists.
    
    Args:
        a: Number to find inverse for
        m: Modulus
        
    Returns:
        Optional[int]: Modular inverse if it exists, None otherwise
        
    Raises:
        ValueError: If inputs are invalid
        
    Example:
        >>> inv = modular_inverse(3, 7)
        >>> assert (3 * inv) % 7 == 1
    """
    if a <= 0 or m <= 0:
        raise ValueError("Both a and m must be positive")
    
    a = a % m
    if a == 0:
        return None
    
    gcd, x, _ = extended_gcd(a, m)
    
    if gcd != 1:
        return None  # Inverse doesn't exist
    
    return (x % m + m) % m


def compute_phi_n(p: int, q: int) -> int:
    """
    Compute Euler's totient function φ(N) for N = p * q.
    
    For RSA modulus N = p * q where p and q are distinct primes:
    φ(N) = (p - 1) * (q - 1)
    
    Args:
        p: First prime factor of N
        q: Second prime factor of N
        
    Returns:
        int: φ(N) = (p - 1) * (q - 1)
        
    Raises:
        ValueError: If inputs are invalid
        
    Note:
        For cryptographic applications, prefer compute_lambda_n() which
        uses Carmichael's lambda function λ(N) = lcm(p-1, q-1).
    """
    if p <= 1 or q <= 1:
        raise ValueError("Both p and q must be greater than 1")
    
    if p == q:
        raise ValueError("p and q must be distinct")
    
    return (p - 1) * (q - 1)


def compute_lambda_n(p: int, q: int) -> int:
    """
    Compute Carmichael's lambda function λ(N) for N = p * q.
    
    For RSA modulus N = p * q where p and q are distinct primes:
    λ(N) = lcm(p - 1, q - 1)
    
    This is the correct modulus for exponent arithmetic in Z*_N.
    
    Args:
        p: First prime factor of N
        q: Second prime factor of N
        
    Returns:
        int: λ(N) = lcm(p - 1, q - 1)
        
    Raises:
        ValueError: If inputs are invalid
    """
    if p <= 1 or q <= 1:
        raise ValueError("Both p and q must be greater than 1")
    
    if p == q:
        raise ValueError("p and q must be distinct")
    
    # lcm(a, b) = a * b / gcd(a, b) = (a // gcd(a, b)) * b
    p_minus_1 = p - 1
    q_minus_1 = q - 1
    gcd_val = math.gcd(p_minus_1, q_minus_1)
    
    return (p_minus_1 // gcd_val) * q_minus_1


def trapdoor_remove_member(A: int, prime: int, N: int, p: int, q: int) -> int:
    """
    Remove a member from RSA accumulator using trapdoor information.
    
    Given accumulator A and prime to remove, computes A^(1/prime) mod N
    using knowledge of N's factorization (p, q).
    
    This is the core trapdoor operation that allows efficient removal
    without recomputing the entire accumulator from scratch.
    
    Mathematical approach:
    1. Compute λ(N) = lcm(p - 1, q - 1) (Carmichael's lambda function)
    2. Find d = prime^(-1) mod λ(N) (modular inverse)
    3. Return A^d mod N
    
    Args:
        A: Current accumulator value
        prime: Prime to remove from accumulator
        N: RSA modulus (N = p * q)
        p: First prime factor of N (trapdoor info)
        q: Second prime factor of N (trapdoor info)
        
    Returns:
        int: New accumulator value after removing prime
        
    Raises:
        ValueError: If inputs are invalid or operation is impossible
        
    Example:
        >>> # Assume we have N = p * q, and accumulator A contains prime 13
        >>> # Remove prime 13 using trapdoor
        >>> A_new = trapdoor_remove_member(A, 13, N, p, q)
        >>> # Verify: A_new^13 ≡ A (mod N)
        >>> assert pow(A_new, 13, N) == A
    """
    # Validate inputs
    if A <= 0 or prime <= 0 or N <= 0 or p <= 0 or q <= 0:
        raise ValueError("All parameters must be positive")
    
    if p * q != N:
        raise ValueError("N must equal p * q")
    
    if prime >= N:
        raise ValueError("Prime must be less than N")
    
    if not (1 <= A < N):
        raise ValueError("Accumulator A must be in [1, N-1]")
    
    if math.gcd(A, N) != 1:
        raise ValueError("Accumulator A must be coprime to N (in Z*_N)")
    
    # Compute λ(N) = lcm(p - 1, q - 1) (Carmichael's lambda function)
    lambda_n = compute_lambda_n(p, q)
    
    # Find modular inverse of prime modulo λ(N)
    # We need d such that prime * d ≡ 1 (mod λ(N))
    inverse_exp = modular_inverse(prime, lambda_n)
    
    if inverse_exp is None:
        raise ValueError(
            f"Cannot compute modular inverse of {prime} mod λ(N). "
            f"gcd({prime}, {lambda_n}) ≠ 1"
        )
    
    # Compute A^(1/prime) = A^d mod N
    result = pow(A, inverse_exp, N)
    
    return result


def trapdoor_batch_remove_members(A: int, primes_to_remove: list[int], N: int, p: int, q: int) -> int:
    """
    Remove multiple members from accumulator using trapdoor information.
    
    Efficiently removes multiple primes by computing the combined inverse
    exponent and performing a single modular exponentiation.
    
    Args:
        A: Current accumulator value
        primes_to_remove: List of primes to remove
        N: RSA modulus (N = p * q)
        p: First prime factor of N
        q: Second prime factor of N
        
    Returns:
        int: New accumulator value after removing all primes
        
    Raises:
        ValueError: If inputs are invalid or operation is impossible
    """
    if not primes_to_remove:
        return A
    
    # Validate inputs
    if A <= 0 or N <= 0 or p <= 0 or q <= 0:
        raise ValueError("All parameters must be positive")
    
    if p * q != N:
        raise ValueError("N must equal p * q")
    
    if not (1 <= A < N):
        raise ValueError("Accumulator A must be in [1, N-1]")
    
    if math.gcd(A, N) != 1:
        raise ValueError("Accumulator A must be coprime to N (in Z*_N)")
    
    # Compute λ(N) = lcm(p - 1, q - 1)
    lambda_n = compute_lambda_n(p, q)
    
    # Pre-check all primes and compute product
    product = 1
    for prime in primes_to_remove:
        if prime <= 0 or prime >= N:
            raise ValueError(f"Invalid prime: {prime}")
        if math.gcd(prime, lambda_n) != 1:
            raise ValueError(f"Prime {prime} not coprime with λ(N)")
        product = (product * prime) % lambda_n
    
    # Find modular inverse of the product
    inverse_exp = modular_inverse(product, lambda_n)
    
    if inverse_exp is None:
        raise ValueError(
            f"Cannot compute modular inverse of product mod λ(N). "
            f"gcd({product}, {lambda_n}) ≠ 1"
        )
    
    # Compute A^(1/product) mod N
    result = pow(A, inverse_exp, N)
    
    return result


def validate_prime_for_accumulator(prime: int, N: int, p: int, q: int) -> None:
    """
    Validate that a prime is suitable for use in RSA accumulator.
    
    Checks that the prime is coprime with λ(N) to ensure removal
    operations will work correctly.
    
    Args:
        prime: Prime to validate
        N: RSA modulus (N = p * q)
        p: First prime factor of N
        q: Second prime factor of N
        
    Raises:
        ValueError: If prime is not suitable for accumulator use
    """
    if prime <= 0:
        raise ValueError("Prime must be positive")
    
    if prime >= N:
        raise ValueError("Prime must be less than N")
    
    if p * q != N:
        raise ValueError("N must equal p * q")
    
    lambda_n = compute_lambda_n(p, q)
    
    if math.gcd(prime, lambda_n) != 1:
        raise ValueError(
            f"Prime {prime} is not coprime with λ(N) = {lambda_n}. "
            f"This prime cannot be safely removed using trapdoor operations."
        )


def verify_trapdoor_removal(A_old: int, A_new: int, removed_prime: int, N: int) -> bool:
    """
    Verify that a trapdoor removal operation was performed correctly.
    
    Checks that A_new^removed_prime ≡ A_old (mod N)
    
    Args:
        A_old: Original accumulator value
        A_new: New accumulator value after removal
        removed_prime: Prime that was removed
        N: RSA modulus
        
    Returns:
        bool: True if removal is verified, False otherwise
    """
    if A_old <= 0 or A_new <= 0 or removed_prime <= 0 or N <= 0:
        return False
    
    # Check if A_new^removed_prime ≡ A_old (mod N)
    return pow(A_new, removed_prime, N) == A_old


def _test_trapdoor_operations() -> None:
    """Test trapdoor operations with small primes."""
    print("Testing Trapdoor Operations:")
    
    # Use small primes for testing
    p, q = 11, 19
    N = p * q  # N = 209
    # Use QR base: g = h^2 mod N (h=2 -> g=4)
    g = pow(2, 2, N)  # g = 4, ensuring g is in quadratic residue subgroup
    lambda_n = compute_lambda_n(p, q)  # λ(N) = lcm(10, 18) = 90
    phi_n = compute_phi_n(p, q)  # φ(N) = 10 * 18 = 180
    
    print(f"N = {N} (= {p} * {q}), g = {g} (QR base)")
    print(f"λ(N) = {lambda_n} (Carmichael lambda)")
    print(f"φ(N) = {phi_n} (Euler totient)")
    
    # Test 1: Extended GCD
    print("\n1. Testing Extended GCD:")
    a, b = 35, 15
    gcd, x, y = extended_gcd(a, b)
    print(f"   extended_gcd({a}, {b}) = ({gcd}, {x}, {y})")
    print(f"   Verification: {a} * {x} + {b} * {y} = {a*x + b*y} (should equal {gcd})")
    
    # Test 2: Modular Inverse
    print("\n2. Testing Modular Inverse:")
    a, m = 3, 7
    inv = modular_inverse(a, m)
    print(f"   modular_inverse({a}, {m}) = {inv}")
    if inv:
        print(f"   Verification: ({a} * {inv}) % {m} = {(a * inv) % m} (should be 1)")
    
    # Test 3: λ(N) and φ(N) computation
    print(f"\n3. Testing λ(N) and φ(N) computation:")
    computed_lambda = compute_lambda_n(p, q)
    computed_phi = compute_phi_n(p, q)
    expected_lambda = 90  # lcm(10, 18) = 90
    expected_phi = (p - 1) * (q - 1)
    print(f"   λ({N}) = {computed_lambda}, expected = {expected_lambda}")
    print(f"   φ({N}) = {computed_phi}, expected = {expected_phi}")
    
    # Test 4: Trapdoor removal with primes coprime to λ(N)
    print(f"\n4. Testing Trapdoor Removal:")
    
    # Use primes that are coprime to λ(N) = 90 = 2 * 3^2 * 5
    # Good primes: 7, 11, 13, 17, 19, 23, 29, etc. (not 2, 3, 5)
    primes = [7, 13, 17]  # All coprime to 90
    A = g
    for prime in primes:
        A = pow(A, prime, N)
    print(f"   Initial accumulator A = {A} (contains primes {primes})")
    
    # Remove prime 13 using trapdoor
    prime_to_remove = 13
    try:
        A_new = trapdoor_remove_member(A, prime_to_remove, N, p, q)
        print(f"   After removing {prime_to_remove}: A_new = {A_new}")
        
        # Verify removal
        is_valid = verify_trapdoor_removal(A, A_new, prime_to_remove, N)
        print(f"   Verification: {is_valid}")
        
        # Double-check: A_new should equal accumulator of remaining primes
        remaining_primes = [7, 17]
        expected_A = g
        for prime in remaining_primes:
            expected_A = pow(expected_A, prime, N)
        print(f"   Expected A_new (recomputed): {expected_A}")
        print(f"   Match: {A_new == expected_A}")
        
    except ValueError as e:
        print(f"   Error: {e}")
    
    # Test 5: Batch removal
    print(f"\n5. Testing Batch Removal:")
    A_batch = g
    batch_primes = [7, 11, 13, 17]  # All coprime to λ(N) = 90
    for prime in batch_primes:
        A_batch = pow(A_batch, prime, N)
    print(f"   Initial accumulator A = {A_batch} (contains primes {batch_primes})")
    
    # Remove multiple primes
    primes_to_remove = [11, 17]
    try:
        A_batch_new = trapdoor_batch_remove_members(A_batch, primes_to_remove, N, p, q)
        print(f"   After removing {primes_to_remove}: A_new = {A_batch_new}")
        
        # Verify by recomputing from remaining primes
        remaining_primes = [7, 13]
        expected_A = g
        for prime in remaining_primes:
            expected_A = pow(expected_A, prime, N)
        print(f"   Expected A_new (recomputed): {expected_A}")
        print(f"   Match: {A_batch_new == expected_A}")
        
    except ValueError as e:
        print(f"   Error: {e}")
    
    # Test 6: Test with problematic primes (should fail gracefully)
    print(f"\n6. Testing with problematic primes:")
    try:
        # Try to remove prime 5, which divides λ(N) = 90
        A_test = pow(g, 5, N)  # A = g^5
        A_fail = trapdoor_remove_member(A_test, 5, N, p, q)
        print(f"   Unexpected success removing prime 5")
    except ValueError as e:
        print(f"   Expected error removing prime 5: {e}")
    
    try:
        # Try to remove prime 3, which divides λ(N) = 90  
        A_test = pow(g, 3, N)  # A = g^3
        A_fail = trapdoor_remove_member(A_test, 3, N, p, q)
        print(f"   Unexpected success removing prime 3")
    except ValueError as e:
        print(f"   Expected error removing prime 3: {e}")


if __name__ == "__main__":
    _test_trapdoor_operations()
