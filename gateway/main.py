"""
IoT Identity Gateway - Main FastAPI Application

Provides REST API endpoints for device enrollment, authentication, and revocation
using RSA accumulator with trapdoor operations.
"""

import os
import sys
import logging
import hashlib
import secrets
import traceback
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from cryptography.hazmat.primitives import serialization

# Add parent directory to path for importing accumulator modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import accumulator modules
from accum.accumulator import add_member, verify_membership
from accum.trapdoor_operations import trapdoor_remove_member_with_lambda
from accum.hash_to_prime import hash_to_prime_coprime_lambda
from accum.rsa_key_generator import verify_device_signature
from accum.rsa_key_generator import generate_ed25519_keypair, generate_rsa_keypair
from accum.witness_refresh import update_witness_on_addition, refresh_witness

# Import gateway modules  
from settings import settings
from db import DatabaseManager, DeviceStatus, MetaKeys
from chain_client import ChainClient
from models import (
    EnrollRequest, EnrollResponse,
    AuthRequest, AuthResponse, 
    RevokeRequest, RevokeResponse,
    RootResponse, StatusResponse,
    KeyGenRequest, KeyGenResponse,
    ErrorResponse
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="IoT Identity Gateway",
    description="RSA Accumulator-based IoT Device Identity Management System",
    version="1.0.0"
)

# Global instances
db: DatabaseManager = None
chain: ChainClient = None


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    global db, chain
    
    try:
        logger.info("Starting IoT Identity Gateway...")
        
        # Initialize database
        db = DatabaseManager(settings.db_path)
        logger.info("Database initialized")
        
        # Initialize blockchain client
        chain = ChainClient()
        logger.info("Blockchain client initialized")
        
        # Seed database with RSA parameters if not present
        await _seed_initial_data()
        
        # Sync with blockchain state
        await _sync_blockchain_state()
        
        logger.info("IoT Identity Gateway started successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        logger.error(traceback.format_exc())
        raise


async def _seed_initial_data():
    """Seed database with initial RSA parameters."""
    if not db.get_meta(MetaKeys.N_HEX):
        db.set_meta(MetaKeys.N_HEX, settings.n_hex)
        db.set_meta(MetaKeys.G_HEX, settings.g_hex) 
        db.set_meta(MetaKeys.LAMBDA_N_HEX, settings.lambda_n_hex)
        logger.info("Seeded RSA parameters into database")


async def _sync_blockchain_state():
    """Sync database state with blockchain."""
    try:
        # Get current state from blockchain
        acc_hex, hash_hex, version = chain.get_state()
        
        # Update database metadata
        db.set_meta(MetaKeys.ROOT_HEX, acc_hex)
        db.set_meta(MetaKeys.VERSION, str(version))
        
        logger.info(f"Synced with blockchain: version={version}")
        
    except Exception as e:
        logger.error(f"Failed to sync with blockchain: {e}")
        raise


def _compute_device_id(public_key_pem: str) -> bytes:
    """Compute device ID from public key DER."""
    try:
        # Load public key and get DER format
        public_key = serialization.load_pem_public_key(public_key_pem.encode())
        der_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Device ID = keccak256(DER)
        return hashlib.sha3_256(der_bytes).digest()  # 32 bytes
        
    except Exception as e:
        raise ValueError(f"Invalid public key PEM: {e}")


def _handle_error(e: Exception, default_message: str) -> JSONResponse:
    """Handle exceptions and return consistent error responses."""
    logger.error(f"Error: {e}")
    logger.error(traceback.format_exc())
    
    if isinstance(e, ValueError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": str(e), "code": "VALIDATION_ERROR"}
        )
    elif isinstance(e, PermissionError):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": str(e), "code": "PERMISSION_DENIED"}
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": default_message, "code": "INTERNAL_ERROR"}
        )


