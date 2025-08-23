"""
Unit Tests for Utility Functions

Tests cryptographic utilities, validation functions, and rate limiting.
"""

import base64
import os
import time
import pytest
from fastapi import HTTPException
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

try:
    from gateway.utils import (
        hex_to_bytes, bytes_to_hex, validate_hex_string,
        parse_ed25519_public_key_pem, verify_ed25519_signature,
        constant_time_compare, ip_rate_limiter, device_rate_limiter
    )
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from utils import (
        hex_to_bytes, bytes_to_hex, validate_hex_string,
        parse_ed25519_public_key_pem, verify_ed25519_signature,
        constant_time_compare, ip_rate_limiter, device_rate_limiter
    )


class TestHexConversion:
    """Test hex string and bytes conversion utilities."""
    
    def test_hex_to_bytes_basic(self):
        """Test basic hex to bytes conversion."""
        hex_str = "0x48656c6c6f"  # "Hello" in hex
        result = hex_to_bytes(hex_str)
        assert result == b"Hello"
    
    def test_hex_to_bytes_without_prefix(self):
        """Test hex conversion without 0x prefix."""
        hex_str = "48656c6c6f"
        result = hex_to_bytes(hex_str)
        assert result == b"Hello"
    
    def test_hex_to_bytes_empty(self):
        """Test hex conversion with empty string."""
        result = hex_to_bytes("0x")
        assert result == b""
        
        result = hex_to_bytes("")
        assert result == b""
    
    def test_hex_to_bytes_invalid(self):
        """Test hex conversion with invalid hex string."""
        with pytest.raises(HTTPException) as exc_info:
            hex_to_bytes("0xgg")  # Invalid hex character
        assert exc_info.value.status_code == 400
        assert "Invalid hex string" in str(exc_info.value.detail)
    
    def test_bytes_to_hex_basic(self):
        """Test basic bytes to hex conversion."""
        data = b"Hello"
        result = bytes_to_hex(data)
        assert result == "0x48656c6c6f"
    
    def test_bytes_to_hex_empty(self):
        """Test bytes to hex with empty bytes."""
        result = bytes_to_hex(b"")
        assert result == "0x"
    
    def test_bytes_to_hex_binary_data(self):
        """Test bytes to hex with binary data."""
        data = bytes([0, 1, 255, 128])
        result = bytes_to_hex(data)
        assert result == "0x0001ff80"
    
    def test_hex_roundtrip(self):
        """Test that hex conversion is reversible."""
        original = b"Test data with \x00 null bytes and \xff high bytes"
        hex_str = bytes_to_hex(original)
        recovered = hex_to_bytes(hex_str)
        assert original == recovered


class TestHexValidation:
    """Test hex string validation functions."""
    
    def test_validate_hex_string_valid(self):
        """Test validation of valid hex strings."""
        valid_hex = "0x1234abcd"
        result = validate_hex_string(valid_hex)
        assert result == valid_hex
    
    def test_validate_hex_string_with_length(self):
        """Test validation with expected byte length."""
        hex_32_bytes = "0x" + "ab" * 32  # 32 bytes
        result = validate_hex_string(hex_32_bytes, expected_length=32)
        assert result == hex_32_bytes
    
    def test_validate_hex_string_wrong_length(self):
        """Test validation fails with wrong length."""
        hex_str = "0x1234"  # 2 bytes
        with pytest.raises(HTTPException) as exc_info:
            validate_hex_string(hex_str, expected_length=4)
        assert exc_info.value.status_code == 400
        assert "expected 4 bytes" in str(exc_info.value.detail)
    
    def test_validate_hex_string_invalid_format(self):
        """Test validation fails with invalid format."""
        with pytest.raises(HTTPException) as exc_info:
            validate_hex_string("not_hex")
        assert exc_info.value.status_code == 400
        assert "Invalid hex string format" in str(exc_info.value.detail)
    
    def test_validate_hex_string_non_string(self):
        """Test validation fails with non-string input."""
        with pytest.raises(HTTPException) as exc_info:
            validate_hex_string(123)
        assert exc_info.value.status_code == 400
        assert "Input must be a string" in str(exc_info.value.detail)
    
    def test_validate_hex_string_missing_prefix(self):
        """Test validation fails without 0x prefix."""
        with pytest.raises(HTTPException) as exc_info:
            validate_hex_string("1234abcd")
        assert exc_info.value.status_code == 400
        assert "Must start with '0x'" in str(exc_info.value.detail)


