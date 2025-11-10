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
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
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
from supabase_db import SupabaseDatabaseManager as DatabaseManager, DeviceStatus, MetaKeys
from chain_client import ChainClient
from models import (
    EnrollRequest, EnrollResponse,
    AuthRequest, AuthResponse, 
    RevokeRequest, RevokeResponse,
    RootResponse, StatusResponse,
    KeyGenRequest, KeyGenResponse,
    WitnessResponse,
    DeviceListResponse,
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

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        db = DatabaseManager(settings.supabase_url, settings.supabase_key)
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
        
        # Update blockchain (multi-sig mode only)
        result = chain.register_device(device_id_hex, new_root_hex)
        
        # Result is always (safe_tx_hash, tx_params) in multi-sig mode
        tx_hash, tx_params = result
        logger.warning(f"⚠️  Multi-sig enrollment pending: {tx_hash}")
        
        # Store pending transaction with metadata and Safe parameters
        pending_multisig_txs[tx_hash] = {
            'safeTxHash': tx_hash,
            'operationType': 'enroll',
            'type': 'registerDevice',
            'device_id': device_id_hex,
            'deviceIdHex': device_id_hex,
            'pubkey_pem': request.publicKeyPEM,
            'id_prime': str(id_prime),
            'witness': current_root_hex,
            'key_type': request.keyType,
            'newAccumulator': new_root_hex,
            'oldAccumulator': current_root_hex,
            # Safe transaction parameters from chain_client
            **tx_params,
            # Metadata
            'signatures': [],
            'status': 'pending',
            'proposer': settings.safe_owners[0] if settings.safe_owners else '0x0000000000000000000000000000000000000000',
            'createdAt': datetime.now().isoformat(),
            'required_signatures': 3
        }
        
        return JSONResponse(
            status_code=202,
            content={
                "status": "pending",
                "message": "Device enrollment requires multi-sig approval",
                "safeTxHash": tx_hash,
                "device_id": device_id_hex,
                "deviceIdHex": device_id_hex,
                "idPrime": str(id_prime),
                "witnessHex": current_root_hex,
                "required_signatures": 3,
                "multisig_url": "http://localhost:3000/multisig-approve"
            }
        )
        # When a new device is added, all existing witnesses become stale
        # We use trapdoor division to compute: witness = new_root^(1/prime) mod N
        active_devices = db.get_active_devices()
        
        # Get the NEW accumulator root (after syncing with blockchain)
        new_root_after_sync_hex = db.get_meta(MetaKeys.ROOT_HEX)
        new_root_after_sync = settings.parse_accumulator_from_hex(new_root_after_sync_hex)
        
        refreshed_count = 0
        for device in active_devices:
            # Skip the newly enrolled device (it already has correct witness)
            if device['device_id'] == device_id:
                continue
                
            device_prime = device['id_prime']
            if isinstance(device_prime, str):
                device_prime = int(device_prime)
                
            # Compute fresh witness using trapdoor division:
            # witness = new_root^(1/device_prime) mod N
            # This gives us the accumulator without this device's prime
            fresh_witness = trapdoor_remove_member_with_lambda(
                A=new_root_after_sync,
                prime=device_prime,
                N=settings.N,
                lambda_n=settings.lambda_n
            )
            fresh_witness_hex = settings.format_accumulator_to_hex(fresh_witness)
            
            # Update witness in database
            db.update_device_witness(device['device_id'], fresh_witness_hex)
            refreshed_count += 1
            
        logger.info(f"Device enrolled successfully: {device_id_hex}")
        logger.info(f"Refreshed witnesses for {refreshed_count} existing devices")
        
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
        stored_witness_hex = device['witness']
        new_witness_hex = None
        
        # Verify membership proof: witness^prime ≡ root (mod N)
        is_member = verify_membership(witness_int, request.idPrime, current_root, settings.N)
        
        if not is_member:
            logger.warning(f"Membership verification failed for device: {request.deviceIdHex}")
            # Try with stored witness in case client is outdated
            stored_witness_int = int(stored_witness_hex, 16) 
            is_member_stored = verify_membership(stored_witness_int, request.idPrime, current_root, settings.N)
            
            if not is_member_stored:
                raise ValueError("Membership proof verification failed")
            else:
                # Client has outdated witness, provide the current one
                logger.info(f"Client has outdated witness, returning updated witness")
                new_witness_hex = stored_witness_hex
        
        # Check if client witness differs from stored (even if verification passed)
        elif request.witnessHex != stored_witness_hex:
            logger.info(f"Client witness differs from stored, returning updated witness")
            new_witness_hex = stored_witness_hex
        
        # Verify cryptographic signature (signing is over the nonce hex string itself)
        is_signature_valid = verify_device_signature(
            message=request.nonceHex,
            signature_base64=request.signatureB64,
            public_key_pem=request.publicKeyPEM,
            key_type=request.keyType
        )
        
        if not is_signature_valid:
            raise ValueError("Signature verification failed")
        
        # Authentication successful
        logger.info(f"Device authenticated successfully: {request.deviceIdHex}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=AuthResponse(
                ok=True,
                newWitnessHex=new_witness_hex,  # Return updated witness if client is outdated
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
        
        # Update blockchain (multi-sig mode only)
        result = chain.revoke_device(request.deviceIdHex, new_root_hex)
        
        # Result is always (safe_tx_hash, tx_params) in multi-sig mode
        tx_hash, tx_params = result
        logger.warning(f"⚠️  Multi-sig revocation pending: {tx_hash}")
        
        # Store pending transaction with metadata and Safe parameters
        pending_multisig_txs[tx_hash] = {
            'safeTxHash': tx_hash,
            'operationType': 'revoke',
            'type': 'revokeDevice',
            'device_id': request.deviceIdHex,
            'deviceIdHex': request.deviceIdHex,
            'id_prime': str(device['id_prime']),
            'newAccumulator': new_root_hex,
            'oldAccumulator': current_root_hex,
            # Safe transaction parameters from chain_client
            **tx_params,
            # Metadata
            'signatures': [],
            'status': 'pending',
            'proposer': settings.safe_owners[0] if settings.safe_owners else '0x0000000000000000000000000000000000000000',
            'createdAt': datetime.now().isoformat(),
            'required_signatures': 3
        }
        
        return JSONResponse(
            status_code=202,
            content={
                "status": "pending",
                "message": "Device revocation requires multi-sig approval",
                "safeTxHash": tx_hash,
                "device_id": request.deviceIdHex,
                "required_signatures": 3,
                "multisig_url": "http://localhost:3000/multisig-approve"
            }
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
            "GET /status": "Get system status",
            "POST /keygen": "Generate test keypair (demo only)",
            "GET /witness/{deviceIdHex}": "Get device witness"
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


@app.get("/witness/{device_id_hex}", response_model=WitnessResponse)
async def get_device_witness(device_id_hex: str) -> JSONResponse:
    """
    Get the current witness for a specific device.
    
    This endpoint returns the latest witness stored in the database,
    which is kept fresh by enrollment and revocation operations.
    """
    try:
        # Validate device ID format
        if len(device_id_hex) != 64:
            raise ValueError("Device ID must be 64 hex characters")
        
        # Get device from database
        device_id = bytes.fromhex(device_id_hex)
        device = db.get_device(device_id)
        
        if not device:
            raise ValueError("Device not found")
        
        # Return current witness and device status
        status_map = {
            DeviceStatus.ACTIVE: "active",
            DeviceStatus.REVOKED: "revoked"
        }
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=WitnessResponse(
                deviceIdHex=device_id_hex.lower(),
                witnessHex=device['witness'],
                status=status_map.get(device['status'], 'unknown'),
                lastUpdated=device['updated_at']
            ).dict()
        )
        
    except ValueError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": str(e), "code": "INVALID_REQUEST"}
        )
    except Exception as e:
        return _handle_error(e, "Failed to get device witness")


@app.get("/devices", response_model=DeviceListResponse)
async def get_devices(status_filter: Optional[str] = None) -> JSONResponse:
    """
    Get list of all devices from the database.
    
    Query Parameters:
        status_filter: Filter by status ('active', 'revoked', or omit for all)
    
    Returns:
        DeviceListResponse with list of devices and counts
    """
    try:
        logger.info(f"Fetching devices with status filter: {status_filter}")
        
        # Map status string to integer
        status_int = None
        if status_filter:
            status_lower = status_filter.lower()
            if status_lower == 'active':
                status_int = DeviceStatus.ACTIVE
            elif status_lower == 'revoked':
                status_int = DeviceStatus.REVOKED
            else:
                raise ValueError(f"Invalid status filter: {status_filter}. Use 'active' or 'revoked'")
        
        # Get devices from database
        devices_data = db.get_all_devices(status=status_int)
        logger.info(f"Retrieved {len(devices_data)} devices from database")
        
        # Convert to response model
        device_list = []
        for device in devices_data:
            try:
                # Handle both bytes and string device_id
                device_id_hex = device['device_id'].hex() if isinstance(device['device_id'], bytes) else device['device_id']
                
                device_list.append({
                    'deviceIdHex': device_id_hex,
                    'keyType': device['key_type'],
                    'idPrime': device['id_prime'],
                    'status': device['status'],
                    'createdAt': device['created_at'],
                    'updatedAt': device['updated_at']
                })
            except Exception as e:
                logger.error(f"Error processing device: {e}, device data: {device}")
                continue
        
        # Count by status
        all_devices = db.get_all_devices() if status_int else devices_data
        active_count = sum(1 for d in all_devices if d['status'] == DeviceStatus.ACTIVE)
        revoked_count = sum(1 for d in all_devices if d['status'] == DeviceStatus.REVOKED)
        
        logger.info(f"Returning {len(device_list)} devices (active: {active_count}, revoked: {revoked_count})")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                'devices': device_list,
                'total': len(all_devices),
                'active': active_count,
                'revoked': revoked_count
            }
        )
        
    except ValueError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": str(e), "code": "INVALID_REQUEST"}
        )
    except Exception as e:
        return _handle_error(e, "Failed to fetch devices")


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


