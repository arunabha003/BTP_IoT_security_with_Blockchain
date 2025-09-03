"""
FastAPI Server for RSA Accumulator Operations

This server provides REST API endpoints for all RSA accumulator operations,
key generation, and device management functionality.
"""

import json
import base64
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import accum package functions
import sys
import os
# Add the accum package to Python path
accum_path = os.path.join(os.path.dirname(__file__), '..', 'accum')
sys.path.insert(0, accum_path)

# Import modules directly to avoid package import issues
from rsa_params import load_params
from accumulator import (
    add_member,
    recompute_root,
    membership_witness,
    verify_membership,
)
from hash_to_prime import hash_to_prime
from witness_refresh import refresh_witness
from rsa_key_generator import (
    generate_ed25519_keypair,
    generate_rsa_keypair,
    generate_test_devices,
    save_test_devices,
    load_test_devices,
    generate_device_signature,
    verify_device_signature,
    get_key_info,
)
from trapdoor_operations import (
    trapdoor_remove_member,
    trapdoor_batch_remove_members,
    trapdoor_remove_member_with_lambda,
    trapdoor_batch_remove_members_with_lambda,
    verify_trapdoor_removal,
    compute_lambda_n,
)

# Pydantic models for request/response
class KeyGenerationRequest(BaseModel):
    key_type: str = "ed25519"  # "ed25519" or "rsa"
    num_devices: Optional[int] = 1

class SignatureRequest(BaseModel):
    message: str
    private_key_data: str
    key_type: str = "ed25519"

class VerificationRequest(BaseModel):
    message: str
    signature: str
    public_key_pem: str
    key_type: str = "ed25519"

class HashToPrimeRequest(BaseModel):
    data: str  # Base64 encoded data
    max_attempts: Optional[int] = 10000

class AddMemberRequest(BaseModel):
    current_accumulator: int
    prime: int

class RecomputeRootRequest(BaseModel):
    primes: List[int]

class MembershipWitnessRequest(BaseModel):
    primes: List[int]
    target_prime: int

class VerifyMembershipRequest(BaseModel):
    witness: int
    prime: int
    accumulator: int

class RefreshWitnessRequest(BaseModel):
    target_prime: int
    primes: List[int]

class TrapdoorRemoveRequest(BaseModel):
    current_accumulator: int
    prime_to_remove: int

class TrapdoorBatchRemoveRequest(BaseModel):
    current_accumulator: int
    primes_to_remove: List[int]

class TrapdoorRemoveLambdaRequest(BaseModel):
    current_accumulator: int
    prime_to_remove: int

class TrapdoorBatchRemoveLambdaRequest(BaseModel):
    current_accumulator: int
    primes_to_remove: List[int]

class VerifyTrapdoorRemovalRequest(BaseModel):
    old_accumulator: int
    new_accumulator: int
    removed_prime: int

class DeviceData(BaseModel):
    device_id: str
    private_key: Optional[str]
    public_key: str
    key_type: str
    status: str

class AccumulatorResponse(BaseModel):
    result: int
    operation: str
    success: bool

class KeyResponse(BaseModel):
    private_key: Optional[str]
    public_key: str
    key_type: str
    key_info: Optional[Dict[str, Any]] = None

class DeviceResponse(BaseModel):
    devices: Dict[str, Dict[str, str]]
    count: int

