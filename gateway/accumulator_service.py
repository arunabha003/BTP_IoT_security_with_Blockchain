"""
RSA Accumulator Service

Service layer for RSA accumulator operations integrated with the blockchain.
"""

import logging
import sys
import os
from typing import List, Set, Optional, Tuple, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add accum package to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'accum'))

try:
    from .database import get_db_session
    from .models import Device, AccumulatorRoot
    from .blockchain import blockchain_client
    from .utils import bytes_to_hex, hex_to_bytes, int_to_bytes, bytes_to_int
except ImportError:
    from database import get_db_session
    from models import Device, AccumulatorRoot
    from blockchain import blockchain_client
    from utils import bytes_to_hex, hex_to_bytes, int_to_bytes, bytes_to_int

# Import RSA accumulator functions
try:
    from rsa_params import load_params
    from hash_to_prime import hash_to_prime
    from accumulator import add_member, recompute_root, membership_witness, verify_membership
    from witness_refresh import refresh_witness
except ImportError as e:
    logging.error(f"Failed to import RSA accumulator modules: {e}")
    # Create stub functions for testing
    def load_params():
        return (2**2048 - 1, 2)  # Dummy values
    def hash_to_prime(data):
        return 17  # Dummy prime
    def add_member(A, p, N):
        return pow(A, p, N)
    def recompute_root(primes, N, g):
        if not primes:
            return g
        product = 1
        for p in primes:
            product *= p
        return pow(g, product, N)
    def membership_witness(other_primes, N, g):
        return recompute_root(other_primes, N, g)
    def verify_membership(w, p, A, N):
        return pow(w, p, N) == A
    def refresh_witness(p, primes, N, g):
        other_primes = [prime for prime in primes if prime != p]
        return membership_witness(other_primes, N, g)

logger = logging.getLogger(__name__)