# ============================================================================
# MULTI-SIGNATURE ENDPOINTS
# ============================================================================

# In-memory storage for pending transactions (use Redis in production)
pending_multisig_txs = {}

@app.get("/multisig/safe-info")
async def get_safe_info():
    """Get Gnosis Safe configuration."""
    try:
        safe_info = chain.get_safe_info()
        return {
            "safeAddress": safe_info["safe_address"],
            "registryAddress": safe_info["registry_address"],
            "threshold": safe_info["threshold"],
            "owners": safe_info["owners"]
        }
    except Exception as e:
        logger.error(f"Error getting Safe info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/multisig/propose")
async def propose_transaction(proposal: Dict[str, Any]):
    """Propose a new multi-sig transaction."""
    try:
        safe_tx_hash = proposal["safeTxHash"]
        
        # Store pending transaction
        pending_multisig_txs[safe_tx_hash] = {
            **proposal,
            "status": "pending",
            "executedTxHash": None,
            "executedAt": None
        }
        
        logger.info(f"Transaction proposed: {safe_tx_hash}")
        return {
            "success": True,
            "safeTxHash": safe_tx_hash,
            "signatures": proposal["signatures"]
        }
    except Exception as e:
        logger.error(f"Error proposing transaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/multisig/pending")
async def get_pending_transactions():
    """Get all pending multi-sig transactions."""
    try:
        pending = [
            tx for tx in pending_multisig_txs.values()
            if tx["status"] == "pending"
        ]
        return {"transactions": pending}
    except Exception as e:
        logger.error(f"Error getting pending transactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/multisig/sign")