# Initialize FastAPI app
app = FastAPI(
    title="RSA Accumulator Server",
    description="REST API for RSA Accumulator Operations and IoT Device Management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for demonstration (in production, use database)
accumulator_state = {
    "current_accumulator": None,
    "primes": [],
    "witnesses": {},
    "devices": {}
}

@app.on_event("startup")
async def startup_event():
    """Initialize the server with production parameters."""
    try:
        N, g = load_params()
        accumulator_state["current_accumulator"] = g
        accumulator_state["modulus"] = N
        accumulator_state["generator"] = g
        print(f"✅ Server initialized with production parameters (N: {N.bit_length()} bits)")
    except Exception as e:
        print(f"❌ Failed to load parameters: {e}")
        raise

@app.get("/")
async def root():
    """Root endpoint with server status."""
    return {
        "message": "RSA Accumulator Server",
        "status": "running",
        "version": "1.0.0",
        "endpoints": [
            "/docs - API Documentation",
            "/status - Server status and accumulator state",
            "/key/generate - Generate cryptographic keys",
            "/key/info - Get key information",
            "/accumulator/add - Add member to accumulator",
            "/accumulator/witness - Generate membership witness",
            "/accumulator/verify - Verify membership",
            "/accumulator/refresh - Refresh witness",
            "/accumulator/recompute - Recompute accumulator root",
            "/accumulator/trapdoor/remove - Remove member via trapdoor (p,q)",
            "/accumulator/trapdoor/batch-remove - Batch remove members via trapdoor (p,q)",
            "/accumulator/trapdoor/remove-lambda - Remove member via trapdoor (lambda_n)",
            "/accumulator/trapdoor/batch-remove-lambda - Batch remove via trapdoor (lambda_n)",
            "/accumulator/trapdoor/verify-removal - Verify trapdoor removal",
            "/hash-to-prime - Convert data to prime",
            "/signature/generate - Generate digital signature",
            "/signature/verify - Verify digital signature",
            "/devices/generate - Generate test devices",
            "/devices - Get all devices",
            "/devices/save - Save devices to file",
            "/devices/load - Load devices from file"
        ]
    }

@app.get("/status")
async def get_status():
    """Get server status and current accumulator state."""
    return {
        "status": "operational",
        "current_accumulator": accumulator_state["current_accumulator"],
        "total_primes": len(accumulator_state["primes"]),
        "total_devices": len(accumulator_state["devices"]),
        "modulus_bits": accumulator_state["modulus"].bit_length() if "modulus" in accumulator_state else 0
    }

# Key Generation Endpoints
@app.post("/key/generate", response_model=KeyResponse)
async def generate_key(request: KeyGenerationRequest):
    """Generate cryptographic key pairs."""
    try:
        if request.key_type == "ed25519":
            private_key, public_key = generate_ed25519_keypair()
            key_info = get_key_info(public_key)
            return KeyResponse(
                private_key=private_key,
                public_key=public_key,
                key_type="ed25519",
                key_info=key_info
            )
        elif request.key_type == "rsa":
            private_key, public_key = generate_rsa_keypair()
            key_info = get_key_info(public_key)
            return KeyResponse(
                private_key=private_key,
                public_key=public_key,
                key_type="rsa",
                key_info=key_info
            )
        else:
            raise HTTPException(status_code=400, detail="key_type must be 'ed25519' or 'rsa'")
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Key generation failed: {str(e)}")

@app.post("/key/info")
async def get_key_information(public_key_pem: str):
    """Get information about a public key."""
    try:
        info = get_key_info(public_key_pem)
        return {"key_info": info}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse key: {str(e)}")

# Accumulator Operations Endpoints
@app.post("/accumulator/add", response_model=AccumulatorResponse)
async def add_to_accumulator(request: AddMemberRequest):
    """Add a member to the accumulator."""
    try:
        N = accumulator_state["modulus"]
        new_accumulator = add_member(request.current_accumulator, request.prime, N)

        # Update global state
        accumulator_state["current_accumulator"] = new_accumulator
        if request.prime not in accumulator_state["primes"]:
            accumulator_state["primes"].append(request.prime)

        return AccumulatorResponse(
            result=new_accumulator,
            operation="add_member",
            success=True
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to add member: {str(e)}")

@app.post("/accumulator/recompute", response_model=AccumulatorResponse)
async def recompute_accumulator_root(request: RecomputeRootRequest):
    """Recompute accumulator root from scratch."""
    try:
        N = accumulator_state["modulus"]
        g = accumulator_state["generator"]
        new_accumulator = recompute_root(request.primes, N, g)

        # Update global state
        accumulator_state["current_accumulator"] = new_accumulator
        accumulator_state["primes"] = request.primes

        return AccumulatorResponse(
            result=new_accumulator,
            operation="recompute_root",
            success=True
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to recompute root: {str(e)}")

@app.post("/accumulator/witness")
async def generate_membership_witness(request: MembershipWitnessRequest):
    """Generate a membership witness for a prime."""
    try:
        N = accumulator_state["modulus"]
        g = accumulator_state["generator"]
        witness = membership_witness(set(request.primes), request.target_prime, N, g)

        # Update global state
        accumulator_state["witnesses"][str(request.target_prime)] = witness

        return {
            "witness": witness,
            "target_prime": request.target_prime,
            "primes_count": len(request.primes),
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to generate witness: {str(e)}")

@app.post("/accumulator/verify")
async def verify_membership_proof(request: VerifyMembershipRequest):
    """Verify a membership proof."""
    try:
        N = accumulator_state["modulus"]
        is_valid = verify_membership(request.witness, request.prime, request.accumulator, N)

        return {
            "is_valid": is_valid,
            "prime": request.prime,
            "accumulator": request.accumulator,
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Verification failed: {str(e)}")

@app.post("/accumulator/refresh")
async def refresh_membership_witness(request: RefreshWitnessRequest):
    """Refresh a membership witness after accumulator changes."""
    try:
        N = accumulator_state["modulus"]
        g = accumulator_state["generator"]
        new_witness = refresh_witness(request.target_prime, set(request.primes), N, g)

        # Update global state
        accumulator_state["witnesses"][str(request.target_prime)] = new_witness

        return {
            "new_witness": new_witness,
            "target_prime": request.target_prime,
            "primes_count": len(request.primes),
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to refresh witness: {str(e)}")

# Trapdoor Revocation Endpoints
@app.post("/accumulator/trapdoor/remove")
async def trapdoor_remove_member_endpoint(request: TrapdoorRemoveRequest):
    """Remove a member from accumulator using trapdoor (p, q factors)."""
    try:
        N = accumulator_state["modulus"]

        # Load trapdoor factors from params.json
        params_file = Path(__file__).parent.parent / "accum" / "params.json"
        with open(params_file, "r") as f:
            params = json.load(f)

        p = int(params["p"], 16)
        q = int(params["q"], 16)

        new_accumulator = trapdoor_remove_member(
            request.current_accumulator,
            request.prime_to_remove,
            N, p, q
        )

        # Update global state
        accumulator_state["current_accumulator"] = new_accumulator

        return {
            "new_accumulator": new_accumulator,
            "removed_prime": request.prime_to_remove,
            "operation": "trapdoor_remove_member",
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to remove member via trapdoor: {str(e)}")

@app.post("/accumulator/trapdoor/batch-remove")
async def trapdoor_batch_remove_members_endpoint(request: TrapdoorBatchRemoveRequest):
    """Remove multiple members from accumulator using trapdoor (p, q factors)."""
    try:
        N = accumulator_state["modulus"]

        # Load trapdoor factors from params.json
        params_file = Path(__file__).parent.parent / "accum" / "params.json"
        with open(params_file, "r") as f:
            params = json.load(f)

        p = int(params["p"], 16)
        q = int(params["q"], 16)

        new_accumulator = trapdoor_batch_remove_members(
            request.current_accumulator,
            request.primes_to_remove,
            N, p, q
        )

        # Update global state
        accumulator_state["current_accumulator"] = new_accumulator

        return {
            "new_accumulator": new_accumulator,
            "removed_primes": request.primes_to_remove,
            "removed_count": len(request.primes_to_remove),
            "operation": "trapdoor_batch_remove_members",
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to batch remove members via trapdoor: {str(e)}")

@app.post("/accumulator/trapdoor/remove-lambda")
async def trapdoor_remove_member_lambda_endpoint(request: TrapdoorRemoveLambdaRequest):
    """Remove a member from accumulator using trapdoor (lambda_n)."""
    try:
        N = accumulator_state["modulus"]

        # Load trapdoor factors from params.json
        params_file = Path(__file__).parent.parent / "accum" / "params.json"
        with open(params_file, "r") as f:
            params = json.load(f)

        p = int(params["p"], 16)
        q = int(params["q"], 16)
        lambda_n = compute_lambda_n(p, q)

        new_accumulator = trapdoor_remove_member_with_lambda(
            request.current_accumulator,
            request.prime_to_remove,
            N, lambda_n
        )

        # Update global state
        accumulator_state["current_accumulator"] = new_accumulator

        return {
            "new_accumulator": new_accumulator,
            "removed_prime": request.prime_to_remove,
            "lambda_n": lambda_n,
            "operation": "trapdoor_remove_member_with_lambda",
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to remove member via trapdoor lambda: {str(e)}")

@app.post("/accumulator/trapdoor/batch-remove-lambda")
async def trapdoor_batch_remove_lambda_endpoint(request: TrapdoorBatchRemoveLambdaRequest):
    """Remove multiple members from accumulator using trapdoor (lambda_n)."""
    try:
        N = accumulator_state["modulus"]

        # Load trapdoor factors from params.json
        params_file = Path(__file__).parent.parent / "accum" / "params.json"
        with open(params_file, "r") as f:
            params = json.load(f)

        p = int(params["p"], 16)
        q = int(params["q"], 16)
        lambda_n = compute_lambda_n(p, q)

        new_accumulator = trapdoor_batch_remove_members_with_lambda(
            request.current_accumulator,
            request.primes_to_remove,
            N, lambda_n
        )

        # Update global state
        accumulator_state["current_accumulator"] = new_accumulator

        return {
            "new_accumulator": new_accumulator,
            "removed_primes": request.primes_to_remove,
            "removed_count": len(request.primes_to_remove),
            "lambda_n": lambda_n,
            "operation": "trapdoor_batch_remove_members_with_lambda",
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to batch remove members via trapdoor lambda: {str(e)}")

@app.post("/accumulator/trapdoor/verify-removal")
async def verify_trapdoor_removal_endpoint(request: VerifyTrapdoorRemovalRequest):
    """Verify that trapdoor removal was performed correctly."""
    try:
        N = accumulator_state["modulus"]

        is_valid = verify_trapdoor_removal(
            request.old_accumulator,
            request.new_accumulator,
            request.removed_prime,
            N
        )

        return {
            "is_valid": is_valid,
            "old_accumulator": request.old_accumulator,
            "new_accumulator": request.new_accumulator,
            "removed_prime": request.removed_prime,
            "verification": "trapdoor_removal",
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to verify trapdoor removal: {str(e)}")

# Hash-to-Prime Endpoint
@app.post("/hash-to-prime")
async def convert_to_prime(request: HashToPrimeRequest):
    """Convert arbitrary data to a prime number."""
    try:
        # Decode base64 data
        data = base64.b64decode(request.data)
        prime = hash_to_prime(data, max_attempts=request.max_attempts)

        return {
            "prime": prime,
            "input_data_length": len(data),
            "max_attempts": request.max_attempts,
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Hash-to-prime conversion failed: {str(e)}")

# Signature Endpoints
@app.post("/signature/generate")
async def generate_signature(request: SignatureRequest):
    """Generate a digital signature."""
    try:
        signature = generate_device_signature(
            request.message,
            request.private_key_data,
            request.key_type
        )

        return {
            "signature": signature,
            "message": request.message,
            "key_type": request.key_type,
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Signature generation failed: {str(e)}")

@app.post("/signature/verify")
async def verify_signature(request: VerificationRequest):
    """Verify a digital signature."""
    try:
        is_valid = verify_device_signature(
            request.message,
            request.signature,
            request.public_key_pem,
            request.key_type
        )

        return {
            "is_valid": is_valid,
            "message": request.message,
            "key_type": request.key_type,
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Signature verification failed: {str(e)}")

# Device Management Endpoints
@app.post("/devices/generate", response_model=DeviceResponse)
async def generate_devices(request: KeyGenerationRequest):
    """Generate test IoT devices with cryptographic keys."""
    try:
        devices = generate_test_devices(request.num_devices, request.key_type)

        # Update global state
        accumulator_state["devices"].update(devices)

        return DeviceResponse(
            devices=devices,
            count=len(devices)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Device generation failed: {str(e)}")

@app.post("/devices/save")
async def save_devices_to_file(filename: str = "server_devices.json"):
    """Save devices to a JSON file."""
    try:
        save_test_devices(accumulator_state["devices"], filename)
        return {
            "filename": filename,
            "device_count": len(accumulator_state["devices"]),
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save devices: {str(e)}")

@app.get("/devices/load")
async def load_devices_from_file(filename: str = "server_devices.json"):
    """Load devices from a JSON file."""
    try:
        devices = load_test_devices(filename)
        accumulator_state["devices"] = devices
        return DeviceResponse(
            devices=devices,
            count=len(devices)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load devices: {str(e)}")

@app.get("/devices")
async def get_all_devices():
    """Get all registered devices."""
    return DeviceResponse(
        devices=accumulator_state["devices"],
        count=len(accumulator_state["devices"])
    )

@app.delete("/devices")
async def clear_devices():
    """Clear all device data."""
    accumulator_state["devices"] = {}
    accumulator_state["primes"] = []
    accumulator_state["witnesses"] = {}
    accumulator_state["current_accumulator"] = accumulator_state["generator"]

    return {
        "message": "All device data cleared",
        "success": True
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
