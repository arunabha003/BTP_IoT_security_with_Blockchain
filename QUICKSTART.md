# IoT Identity Gateway - Quick Start Guide

This guide will help you set up and run the IoT Identity Gateway MVP on Anvil in under 10 minutes.

## Overview

The IoT Identity Gateway provides a REST API for managing IoT device identities using RSA accumulators with trapdoor operations. It supports:

- **Device Enrollment**: Add new devices to the accumulator
- **Device Authentication**: Verify device membership and signatures  
- **Device Revocation**: Remove devices using efficient trapdoor operations
- **Accumulator Queries**: Get current root and system status

## Prerequisites

- **Foundry** (for smart contracts and Anvil)
- **Python 3.11** (for the gateway; we use a 3.11 venv)
- **pip** (Python package manager)

## Step 1: Start Anvil

Open a terminal and start the local Ethereum node:

```bash
anvil
```

This will start Anvil on `http://127.0.0.1:8545` with 10 test accounts. **Keep this terminal open.**

Copy one of the private keys from the output (we'll use the first one):
```
Private Keys
==================
(0) 0xac0974bec39a17e36ba4a6b4d238ff944bacb378cbed5efcae784d7bf4f2ff80
```

## Step 2: Deploy Smart Contract

In a new terminal, navigate to the project directory:

```bash
cd /path/to/BTP_IoT_security_with_Blockchain
```

Set environment variable and deploy:

```bash
  export RPC_URL=http://127.0.0.1:8545
  export PRIVATE_KEY_ADMIN=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
  cd contracts
  forge script script/DeployRegistryMock.s.sol --broadcast --rpc-url $RPC_URL --private-key $PRIVATE_KEY_ADMIN
```

The output will show the deployed contract address. Copy it for the next step:
```
RegistryMock address: 0x5FbDB2315678afecb367f032d93F642f64180aa3
```

## Step 3: Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and update these values:

```bash
# Update with your deployed contract address
REGISTRY_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3

# The private key should already match from Step 1
PRIVATE_KEY_ADMIN=0xac0974bec39a17e36ba4a6b4d238ff944bacb378cbed5efcae784d7bf4f2ff80

# Other values can stay as defaults for testing
```

**Important**: The RSA parameters and `LAMBDA_N_HEX` are already configured with production-ready 2048-bit values.

## Step 4: Create Python 3.11 venv and install deps

Use a dedicated Python 3.11 virtual environment and install requirements:

```bash
cd gateway
# Clean any old venvs (optional)
rm -rf venv

# Create and activate Python 3.11 venv
python3.11 -m venv .venv311
source .venv311/bin/activate   # Windows: .venv311\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 5: Start the Gateway

Start the FastAPI server:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --log-level info
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Starting IoT Identity Gateway...
INFO:     Database initialized
INFO:     Blockchain client initialized
INFO:     IoT Identity Gateway started successfully
INFO:     Application startup complete.
```

## Step 6: Test the API

Open a new terminal and test the endpoints:

### Check System Status
```bash
curl -X GET http://127.0.0.1:8000/status
```

Expected response:
```json
{
  "status": "healthy",
  "version": 1,
  "totalDevices": 0,
  "activeDevices": 0,
  "revokedDevices": 0,
  "chainConnected": true
}
```

### Get Current Accumulator Root
```bash
curl -X GET http://127.0.0.1:8000/root
```

Expected response:
```json
{
  "rootHex": "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004",
  "version": 1
}
```

### Verify On-Chain State with cast (optional but recommended)

```bash
# From repo root
export RPC_URL=http://127.0.0.1:8545
export REG=0x5FbDB2315678afecb367f032d93F642f64180aa3  # your deployed address

# Version (should increase with each enroll/revoke)
cast call $REG "version()(uint256)" --rpc-url $RPC_URL

# Stored hash (should change after each update)
cast call $REG "storedHash()(bytes32)" --rpc-url $RPC_URL

# Full state (bytes accumulator, bytes32 hash, uint256 version)
cast call $REG "getCurrentState()(bytes,bytes32,uint256)" --rpc-url $RPC_URL
```

## Step 7: Complete End-to-End Test

### 1. Enroll a Device

First, generate a test key pair for the device (you can use the existing key generator):

```bash
PUB_PEM=$(curl -s -X POST http://127.0.0.1:8000/keygen \
  -H "Content-Type: application/json" -d '{"keyType":"ed25519"}' \
  | jq -r '.publicKeyPEM')
```

Copy the public key PEM output, then enroll the device:

```bash
curl -s -X POST http://127.0.0.1:8000/enroll \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg pem "$PUB_PEM" --arg kt "ed25519" '{publicKeyPEM:$pem, keyType:$kt}')"
```

Expected response:
```json
{
{"deviceIdHex":"8424f6f65ec723c17bed564d6105a30a90d8cf20a060c14294e762112c3dea2d","idPrime":73046701764652583113768529808202475898591418926378149777450666349220137023063,"witnessHex":"00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004","rootHex":"a5af8ca7777fd49941bdcf9385ecabb0ce26d43f0be425e6a17205dca928d2835d5ddaac9ed10baa7434fe279b3b42266a2bad12df67486605d1dcf91a39471c88203c13f773ba92981ac6f4531029e3fea055134d853c4dc90e8b7bfbfecea3bd18fe7bfb4cf877538ecf468608d5e06a23f0a5dcd4bc2113925ab27c19ab9519042125ff60a5d2e690d7923725e267c616cbdf9296ce39edd8e043846f4fd97442beab5dbea9ebb806130ef380129b4db2d6a14c792ed18a149ba830dd9ca069d013bac2473b43353fc4cf30f02c1f41d081ae874644dce916b691eac7dd38e213ccc0e69e01da1ec1031826d8f46d43526111bbe97be960ae50cc8ed8140c"}
}
```

Save the `deviceIdHex`, `idPrime`, and `witnessHex` for the next steps.

### 2. Authenticate the Device

Generate a signature for authentication:

```bash
PYTHONPATH=. python3.11 - << 'PY'
from accum.rsa_key_generator import generate_device_signature
import secrets
private_key = 'YOUR_PRIVATE_KEY_FROM_STEP_1'
nonce = secrets.token_hex(16)
signature = generate_device_signature(nonce, private_key, 'ed25519')
print('Nonce:', nonce)
print('Signature:', signature)
PY
```

Now authenticate:

```bash
curl -X POST http://127.0.0.1:8000/auth \
  -H "Content-Type: application/json" \
  -d '{
    "deviceIdHex": "YOUR_DEVICE_ID_FROM_ENROLL",
    "idPrime": YOUR_ID_PRIME_FROM_ENROLL,
    "witnessHex": "YOUR_WITNESS_FROM_ENROLL", 
    "signatureB64": "YOUR_SIGNATURE_FROM_ABOVE",
    "nonceHex": "YOUR_NONCE_FROM_ABOVE",
    "publicKeyPEM": "YOUR_PUBLIC_KEY_PEM",
    "keyType": "ed25519"
  }'
```

Expected response:
```json
{
  "ok": true,
  "newWitnessHex": null,
  "message": "Authentication successful"
}
```

### 3. Revoke the Device

Revoke the device using trapdoor operations:

```bash
curl -X POST http://127.0.0.1:8000/revoke \
  -H "Content-Type: application/json" \
  -d '{
    "deviceIdHex": "YOUR_DEVICE_ID_FROM_ENROLL"
  }'
```

Expected response:
```json
{
  "ok": true,
  "rootHex": "new_accumulator_root_after_removal...",
  "message": "Device revoked successfully"
}
```

### 4. Verify Revocation

Try to authenticate the revoked device again - it should fail:

```bash
curl -X POST http://127.0.0.1:8000/auth \
  -H "Content-Type: application/json" \
  -d '{
    "deviceIdHex": "YOUR_DEVICE_ID_FROM_ENROLL",
    "idPrime": YOUR_ID_PRIME_FROM_ENROLL,
    "witnessHex": "YOUR_WITNESS_FROM_ENROLL",
    "signatureB64": "YOUR_SIGNATURE",
    "nonceHex": "YOUR_NONCE",
    "publicKeyPEM": "YOUR_PUBLIC_KEY_PEM",
    "keyType": "ed25519"
  }'
```

Expected error response:
```json
{
  "error": "Device is not active",
  "code": "VALIDATION_ERROR"
}
```

## API Documentation

Once the gateway is running, you can access the interactive API documentation at:

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

## Key Features Demonstrated

✅ **Trapdoor-based revocation**: The `/revoke` endpoint uses `trapdoor_remove_member_with_lambda()` for efficient removal  
✅ **Coprime prime generation**: Device primes are generated coprime to λ(N) using `hash_to_prime_coprime_lambda()`  
✅ **Blockchain integration**: All accumulator updates are stored on the RegistryMock contract  
## Where is the database?

- The gateway uses SQLite at `gateway/gateway.db`.
- Inspect it with:
  ```bash
  cd gateway
  sqlite3 gateway.db ".tables"
  sqlite3 gateway.db "SELECT key, value FROM meta;"     # root, version, params
  sqlite3 gateway.db "SELECT hex(device_id), status FROM devices;"  # devices
  ```

✅ **Cryptographic verification**: Device signatures are verified using Ed25519/RSA  
✅ **Witness management**: Witnesses are updated automatically when the accumulator changes

## Troubleshooting

### "Cannot connect to blockchain"
- Make sure Anvil is running on http://127.0.0.1:8545
- Check that `RPC_URL` in `.env` matches your Anvil instance

### "Contract owner mismatch"  
- Ensure `PRIVATE_KEY_ADMIN` in `.env` matches the account used for deployment
- Verify the contract was deployed successfully

### "Invalid accumulator hex length"
- This usually indicates a configuration issue with RSA parameters
- Make sure all hex values in `.env` are properly formatted (with 0x prefix)

### "Membership proof verification failed"
- This can happen if the accumulator state is out of sync
- Try restarting the gateway to refresh the state
- Check that the device was properly enrolled first

## Next Steps

- **Scale testing**: Enroll multiple devices and test batch operations
- **Performance testing**: Measure enrollment, auth, and revocation latency  
- **Integration**: Connect real IoT devices using the API
- **Security audit**: Review the trapdoor secret management
- **Production deployment**: Move to a real blockchain network

## Security Notes

🔐 **Critical**: The `LAMBDA_N_HEX` value in `.env` is the trapdoor secret. In production:
- Store it securely (HSM, key vault)
- Never commit it to version control
- Restrict access to authorized operators only
- Consider secret rotation strategies

The current setup is designed for MVP testing on Anvil. For production deployment, implement proper secret management, access controls, and monitoring.

## Architecture Summary

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   IoT Device    │───▶│   Gateway    │───▶│   Anvil     │
│                 │    │  (FastAPI)   │    │ (Registry)  │
│ • Ed25519/RSA   │    │ • Accumulator│    │ • Contract  │
│ • Signatures    │    │ • Trapdoors  │    │ • Events    │
│ • Witnesses     │    │ • SQLite DB  │    │ • State     │
└─────────────────┘    └──────────────┘    └─────────────┘
```

The gateway acts as the trusted accumulator manager, using trapdoor operations to efficiently add and remove devices while maintaining blockchain state consistency.
