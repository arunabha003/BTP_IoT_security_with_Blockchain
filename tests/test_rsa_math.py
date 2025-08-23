"""
RSA Accumulator Mathematics Verification

Tests that verify the RSA accumulator mathematics are implemented correctly
according to the specification in the user query.

This includes:
- Basic accumulator operations (add, verify, revoke)
- Mathematical properties (w^p ≡ A mod N)
- Incremental vs batch computation consistency
- Witness refresh after revocation
"""

import pytest
from typing import Set, Dict


def test_toy_rsa_example():
    """Test the exact toy example from the user specification."""
    # RSA parameters from the example
    N = 209  # 11 * 19
    g = 4    # 2^2 mod 209
    
    # Device primes from the example
    device_primes = [13, 17, 23]
    
    print(f"\n🧮 Testing RSA Accumulator Math (N={N}, g={g})")
    print("=" * 50)
    
    # Build accumulator incrementally as specified
    A = [g]  # A[0] = g = 4
    witnesses = {}
    
    print(f"Initial: A₀ = {A[0]}")
    
    # Add device 13
    A.append(pow(A[0], 13, N))  # A₁ = A₀^13 mod N
    witnesses[13] = A[0]  # witness for 13 is old accumulator
    print(f"Add 13:  A₁ = {A[0]}^13 mod {N} = {A[1]}")
    print(f"         w₁₃ = {witnesses[13]}")
    
    # Add device 17
    A.append(pow(A[1], 17, N))  # A₂ = A₁^17 mod N
    witnesses[13] = pow(witnesses[13], 17, N)  # update witness for 13
    witnesses[17] = A[1]  # witness for 17 is old accumulator
    print(f"Add 17:  A₂ = {A[1]}^17 mod {N} = {A[2]}")
    print(f"         w₁₃ = {witnesses[13]} (updated)")
    print(f"         w₁₇ = {witnesses[17]}")
    
    # Add device 23
    A.append(pow(A[2], 23, N))  # A₃ = A₂^23 mod N
    witnesses[13] = pow(witnesses[13], 23, N)  # update witness for 13
    witnesses[17] = pow(witnesses[17], 23, N)  # update witness for 17
    witnesses[23] = A[2]  # witness for 23 is old accumulator
    print(f"Add 23:  A₃ = {A[2]}^23 mod {N} = {A[3]}")
    print(f"         w₁₃ = {witnesses[13]} (updated)")
    print(f"         w₁₇ = {witnesses[17]} (updated)")
    print(f"         w₂₃ = {witnesses[23]}")
    
    current_accumulator = A[3]  # A₃ = 196
    
    # Verify the expected values from the specification
    assert current_accumulator == 196, f"Expected A₃=196, got {current_accumulator}"
    assert witnesses[13] == 180, f"Expected w₁₃=180, got {witnesses[13]}"
    assert witnesses[17] == 168, f"Expected w₁₇=168, got {witnesses[17]}"
    assert witnesses[23] == 169, f"Expected w₂₃=169, got {witnesses[23]}"
    
    print(f"\n✅ All intermediate values match specification!")
    
    # Verify membership proofs: w^p ≡ A (mod N)
    print(f"\n🔍 Verifying membership proofs:")
    for prime in device_primes:
        witness = witnesses[prime]
        computed = pow(witness, prime, N)
        is_valid = computed == current_accumulator
        
        print(f"   Device {prime}: {witness}^{prime} mod {N} = {computed} {'✅' if is_valid else '❌'}")
        assert is_valid, f"Membership proof failed for device {prime}"
    
    print(f"\n✅ All membership proofs verified!")
    
    # Test revocation (trapdoorless method)
    print(f"\n🚫 Testing revocation of device 17...")
    
    # Remove device 17, recompute from remaining set {13, 23}
    remaining_primes = [13, 23]
    product = 1
    for p in remaining_primes:
        product *= p
    
    new_accumulator = pow(g, product, N)  # g^(13*23) mod N
    print(f"   New accumulator = {g}^({13}×{23}) mod {N} = {g}^{product} mod {N} = {new_accumulator}")
    
    # Expected value from specification
    assert new_accumulator == 168, f"Expected new accumulator=168, got {new_accumulator}"
    
    # Verify old witness for device 17 no longer works
    old_witness_17 = witnesses[17]
    old_proof = pow(old_witness_17, 17, N)
    revocation_works = old_proof != new_accumulator
    
    print(f"   Old witness 17: {old_witness_17}^17 mod {N} = {old_proof} (should ≠ {new_accumulator})")
    print(f"   Revocation works: {'✅' if revocation_works else '❌'}")
    assert revocation_works, "Revocation should invalidate old witness"
    
    # Verify remaining devices still work with refreshed witnesses
    print(f"\n🔄 Testing witness refresh for remaining devices:")
    for prime in remaining_primes:
        # Compute fresh witness for remaining device
        other_primes_product = 1
        for other_prime in remaining_primes:
            if other_prime != prime:
                other_primes_product *= other_prime
        
        fresh_witness = pow(g, other_primes_product, N)
        fresh_proof = pow(fresh_witness, prime, N)
        is_valid = fresh_proof == new_accumulator
        
        print(f"   Device {prime}: fresh witness = {fresh_witness}")
        print(f"   Proof: {fresh_witness}^{prime} mod {N} = {fresh_proof} {'✅' if is_valid else '❌'}")
        assert is_valid, f"Fresh witness failed for device {prime}"
    
    print(f"\n🎉 RSA Accumulator Mathematics: ALL TESTS PASSED!")


