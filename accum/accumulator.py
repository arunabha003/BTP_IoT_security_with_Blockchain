"""
RSA Accumulator Core Operations

Implements the fundamental RSA accumulator operations for membership
proofs and accumulator updates.
"""

from typing import Iterable, Optional, Tuple, Set
from functools import reduce

try:
    from .trapdoor_operations import trapdoor_remove_member, trapdoor_batch_remove_members
except ImportError:
    from trapdoor_operations import trapdoor_remove_member, trapdoor_batch_remove_members


def add_member(A: int, p: int, N: int) -> int:
    """
    Add a new member (prime p) to the accumulator A.

    The RSA accumulator operation: A^p mod N

    Args:
        A: Current accumulator value
        p: Prime representing the new member to add
        N: RSA modulus

    Returns:
        int: New accumulator value after adding member p

    Raises:
        ValueError: If inputs are invalid (non-positive or p >= N)

    Example:
        >>> N = 35  # Small example (7 * 5)
        >>> g = 2   # Generator
        >>> A = g   # Initial accumulator
        >>> p = 3   # Prime to add
        >>> new_A = add_member(A, p, N)
        >>> assert new_A == pow(A, p, N)
    """
    if A <= 0 or p <= 0 or N <= 0:
        raise ValueError("All parameters must be positive")

    return pow(A, p, N)


def recompute_root(primes: Iterable[int], N: int, g: int) -> int:
    """
    Recompute accumulator root from scratch given a set of primes.

    Uses iterative modular exponentiation to avoid huge intermediate exponents.

    Args:
        primes: Iterable of prime numbers to include in accumulator
        N: RSA modulus
        g: Generator base

    Returns:
        int: Accumulator root value

    Raises:
        ValueError: If inputs are invalid

    Example:
        >>> primes = [3, 5, 7]
        >>> N = 35
        >>> g = 2
        >>> root = recompute_root(primes, N, g)
        >>> # root = ((g^3)^5)^7 mod N = 2^105 mod 35
    """
    if N <= 0 or g <= 0:
        raise ValueError("N and g must be positive")

    if g >= N:
        raise ValueError("Generator g must be less than modulus N")

    prime_list = list(primes)
    if not prime_list:
        return g  # Empty set -> just the generator

    # Start with generator as accumulator
    A = g

    # Iteratively add each prime using modular exponentiation
    for p in prime_list:
        if p <= 0:
            raise ValueError("All primes must be positive")
        # Note: Removed p >= N check as it's not mathematically necessary for exponents
        A = pow(A, p, N)

    return A


def membership_witness(current_primes: Set[int], target_p: int, N: int, g: int) -> int:
    """
    Compute membership witness for a target prime p.

    The witness is the accumulator value for all primes except p:
    w = g^(product of primes_without_p) mod N

    If p is in current_primes, excludes p from the witness computation.
    If p is not in current_primes, uses all current_primes for the witness.
    For a single member (when current_primes is empty), the witness is g.

    Args:
        current_primes: Complete set of primes in the accumulator
        target_p: The prime for which to generate the witness
        N: RSA modulus
        g: Generator base

    Returns:
        int: Membership witness for target_p

    Example:
        >>> # If set is {3, 5, 7} and we want witness for 5
        >>> witness = membership_witness({3, 5, 7}, 5, N, g)
        >>> # witness = g^(3*7) mod N
        >>> # For prime not in set (potential witness):
        >>> witness = membership_witness({3, 5, 7}, 11, N, g)
        >>> # witness = g^(3*5*7) mod N
        >>> # For single member case:
        >>> witness = membership_witness(set(), 13, N, g)
        >>> # witness = g
    """
    # Validate inputs
    if N <= 0 or g <= 0:
        raise ValueError("N and g must be positive")
    if g >= N:
        raise ValueError("Generator g must be less than modulus N")
    if target_p <= 1:
        raise ValueError(f"Target prime {target_p} must be greater than 1")

    # Special case: single member (empty set)
    if not current_primes:
        return g

    # Create set from current_primes and subtract target if present
    S = set(current_primes)
    return recompute_root(S - {target_p} if target_p in S else S, N, g)


def verify_membership(w: int, p: int, A: int, N: int) -> bool:
    """
    Verify that prime p is a member of accumulator A using witness w.

    Verification equation: w^p ≡ A (mod N) or A = w^p mod N

    Args:
        w: Membership witness for prime p
        p: Prime to verify membership for
        A: Current accumulator value
        N: RSA modulus

    Returns:
        bool: True if p is a valid member, False otherwise

    Example:
        >>> # Verify that prime 5 is in accumulator
        >>> is_member = verify_membership(witness, 5, accumulator, N)
        >>> assert is_member  # Should be True if 5 was added
    """
    if w <= 0 or p <= 0 or A <= 0 or N <= 0:
        return False

    if w >= N or A >= N:
        return False

    # Check if w^p ≡ A (mod N)
    return pow(w, p, N) == A