@app.post("/enroll", response_model=EnrollResponse)
async def enroll_device(request: EnrollRequest) -> JSONResponse:
    """
    Enroll a new IoT device in the accumulator.
    
    This endpoint:
    1. Computes device ID from public key DER
    2. Generates prime coprime to λ(N) 
    3. Adds device to accumulator using trapdoor-safe operations
    4. Updates blockchain state
    5. Stores device in database
    """
    try:
        logger.info(f"Enrolling device with key type: {request.keyType}")
        
        # Compute device ID
        device_id = _compute_device_id(request.publicKeyPEM)
        device_id_hex = device_id.hex()
        
        # Check if device already exists
        if db.device_exists(device_id):
            raise ValueError(f"Device already enrolled: {device_id_hex}")
        
        # Get DER bytes for prime generation
        public_key = serialization.load_pem_public_key(request.publicKeyPEM.encode())
        der_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Generate prime coprime to λ(N)
        id_prime = hash_to_prime_coprime_lambda(der_bytes, settings.lambda_n)
        logger.info(f"Generated prime: {id_prime}")
        
        # Get current accumulator state
        current_root_hex = db.get_meta(MetaKeys.ROOT_HEX)
        if not current_root_hex:
            raise ValueError("Accumulator state not initialized")
        
        current_root = settings.parse_accumulator_from_hex(current_root_hex)
        
        # Add member to accumulator  
        new_root = add_member(current_root, id_prime, settings.N)
        new_root_hex = settings.format_accumulator_to_hex(new_root)
        
        # Update blockchain
        tx_hash = chain.register_device(device_id_hex, new_root_hex)
        logger.info(f"Blockchain updated: {tx_hash}")
        
        # Sync state from blockchain
        await _sync_blockchain_state()
        
        # Store device in database (witness = previous root)
        db.insert_device(
            device_id=device_id,
            pubkey_pem=request.publicKeyPEM,
            id_prime=id_prime,
            witness=current_root_hex,  # Witness for membership proof
            key_type=request.keyType,
            status=DeviceStatus.ACTIVE
        )
        
        logger.info(f"Device enrolled successfully: {device_id_hex}")
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=EnrollResponse(
                deviceIdHex=device_id_hex,
                idPrime=id_prime,
                witnessHex=current_root_hex,
                rootHex=new_root_hex
            ).dict()
        )
        
    except Exception as e:
        return _handle_error(e, "Device enrollment failed")


@app.post("/auth", response_model=AuthResponse) 
async def authenticate_device(request: AuthRequest) -> JSONResponse:
    """
    Authenticate a device using membership proof and signature.
    
    This endpoint:
    1. Verifies device exists and is active
    2. Checks membership proof (witness^prime ≡ root mod N)
    3. Verifies cryptographic signature  
    4. Updates witness if accumulator changed
    """
    try:
        logger.info(f"Authenticating device: {request.deviceIdHex}")
        
        # Get device from database
        device_id = bytes.fromhex(request.deviceIdHex)
        device = db.get_device(device_id)
        
        if not device:
            raise ValueError("Device not found")
        
        if device['status'] != DeviceStatus.ACTIVE:
            raise ValueError("Device is not active")
        
        # Verify device identity matches
        if device['id_prime'] != request.idPrime:
            raise ValueError("Identity prime mismatch")
        
        # Get current accumulator root
        current_root_hex = db.get_meta(MetaKeys.ROOT_HEX)
        current_root = settings.parse_accumulator_from_hex(current_root_hex)
        
        # Parse witness from request
        witness_int = int(request.witnessHex, 16)
        
        # Verify membership proof: witness^prime ≡ root (mod N)
        is_member = verify_membership(witness_int, request.idPrime, current_root, settings.N)
        
        if not is_member:
            logger.warning(f"Membership verification failed for device: {request.deviceIdHex}")
            # Try with stored witness in case client is outdated
            stored_witness_int = int(device['witness'], 16) 
            is_member_stored = verify_membership(stored_witness_int, request.idPrime, current_root, settings.N)
            
            if not is_member_stored:
                raise ValueError("Membership proof verification failed")
            else:
                # Client has outdated witness, we'll provide updated one
                witness_int = stored_witness_int
        
        # Verify cryptographic signature (signing is over the nonce hex string itself)
        is_signature_valid = verify_device_signature(
            message=request.nonceHex,
            signature_base64=request.signatureB64,
            public_key_pem=request.publicKeyPEM,
            key_type=request.keyType
        )
        
        if not is_signature_valid:
            raise ValueError("Signature verification failed")
        
        # Check if witness needs updating
        stored_witness_hex = device['witness']
        new_witness_hex = None
        
        if stored_witness_hex != request.witnessHex:
            # Witness is outdated, compute fresh witness
            active_primes = db.get_active_primes()
            if request.idPrime in active_primes:
                fresh_witness = refresh_witness(
                    target_p=request.idPrime,
                    set_primes=set(active_primes),
                    N=settings.N,
                    g=settings.g
                )
                new_witness_hex = settings.format_accumulator_to_hex(fresh_witness)
                
                # Update stored witness
                db.update_device_witness(device_id, new_witness_hex)
                logger.info(f"Updated witness for device: {request.deviceIdHex}")
        
        logger.info(f"Device authenticated successfully: {request.deviceIdHex}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=AuthResponse(
                ok=True,
                newWitnessHex=new_witness_hex,
                message="Authentication successful"
            ).dict()
        )
        
    except Exception as e:
        return _handle_error(e, "Device authentication failed")


