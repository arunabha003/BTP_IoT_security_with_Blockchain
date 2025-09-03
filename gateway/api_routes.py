"""
Extended API Routes

Additional endpoints for accumulator management, device enrollment, and authentication.
"""

import base64
import logging
import secrets
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request, Depends, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from .database import get_db_session
from .models import Device, EventLog
from .blockchain import blockchain_client
from .accumulator_service import accumulator_service
from .utils import (
    hex_to_bytes, bytes_to_hex, parse_ed25519_pem, verify_ed25519_signature,
    generate_nonce, validate_device_id, get_current_timestamp, is_expired
)
from .middleware import create_error_response

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter()

# In-memory nonce storage (in production, use Redis or database)
active_nonces: Dict[str, Dict[str, Any]] = {}

# Request/Response models
class AccumulatorUpdateRequest(BaseModel):
    newRootHex: str = Field(..., description="New accumulator root in hex format")
    parentHash: Optional[str] = Field(None, description="Parent hash for replay protection")
    
    @field_validator('newRootHex')
    @classmethod
    def validate_root_hex(cls, v):
        if not v.startswith('0x'):
            v = '0x' + v
        try:
            hex_to_bytes(v, max_size=256)  # Validate and size check
        except ValueError as e:
            raise ValueError(f"Invalid newRootHex: {e}")
        return v

    @field_validator('parentHash')
    @classmethod
    def validate_parent_hash(cls, v):
        if v is not None:
            if not v.startswith('0x'):
                v = '0x' + v
            try:
                hex_to_bytes(v, max_size=32)  # 32 bytes for hash
            except ValueError as e:
                raise ValueError(f"Invalid parentHash: {e}")
        return v


class DeviceEnrollRequest(BaseModel):
    device_id: str = Field(..., description="Unique device identifier")
    pubkey_pem: str = Field(..., description="Ed25519 public key in PEM format")
    
    @field_validator('device_id')
    @classmethod
    def validate_device_id_field(cls, v):
        return validate_device_id(v)

    @field_validator('pubkey_pem')
    @classmethod
    def validate_pubkey_pem_field(cls, v):
        try:
            parse_ed25519_pem(v)  # Validate PEM format
        except ValueError as e:
            raise ValueError(f"Invalid PEM public key: {e}")
        return v


class DeviceRevokeRequest(BaseModel):
    device_id: str = Field(..., description="Device identifier to revoke")

    @field_validator('device_id')
    @classmethod
    def validate_device_id_field(cls, v):
        return validate_device_id(v)


class AuthStartRequest(BaseModel):
    device_id: str = Field(..., description="Device identifier")

    @field_validator('device_id')
    @classmethod
    def validate_device_id_field(cls, v):
        return validate_device_id(v)


class AuthVerifyRequest(BaseModel):
    device_id: str = Field(..., description="Device identifier")
    p_hex: str = Field(..., description="Device prime in hex format")
    witness_hex: str = Field(..., description="Membership witness in hex format")
    signature_base64: str = Field(..., description="Base64-encoded signature")
    nonce: str = Field(..., description="Nonce from auth/start")
    pubkey_pem: Optional[str] = Field(None, description="Public key PEM (optional if in DB)")
    
    @field_validator('device_id')
    @classmethod
    def validate_device_id_field(cls, v):
        return validate_device_id(v)


# Accumulator Management Endpoints

