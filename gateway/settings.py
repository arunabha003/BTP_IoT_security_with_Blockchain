"""
Settings and Configuration for IoT Identity Gateway

Loads configuration from environment variables and provides
settings for the FastAPI application.
"""

import os
import math
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        # Blockchain settings
        self.rpc_url: str = os.getenv("RPC_URL", "http://127.0.0.1:8545")
        self.private_key_admin: str = os.getenv("PRIVATE_KEY_ADMIN", "")
        self.registry_address: str = os.getenv("REGISTRY_ADDRESS", "")
        
        # RSA Accumulator parameters (from params.json)
        self.n_hex: str = os.getenv("N_HEX", "")
        self.g_hex: str = os.getenv("G_HEX", "0x4") 
        
        # Trapdoor information (KEEP SECRET)
        self.lambda_n_hex: str = os.getenv("LAMBDA_N_HEX", "")
        
        # Database settings
        self.db_path: str = os.getenv("DB_PATH", "gateway.db")
        
        # Server settings
        self.host: str = os.getenv("HOST", "127.0.0.1")
        self.port: int = int(os.getenv("PORT", "8000"))
        
        # Validation
        self._validate_settings()
    
    def _validate_settings(self):
        """Validate critical settings on startup."""
        if not self.private_key_admin:
            raise ValueError("PRIVATE_KEY_ADMIN must be set")
        
        if not self.registry_address:
            raise ValueError("REGISTRY_ADDRESS must be set")
        
        if not self.n_hex:
            raise ValueError("N_HEX must be set")
        
        if not self.lambda_n_hex:
            raise ValueError("LAMBDA_N_HEX must be set")
        
        # Validate hex format
        try:
            if not self.n_hex.startswith("0x"):
                raise ValueError("N_HEX must start with 0x")
            
            if not self.g_hex.startswith("0x"):
                raise ValueError("G_HEX must start with 0x")
            
            if not self.lambda_n_hex.startswith("0x"):
                raise ValueError("LAMBDA_N_HEX must start with 0x")
        except Exception as e:
            raise ValueError(f"Invalid hex format in settings: {e}")
    
    @property 
    def N(self) -> int:
        """RSA modulus N as integer."""
        return int(self.n_hex, 16)
    
    @property
    def g(self) -> int:
        """Generator g as integer.""" 
        return int(self.g_hex, 16)
    
    @property
    def lambda_n(self) -> int:
        """Carmichael's lambda function λ(N) as integer."""
        return int(self.lambda_n_hex, 16)
    
    def get_registry_abi(self) -> list:
        """Get minimal ABI for RegistryMock contract."""
        return [
            {
                "inputs": [{"internalType": "bytes", "name": "initialAccumulator", "type": "bytes"}],
                "stateMutability": "nonpayable",
                "type": "constructor"
            },
            {
                "inputs": [],
                "name": "getCurrentState", 
                "outputs": [
                    {"internalType": "bytes", "name": "accumulator", "type": "bytes"},
                    {"internalType": "bytes32", "name": "hash", "type": "bytes32"},
                    {"internalType": "uint256", "name": "ver", "type": "uint256"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "bytes", "name": "newAccumulator", "type": "bytes"},
                    {"internalType": "bytes32", "name": "parentHash", "type": "bytes32"},
                    {"internalType": "bytes32", "name": "operationId", "type": "bytes32"}
                ],
                "name": "updateAccumulator",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "bytes", "name": "deviceId", "type": "bytes"},
                    {"internalType": "bytes", "name": "newAccumulator", "type": "bytes"}, 
                    {"internalType": "bytes32", "name": "parentHash", "type": "bytes32"},
                    {"internalType": "bytes32", "name": "operationId", "type": "bytes32"}
                ],
                "name": "registerDevice",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "bytes", "name": "deviceId", "type": "bytes"},
                    {"internalType": "bytes", "name": "newAccumulator", "type": "bytes"},
                    {"internalType": "bytes32", "name": "parentHash", "type": "bytes32"},
                    {"internalType": "bytes32", "name": "operationId", "type": "bytes32"}
                ],
                "name": "revokeDevice",
                "outputs": [],
                "stateMutability": "nonpayable", 
                "type": "function"
            },
            {
                "inputs": [],
                "name": "owner",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    def format_accumulator_to_hex(self, accumulator_int: int) -> str:
        """Format accumulator integer to 256-byte hex string."""
        # Convert to bytes (256 bytes = 2048 bits)
        accumulator_bytes = accumulator_int.to_bytes(256, byteorder='big')
        return accumulator_bytes.hex()
    
    def parse_accumulator_from_hex(self, hex_str: str) -> int:
        """Parse accumulator from hex string to integer."""
        # Remove 0x prefix if present
        if hex_str.startswith('0x'):
            hex_str = hex_str[2:]
        
        # Ensure it's 512 hex chars (256 bytes)
        if len(hex_str) != 512:
            raise ValueError(f"Accumulator hex must be 512 chars (256 bytes), got {len(hex_str)}")
        
        return int(hex_str, 16)


# Global settings instance
settings = Settings()


def compute_lambda_n_from_factors(p_hex: str, q_hex: str) -> str:
    """
    Compute λ(N) from RSA factors p and q.
    
    This is a utility function for computing lambda_n when you have
    the factors but not the precomputed lambda value.
    
    Args:
        p_hex: First prime factor as hex string
        q_hex: Second prime factor as hex string
        
    Returns:
        str: λ(N) as hex string
    """
    p = int(p_hex, 16)
    q = int(q_hex, 16)
    
    # λ(N) = lcm(p-1, q-1)
    p_minus_1 = p - 1
    q_minus_1 = q - 1
    gcd_val = math.gcd(p_minus_1, q_minus_1)
    lambda_n = (p_minus_1 // gcd_val) * q_minus_1
    
    return hex(lambda_n)


def main():
    """Test settings loading."""
    print("IoT Identity Gateway Settings")
    print("=" * 40)
    print(f"RPC URL: {settings.rpc_url}")
    print(f"Registry: {settings.registry_address}")
    print(f"Database: {settings.db_path}")
    print(f"Host: {settings.host}:{settings.port}")
    print(f"N (first 20 chars): {settings.n_hex[:22]}...")
    print(f"g: {settings.g_hex}")
    print(f"λ(N) (first 20 chars): {settings.lambda_n_hex[:22]}...")
    
    # Test accumulator formatting
    test_acc = settings.g  # Start with generator
    hex_str = settings.format_accumulator_to_hex(test_acc)
    print(f"Test accumulator hex (256 bytes): {hex_str[:32]}...{hex_str[-32:]}")
    
    parsed = settings.parse_accumulator_from_hex(hex_str)
    print(f"Round-trip test: {test_acc == parsed}")


if __name__ == "__main__":
    main()
