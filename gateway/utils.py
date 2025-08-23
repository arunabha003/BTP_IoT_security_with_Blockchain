"""
Utility Functions

Helper functions for hex/bytes conversion, validation, and cryptographic operations.
"""

import hashlib
import secrets
import time
from typing import Union, Optional
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


def hex_to_bytes(hex_str: str, max_size: int = 256) -> bytes:
    """
    Convert hex string to bytes with size validation.
    
    Args:
        hex_str: Hex string (with or without 0x prefix)
        max_size: Maximum allowed size in bytes
        
    Returns:
        bytes: Decoded bytes
        
    Raises:
        ValueError: If hex is invalid or too large
    """
    if not isinstance(hex_str, str):
        raise ValueError("Input must be a string")
    
    # Remove 0x prefix if present
    if hex_str.startswith('0x'):
        hex_str = hex_str[2:]
    
    # Validate hex characters
    if not all(c in '0123456789abcdefABCDEF' for c in hex_str):
        raise ValueError("Invalid hex characters")
    
    # Ensure even length
    if len(hex_str) % 2 != 0:
        hex_str = '0' + hex_str
    
    try:
        result = bytes.fromhex(hex_str)
    except ValueError as e:
        raise ValueError(f"Invalid hex string: {e}")
    
    if len(result) > max_size:
        raise ValueError(f"Data too large: {len(result)} bytes > {max_size} bytes")
    
    return result


def bytes_to_hex(data: bytes, prefix: bool = True) -> str:
    """
    Convert bytes to hex string.
    
    Args:
        data: Bytes to convert
        prefix: Whether to add 0x prefix
        
    Returns:
        str: Hex string
    """
    if not isinstance(data, bytes):
        raise ValueError("Input must be bytes")
    
    hex_str = data.hex()
    return f"0x{hex_str}" if prefix else hex_str


def int_to_bytes(value: int, length: int = 32) -> bytes:
    """
    Convert integer to bytes with fixed length.
    
    Args:
        value: Integer to convert
        length: Target byte length
        
    Returns:
        bytes: Fixed-length bytes representation
    """
    if value < 0:
        raise ValueError("Value must be non-negative")
    
    try:
        return value.to_bytes(length, byteorder='big')
    except OverflowError:
        raise ValueError(f"Value too large for {length} bytes")


def bytes_to_int(data: bytes) -> int:
    """
    Convert bytes to integer.
    
    Args:
        data: Bytes to convert
        
    Returns:
        int: Integer value
    """
    if not isinstance(data, bytes):
        raise ValueError("Input must be bytes")
    
    return int.from_bytes(data, byteorder='big')


def parse_ed25519_pem(pem_data: str) -> bytes:
    """
    Parse Ed25519 public key from PEM format.
    
    Args:
        pem_data: PEM-encoded public key string
        
    Returns:
        bytes: Raw 32-byte Ed25519 public key
        
    Raises:
        ValueError: If PEM is invalid or not Ed25519
    """
    if not isinstance(pem_data, str):
        raise ValueError("PEM data must be a string")
    
    try:
        # Parse PEM
        public_key = serialization.load_pem_public_key(pem_data.encode())
        
        # Ensure it's Ed25519
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            raise ValueError("Key is not Ed25519")
        
        # Extract raw bytes
        raw_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        return raw_bytes
        
    except Exception as e:
        raise ValueError(f"Invalid Ed25519 PEM: {e}")


def verify_ed25519_signature(
    message: bytes, 
    signature: bytes, 
    public_key_bytes: bytes
) -> bool:
    """
    Verify Ed25519 signature.
    
    Args:
        message: Message that was signed
        signature: 64-byte signature
        public_key_bytes: 32-byte public key
        
    Returns:
        bool: True if signature is valid
    """
    try:
        if len(signature) != 64:
            return False
        if len(public_key_bytes) != 32:
            return False
        
        # Reconstruct public key
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
        
        # Verify signature
        public_key.verify(signature, message)
        return True
        
    except Exception:
        return False


def generate_nonce() -> str:
    """
    Generate a cryptographically secure nonce.
    
    Returns:
        str: 32-character hex nonce
    """
    return secrets.token_hex(16)


def constant_time_compare(a: str, b: str) -> bool:
    """
    Constant-time string comparison to prevent timing attacks.
    
    Args:
        a: First string
        b: Second string
        
    Returns:
        bool: True if strings are equal
    """
    if len(a) != len(b):
        return False
    
    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    
    return result == 0


def hash_data(*args) -> str:
    """
    Hash arbitrary data with SHA-256.
    
    Args:
        *args: Data to hash (strings, bytes, ints)
        
    Returns:
        str: Hex hash
    """
    hasher = hashlib.sha256()
    
    for arg in args:
        if isinstance(arg, str):
            hasher.update(arg.encode())
        elif isinstance(arg, bytes):
            hasher.update(arg)
        elif isinstance(arg, int):
            hasher.update(str(arg).encode())
        else:
            hasher.update(str(arg).encode())
    
    return hasher.hexdigest()


def validate_device_id(device_id: str) -> str:
    """
    Validate and normalize device ID.
    
    Args:
        device_id: Device identifier
        
    Returns:
        str: Normalized device ID
        
    Raises:
        ValueError: If device ID is invalid
    """
    if not isinstance(device_id, str):
        raise ValueError("Device ID must be a string")
    
    device_id = device_id.strip()
    
    if not device_id:
        raise ValueError("Device ID cannot be empty")
    
    if len(device_id) > 64:
        raise ValueError("Device ID too long (max 64 characters)")
    
    # Allow alphanumeric, hyphens, underscores
    if not all(c.isalnum() or c in '-_' for c in device_id):
        raise ValueError("Device ID contains invalid characters")
    
    return device_id


def get_current_timestamp() -> int:
    """Get current Unix timestamp."""
    return int(time.time())


def is_expired(timestamp: int, ttl_seconds: int) -> bool:
    """Check if timestamp is expired."""
    return (get_current_timestamp() - timestamp) > ttl_seconds


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # key -> list of timestamps
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for key."""
        now = get_current_timestamp()
        
        # Clean old requests
        if key in self.requests:
            self.requests[key] = [
                ts for ts in self.requests[key] 
                if (now - ts) < self.window_seconds
            ]
        else:
            self.requests[key] = []
        
        # Check rate limit
        if len(self.requests[key]) >= self.max_requests:
            return False
        
        # Record this request
        self.requests[key].append(now)
        return True
    
    def cleanup(self):
        """Clean up expired entries."""
        now = get_current_timestamp()
        keys_to_remove = []
        
        for key, timestamps in self.requests.items():
            # Remove old timestamps
            self.requests[key] = [
                ts for ts in timestamps 
                if (now - ts) < self.window_seconds
            ]
            
            # Mark empty entries for removal
            if not self.requests[key]:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.requests[key]


# Global rate limiter instances
device_rate_limiter = RateLimiter(max_requests=5, window_seconds=300)  # 5 per 5 minutes
ip_rate_limiter = RateLimiter(max_requests=20, window_seconds=60)      # 20 per minute