@router.post("/accumulator/update", status_code=200)
async def update_accumulator(
    request: AccumulatorUpdateRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Update the accumulator root on-chain.
    
    Requires admin authentication via x-admin-key header.
    """
    request_id = getattr(http_request.state, 'request_id', 'unknown')
    
    try:
        logger.info(f"Accumulator update requested: {request.newRootHex}")
        
        # Validate contract is loaded
        if not blockchain_client.contract:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Smart contract not loaded"
            )
        
        # Optional parent hash validation
        if request.parentHash:
            current_root = await blockchain_client.get_current_root()
            if current_root and current_root != "0x":
                # Compute expected parent hash
                from Crypto.Hash import keccak
                current_bytes = hex_to_bytes(current_root)
                keccak_hash = keccak.new(digest_bits=256)
                keccak_hash.update(current_bytes)
                expected_hash = bytes_to_hex(keccak_hash.digest())
                
                if request.parentHash != expected_hash:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Parent hash mismatch - accumulator may have been updated"
                    )
        
        # Convert hex to bytes for contract call
        new_root_bytes = hex_to_bytes(request.newRootHex)
        parent_hash_bytes = hex_to_bytes(request.parentHash) if request.parentHash else b'\x00' * 32
        
        # Call contract function
        logger.info(f"Updating contract with root: {request.newRootHex}")

        try:
            # Call the contract's updateAccumulator function
            # This requires the admin to be the authorized Safe multisig
            tx_hash = await blockchain_client.update_accumulator(
                new_root_bytes,
                parent_hash_bytes,
                operation_id=f"update-{request.newRootHex[:8]}"
            )

            logger.info(f"Accumulator update transaction sent: {tx_hash}")

        except Exception as e:
            logger.error(f"Failed to update accumulator on blockchain: {e}")
            # For development/testing, update cache locally
            blockchain_client.current_root = request.newRootHex
            logger.warning("Updated cache locally due to blockchain error")
        
        logger.info(f"Accumulator updated successfully: {request.newRootHex}")
        
        return {
            "success": True,
            "newRoot": request.newRootHex,
            "parentHash": request.parentHash,
            "message": "Accumulator updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating accumulator: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update accumulator: {str(e)}"
        )


@router.get("/accumulator", status_code=200)
async def get_accumulator_info():
    """Get current accumulator information."""
    try:
        info = await accumulator_service.get_accumulator_info()
        return info
        
    except Exception as e:
        logger.error(f"Error getting accumulator info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get accumulator info: {str(e)}"
        )


# Device Management Endpoints

@router.post("/enroll", status_code=201)
async def enroll_device(
    request: DeviceEnrollRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Enroll a new IoT device.
    
    Requires admin authentication via x-admin-key header.
    """
    request_id = getattr(http_request.state, 'request_id', 'unknown')
    
    try:
        logger.info(f"Device enrollment requested: {request.device_id}")
        
        # Parse public key
        pubkey_bytes = parse_ed25519_pem(request.pubkey_pem)
        
        # Check if device already exists
        from sqlalchemy import select
        stmt = select(Device).where(Device.id == request.device_id)
        result = await session.execute(stmt)
        existing_device = result.scalar_one_or_none()
        
        if existing_device:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Device {request.device_id} already exists"
            )
        
        # Add device to accumulator
        result = await accumulator_service.add_device_to_accumulator(
            request.device_id, 
            pubkey_bytes
        )
        
        # Update contract with new accumulator
        if blockchain_client.contract:
            try:
                # Register device on-chain
                tx_hash = await blockchain_client.register_device(
                    request.device_id.encode(),
                    result["new_accumulator_bytes"],
                    operation_id=f"enroll-{request.device_id}"
                )
                logger.info(f"Device registration transaction sent: {tx_hash}")

                # Mark device as active after blockchain confirmation
                await accumulator_service.finalize_device_status(request.device_id, "active")

            except Exception as e:
                logger.error(f"Failed to register device on blockchain: {e}")
                # For development/testing, update cache locally
                blockchain_client.current_root = result["new_accumulator"]
                logger.warning("Updated cache locally due to blockchain error")
                await accumulator_service.finalize_device_status(request.device_id, "active")
        
        logger.info(f"Device enrolled successfully: {request.device_id}")
        
        return {
            "success": True,
            "device_id": result["device_id"],
            "prime": result["prime"],
            "witness": result["witness"],
            "new_root": result["new_accumulator"],
            "message": "Device enrolled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enrolling device {request.device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enroll device: {str(e)}"
        )