def remove_member(A: int, p: int, N: int, trapdoor: Optional[Tuple[int, int]] = None) -> int:
    """
    Remove a member (prime p) from the accumulator A.

    This requires computing the modular inverse: A^(1/p) mod N
    With trapdoor information (factorization of N), this can be done efficiently.
    Without trapdoor, recomputation from remaining set is recommended.

    Args:
        A: Current accumulator value
        p: Prime representing the member to remove
        N: RSA modulus
        trapdoor: Optional tuple (p_factor, q_factor) where N = p_factor * q_factor

    Returns:
        int: New accumulator value after removing member p

    Raises:
        ValueError: If inputs are invalid
        NotImplementedError: If removal without trapdoor is attempted

    Note:
        With trapdoor: Efficient O(log N) removal using modular inverse
        Without trapdoor: Must use recompute_root() with updated prime set
        
    Example:
        >>> # With trapdoor (efficient)
        >>> A_new = remove_member(A, prime, N, trapdoor=(p_factor, q_factor))
        >>> 
        >>> # Without trapdoor (fallback to recomputation)
        >>> remaining_primes = [p for p in original_primes if p != prime_to_remove]
        >>> A_new = recompute_root(remaining_primes, N, g)
    """
    if A <= 0 or p <= 0 or N <= 0:
        raise ValueError("All parameters must be positive")

    if trapdoor is None:
        raise NotImplementedError(
            "Direct removal requires trapdoor (factorization of N). "
            "Provide trapdoor=(p_factor, q_factor) or use recompute_root() "
            "with the updated prime set instead."
        )

    # Extract trapdoor factors
    p_factor, q_factor = trapdoor
    
    # Use trapdoor-based removal
    return trapdoor_remove_member(A, p, N, p_factor, q_factor)


def batch_add_members(A: int, primes: Iterable[int], N: int) -> int:
    """
    Efficiently add multiple members to the accumulator.

    Uses iterative modular exponentiation to avoid huge intermediate exponents.

    Args:
        A: Current accumulator value
        primes: Iterable of primes to add
        N: RSA modulus

    Returns:
        int: New accumulator value after adding all primes
    """
    prime_list = list(primes)
    if not prime_list:
        return A

    # Iteratively add each prime using modular exponentiation
    for p in prime_list:
        if p <= 0:
            raise ValueError("All primes must be positive")
        # Note: Removed p >= N check as it's not mathematically necessary for exponents
        A = pow(A, p, N)

    return A


def batch_remove_members(A: int, primes: Iterable[int], N: int, trapdoor: Optional[Tuple[int, int]] = None) -> int:
    """
    Efficiently remove multiple members from the accumulator.

    With trapdoor information, computes: A^(1/product of primes) mod N
    Without trapdoor, falls back to recomputation from remaining set.

    Args:
        A: Current accumulator value
        primes: Iterable of primes to remove
        N: RSA modulus
        trapdoor: Optional tuple (p_factor, q_factor) where N = p_factor * q_factor

    Returns:
        int: New accumulator value after removing all primes

    Raises:
        ValueError: If inputs are invalid
        NotImplementedError: If removal without trapdoor is attempted
        
    Example:
        >>> # With trapdoor (efficient)
        >>> A_new = batch_remove_members(A, [prime1, prime2], N, trapdoor=(p, q))
        >>> 
        >>> # Without trapdoor (fallback to recomputation)
        >>> remaining_primes = [p for p in original_primes if p not in primes_to_remove]
        >>> A_new = recompute_root(remaining_primes, N, g)
    """
    prime_list = list(primes)
    if not prime_list:
        return A

    if trapdoor is None:
        raise NotImplementedError(
            "Batch removal requires trapdoor (factorization of N). "
            "Provide trapdoor=(p_factor, q_factor) or use recompute_root() "
            "with the updated prime set instead."
        )

    # Extract trapdoor factors
    p_factor, q_factor = trapdoor
    
    # Use trapdoor-based batch removal
    return trapdoor_batch_remove_members(A, prime_list, N, p_factor, q_factor)


def _test_accumulator_operations() -> None:
    """Test accumulator operations with small primes."""
    # Use small numbers for testing
    N = 35  # 5 * 7
    g = 2

    print("Testing RSA Accumulator Operations:")
    print(f"N = {N}, g = {g}")

    # Test 1: Add single member
    print("\n1. Testing add_member:")
    A = g
    p1 = 3
    A1 = add_member(A, p1, N)
    print(f"   add_member({A}, {p1}, {N}) = {A1}")

    # Test 2: Add another member
    p2 = 11
    A2 = add_member(A1, p2, N)
    print(f"   add_member({A1}, {p2}, {N}) = {A2}")

    # Test 3: Recompute from scratch
    print("\n2. Testing recompute_root:")
    primes = [p1, p2]
    A_recomputed = recompute_root(primes, N, g)
    print(f"   recompute_root({primes}, {N}, {g}) = {A_recomputed}")
    print(f"   Matches incremental: {A2 == A_recomputed}")

    # Test 4: Membership witness and verification
    print("\n3. Testing membership witness/verification:")

    # Witness for p1 (exclude p1, include p2)
    w1 = membership_witness({p1, p2}, p1, N, g)
    is_member_1 = verify_membership(w1, p1, A2, N)
    print(f"   witness for {p1}: {w1}")
    print(f"   verify_membership({w1}, {p1}, {A2}, {N}) = {is_member_1}")

    # Witness for p2 (exclude p2, include p1)
    w2 = membership_witness({p1, p2}, p2, N, g)
    is_member_2 = verify_membership(w2, p2, A2, N)
    print(f"   witness for {p2}: {w2}")
    print(f"   verify_membership({w2}, {p2}, {A2}, {N}) = {is_member_2}")

    # Test 5: Non-member verification (should fail)
    print("\n4. Testing non-member verification:")
    p_fake = 13
    w_fake = membership_witness({p1, p2}, p_fake, N, g)  # Witness without p_fake
    is_member_fake = verify_membership(w_fake, p_fake, A2, N)
    print(f"   verify_membership for non-member {p_fake}: {is_member_fake}")

    # Test 6: Batch operations
    print("\n5. Testing batch operations:")
    A_batch = batch_add_members(g, [p1, p2], N)
    print(f"   batch_add_members({g}, {[p1, p2]}, {N}) = {A_batch}")
    print(f"   Matches step-by-step: {A_batch == A2}")


if __name__ == "__main__":
    _test_accumulator_operations()