async def sign_transaction(signature_data: Dict[str, Any]):
    """Add signature to pending transaction."""
    try:
        safe_tx_hash = signature_data["safeTxHash"]
        
        if safe_tx_hash not in pending_multisig_txs:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        tx = pending_multisig_txs[safe_tx_hash]
        
        # Check if already signed by this address
        signer = signature_data["signer"].lower()
        if any(sig["signer"].lower() == signer for sig in tx["signatures"]):
            raise HTTPException(status_code=400, detail="Already signed by this address")
        
        # Add signature
        tx["signatures"].append({
            "signer": signature_data["signer"],
            "signature": signature_data["signature"],
            "r": signature_data["r"],
            "s": signature_data["s"],
            "v": signature_data["v"]
        })
        
        logger.info(f"Signature added to {safe_tx_hash} by {signer}")
        return {
            "success": True,
            "signatures": len(tx["signatures"]),
            "threshold": tx.get("requiredSignatures", tx.get("required_signatures", 3))
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding signature: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/multisig/execute")
async def execute_transaction(execution_data: Dict[str, Any]):
    """Mark transaction as executed and process the operation."""
    try:
        safe_tx_hash = execution_data["safeTxHash"]
        
        if safe_tx_hash not in pending_multisig_txs:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        tx = pending_multisig_txs[safe_tx_hash]
        tx["status"] = "executed"
        tx["executedTxHash"] = execution_data["txHash"]
        tx["executedAt"] = execution_data.get("blockNumber")
        
        logger.info(f"Transaction executed: {safe_tx_hash} -> {execution_data['txHash']}")
        
        # Process the transaction based on type
        operation_type = tx.get("operationType")
        
        if operation_type == "enroll":
            # Sync blockchain state
            await _sync_blockchain_state()
            
            # Store device in database
            device_id = bytes.fromhex(tx["device_id"])
            db.insert_device(
                device_id=device_id,
                pubkey_pem=tx["pubkey_pem"],
                id_prime=int(tx["id_prime"]),
                witness=tx["witness"],  # Old accumulator (witness for membership proof)
                key_type=tx["key_type"],
                status=DeviceStatus.ACTIVE
            )
            logger.info(f"Device {tx['device_id'][:16]}... stored in database")
            
            # Refresh witnesses for all existing active devices
            active_devices = db.get_active_devices()
            new_root_hex = db.get_meta(MetaKeys.ROOT_HEX)
            new_root = settings.parse_accumulator_from_hex(new_root_hex)
            
            refreshed_count = 0
            for dev in active_devices:
                # Skip the newly enrolled device (it already has correct witness)
                if dev['device_id'] == device_id:
                    continue
                
                device_prime = dev['id_prime']
                if isinstance(device_prime, str):
                    device_prime = int(device_prime)
                
                # Compute fresh witness using trapdoor division
                fresh_witness = trapdoor_remove_member_with_lambda(
                    A=new_root,
                    prime=device_prime,
                    N=settings.N,
                    lambda_n=settings.lambda_n
                )
                fresh_witness_hex = settings.format_accumulator_to_hex(fresh_witness)
                db.update_device_witness(dev['device_id'], fresh_witness_hex)
                refreshed_count += 1
            
            logger.info(f"Refreshed witnesses for {refreshed_count} existing devices")
        
        elif operation_type == "revoke":
            # Sync blockchain state
            await _sync_blockchain_state()
            
            # Update device status in database
            device_id = bytes.fromhex(tx["device_id"])
            db.update_device_status(device_id, DeviceStatus.REVOKED)
            logger.info(f"Device {tx['device_id'][:16]}... marked as revoked in database")
            
            # Refresh witnesses for remaining active devices
            active_devices = db.get_active_devices()
            new_root_hex = db.get_meta(MetaKeys.ROOT_HEX)
            new_root = settings.parse_accumulator_from_hex(new_root_hex)
            
            refreshed_count = 0
            for dev in active_devices:
                device_prime = dev['id_prime']
                if isinstance(device_prime, str):
                    device_prime = int(device_prime)
                
                # Compute fresh witness using trapdoor division
                fresh_witness = trapdoor_remove_member_with_lambda(
                    A=new_root,
                    prime=device_prime,
                    N=settings.N,
                    lambda_n=settings.lambda_n
                )
                fresh_witness_hex = settings.format_accumulator_to_hex(fresh_witness)
                db.update_device_witness(dev['device_id'], fresh_witness_hex)
                refreshed_count += 1
            
            logger.info(f"Refreshed witnesses for {refreshed_count} remaining active devices")
        
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing executed transaction: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info"
    )
