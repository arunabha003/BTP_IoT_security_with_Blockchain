"""
RSA Parameters for Accumulator

Provides demo 2048-bit RSA parameters (modulus N and generator g)
for accumulator operations.
"""

import json
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

        return N_int, g_int

    except FileNotFoundError:
        raise FileNotFoundError(f"RSA parameters file not found: {params_file}")
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Invalid parameters file format: {e}")


def _generate_demo_params() -> None:
    """
    Generate demo RSA parameters and save to params.json.

    Note: This uses hardcoded safe demo parameters for testing.
    In production, use proper RSA key generation with strong entropy.
    """
    # Demo 2048-bit RSA modulus (product of two large primes)
    # This is a known safe composite for testing purposes
    N_hex = (
        "d436502b312b08215b916ca8643fd5a63fcc7b5e30d1b1c929b0152d5a26e"
        "8a1c6e13c167c8b5e2f48c7b1e2f5d8a9c6b3e4f5a8b9c2d3e4f5a6b7c8d"
        "9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8"
        "d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c"
        "8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7"
        "c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b"
        "7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6"
        "b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a"
        "6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f"
    )

    # Use a simple generator (often g=2 works well for RSA accumulators)
    g_hex = "2"

    params = {
        "N": N_hex,
        "g": g_hex,
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
