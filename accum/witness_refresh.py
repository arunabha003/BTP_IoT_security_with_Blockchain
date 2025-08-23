"""
Witness Refresh for RSA Accumulators

Handles updating membership witnesses when the accumulator changes
due to additions or removals of other members.
"""

from typing import Set

try:
    from .accumulator import recompute_root
except ImportError:
    from accumulator import recompute_root


def refresh_witness(target_p: int, set_primes: Set[int], N: int, g: int) -> int:
    """
    Refresh the membership witness for a target prime after set changes.

    When the accumulator set changes (members added/removed), existing
    witnesses become stale and need to be refreshed. This function
    recomputes the witness for target_p given the current set.

    Args:
        target_p: The prime whose witness needs refreshing
        set_primes: Current complete set of primes in the accumulator
        N: RSA modulus
        g: Generator base

    Returns:
        int: Updated witness for target_p

    Raises:
        ValueError: If target_p is not in set_primes or parameters are invalid

    Example:
        >>> # Initial set: {3, 5, 7}, witness for 5
        >>> old_witness = membership_witness([3, 7], N, g)
        >>>
        >>> # Add new member 11: set becomes {3, 5, 7, 11}
        >>> new_set = {3, 5, 7, 11}
        >>> new_witness = refresh_witness(5, new_set, N, g)
        >>> # new_witness = g^(3*7*11) mod N
    """
    if target_p not in set_primes:
        raise ValueError(f"Target prime {target_p} not found in set_primes")

    if N <= 0 or g <= 0:
        raise ValueError("N and g must be positive")

    if target_p <= 0:
        raise ValueError("target_p must be positive")

    # Create set without target prime
    primes_without_target = set_primes - {target_p}

    # Recompute witness as accumulator of remaining primes
    return recompute_root(primes_without_target, N, g)


def batch_refresh_witnesses(set_primes: Set[int], N: int, g: int) -> dict[int, int]:
    """
    Refresh witnesses for all members in the current set.

    Efficiently computes fresh witnesses for all primes in the set.
    This is useful after major set changes or for periodic refresh.

    Args:
        set_primes: Complete set of primes currently in the accumulator
        N: RSA modulus
        g: Generator base

    Returns:
        dict[int, int]: Mapping from prime -> witness

    Example:
        >>> current_set = {3, 5, 7, 11}
        >>> witnesses = batch_refresh_witnesses(current_set, N, g)
        >>> # witnesses[5] = g^(3*7*11) mod N
        >>> # witnesses[7] = g^(3*5*11) mod N
    """
    if N <= 0 or g <= 0:
        raise ValueError("N and g must be positive")

    witnesses = {}

    for target_prime in set_primes:
        # Compute witness for this prime
        witnesses[target_prime] = refresh_witness(target_prime, set_primes, N, g)

    return witnesses


def update_witness_on_addition(old_witness: int, added_prime: int, N: int) -> int:
    """
    Update an existing witness when a new prime is added to the set.

    When a new prime is added, existing witnesses can be updated efficiently:
    new_witness = old_witness^added_prime mod N

    Args:
        old_witness: Existing witness before addition
        added_prime: The prime that was just added to the set
        N: RSA modulus

    Returns:
        int: Updated witness after addition

    Note:
        This is more efficient than full recomputation for single additions.
    """
    if old_witness <= 0 or added_prime <= 0 or N <= 0:
        raise ValueError("All parameters must be positive")

    return pow(old_witness, added_prime, N)


def update_witness_on_removal(old_witness: int, removed_prime: int, N: int) -> int:
    """
    Update an existing witness when a prime is removed from the set.

    When a prime is removed, existing witnesses need to be "divided" by
    that prime: new_witness = old_witness^(1/removed_prime) mod N

    Args:
        old_witness: Existing witness before removal
        removed_prime: The prime that was just removed from the set
        N: RSA modulus

    Returns:
        int: Updated witness after removal

    Raises:
        NotImplementedError: Removal without trapdoor not implemented

    Note:
        This requires computing modular inverse, which needs either:
        1. Factorization of N (trapdoor), or
        2. Extended Euclidean algorithm (if gcd(removed_prime, φ(N)) = 1)

        For simplicity, we recommend using refresh_witness() instead.
    """
    raise NotImplementedError(
        "Efficient witness update on removal requires trapdoor information. "
        "Use refresh_witness() or batch_refresh_witnesses() instead."
    )


def _test_witness_refresh() -> None:
    """Test witness refresh operations."""
    # Use small numbers for testing
    N = 35  # 5 * 7
    g = 2

    print("Testing Witness Refresh Operations:")
    print(f"N = {N}, g = {g}")

    # Initial set
    initial_set = {3, 11}
    print(f"\nInitial set: {initial_set}")

    # Get initial witnesses
    initial_witnesses = batch_refresh_witnesses(initial_set, N, g)
    print(f"Initial witnesses: {initial_witnesses}")

    # Add a new member
    new_prime = 13
    updated_set = initial_set | {new_prime}
    print(f"\nAdding prime {new_prime}, new set: {updated_set}")

    # Method 1: Full refresh
    new_witnesses_full = batch_refresh_witnesses(updated_set, N, g)
    print(f"New witnesses (full refresh): {new_witnesses_full}")

    # Method 2: Incremental update for existing members
    print("\nIncremental witness updates:")
    for prime in initial_set:
        old_witness = initial_witnesses[prime]
        new_witness_incremental = update_witness_on_addition(old_witness, new_prime, N)
        new_witness_full = new_witnesses_full[prime]

        print(f"  Prime {prime}:")
        print(f"    Old witness: {old_witness}")
        print(f"    Incremental: {new_witness_incremental}")
        print(f"    Full refresh: {new_witness_full}")
        print(f"    Match: {new_witness_incremental == new_witness_full}")

    # Test individual refresh
    print("\nTesting individual refresh_witness:")
    for prime in updated_set:
        witness = refresh_witness(prime, updated_set, N, g)
        expected = new_witnesses_full[prime]
        print(
            f"  refresh_witness({prime}) = {witness}, expected = {expected}, match = {witness == expected}"
        )

    # Test error cases
    print("\nTesting error cases:")
    try:
        refresh_witness(999, updated_set, N, g)  # Prime not in set
        print("  ERROR: Should have raised ValueError")
    except ValueError as e:
        print(f"  ✓ Correctly raised ValueError: {e}")


if __name__ == "__main__":
    _test_witness_refresh()
