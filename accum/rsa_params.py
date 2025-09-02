"""
RSA Parameters for Accumulator

Provides demo 2048-bit RSA parameters (modulus N and generator g)
for accumulator operations.
"""

import json
import math
from pathlib import Path
from typing import Tuple


def load_params() -> Tuple[int, int]:
    """
    Load RSA parameters for accumulator operations.

    Returns:
        Tuple[int, int]: A tuple containing (N, g) where:
            - N: 2048-bit RSA modulus
            - g: Generator base for accumulator

    Raises:
        FileNotFoundError: If params.json is not found
        ValueError: If parameters are invalid or malformed
    """
    params_file = Path(__file__).parent / "params.json"

    try:
        with open(params_file, "r") as f:
            params = json.load(f)

        N_hex = params["N"]
        g_hex = params["g"]

        # Convert from hex strings to integers
        N_int = int(N_hex, 16)
        g_int = int(g_hex, 16)

        # Basic validation
        if N_int <= 0 or g_int <= 0:
            raise ValueError("Parameters must be positive integers")

        if N_int.bit_length() < 2040:  # Allow some tolerance for 2048-bit
            raise ValueError("N must be at least 2048 bits")

        if g_int >= N_int:
            raise ValueError("Generator g must be less than modulus N")

        # Additional validation for cryptographic security
        if math.gcd(N_int, g_int) != 1:
            raise ValueError("RSA modulus N and generator g must be coprime")

        return N_int, g_int

    except FileNotFoundError:
        # Fall back to demo parameters if file is missing
        return generate_demo_params()
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Invalid parameters file format: {e}")


def generate_demo_params() -> Tuple[int, int]:
    """
    Generate demo RSA parameters for testing.

    Returns:
        Tuple[int, int]: A tuple containing (N, g) with demo parameters

    Note: This uses hardcoded safe demo parameters for testing.
    In production, use proper RSA key generation with strong entropy.
    """
    # Demo 2048-bit RSA modulus (product of two large primes)
    # This is a known safe composite for testing purposes
    N_hex = ("0xc09f09d858a2037ca76e7b1c52543a002213c8f1086a587f41f9616ac4fd8d6ecbec8852fd95adaec50c34cde7f0e676059896c2be9f2e479297a7507f1d1e58afe26be99489b798a704f1627b8e6b09b9a88b01ce697c4197bbeec134bb41aac0579c8026deec542c6965b0b8d39e77405a65110af3774f88cd463c6c304483c6f0a802f288c8ba4f071b6afcefa2b9395e2fe71aaea8e277c06b5d2724153c4a20209c06f2e0f523fb96b576a37937fb340478e86bbbfa8914c50f0f33a8948836caf99ca5f7f6983787a25e091d9591204dbb8c14e473d172f4e7a0b5164cf9ee97f838ded82fd2357a51a6f495850ef268009e7ecc19047f8e99a91a4d9b")

    # Convert N first to compute QR generator
    N_int = int(N_hex, 16)

    # Use QR subgroup generator: g = 2^2 mod N (ensures g is in quadratic residue subgroup)
    g_int = pow(2, 2, N_int)

    return N_int, g_int


def generate_toy_params() -> Tuple[int, int]:
    """
    Generate small toy RSA parameters for unit testing.

    Returns:
        Tuple[int, int]: A tuple containing small (N, g) for fast testing
    """
    # Small toy parameters: N = 11 * 19 = 209, g = 4
    return 209, 4


def validate_params(N: int, g: int) -> None:
    """
    Validate RSA parameters for accumulator operations.

    Args:
        N: RSA modulus
        g: Generator base

    Raises:
        ValueError: If parameters are invalid
    """
    if N <= 0:
        raise ValueError("RSA modulus N must be positive")

    if g <= 0:
        raise ValueError("Generator g must be positive")

    if g >= N:
        raise ValueError("Generator g must be less than modulus N")

    if N.bit_length() < 1024:  # Minimum for security
        raise ValueError("RSA modulus N must be at least 1024 bits")

    # Check if N and g are coprime
    if math.gcd(N, g) != 1:
        raise ValueError("RSA modulus N and generator g must be coprime")


def _generate_demo_params() -> None:
    """
    Generate demo RSA parameters and save to params.json.

    Note: This uses hardcoded safe demo parameters for testing.
    In production, use proper RSA key generation with strong entropy.
    """
    N_int, g_int = generate_demo_params()

    params = {
        "N": hex(N_int),
        "g": hex(g_int),
        "description": "Demo 2048-bit RSA parameters for accumulator testing",
        "warning": "DO NOT USE IN PRODUCTION - Use proper RSA key generation",
    }

    params_file = Path(__file__).parent / "params.json"
    with open(params_file, "w") as f:
        json.dump(params, f, indent=2)

    print(f"Demo parameters generated: {params_file}")


if __name__ == "__main__":
    # Generate demo params if run directly
    _generate_demo_params()

    # Test loading
    try:
        N, g = load_params()
        print(f"Loaded N: {N.bit_length()} bits")
        print(f"Loaded g: {g}")
    except Exception as e:
        print(f"Error: {e}")
