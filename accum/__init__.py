"""
RSA Accumulator Package for IoT Device Identity Management

This package provides RSA accumulator functionality for managing
revocable IoT device identities with cryptographic proofs.
"""

try:
    # Try relative imports first (when used as package)
    from .accumulator import (
        add_member,
        recompute_root,
        membership_witness,
        verify_membership,
    )
    from .hash_to_prime import hash_to_prime
    from .rsa_params import load_params
    from .witness_refresh import refresh_witness
    from .rsa_key_generator import (
        generate_ed25519_keypair,
        generate_rsa_keypair,
        generate_test_devices,
        save_test_devices,
        load_test_devices,
        generate_device_signature,
        verify_device_signature,
        get_key_info,
    )
except ImportError:
    # Fall back to absolute imports (when imported from outside)
    from accumulator import (
        add_member,
        recompute_root,
        membership_witness,
        verify_membership,
    )
    from hash_to_prime import hash_to_prime
    from rsa_params import load_params
    from witness_refresh import refresh_witness
    from rsa_key_generator import (
        generate_ed25519_keypair,
        generate_rsa_keypair,
        generate_test_devices,
        save_test_devices,
        load_test_devices,
        generate_device_signature,
        verify_device_signature,
        get_key_info,
    )

__version__ = "0.1.0"
__all__ = [
    "add_member",
    "recompute_root",
    "membership_witness",
    "verify_membership",
    "hash_to_prime",
    "load_params",
    "refresh_witness",
    "generate_ed25519_keypair",
    "generate_rsa_keypair",
    "generate_test_devices",
    "save_test_devices",
    "load_test_devices",
    "generate_device_signature",
    "verify_device_signature",
    "get_key_info",
]