class TestEd25519Utilities:
    """Test Ed25519 cryptographic utilities."""
    
    @pytest.fixture
    def ed25519_keypair(self):
        """Generate Ed25519 keypair for testing."""
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_key, public_key, public_pem
    
    def test_parse_ed25519_public_key_pem_valid(self, ed25519_keypair):
        """Test parsing valid Ed25519 public key PEM."""
        _, expected_public_key, public_pem = ed25519_keypair
        
        parsed_key = parse_ed25519_public_key_pem(public_pem)
        
        # Keys should be equivalent
        assert isinstance(parsed_key, ed25519.Ed25519PublicKey)
        
        # Verify by comparing public bytes
        expected_bytes = expected_public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        parsed_bytes = parsed_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        assert expected_bytes == parsed_bytes
    
    def test_parse_ed25519_public_key_pem_invalid(self):
        """Test parsing invalid PEM data."""
        invalid_pem = b"-----BEGIN PUBLIC KEY-----\nInvalidData\n-----END PUBLIC KEY-----"
        
        with pytest.raises(HTTPException) as exc_info:
            parse_ed25519_public_key_pem(invalid_pem)
        assert exc_info.value.status_code == 400
        assert "Invalid Ed25519 public key PEM" in str(exc_info.value.detail)
    
    def test_parse_ed25519_wrong_key_type(self):
        """Test parsing PEM with wrong key type (not Ed25519)."""
        # Generate RSA key PEM (wrong type)
        from cryptography.hazmat.primitives.asymmetric import rsa
        rsa_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        rsa_public_key = rsa_private_key.public_key()
        rsa_pem = rsa_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        with pytest.raises(HTTPException) as exc_info:
            parse_ed25519_public_key_pem(rsa_pem)
        assert exc_info.value.status_code == 400
        assert "not an Ed25519 public key" in str(exc_info.value.detail)
    
    def test_verify_ed25519_signature_valid(self, ed25519_keypair):
        """Test Ed25519 signature verification with valid signature."""
        private_key, public_key, _ = ed25519_keypair
        
        message = b"test message for signing"
        signature = private_key.sign(message)
        
        is_valid = verify_ed25519_signature(public_key, message, signature)
        assert is_valid is True
    
    def test_verify_ed25519_signature_invalid(self, ed25519_keypair):
        """Test Ed25519 signature verification with invalid signature."""
        private_key, public_key, _ = ed25519_keypair
        
        message = b"test message"
        signature = private_key.sign(message)
        
        # Modify message (signature should be invalid)
        wrong_message = b"wrong message"
        is_valid = verify_ed25519_signature(public_key, wrong_message, signature)
        assert is_valid is False
    
    def test_verify_ed25519_signature_corrupted(self, ed25519_keypair):
        """Test signature verification with corrupted signature."""
        private_key, public_key, _ = ed25519_keypair
        
        message = b"test message"
        signature = private_key.sign(message)
        
        # Corrupt signature
        corrupted_signature = signature[:-1] + b'\x00'
        is_valid = verify_ed25519_signature(public_key, message, corrupted_signature)
        assert is_valid is False