def test_batch_vs_incremental_consistency():
    """Test that batch and incremental accumulator computation give same result."""
    N = 209
    g = 4
    primes = [13, 17, 23, 29, 31]
    
    print(f"\n🧮 Testing Batch vs Incremental Consistency")
    print("=" * 45)
    
    # Incremental computation
    incremental_A = g
    for prime in primes:
        incremental_A = pow(incremental_A, prime, N)
    
    # Batch computation  
    product = 1
    for prime in primes:
        product *= prime
    batch_A = pow(g, product, N)
    
    print(f"Incremental: A = {incremental_A}")
    print(f"Batch:       A = {batch_A}")
    print(f"Match:       {'✅' if incremental_A == batch_A else '❌'}")
    
    assert incremental_A == batch_A, "Incremental and batch should give same result"


def test_witness_computation_methods():
    """Test different methods of computing witnesses give consistent results."""
    N = 209
    g = 4
    all_primes = [13, 17, 23]
    target_prime = 17
    
    print(f"\n🧮 Testing Witness Computation Methods")
    print("=" * 40)
    
    # Method 1: Direct computation (product of others)
    other_primes = [p for p in all_primes if p != target_prime]
    product = 1
    for p in other_primes:
        product *= p
    witness_direct = pow(g, product, N)
    
    # Method 2: Division from full accumulator (if we had trapdoor)
    # For testing, we'll simulate this by computing full then "dividing"
    full_product = 1
    for p in all_primes:
        full_product *= p
    full_accumulator = pow(g, full_product, N)
    
    # Verify witness by checking membership
    proof = pow(witness_direct, target_prime, N)
    is_valid = proof == full_accumulator
    
    print(f"Target prime: {target_prime}")
    print(f"Other primes: {other_primes}")
    print(f"Witness:      {witness_direct}")
    print(f"Proof:        {witness_direct}^{target_prime} mod {N} = {proof}")
    print(f"Full accum:   {full_accumulator}")
    print(f"Valid:        {'✅' if is_valid else '❌'}")
    
    assert is_valid, "Witness should validate against full accumulator"


def test_accumulator_properties():
    """Test mathematical properties of the RSA accumulator."""
    N = 209
    g = 4
    
    print(f"\n🧮 Testing Accumulator Properties")
    print("=" * 35)
    
    # Property 1: Empty accumulator is the generator
    empty_accumulator = g
    print(f"Empty accumulator = g = {empty_accumulator}")
    
    # Property 2: Single element accumulator
    single_prime = 13
    single_accumulator = pow(g, single_prime, N)
    single_witness = g  # witness for single element is generator
    single_proof = pow(single_witness, single_prime, N)
    
    print(f"Single element {single_prime}:")
    print(f"  Accumulator: {g}^{single_prime} mod {N} = {single_accumulator}")
    print(f"  Witness: {single_witness}")
    print(f"  Proof: {single_witness}^{single_prime} mod {N} = {single_proof}")
    print(f"  Valid: {'✅' if single_proof == single_accumulator else '❌'}")
    
    assert single_proof == single_accumulator, "Single element proof should work"
    
    # Property 3: Order independence
    primes_order1 = [13, 17, 23]
    primes_order2 = [23, 13, 17]
    
    # Compute accumulator with different orders
    A1 = g
    for p in primes_order1:
        A1 = pow(A1, p, N)
    
    A2 = g
    for p in primes_order2:
        A2 = pow(A2, p, N)
    
    print(f"Order independence:")
    print(f"  Order {primes_order1}: A = {A1}")
    print(f"  Order {primes_order2}: A = {A2}")
    print(f"  Match: {'✅' if A1 == A2 else '❌'}")
    
    assert A1 == A2, "Accumulator should be order-independent"
    
    print(f"\n✅ All accumulator properties verified!")


if __name__ == "__main__":
    test_toy_rsa_example()
    test_batch_vs_incremental_consistency()
    test_witness_computation_methods()
    test_accumulator_properties()
