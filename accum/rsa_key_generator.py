"""
Cryptographic Key Generation Utilities for IoT Device Identity Management

This module provides functions to generate Ed25519 and RSA key pairs for use
in the RSA accumulator system for IoT device authentication and identity management.
"""

import json
import base64
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ed25519
from cryptography.hazmat.backends import default_backend


def generate_rsa_keypair(key_size: int = 2048, public_exponent: int = 65537) -> Tuple[str, str]:
    """
    Generate an RSA keypair for IoT device authentication.
    
    RSA keys are used when compatibility with existing systems is required,
    though Ed25519 is generally preferred for new IoT deployments.
    
    Args:
        key_size: RSA key size in bits (default: 2048, minimum: 2048)
        public_exponent: Public exponent (default: 65537)
        
    Returns:
        Tuple[str, str]: (private_key_pem, public_key_pem)
            - private_key_pem: PEM-formatted private key (PKCS#8 format)
            - public_key_pem: PEM-formatted public key (SubjectPublicKeyInfo format)
            
    Raises:
        ValueError: If key_size is less than 2048 bits
        
    Example:
        >>> private_pem, public_pem = generate_rsa_keypair(2048)
        >>> print(f"Private key length: {len(private_pem)}")
        >>> print(f"Public key: {public_pem[:50]}...")
    """
    if key_size < 2048:
        raise ValueError("RSA key size must be at least 2048 bits for security")
    # Generate RSA keypair
    private_key = rsa.generate_private_key(
        public_exponent=public_exponent,
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
    
    Ed25519 is preferred for IoT devices due to its:
    - Small key size (32 bytes private, 32 bytes public)
    - Fast signature generation and verification
    - High security level (128-bit equivalent)
    - Resistance to side-channel attacks
    
    Returns:
        Tuple[str, str]: (private_key_base64, public_key_pem)
            - private_key_base64: Base64-encoded raw private key (32 bytes)
            - public_key_pem: PEM-formatted public key
            
    Example:
        >>> private_b64, public_pem = generate_ed25519_keypair()
        >>> print(f"Private key: {private_b64}")
        >>> print(f"Public key: {public_pem[:50]}...")
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


def generate_test_devices(num_devices: int = 5, key_type: str = "ed25519") -> Dict[str, Dict[str, str]]:
    """
    Generate a set of test IoT devices with cryptographic keys.
    
    Args:
        num_devices: Number of devices to generate (default: 5)
        key_type: Type of keys to generate ("ed25519" or "rsa", default: "ed25519")
        
    Returns:
        Dict[str, Dict[str, str]]: Dictionary mapping device_id to device data
            Each device contains:
            - device_id: Unique identifier
            - private_key: Private key (format depends on key_type)
            - public_key: Public key in PEM format
            - key_type: Type of key generated
            - status: Generation status
            
    Example:
        >>> devices = generate_test_devices(3, "ed25519")
        >>> print(f"Generated {len(devices)} devices")
        >>> for device_id, data in devices.items():
        ...     print(f"{device_id}: {data['key_type']}")
    """
    if key_type not in ["ed25519", "rsa"]:
        raise ValueError("key_type must be 'ed25519' or 'rsa'")
    
    devices = {}

    for i in range(num_devices):
        device_id = f"sensor_{i:03d}"
        
        if key_type == "ed25519":
            private_key, public_key = generate_ed25519_keypair()
            private_key_field = "private_key_base64"
        else:  # rsa
            private_key, public_key = generate_rsa_keypair()
            private_key_field = "private_key_pem"

        devices[device_id] = {
            "device_id": device_id,
            private_key_field: private_key,
            "public_key_pem": public_key,
            "key_type": key_type,
            "status": "generated"
        }

    return devices


def save_test_devices(devices: Dict[str, Dict[str, str]], filename: str = "test_devices.json") -> None:
    """
    Save generated test devices to JSON file.
    
    Args:
        devices: Dictionary of test devices from generate_test_devices()
        filename: Output filename (default: "test_devices.json")
        
    Example:
        >>> devices = generate_test_devices(5)
        >>> save_test_devices(devices, "my_devices.json")
        >>> print("Devices saved successfully")
    """
    with open(filename, 'w') as f:
        json.dump(devices, f, indent=2)

    print(f"✅ Saved {len(devices)} test devices to {filename}")


def load_test_devices(filename: str = "test_devices.json") -> Dict[str, Dict[str, str]]:
    """
    Load test devices from JSON file.
    
    Args:
        filename: Input filename (default: "test_devices.json")
        
    Returns:
        Dict[str, Dict[str, str]]: Dictionary of device data
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
        
    Example:
        >>> devices = load_test_devices("my_devices.json")
        >>> print(f"Loaded {len(devices)} devices")
    """
    with open(filename, 'r') as f:
        return json.load(f)


def generate_device_signature(message: str, private_key_data: str, key_type: str = "ed25519") -> str:
    """
    Generate a signature for a message using device private key.
    
    Args:
        message: Message to sign (string)
        private_key_data: Device private key (format depends on key_type)
        key_type: Type of key ("ed25519" or "rsa", default: "ed25519")
        
    Returns:
        str: Base64-encoded signature
        
    Raises:
        ValueError: If key_type is not supported
        
    Example:
        >>> private_b64, public_pem = generate_ed25519_keypair()
        >>> signature = generate_device_signature("hello", private_b64, "ed25519")
        >>> print(f"Signature: {signature}")
    """
    if key_type == "ed25519":
        # Decode private key
        private_bytes = base64.b64decode(private_key_data)
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
        
        # Sign message
        signature = private_key.sign(message.encode())
        return base64.b64encode(signature).decode()
        
    elif key_type == "rsa":
        # Load private key from PEM
        private_key = serialization.load_pem_private_key(
            private_key_data.encode(),
            password=None,
            backend=default_backend()
        )
        
        # Sign message (using PSS padding for security)
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        
        signature = private_key.sign(
            message.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode()
        
    else:
        raise ValueError("key_type must be 'ed25519' or 'rsa'")


def verify_device_signature(message: str, signature_base64: str, public_key_pem: str, key_type: str = "ed25519") -> bool:
    """
    Verify a signature using device public key.
    
    Args:
        message: Original message (string)
        signature_base64: Base64-encoded signature
        public_key_pem: Device public key in PEM format
        key_type: Type of key ("ed25519" or "rsa", default: "ed25519")
        
    Returns:
        bool: True if signature is valid, False otherwise
        
    Example:
        >>> private_b64, public_pem = generate_ed25519_keypair()
        >>> signature = generate_device_signature("hello", private_b64)
        >>> is_valid = verify_device_signature("hello", signature, public_pem)
        >>> print(f"Signature valid: {is_valid}")
    """
    try:
        # Load public key
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode(),
            backend=default_backend()
        )

        # Decode signature
        signature = base64.b64decode(signature_base64)

        if key_type == "ed25519":
            # Verify Ed25519 signature
            public_key.verify(signature, message.encode())
            return True
            
        elif key_type == "rsa":
            # Verify RSA signature with PSS padding
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            
            public_key.verify(
                signature,
                message.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
            
        else:
            raise ValueError("key_type must be 'ed25519' or 'rsa'")

    except Exception as e:
        print(f"Signature verification failed: {e}")
        return False


def get_key_info(public_key_pem: str) -> Dict[str, any]:
    """
    Extract information about a public key.
    
    Args:
        public_key_pem: Public key in PEM format
        
    Returns:
        Dict[str, any]: Key information including type, size, etc.
        
    Example:
        >>> _, public_pem = generate_ed25519_keypair()
        >>> info = get_key_info(public_pem)
        >>> print(f"Key type: {info['key_type']}")
    """
    try:
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode(),
            backend=default_backend()
        )
        
        if isinstance(public_key, ed25519.Ed25519PublicKey):
            return {
                "key_type": "ed25519",
                "key_size": 256,  # Ed25519 is 256-bit
                "algorithm": "Ed25519",
                "security_level": "128-bit equivalent"
            }
        elif isinstance(public_key, rsa.RSAPublicKey):
            key_size = public_key.key_size
            return {
                "key_type": "rsa",
                "key_size": key_size,
                "algorithm": "RSA",
                "security_level": f"{key_size // 2}-bit equivalent" if key_size >= 2048 else "insecure"
            }
        else:
            return {
                "key_type": "unknown",
                "algorithm": str(type(public_key).__name__)
            }
            
    except Exception as e:
        return {
            "key_type": "error",
            "error": str(e)
        }


def main():
    """Main function to demonstrate key generation functionality."""
    print("🔐 IoT Identity System - Cryptographic Key Generation")
    print("=" * 60)

    # Generate Ed25519 test devices
    print("📱 Generating Ed25519 test IoT devices...")
    ed25519_devices = generate_test_devices(3, "ed25519")
    save_test_devices(ed25519_devices, "ed25519_test_devices.json")

    # Generate RSA test devices
    print("📱 Generating RSA test IoT devices...")
    rsa_devices = generate_test_devices(3, "rsa")
    save_test_devices(rsa_devices, "rsa_test_devices.json")

    # Display summary
    print("\n📋 Generated Ed25519 Devices:")
    for device_id, device_data in ed25519_devices.items():
        key_info = get_key_info(device_data["public_key_pem"])
        print(f"  • {device_id}: {key_info['algorithm']} ({key_info['security_level']})")

    print("\n📋 Generated RSA Devices:")
    for device_id, device_data in rsa_devices.items():
        key_info = get_key_info(device_data["public_key_pem"])
        print(f"  • {device_id}: {key_info['algorithm']} {key_info['key_size']}-bit ({key_info['security_level']})")

    # Test signature functionality with Ed25519
    print("\n🔏 Testing Ed25519 signature functionality...")
    test_device = list(ed25519_devices.keys())[0]
    test_message = f"auth-challenge-{test_device}"

    # Generate signature
    signature = generate_device_signature(
        test_message,
        ed25519_devices[test_device]["private_key_base64"],
        "ed25519"
    )

    # Verify signature
    is_valid = verify_device_signature(
        test_message,
        signature,
        ed25519_devices[test_device]["public_key_pem"],
        "ed25519"
    )

    if is_valid:
        print("✅ Ed25519 signature verification successful")
    else:
        print("❌ Ed25519 signature verification failed")

    # Test signature functionality with RSA
    print("\n🔏 Testing RSA signature functionality...")
    test_device = list(rsa_devices.keys())[0]
    test_message = f"auth-challenge-{test_device}"

    # Generate signature
    signature = generate_device_signature(
        test_message,
        rsa_devices[test_device]["private_key_pem"],
        "rsa"
    )

    # Verify signature
    is_valid = verify_device_signature(
        test_message,
        signature,
        rsa_devices[test_device]["public_key_pem"],
        "rsa"
    )

    if is_valid:
        print("✅ RSA signature verification successful")
    else:
        print("❌ RSA signature verification failed")

    print("\n🎉 Key generation and testing complete!")
    print("📁 Ed25519 devices saved to: ed25519_test_devices.json")
    print("📁 RSA devices saved to: rsa_test_devices.json")


if __name__ == "__main__":
    main()