class TestConstantTimeComparison:
    """Test constant-time string comparison."""
    
    def test_constant_time_compare_equal(self):
        """Test constant-time comparison with equal strings."""
        assert constant_time_compare("hello", "hello") is True
        assert constant_time_compare("", "") is True
        assert constant_time_compare("123", "123") is True
    
    def test_constant_time_compare_different(self):
        """Test constant-time comparison with different strings."""
        assert constant_time_compare("hello", "world") is False
        assert constant_time_compare("123", "456") is False
        assert constant_time_compare("a", "b") is False
    
    def test_constant_time_compare_different_lengths(self):
        """Test constant-time comparison with different length strings."""
        assert constant_time_compare("short", "longer") is False
        assert constant_time_compare("", "nonempty") is False
        assert constant_time_compare("abc", "ab") is False
    
    def test_constant_time_compare_timing_resistance(self):
        """Test that comparison time is independent of content."""
        # This is a basic test - true timing resistance would require more sophisticated measurement
        import time
        
        # Same length, different content
        str1 = "a" * 100
        str2 = "b" * 100
        
        # Multiple comparisons to average out timing variations
        times = []
        for _ in range(100):
            start = time.perf_counter()
            constant_time_compare(str1, str2)
            end = time.perf_counter()
            times.append(end - start)
        
        # The timing should be relatively consistent (within reasonable bounds)
        avg_time = sum(times) / len(times)
        max_deviation = max(abs(t - avg_time) for t in times)
        
        # Allow for some variance but not excessive
        assert max_deviation < avg_time * 2  # Somewhat loose bound for testing


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def setUp(self):
        """Clear rate limiting state before each test."""
        # Clear the rate limiting dictionaries
        import utils
        utils.ip_request_timestamps.clear()
        utils.device_request_timestamps.clear()
    
    def test_ip_rate_limiter_within_limit(self):
        """Test IP rate limiter allows requests within limit."""
        ip = "192.168.1.1"
        limit = 5
        window = 60
        
        # Should allow requests within limit
        for i in range(limit):
            assert ip_rate_limiter(ip, limit, window) is True
    
    def test_ip_rate_limiter_exceeds_limit(self):
        """Test IP rate limiter blocks requests exceeding limit."""
        ip = "192.168.1.2"
        limit = 3
        window = 60
        
        # Allow requests within limit
        for i in range(limit):
            assert ip_rate_limiter(ip, limit, window) is True
        
        # Should block additional requests
        assert ip_rate_limiter(ip, limit, window) is False
    
    def test_ip_rate_limiter_window_expiry(self):
        """Test IP rate limiter window expiry."""
        ip = "192.168.1.3"
        limit = 2
        window = 1  # 1 second window
        
        # Fill the limit
        assert ip_rate_limiter(ip, limit, window) is True
        assert ip_rate_limiter(ip, limit, window) is True
        assert ip_rate_limiter(ip, limit, window) is False
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should allow requests again
        assert ip_rate_limiter(ip, limit, window) is True
    
    def test_device_rate_limiter_within_limit(self):
        """Test device rate limiter allows requests within limit."""
        device_id = "device_001"
        limit = 3
        window = 300
        
        # Should allow requests within limit
        for i in range(limit):
            assert device_rate_limiter(device_id, limit, window) is True
    
    def test_device_rate_limiter_exceeds_limit(self):
        """Test device rate limiter blocks requests exceeding limit."""
        device_id = "device_002"
        limit = 2
        window = 300
        
        # Allow requests within limit
        for i in range(limit):
            assert device_rate_limiter(device_id, limit, window) is True
        
        # Should block additional requests
        assert device_rate_limiter(device_id, limit, window) is False
    
    def test_rate_limiter_different_clients(self):
        """Test that rate limiting is per-client."""
        limit = 2
        window = 60
        
        # Different IPs should have separate limits
        assert ip_rate_limiter("192.168.1.1", limit, window) is True
        assert ip_rate_limiter("192.168.1.2", limit, window) is True
        assert ip_rate_limiter("192.168.1.1", limit, window) is True
        assert ip_rate_limiter("192.168.1.2", limit, window) is True
        
        # Each should be blocked after their limit
        assert ip_rate_limiter("192.168.1.1", limit, window) is False
        assert ip_rate_limiter("192.168.1.2", limit, window) is False
    
    def test_rate_limiter_sliding_window(self):
        """Test that rate limiting uses sliding window."""
        ip = "192.168.1.4"
        limit = 2
        window = 2  # 2 second window
        
        # Make requests at different times
        assert ip_rate_limiter(ip, limit, window) is True  # t=0
        time.sleep(0.5)
        assert ip_rate_limiter(ip, limit, window) is True  # t=0.5
        assert ip_rate_limiter(ip, limit, window) is False  # t=0.5 (blocked)
        
        time.sleep(1.6)  # t=2.1, first request should have expired
        assert ip_rate_limiter(ip, limit, window) is True  # Should allow again