class AccumulatorService:
    """Service for managing RSA accumulator operations."""
    
    def __init__(self):
        self.N: Optional[int] = None
        self.g: Optional[int] = None
        self._load_params()
    
    def _load_params(self):
        """Load RSA parameters."""
        try:
            self.N, self.g = load_params()
            logger.info(f"Loaded RSA parameters: N={self.N.bit_length()} bits, g={self.g}")
        except Exception as e:
            logger.error(f"Failed to load RSA parameters: {e}")
            # Use dummy values for testing
            self.N, self.g = (2**2048 - 1, 2)
    
    async def get_active_device_primes(self) -> List[int]:
        """Get all active device primes from database."""
        async with get_db_session() as session:
            stmt = select(Device.prime_p).where(Device.status == "active")
            result = await session.execute(stmt)
            
            primes = []
            for row in result:
                try:
                    primes.append(int(row.prime_p))
                except ValueError as e:
                    logger.error(f"Invalid prime in database: {row.prime_p} - {e}")
            
            return primes
    
    async def compute_current_accumulator(self) -> int:
        """Compute current accumulator from active devices."""
        primes = await self.get_active_device_primes()
        
        if not primes:
            return self.g  # Empty accumulator is the generator
        
        return recompute_root(primes, self.N, self.g)
    
    async def add_device_to_accumulator(
        self, 
        device_id: str, 
        pubkey_bytes: bytes
    ) -> Dict[str, Any]:
        """
        Add a new device to the accumulator.
        
        Args:
            device_id: Device identifier
            pubkey_bytes: Device public key bytes
            
        Returns:
            dict: Device info and accumulator data
        """
        # Generate prime from public key
        device_prime = hash_to_prime(pubkey_bytes)
        
        # Get current active primes
        current_primes = await self.get_active_device_primes()
        
        # Compute old accumulator
        old_accumulator = recompute_root(current_primes, self.N, self.g) if current_primes else self.g
        
        # Add new device
        new_accumulator = add_member(old_accumulator, device_prime, self.N)
        
        # Witness for new device is old accumulator
        witness = old_accumulator
        
        # Store device in database
        async with get_db_session() as session:
            device = Device(
                id=device_id,
                pubkey=pubkey_bytes,
                prime_p=str(device_prime),
                status="pending",  # Will be set to active after blockchain update
                last_witness=hex(witness)
            )
            session.add(device)
            await session.commit()
        
        logger.info(f"Added device {device_id} with prime {device_prime}")
        
        return {
            "device_id": device_id,
            "prime": hex(device_prime),
            "witness": hex(witness),
            "old_accumulator": hex(old_accumulator),
            "new_accumulator": hex(new_accumulator),
            "new_accumulator_bytes": int_to_bytes(new_accumulator)
        }
    
    async def revoke_device_from_accumulator(self, device_id: str) -> Dict[str, Any]:
        """
        Revoke a device from the accumulator.
        
        Args:
            device_id: Device identifier
            
        Returns:
            dict: Updated accumulator data
        """
        async with get_db_session() as session:
            # Find device
            stmt = select(Device).where(Device.id == device_id, Device.status == "active")
            result = await session.execute(stmt)
            device = result.scalar_one_or_none()
            
            if not device:
                raise ValueError(f"Active device {device_id} not found")
            
            # Mark as pending revocation
            device.status = "pending-revoke"
            await session.commit()
            
            # Get remaining active primes (excluding this device)
            remaining_primes = await self.get_active_device_primes()
            
            # Remove this device's prime
            device_prime = int(device.prime_p)
            remaining_primes = [p for p in remaining_primes if p != device_prime]
            
            # Compute new accumulator
            new_accumulator = recompute_root(remaining_primes, self.N, self.g) if remaining_primes else self.g
            
            logger.info(f"Revoked device {device_id}, new accumulator computed")
            
            return {
                "device_id": device_id,
                "revoked_prime": hex(device_prime),
                "remaining_primes": len(remaining_primes),
                "new_accumulator": hex(new_accumulator),
                "new_accumulator_bytes": int_to_bytes(new_accumulator)
            }
    
    async def finalize_device_status(self, device_id: str, status: str):
        """Update device status after blockchain confirmation."""
        async with get_db_session() as session:
            stmt = select(Device).where(Device.id == device_id)
            result = await session.execute(stmt)
            device = result.scalar_one_or_none()
            
            if device:
                device.status = status
                if status == "revoked":
                    device.last_witness = None
                await session.commit()
                logger.info(f"Device {device_id} status updated to {status}")
    
    async def verify_device_membership(
        self, 
        device_id: str, 
        witness_hex: str, 
        accumulator_hex: Optional[str] = None
    ) -> bool:
        """
        Verify device membership in accumulator.
        
        Args:
            device_id: Device identifier
            witness_hex: Witness hex string
            accumulator_hex: Accumulator hex (optional, uses current if not provided)
            
        Returns:
            bool: True if membership is valid
        """
        async with get_db_session() as session:
            # Find device
            stmt = select(Device).where(Device.id == device_id, Device.status == "active")
            result = await session.execute(stmt)
            device = result.scalar_one_or_none()
            
            if not device:
                return False
            
            try:
                # Parse inputs
                witness = bytes_to_int(hex_to_bytes(witness_hex))
                device_prime = int(device.prime_p)
                
                # Get accumulator
                if accumulator_hex:
                    accumulator = bytes_to_int(hex_to_bytes(accumulator_hex))
                else:
                    accumulator = await self.compute_current_accumulator()
                
                # Verify membership
                return verify_membership(witness, device_prime, accumulator, self.N)
                
            except Exception as e:
                logger.error(f"Error verifying membership for {device_id}: {e}")
                return False
    
    async def refresh_device_witness(self, device_id: str) -> Optional[str]:
        """
        Refresh witness for a device based on current accumulator state.
        
        Args:
            device_id: Device identifier
            
        Returns:
            str: New witness hex string, or None if device not found
        """
        async with get_db_session() as session:
            # Find device
            stmt = select(Device).where(Device.id == device_id, Device.status == "active")
            result = await session.execute(stmt)
            device = result.scalar_one_or_none()
            
            if not device:
                return None
            
            try:
                device_prime = int(device.prime_p)
                
                # Get all active primes
                all_primes = await self.get_active_device_primes()
                
                # Refresh witness
                new_witness = refresh_witness(device_prime, set(all_primes), self.N, self.g)
                new_witness_hex = hex(new_witness)
                
                # Update database
                device.last_witness = new_witness_hex
                await session.commit()
                
                logger.info(f"Refreshed witness for device {device_id}")
                return new_witness_hex
                
            except Exception as e:
                logger.error(f"Error refreshing witness for {device_id}: {e}")
                return None
    
    async def get_accumulator_info(self) -> Dict[str, Any]:
        """Get current accumulator information."""
        try:
            # Compute current accumulator
            current_accumulator = await self.compute_current_accumulator()
            accumulator_hex = hex(current_accumulator)
            
            # Get active device count
            active_primes = await self.get_active_device_primes()
            
            # Get latest block info from blockchain
            latest_block = None
            if blockchain_client.w3:
                try:
                    latest_block = blockchain_client.w3.eth.block_number
                except Exception:
                    pass
            
            # Get cached root hash (parent hash for next update)
            root_hash = await self._get_cached_root_hash()
            
            return {
                "rootHex": accumulator_hex,
                "rootHash": root_hash,
                "block": latest_block,
                "activeDevices": len(active_primes),
                "parameters": {
                    "N_bits": self.N.bit_length(),
                    "g": self.g
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting accumulator info: {e}")
            raise
    
    async def _get_cached_root_hash(self) -> str:
        """Get the hash of the current accumulator root for replay protection."""
        try:
            current_root = await blockchain_client.get_current_root()
            if current_root and current_root != "0x":
                # Hash the current root for parentHash
                import hashlib
                from Crypto.Hash import keccak
                root_bytes = hex_to_bytes(current_root)
                keccak_hash = keccak.new(digest_bits=256)
                keccak_hash.update(root_bytes)
                return bytes_to_hex(keccak_hash.digest())
            else:
                # No current root, use zero hash
                return "0x" + "00" * 32
        except Exception as e:
            logger.error(f"Error getting cached root hash: {e}")
            return "0x" + "00" * 32


# Global accumulator service instance
accumulator_service = AccumulatorService()
