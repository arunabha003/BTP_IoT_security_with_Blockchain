"""
RSA Key Generator for IoT Identity System Testing

Generates real RSA public keys for testing the accumulator system.
These keys are used to test the complete end-to-end functionality.
"""

import json
import base64
from pathlib import Path
from typing import Dict, List, Tuple
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ed25519
from cryptography.hazmat.backends import default_backend


def generate_rsa_keypair(key_size: int = 2048) -> Tuple[str, str]:
    """
    Generate an RSA keypair and return PEM-formatted keys.

    Args:
        key_size: RSA key size in bits (default: 2048)

    Returns:
        Tuple[str, str]: (private_key_pem, public_key_pem)
    """
    # Generate RSA keypair
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend()
    )

    # Get public key
    public_key = private_key.public_key()

    # Serialize to PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    return private_pem, public_pem


def generate_ed25519_keypair() -> Tuple[str, str]:
    """
    Generate an Ed25519 keypair for IoT device authentication.

    Returns:
        Tuple[str, str]: (private_key_base64, public_key_pem)
    """
    # Generate Ed25519 keypair
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    # Get raw private key bytes and encode as base64
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    private_base64 = base64.b64encode(private_bytes).decode()

    # Get public key as PEM
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    return private_base64, public_pem


def generate_test_devices(num_devices: int = 5) -> Dict[str, Dict[str, str]]:
    """
    Generate a set of test IoT devices with Ed25519 keys.

    Args:
        num_devices: Number of devices to generate

    Returns:
        Dict with device data for testing
    """
    devices = {}

    for i in range(num_devices):
        device_id = f"sensor_{i:03d}"
        private_key_b64, public_key_pem = generate_ed25519_keypair()

        devices[device_id] = {
            "device_id": device_id,
            "private_key_base64": private_key_b64,
            "public_key_pem": public_key_pem,
            "status": "generated"
        }

    return devices


def save_test_devices(devices: Dict[str, Dict[str, str]], filename: str = "test_devices.json"):
    """
    Save generated test devices to JSON file.

    Args:
        devices: Dictionary of test devices
        filename: Output filename
    """
    with open(filename, 'w') as f:
        json.dump(devices, f, indent=2)

    print(f"✅ Saved {len(devices)} test devices to {filename}")


def load_test_devices(filename: str = "test_devices.json") -> Dict[str, Dict[str, str]]:
    """
    Load test devices from JSON file.

    Args:
        filename: Input filename

    Returns:
        Dict with device data
    """
    with open(filename, 'r') as f:
        return json.load(f)


def generate_device_signature(message: str, private_key_base64: str) -> str:
    """
    Generate a signature for a message using device private key.

    Args:
        message: Message to sign
        private_key_base64: Device private key in base64

    Returns:
        str: Base64-encoded signature
    """
    # Decode private key
    private_bytes = base64.b64decode(private_key_base64)
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)

    # Sign message
    signature = private_key.sign(message.encode())
    return base64.b64encode(signature).decode()


def verify_device_signature(message: str, signature_base64: str, public_key_pem: str) -> bool:
    """
    Verify a signature using device public key.

    Args:
        message: Original message
        signature_base64: Base64-encoded signature
        public_key_pem: Device public key in PEM format

    Returns:
        bool: True if signature is valid
    """
    try:
        # Load public key
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode(),
            backend=default_backend()
        )

        # Decode signature
        signature = base64.b64decode(signature_base64)

        # Verify signature
        public_key.verify(signature, message.encode())
        return True

    except Exception as e:
        print(f"Signature verification failed: {e}")
        return False


def main():
    """Main function to generate test keys."""
    print("🔐 IoT Identity System - RSA Key Generator")
    print("=" * 50)

    # Generate test devices
    print("📱 Generating test IoT devices...")
    devices = generate_test_devices(5)

    # Save to file
    save_test_devices(devices, "test_devices.json")

    # Display summary
    print("\n📋 Generated Devices:")
    for device_id, device_data in devices.items():
        print(f"  • {device_id}: {device_data['public_key_pem'][:50]}...")

    # Test signature functionality
    print("\n🔏 Testing signature functionality...")
    test_device = list(devices.keys())[0]
    test_message = f"auth-challenge-{test_device}"

    # Generate signature
    signature = generate_device_signature(
        test_message,
        devices[test_device]["private_key_base64"]
    )

    # Verify signature
    is_valid = verify_device_signature(
        test_message,
        signature,
        devices[test_device]["public_key_pem"]
    )

    if is_valid:
        print("✅ Signature verification successful")
    else:
        print("❌ Signature verification failed")

    print("\n🎉 Key generation complete!")
    print("📁 Test devices saved to: test_devices.json")


if __name__ == "__main__":
    main()