@app.post("/revoke", response_model=RevokeResponse)
async def revoke_device(request: RevokeRequest) -> JSONResponse:
    """
    Revoke a device using trapdoor operations.
    
    This endpoint:
    1. Verifies device exists and is active
    2. Removes device from accumulator using trapdoor
    3. Updates blockchain state  
    4. Marks device as revoked in database
    """
    try:
        logger.info(f"Revoking device: {request.deviceIdHex}")
        
        # Get device from database
        device_id = bytes.fromhex(request.deviceIdHex)
        device = db.get_device(device_id)
        
        if not device:
            raise ValueError("Device not found")
        
        if device['status'] != DeviceStatus.ACTIVE:
            raise ValueError("Device is not active")
        
        # Get current accumulator state
        current_root_hex = db.get_meta(MetaKeys.ROOT_HEX)
        current_root = settings.parse_accumulator_from_hex(current_root_hex)
        
        # Remove device using trapdoor operation
        # This is the key requirement: MUST use trapdoor operations
        new_root = trapdoor_remove_member_with_lambda(
            A=current_root,
            prime=device['id_prime'],
            N=settings.N,
            lambda_n=settings.lambda_n
        )
        new_root_hex = settings.format_accumulator_to_hex(new_root)
        
        logger.info(f"Trapdoor removal complete: {device['id_prime']}")
        
        # Update blockchain
        tx_hash = chain.revoke_device(request.deviceIdHex, new_root_hex)
        logger.info(f"Blockchain updated: {tx_hash}")
        
        # Sync state from blockchain
        await _sync_blockchain_state()
        
        # Mark device as revoked in database
        db.update_device_status(device_id, DeviceStatus.REVOKED)
        
        logger.info(f"Device revoked successfully: {request.deviceIdHex}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=RevokeResponse(
                ok=True,
                rootHex=new_root_hex,
                message="Device revoked successfully"
            ).dict()
        )
        
    except Exception as e:
        return _handle_error(e, "Device revocation failed")


@app.get("/root", response_model=RootResponse)
async def get_accumulator_root() -> JSONResponse:
    """Get current accumulator root and version."""
    try:
        # Sync with blockchain to get latest state
        await _sync_blockchain_state()
        
        root_hex = db.get_meta(MetaKeys.ROOT_HEX)
        version_str = db.get_meta(MetaKeys.VERSION)
        
        if not root_hex or not version_str:
            raise ValueError("Accumulator state not initialized")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=RootResponse(
                rootHex=root_hex,
                version=int(version_str)
            ).dict()
        )
        
    except Exception as e:
        return _handle_error(e, "Failed to get accumulator root")


@app.get("/status", response_model=StatusResponse)
async def get_system_status() -> JSONResponse:
    """Get system status and health information."""
    try:
        # Get database stats
        db_stats = db.get_db_stats()
        
        # Check blockchain connection
        chain_info = chain.get_chain_info()
        
        # Get current version
        version_str = db.get_meta(MetaKeys.VERSION) or "0"
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=StatusResponse(
                status="healthy" if chain_info.get('connected') else "unhealthy",
                version=int(version_str),
                totalDevices=db_stats['total_devices'],
                activeDevices=db_stats['active_devices'], 
                revokedDevices=db_stats['revoked_devices'],
                chainConnected=chain_info.get('connected', False)
            ).dict()
        )
        
    except Exception as e:
        return _handle_error(e, "Failed to get system status")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "IoT Identity Gateway",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "POST /enroll": "Enroll new device",
            "POST /auth": "Authenticate device", 
            "POST /revoke": "Revoke device",
            "GET /root": "Get accumulator root",
            "GET /status": "Get system status"
        }
    }


# Demo/testing: generate keypairs
@app.post("/keygen", response_model=KeyGenResponse)
async def generate_keys(req: KeyGenRequest) -> JSONResponse:
    """
    Generate a device keypair (demo/testing only). Do not expose in production.

    - ed25519: returns base64 private key and PEM public key
    - rsa: returns PEM private/public keys
    """
    try:
        if req.keyType == 'ed25519':
            priv_b64, pub_pem = generate_ed25519_keypair()
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=KeyGenResponse(keyType='ed25519', privateKey=priv_b64, publicKeyPEM=pub_pem).dict()
            )
        else:
            priv_pem, pub_pem = generate_rsa_keypair(2048)
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=KeyGenResponse(keyType='rsa', privateKey=priv_pem, publicKeyPEM=pub_pem).dict()
            )
    except Exception as e:
        return _handle_error(e, "Key generation failed")


# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            code="HTTP_ERROR"
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            code="INTERNAL_ERROR"
        ).dict()
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info"
    )