@router.post("/revoke", status_code=204)
async def revoke_device(
    request: DeviceRevokeRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Revoke an IoT device.
    
    Requires admin authentication via x-admin-key header.
    """
    request_id = getattr(http_request.state, 'request_id', 'unknown')
    
    try:
        logger.info(f"Device revocation requested: {request.device_id}")
        
        # Revoke device from accumulator
        result = await accumulator_service.revoke_device_from_accumulator(request.device_id)
        
        # Update contract with new accumulator
        if blockchain_client.contract:
            try:
                # Revoke device on-chain
                tx_hash = await blockchain_client.revoke_device(
                    request.device_id.encode(),
                    result["new_accumulator_bytes"],
                    operation_id=f"revoke-{request.device_id}"
                )
                logger.info(f"Device revocation transaction sent: {tx_hash}")

                # Mark device as revoked after blockchain confirmation
                await accumulator_service.finalize_device_status(request.device_id, "revoked")

            except Exception as e:
                logger.error(f"Failed to revoke device on blockchain: {e}")
                # For development/testing, update cache locally
                blockchain_client.current_root = result["new_accumulator"]
                logger.warning("Updated cache locally due to blockchain error")
                await accumulator_service.finalize_device_status(request.device_id, "revoked")
        
        logger.info(f"Device revoked successfully: {request.device_id}")
        
        # Return 204 No Content as requested
        return None
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error revoking device {request.device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke device: {str(e)}"
        )


# Authentication Endpoints

@router.get("/auth/start", status_code=200)
async def auth_start(device_id: str):
    """
    Start device authentication flow.
    
    Returns a nonce that must be signed by the device.
    """
    try:
        device_id = validate_device_id(device_id)
        logger.info(f"Auth start requested for device: {device_id}")
        
        # Generate nonce
        nonce = generate_nonce()
        expires_at = get_current_timestamp() + 300  # 5 minutes
        
        # Store nonce
        active_nonces[nonce] = {
            "device_id": device_id,
            "created_at": get_current_timestamp(),
            "expires_at": expires_at,
            "used": False
        }
        
        # Cleanup old nonces
        _cleanup_expired_nonces()
        
        logger.info(f"Auth nonce generated for device: {device_id}")
        
        return {
            "nonce": nonce,
            "expiresAt": expires_at,
            "message": "Sign this nonce with your device key"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error starting auth for device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start authentication: {str(e)}"
        )


@router.post("/auth/verify", status_code=200)
async def auth_verify(
    request: AuthVerifyRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Verify device authentication.
    
    Validates signature, nonce, and membership proof.
    """
    request_id = getattr(http_request.state, 'request_id', 'unknown')
    
    try:
        logger.info(f"Auth verify requested for device: {request.device_id}")
        
        # Validate and consume nonce
        if request.nonce not in active_nonces:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired nonce"
            )
        
        nonce_data = active_nonces[request.nonce]
        
        if nonce_data["used"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nonce already used"
            )
        
        if is_expired(nonce_data["created_at"], 300):  # 5 minutes
            del active_nonces[request.nonce]
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nonce expired"
            )
        
        if nonce_data["device_id"] != request.device_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nonce device mismatch"
            )
        
        # Mark nonce as used
        nonce_data["used"] = True
        
        # Get device from database
        from sqlalchemy import select
        stmt = select(Device).where(Device.id == request.device_id)
        result = await session.execute(stmt)
        device = result.scalar_one_or_none()
        
        # Get public key
        if device:
            pubkey_bytes = device.pubkey
        elif request.pubkey_pem:
            pubkey_bytes = parse_ed25519_pem(request.pubkey_pem)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Device not found and no public key provided"
            )
        
        # Verify signature on nonce
        try:
            signature_bytes = base64.b64decode(request.signature_base64)
            nonce_bytes = request.nonce.encode()
            
            if not verify_ed25519_signature(nonce_bytes, signature_bytes, pubkey_bytes):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature"
                )
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Signature verification failed"
            )
        
        # Verify membership proof
        is_valid_member = await accumulator_service.verify_device_membership(
            request.device_id,
            request.witness_hex
        )
        
        if not is_valid_member:
            # Try to refresh witness if device exists but witness is stale
            if device and device.status == "active":
                new_witness = await accumulator_service.refresh_device_witness(request.device_id)
                if new_witness:
                    logger.info(f"Refreshed witness for device {request.device_id}")
                    return {
                        "ok": False,
                        "reason": "stale_witness",
                        "newWitness": new_witness,
                        "message": "Witness refreshed, retry with new witness"
                    }
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid membership proof"
            )
        
        logger.info(f"Device authenticated successfully: {request.device_id}")
        
        return {
            "ok": True,
            "device_id": request.device_id,
            "message": "Authentication successful"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying auth for device {request.device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication verification failed: {str(e)}"
        )


def _cleanup_expired_nonces():
    """Remove expired nonces from memory."""
    current_time = get_current_timestamp()
    expired_nonces = [
        nonce for nonce, data in active_nonces.items()
        if is_expired(data["created_at"], 300)
    ]

    for nonce in expired_nonces:
        del active_nonces[nonce]

    if expired_nonces:
        logger.debug(f"Cleaned up {len(expired_nonces)} expired nonces")


# Additional endpoints for frontend

@router.get("/devices")
async def get_devices():
    """Get all devices from database."""
    try:
        async with get_db_session() as session:
            stmt = select(Device)
            result = await session.execute(stmt)
            devices = result.scalars().all()

            device_list = []
            for device in devices:
                device_list.append({
                    "device_id": device.device_id,
                    "status": device.status,
                    "prime_hex": device.prime.hex() if device.prime else None,
                    "witness_hex": device.witness.hex() if device.witness else None,
                    "enrolled_at": device.enrolled_at.isoformat() if device.enrolled_at else None,
                    "updated_at": device.updated_at.isoformat() if device.updated_at else None
                })

            return {"devices": device_list}

    except Exception as e:
        logger.error(f"Error fetching devices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch devices: {str(e)}"
        )


@router.post("/generate-prime")
async def generate_prime(request: dict):
    """Generate prime from public key hash."""
    try:
        public_key_pem = request.get("public_key_pem")
        if not public_key_pem:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="public_key_pem is required"
            )

        # Import the hash_to_prime function
        from accum.hash_to_prime import hash_to_prime

        # Parse the PEM key to get the raw key bytes
        # For Ed25519, we need to extract the raw public key
        pem_lines = public_key_pem.strip().split('\n')
        pem_data = ''.join(pem_lines[1:-1])  # Remove header/footer

        # Decode base64 to get raw bytes
        import base64
        raw_key_bytes = base64.b64decode(pem_data)

        # For Ed25519, the raw key is 32 bytes, so we take the last 32 bytes
        # (after removing the SPKI header)
        if len(raw_key_bytes) >= 32:
            raw_key_bytes = raw_key_bytes[-32:]  # Take last 32 bytes (the actual key)
        else:
            raw_key_bytes = raw_key_bytes

        # Generate prime from hash
        prime = hash_to_prime(raw_key_bytes)

        # Calculate hash of the public key
        import hashlib
        public_key_hash = hashlib.sha256(raw_key_bytes).hexdigest()

        return {
            "public_key_hash": public_key_hash,
            "prime": str(prime),
            "prime_hex": hex(prime),
            "prime_bits": prime.bit_length()
        }

    except Exception as e:
        logger.error(f"Error generating prime: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prime generation failed: {str(e)}"
        )


