"""
Pydantic Models for IoT Identity Gateway

Request/Response models for the FastAPI application.
Defines the API contract for all endpoints.
"""

from typing import Optional
from pydantic import BaseModel, Field, validator


# Request Models

class EnrollRequest(BaseModel):
    """Request model for device enrollment."""
    publicKeyPEM: str = Field(..., description="Device public key in PEM format")
    keyType: str = Field(default="ed25519", description="Type of cryptographic key (ed25519 or rsa)")
    
    @validator('keyType')
    def validate_key_type(cls, v):
        if v not in ['ed25519', 'rsa']:
            raise ValueError('keyType must be "ed25519" or "rsa"')
        return v
    
    @validator('publicKeyPEM')
    def validate_public_key_pem(cls, v):
        if not v or not v.strip():
            raise ValueError('publicKeyPEM cannot be empty')
        if '-----BEGIN PUBLIC KEY-----' not in v:
            raise ValueError('publicKeyPEM must be in PEM format')
        if '-----END PUBLIC KEY-----' not in v:
            raise ValueError('publicKeyPEM must be in PEM format')
        return v.strip()


class AuthRequest(BaseModel):
    """Request model for device authentication."""
    deviceIdHex: str = Field(..., description="Device ID as hex string (64 chars)")
    idPrime: int = Field(..., description="Device's identity prime number", gt=0)
    witnessHex: str = Field(..., description="Membership witness as hex string")
    signatureB64: str = Field(..., description="Base64 encoded signature")
    nonceHex: str = Field(..., description="Nonce that was signed (hex string)")
    publicKeyPEM: str = Field(..., description="Device public key in PEM format")
    keyType: str = Field(default="ed25519", description="Type of cryptographic key")
    
    @validator('deviceIdHex')
    def validate_device_id_hex(cls, v):
        if not v or len(v) != 64:
            raise ValueError('deviceIdHex must be 64 hex characters (32 bytes)')
        try:
            int(v, 16)
        except ValueError:
            raise ValueError('deviceIdHex must be valid hex string')
        return v.lower()
    
    @validator('nonceHex')
    def validate_nonce_hex(cls, v):
        if not v:
            raise ValueError('nonceHex cannot be empty')
        try:
            int(v, 16)
        except ValueError:
            raise ValueError('nonceHex must be valid hex string')
        return v.lower()
    
    @validator('keyType')
    def validate_key_type(cls, v):
        if v not in ['ed25519', 'rsa']:
            raise ValueError('keyType must be "ed25519" or "rsa"')
        return v


class RevokeRequest(BaseModel):
    """Request model for device revocation."""
    deviceIdHex: str = Field(..., description="Device ID as hex string (64 chars)")
    
    @validator('deviceIdHex')
    def validate_device_id_hex(cls, v):
        if not v or len(v) != 64:
            raise ValueError('deviceIdHex must be 64 hex characters (32 bytes)')
        try:
            int(v, 16)
        except ValueError:
            raise ValueError('deviceIdHex must be valid hex string')
        return v.lower()


# Response Models

class EnrollResponse(BaseModel):
    """Response model for successful device enrollment."""
    deviceIdHex: str = Field(..., description="Device ID as hex string")
    idPrime: int = Field(..., description="Device's identity prime number")
    witnessHex: str = Field(..., description="Initial membership witness as hex string")
    rootHex: str = Field(..., description="Updated accumulator root as hex string")


class AuthResponse(BaseModel):
    """Response model for device authentication."""
    ok: bool = Field(..., description="Whether authentication was successful")
    newWitnessHex: Optional[str] = Field(None, description="Updated witness if root changed")
    message: Optional[str] = Field(None, description="Additional information")


class RevokeResponse(BaseModel):
    """Response model for device revocation."""
    ok: bool = Field(..., description="Whether revocation was successful")
    rootHex: str = Field(..., description="Updated accumulator root after revocation")
    message: Optional[str] = Field(None, description="Additional information")


class RootResponse(BaseModel):
    """Response model for accumulator root query."""
    rootHex: str = Field(..., description="Current accumulator root as hex string")
    version: int = Field(..., description="Current version number")


# Error Models

class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")
    details: Optional[dict] = Field(None, description="Additional error details")


# Status Models

class StatusResponse(BaseModel):
    """System status response model."""
    status: str = Field(..., description="System status (healthy/unhealthy)")
    version: int = Field(..., description="Current accumulator version")
    totalDevices: int = Field(..., description="Total number of devices")
    activeDevices: int = Field(..., description="Number of active devices")
    revokedDevices: int = Field(..., description="Number of revoked devices")
    chainConnected: bool = Field(..., description="Whether blockchain connection is healthy")


class DeviceInfo(BaseModel):
    """Device information model."""
    deviceIdHex: str = Field(..., description="Device ID as hex string")
    keyType: str = Field(..., description="Type of cryptographic key")
    idPrime: int = Field(..., description="Device's identity prime number")
    status: int = Field(..., description="Device status (1=active, 2=revoked)")
    createdAt: str = Field(..., description="Creation timestamp")
    updatedAt: str = Field(..., description="Last update timestamp")


