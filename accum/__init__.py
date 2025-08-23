"""
RSA Accumulator Package for IoT Device Identity Management

This package provides RSA accumulator functionality for managing
revocable IoT device identities with cryptographic proofs.
"""

from .accumulator import (
    add_member,
    recompute_root,
    membership_witness,
    verify_membership,
)
from .hash_to_prime import hash_to_prime
from .rsa_params import load_params
from .witness_refresh import refresh_witness

__version__ = "0.1.0"
__all__ = [
    "add_member",
    "recompute_root",
    "membership_witness",
    "verify_membership",
    "hash_to_prime",
    "load_params",
    "refresh_witness",
]