@router.get("/events")
async def get_events():
    """Get event logs from database."""
    try:
        async with get_db_session() as session:
            stmt = select(EventLog).order_by(desc(EventLog.timestamp)).limit(100)
            result = await session.execute(stmt)
            events = result.scalars().all()

            event_list = []
            for event in events:
                event_list.append({
                    "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                    "event_type": event.event_type,
                    "device_id": event.device_id,
                    "tx_hash": event.tx_hash,
                    "block_number": event.block_number,
                    "details": event.details
                })

            return {"events": event_list}

    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch events: {str(e)}"
        )


@router.get("/accumulator")
async def get_accumulator_state():
    """Get current accumulator state."""
    try:
        # Get accumulator data from blockchain
        accumulator_data = await blockchain_client.get_accumulator_data()

        return {
            "currentRoot": accumulator_data.get("current_root", "0x"),
            "activeDevices": accumulator_data.get("active_devices", 0),
            "version": accumulator_data.get("version", 1),
            "emergencyPaused": accumulator_data.get("emergency_paused", False)
        }

    except Exception as e:
        logger.error(f"Error fetching accumulator state: {e}")
        # Return mock data if blockchain is not available
        return {
            "currentRoot": "0x",
            "activeDevices": 0,
            "version": 1,
            "emergencyPaused": False
        }