class DeviceListResponse(BaseModel):
    """Response model for device list query."""
    devices: list[DeviceInfo] = Field(..., description="List of devices")
    total: int = Field(..., description="Total number of devices")
    active: int = Field(..., description="Number of active devices")
    revoked: int = Field(..., description="Number of revoked devices")


# Key generation models

class KeyGenRequest(BaseModel):
    """Request to generate a device keypair for testing."""
    keyType: str = Field(default="ed25519", description="ed25519 or rsa")

    @validator('keyType')
    def validate_key_type(cls, v):
        if v not in ['ed25519', 'rsa']:
            raise ValueError('keyType must be "ed25519" or "rsa"')
        return v


class KeyGenResponse(BaseModel):
    """Response containing generated key material (demo use only)."""
    keyType: str
    privateKey: str = Field(..., description="Base64 for ed25519; PEM for RSA")
    publicKeyPEM: str


class WitnessResponse(BaseModel):
    """Response model for witness query."""
    deviceIdHex: str = Field(..., description="Device ID as hex string")
    witnessHex: str = Field(..., description="Current witness as hex string")
    status: str = Field(..., description="Device status (active/revoked)")
    lastUpdated: str = Field(..., description="When witness was last updated")


# Utility Models for Testing

class TestEnrollRequest(BaseModel):
    """Simplified model for testing enrollment without real keys."""
    deviceName: str = Field(..., description="Human-readable device name")
    keyType: str = Field(default="ed25519", description="Type of key to generate")
    
    @validator('keyType')
    def validate_key_type(cls, v):
        if v not in ['ed25519', 'rsa']:
            raise ValueError('keyType must be "ed25519" or "rsa"')
        return v


class TestAuthRequest(BaseModel):
    """Simplified model for testing authentication."""
    deviceIdHex: str = Field(..., description="Device ID as hex string")
    message: str = Field(default="test-auth", description="Message to sign for testing")
    
    @validator('deviceIdHex')
    def validate_device_id_hex(cls, v):
        if not v or len(v) != 64:
            raise ValueError('deviceIdHex must be 64 hex characters (32 bytes)')
        return v.lower()


# Configuration Models

class AccumulatorParams(BaseModel):
    """Model for accumulator parameters."""
    N_hex: str = Field(..., description="RSA modulus N as hex string")
    g_hex: str = Field(..., description="Generator g as hex string")
    lambda_n_hex: Optional[str] = Field(None, description="Carmichael lambda as hex string")
    keySize: int = Field(..., description="RSA key size in bits")
    securityLevel: str = Field(..., description="Security level description")


def main():
    """Test model validation."""
    print("Testing Pydantic Models")
    print("=" * 40)
    
    # Test EnrollRequest
    try:
        enroll_req = EnrollRequest(
            publicKeyPEM="""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAtest_key_data_here_32_bytes
-----END PUBLIC KEY-----""",
            keyType="ed25519"
        )
        print(f"✓ Valid EnrollRequest: {enroll_req.keyType}")
    except Exception as e:
        print(f"✗ EnrollRequest validation failed: {e}")
    
    # Test invalid keyType
    try:
        invalid_req = EnrollRequest(
            publicKeyPEM="-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----",
            keyType="invalid"
        )
        print("✗ Should have failed validation")
    except Exception as e:
        print(f"✓ Correctly rejected invalid keyType: {e}")
    
    # Test AuthRequest
    try:
        auth_req = AuthRequest(
            deviceIdHex="1234567890abcdef" * 8,  # 64 hex chars
            idPrime=12345,
            witnessHex="abcdef123456",
            signatureB64="dGVzdA==",  # base64 "test"
            nonceHex="deadbeef",
            publicKeyPEM="-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----",
            keyType="ed25519"
        )
        print(f"✓ Valid AuthRequest: {auth_req.deviceIdHex[:16]}...")
    except Exception as e:
        print(f"✗ AuthRequest validation failed: {e}")
    
    # Test invalid deviceIdHex
    try:
        invalid_auth = AuthRequest(
            deviceIdHex="invalid",  # Wrong length
            idPrime=12345,
            witnessHex="abc",
            signatureB64="dGVzdA==",
            nonceHex="deadbeef",
            publicKeyPEM="-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----"
        )
        print("✗ Should have failed validation")
    except Exception as e:
        print(f"✓ Correctly rejected invalid deviceIdHex: {e}")
    
    # Test Response models
    enroll_resp = EnrollResponse(
        deviceIdHex="1234567890abcdef" * 8,
        idPrime=12345,
        witnessHex="abcdef123456",
        rootHex="fedcba987654"
    )
    print(f"✓ Valid EnrollResponse: {enroll_resp.idPrime}")
    
    auth_resp = AuthResponse(
        ok=True,
        newWitnessHex="updated_witness",
        message="Authentication successful"
    )
    print(f"✓ Valid AuthResponse: {auth_resp.ok}")
    
    print("Model validation tests complete")


if __name__ == "__main__":
    main()
