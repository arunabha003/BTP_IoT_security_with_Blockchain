# RSA Accumulator Server - Complete API Guide

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- FastAPI dependencies installed
- Accum package accessible

### Start the Server

```bash
# Navigate to server directory
cd accum_server

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Start the server
python main.py

# Server will be available at:
# http://localhost:8000
# API Documentation: http://localhost:8000/docs
# Alternative Docs: http://localhost:8000/redoc
```

### Verify Server is Running

```bash
# Basic connectivity test
curl http://localhost:8000/

# Expected response:
{
  "message": "RSA Accumulator Server",
  "status": "running",
  "version": "1.0.0",
  "endpoints": [...]
}
```

---

## 📋 Complete API Reference

### 🔍 Server Status

#### Get Server Information
```bash
curl http://localhost:8000/
```

#### Get Detailed Status
```bash
curl http://localhost:8000/status
```

**Response:**
```json
{
  "status": "operational",
  "current_accumulator": 4,
  "total_primes": 0,
  "total_devices": 0,
  "modulus_bits": 2048
}
```

---

### 🔑 Key Generation

#### Generate Ed25519 Key Pair
```bash
curl -X POST "http://localhost:8000/key/generate" \
  -H "Content-Type: application/json" \
  -d '{"key_type": "ed25519"}'
```

**Response:**
```json
{
  "private_key": "base64_encoded_private_key",
  "public_key": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n",
  "key_type": "ed25519",
  "key_info": {
    "key_type": "ed25519",
    "key_size": 256,
    "algorithm": "Ed25519",
    "security_level": "128-bit equivalent"
  }
}
```

#### Generate RSA Key Pair
```bash
curl -X POST "http://localhost:8000/key/generate" \
  -H "Content-Type: application/json" \
  -d '{"key_type": "rsa"}'
```

**Response:**
```json
{
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "public_key": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n",
  "key_type": "rsa",
  "key_info": {
    "key_type": "rsa",
    "key_size": 2048,
    "algorithm": "RSA",
    "security_level": "1024-bit equivalent"
  }
}
```

#### Invalid Key Type (Error Example)
```bash
curl -X POST "http://localhost:8000/key/generate" \
  -H "Content-Type: application/json" \
  -d '{"key_type": "invalid"}'
```

**Response (400 Bad Request):**
```json
{
  "detail": "key_type must be 'ed25519' or 'rsa'"
}
```

#### Get Key Information
```bash
curl -X POST "http://localhost:8000/key/info?public_key_pem=-----BEGIN%20PUBLIC%20KEY-----%0A..." \
  -H "Content-Type: application/json"
```

---

### 📱 Device Management

#### Generate Multiple Devices (Ed25519)
```bash
curl -X POST "http://localhost:8000/devices/generate" \
  -H "Content-Type: application/json" \
  -d '{"key_type": "ed25519", "num_devices": 5}'
```

#### Generate Multiple Devices (RSA)
```bash
curl -X POST "http://localhost:8000/devices/generate" \
  -H "Content-Type: application/json" \
  -d '{"key_type": "rsa", "num_devices": 3}'
```

**Response:**
```json
{
  "devices": {
    "sensor_000": {
      "device_id": "sensor_000",
      "private_key_base64": "...",
      "public_key_pem": "...",
      "key_type": "ed25519",
      "status": "generated"
    },
    ...
  },
  "count": 5
}
```

#### Get All Devices
```bash
curl http://localhost:8000/devices
```

#### Save Devices to File
```bash
curl -X POST "http://localhost:8000/devices/save?filename=my_devices.json"
```

**Response:**
```json
{
  "filename": "my_devices.json",
  "device_count": 5,
  "success": true
}
```

#### Load Devices from File
```bash
curl "http://localhost:8000/devices/load?filename=my_devices.json"
```

#### Clear All Devices
```bash
curl -X DELETE http://localhost:8000/devices
```

**Response:**
```json
{
  "message": "All device data cleared",
  "success": true
}
```

---

### 🔢 Hash-to-Prime Conversion

#### Convert Data to Prime
```bash
curl -X POST "http://localhost:8000/hash-to-prime" \
  -H "Content-Type: application/json" \
  -d '{"data": "SGVsbG8gV29ybGQ=", "max_attempts": 10000}'
```

**Note:** Data must be base64 encoded

**Response:**
```json
{
  "prime": 1234567890123456789012345678901234567890,
  "input_data_length": 11,
  "max_attempts": 10000,
  "success": true
}
```

#### Example with Device Key
```bash
# First generate a key
KEY_RESPONSE=$(curl -s -X POST "http://localhost:8000/key/generate" \
  -H "Content-Type: application/json" \
  -d '{"key_type": "ed25519"}')

# Extract public key and convert to prime
PUBLIC_KEY=$(echo $KEY_RESPONSE | jq -r '.public_key' | base64)
curl -X POST "http://localhost:8000/hash-to-prime" \
  -H "Content-Type: application/json" \
  -d "{\"data\": \"$PUBLIC_KEY\", \"max_attempts\": 10000}"
```

---

### 🔐 Digital Signatures

#### Generate Signature (Ed25519)
```bash
# First get a private key
PRIVATE_KEY=$(curl -s -X POST "http://localhost:8000/key/generate" \
  -H "Content-Type: application/json" -d '{"key_type": "ed25519"}' | jq -r '.private_key')

# Generate signature
curl -X POST "http://localhost:8000/signature/generate" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Hello IoT Device\", \"private_key_data\": \"$PRIVATE_KEY\", \"key_type\": \"ed25519\"}"
```

**Response:**
```json
{
  "signature": "base64_encoded_signature",
  "message": "Hello IoT Device",
  "key_type": "ed25519",
  "success": true
}
```

#### Generate Signature (RSA)
```bash
# Get RSA private key
PRIVATE_KEY=$(curl -s -X POST "http://localhost:8000/key/generate" \
  -H "Content-Type: application/json" -d '{"key_type": "rsa"}' | jq -r '.private_key')

# Generate signature
curl -X POST "http://localhost:8000/signature/generate" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Hello IoT Device\", \"private_key_data\": \"$PRIVATE_KEY\", \"key_type\": \"rsa\"}"
```

#### Verify Signature
```bash
# Get both keys
KEY_DATA=$(curl -s -X POST "http://localhost:8000/key/generate" \
  -H "Content-Type: application/json" -d '{"key_type": "ed25519"}')

PRIVATE_KEY=$(echo $KEY_DATA | jq -r '.private_key')
PUBLIC_KEY=$(echo $KEY_DATA | jq -sRr '.public_key')

# Generate signature
SIG_DATA=$(curl -s -X POST "http://localhost:8000/signature/generate" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"test message\", \"private_key_data\": \"$PRIVATE_KEY\", \"key_type\": \"ed25519\"}")

SIGNATURE=$(echo $SIG_DATA | jq -r '.signature')

# Verify signature (Note: May have JSON parsing issues with PEM keys)
curl -X POST "http://localhost:8000/signature/verify" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"test message\", \"signature\": \"$SIGNATURE\", \"public_key_pem\": \"$PUBLIC_KEY\", \"key_type\": \"ed25519\"}"
```

---

### 🏗️ RSA Accumulator Operations

#### Build Accumulator from Primes
```bash
# Generate some primes first
PRIME1=$(curl -s -X POST "http://localhost:8000/hash-to-prime" \
  -H "Content-Type: application/json" \
  -d '{"data": "ZGF0YV8x", "max_attempts": 10000}' | jq -r '.prime')

PRIME2=$(curl -s -X POST "http://localhost:8000/hash-to-prime" \
  -H "Content-Type: application/json" \
  -d '{"data": "ZGF0YV8y", "max_attempts": 10000}' | jq -r '.prime')

# Build accumulator
curl -X POST "http://localhost:8000/accumulator/recompute" \
  -H "Content-Type: application/json" \
  -d "{\"primes\": [$PRIME1, $PRIME2]}"
```

**Response:**
```json
{
  "result": "large_accumulator_value",
  "operation": "recompute_root",
  "success": true
}
```

#### Add Member to Accumulator
```bash
# Get current accumulator value
CURRENT_ACC=$(curl -s http://localhost:8000/status | jq -r '.current_accumulator')

# Generate new prime
NEW_PRIME=$(curl -s -X POST "http://localhost:8000/hash-to-prime" \
  -H "Content-Type: application/json" \
  -d '{"data": "bmV3X2RhdGE=", "max_attempts": 10000}' | jq -r '.prime')

# Add to accumulator
curl -X POST "http://localhost:8000/accumulator/add" \
  -H "Content-Type: application/json" \
  -d "{\"current_accumulator\": $CURRENT_ACC, \"prime\": $NEW_PRIME}"
```

#### Generate Membership Witness
```bash
# Using the primes from above
curl -X POST "http://localhost:8000/accumulator/witness" \
  -H "Content-Type: application/json" \
  -d "{\"primes\": [$PRIME1, $PRIME2], \"target_prime\": $PRIME1}"
```

**Response:**
```json
{
  "witness": "large_witness_value",
  "target_prime": 12345,
  "primes_count": 2,
  "success": true
}
```

#### Verify Membership Proof
```bash
# Generate witness for PRIME1
WITNESS=$(curl -s -X POST "http://localhost:8000/accumulator/witness" \
  -H "Content-Type: application/json" \
  -d "{\"primes\": [$PRIME1, $PRIME2], \"target_prime\": $PRIME1}" | jq -r '.witness')

# Get accumulator value
ACCUMULATOR=$(curl -s http://localhost:8000/status | jq -r '.current_accumulator')

# Verify membership
curl -X POST "http://localhost:8000/accumulator/verify" \
  -H "Content-Type: application/json" \
  -d "{\"witness\": \"$WITNESS\", \"prime\": $PRIME1, \"accumulator\": \"$ACCUMULATOR\"}"
```

**Response:**
```json
{
  "is_valid": true,
  "prime": 12345,
  "accumulator": "accumulator_value",
  "success": true
}
```

#### Refresh Witness After Changes
```bash
# After adding a new prime, refresh existing witnesses
curl -X POST "http://localhost:8000/accumulator/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"target_prime\": $PRIME1, \"primes\": [$PRIME1, $PRIME2, $NEW_PRIME]}"
```

**Response:**
```json
{
  "new_witness": "updated_witness_value",
  "target_prime": 12345,
  "primes_count": 3,
  "success": true
}
```

---

### 🗝️ Trapdoor Revocation Operations

#### Remove Single Member (Trapdoor with p,q)
```bash
curl -X POST "http://localhost:8000/accumulator/trapdoor/remove" \
  -H "Content-Type: application/json" \
  -d "{\"current_accumulator\": $CURRENT_ACC, \"prime_to_remove\": $PRIME_TO_REMOVE}"
```

**Response:**
```json
{
  "new_accumulator": "updated_accumulator_value",
  "removed_prime": 12345,
  "operation": "trapdoor_remove_member",
  "success": true
}
```

#### Remove Multiple Members (Trapdoor with p,q)
```bash
curl -X POST "http://localhost:8000/accumulator/trapdoor/batch-remove" \
  -H "Content-Type: application/json" \
  -d "{\"current_accumulator\": $CURRENT_ACC, \"primes_to_remove\": [$PRIME1, $PRIME2]}"
```

**Response:**
```json
{
  "new_accumulator": "updated_accumulator_value",
  "removed_primes": [12345, 67890],
  "removed_count": 2,
  "operation": "trapdoor_batch_remove_members",
  "success": true
}
```

#### Remove Single Member (Trapdoor with lambda_n)
```bash
curl -X POST "http://localhost:8000/accumulator/trapdoor/remove-lambda" \
  -H "Content-Type: application/json" \
  -d "{\"current_accumulator\": $CURRENT_ACC, \"prime_to_remove\": $PRIME_TO_REMOVE}"
```

**Response:**
```json
{
  "new_accumulator": "updated_accumulator_value",
  "removed_prime": 12345,
  "lambda_n": "lambda_value",
  "operation": "trapdoor_remove_member_with_lambda",
  "success": true
}
```

#### Remove Multiple Members (Trapdoor with lambda_n)
```bash
curl -X POST "http://localhost:8000/accumulator/trapdoor/batch-remove-lambda" \
  -H "Content-Type: application/json" \
  -d "{\"current_accumulator\": $CURRENT_ACC, \"primes_to_remove\": [$PRIME1, $PRIME2]}"
```

**Response:**
```json
{
  "new_accumulator": "updated_accumulator_value",
  "removed_primes": [12345, 67890],
  "removed_count": 2,
  "lambda_n": "lambda_value",
  "operation": "trapdoor_batch_remove_members_with_lambda",
  "success": true
}
```

#### Verify Trapdoor Removal
```bash
curl -X POST "http://localhost:8000/accumulator/trapdoor/verify-removal" \
  -H "Content-Type: application/json" \
  -d "{\"old_accumulator\": $OLD_ACC, \"new_accumulator\": $NEW_ACC, \"removed_prime\": $REMOVED_PRIME}"
```

**Response:**
```json
{
  "is_valid": true,
  "old_accumulator": "old_value",
  "new_accumulator": "new_value",
  "removed_prime": 12345,
  "verification": "trapdoor_removal",
  "success": true
}
```

---

## 🔄 Complete Workflow Examples

### IoT Device Lifecycle Demo

```bash
#!/bin/bash
# Complete IoT device lifecycle demonstration

echo "🚀 Starting IoT Device Lifecycle Demo"
echo "======================================"

# 1. Check server status
echo "1. Checking server status..."
curl -s http://localhost:8000/status | jq .

# 2. Generate IoT devices
echo "2. Generating 3 Ed25519 IoT devices..."
curl -s -X POST "http://localhost:8000/devices/generate" \
  -H "Content-Type: application/json" \
  -d '{"key_type": "ed25519", "num_devices": 3}' | jq '.count'

# 3. Convert device keys to primes
echo "3. Converting device keys to primes..."
DEVICES=$(curl -s http://localhost:8000/devices)
PRIMES=()

for device_id in $(echo $DEVICES | jq -r '.devices | keys[]'); do
    # Extract public key
    PUBLIC_KEY=$(echo $DEVICES | jq -r ".devices[\"$device_id\"].public_key_pem")
    # Convert to base64 for API
    ENCODED_KEY=$(echo -n "$PUBLIC_KEY" | base64)
    # Generate prime
    PRIME=$(curl -s -X POST "http://localhost:8000/hash-to-prime" \
      -H "Content-Type: application/json" \
      -d "{\"data\": \"$ENCODED_KEY\", \"max_attempts\": 10000}" | jq -r '.prime')
    PRIMES+=($PRIME)
    echo "   $device_id -> Prime: $PRIME"
done

# 4. Build accumulator
echo "4. Building RSA accumulator..."
PRIMES_JSON=$(printf '%s\n' "${PRIMES[@]}" | jq -R . | jq -s .)
ACCUMULATOR=$(curl -s -X POST "http://localhost:8000/accumulator/recompute" \
  -H "Content-Type: application/json" \
  -d "{\"primes\": $PRIMES_JSON}" | jq -r '.result')
echo "   Accumulator built: $ACCUMULATOR"

# 5. Generate membership witnesses
echo "5. Generating membership witnesses..."
for i in "${!PRIMES[@]}"; do
    PRIME=${PRIMES[$i]}
    WITNESS=$(curl -s -X POST "http://localhost:8000/accumulator/witness" \
      -H "Content-Type: application/json" \
      -d "{\"primes\": $PRIMES_JSON, \"target_prime\": $PRIME}" | jq -r '.witness')
    echo "   Witness for prime $i: generated"

    # 6. Verify membership
    VERIFICATION=$(curl -s -X POST "http://localhost:8000/accumulator/verify" \
      -H "Content-Type: application/json" \
      -d "{\"witness\": \"$WITNESS\", \"prime\": $PRIME, \"accumulator\": \"$ACCUMULATOR\"}" | jq -r '.is_valid')
    echo "   Membership verification for prime $i: $VERIFICATION"
done

# 7. Save device data
echo "7. Saving device data..."
curl -s -X POST "http://localhost:8000/devices/save?filename=demo_devices.json" | jq '.success'

echo "🎉 IoT Device Lifecycle Demo Complete!"
```

### Device Authentication Flow

```bash
#!/bin/bash
# Device authentication demonstration

echo "🔐 Device Authentication Flow"
echo "============================"

# Generate device key
echo "1. Generating device key..."
KEY_DATA=$(curl -s -X POST "http://localhost:8000/key/generate" \
  -H "Content-Type: application/json" \
  -d '{"key_type": "ed25519"}')

PRIVATE_KEY=$(echo $KEY_DATA | jq -r '.private_key')
PUBLIC_KEY=$(echo $KEY_DATA | jq -r '.public_key')

# Generate authentication challenge
CHALLENGE="auth-challenge-$(date +%s)"

# Generate signature
echo "2. Generating authentication signature..."
SIG_DATA=$(curl -s -X POST "http://localhost:8000/signature/generate" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"$CHALLENGE\", \"private_key_data\": \"$PRIVATE_KEY\", \"key_type\": \"ed25519\"}")

SIGNATURE=$(echo $SIG_DATA | jq -r '.signature')
echo "   Signature generated"

# Verify signature (Note: JSON parsing may fail with PEM keys)
echo "3. Verifying authentication signature..."
# This may fail due to PEM key JSON parsing issues
# In production, use base64 encoded keys

echo "   Challenge: $CHALLENGE"
echo "   Signature: ${SIGNATURE:0:50}..."
echo "🔐 Authentication flow complete!"
```

---

## 📊 Response Codes

### Success Responses
- **200 OK**: Request successful
- **201 Created**: Resource created successfully

### Error Responses
- **400 Bad Request**: Invalid request data or parameters
- **422 Unprocessable Content**: JSON parsing error
- **500 Internal Server Error**: Server-side error

### Common Error Messages
- `"key_type must be 'ed25519' or 'rsa'"` - Invalid key type specified
- `"Could not find prime within max_attempts"` - Hash-to-prime conversion failed
- `"JSON decode error"` - Invalid JSON in request body

---

## 🔧 Troubleshooting

### Server Won't Start
```bash
# Check if port 8000 is available
lsof -i :8000

# Kill any existing processes
kill -9 $(lsof -t -i :8000)

# Try starting with different port
PORT=8080 python main.py
```

### Import Errors
```bash
# Check if accum package is accessible
cd ../accum
python3 -c "from rsa_params import load_params; print('OK')"

# Fix Python path issues
export PYTHONPATH=$PYTHONPATH:$(pwd)/../accum
```

### Large Response Issues
```bash
# For large accumulator values, use jq to format output
curl -s "http://localhost:8000/status" | jq '.'
```

### JSON Parsing Issues with Keys
```bash
# Convert PEM to base64 for API calls
PEM_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n"
B64_KEY=$(echo -n "$PEM_KEY" | base64)
curl -X POST "http://localhost:8000/hash-to-prime" \
  -H "Content-Type: application/json" \
  -d "{\"data\": \"$B64_KEY\"}"
```

---

## 🚀 Production Deployment

### Using Docker
```bash
# Create Dockerfile
cat > Dockerfile << EOF
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Build and run
docker build -t accum-server .
docker run -p 8000:8000 accum-server
```

### Environment Variables
```bash
# Set custom host/port
export HOST=0.0.0.0
export PORT=8080
uvicorn main:app --host $HOST --port $PORT

# Production settings
export WORKERS=4
uvicorn main:app --workers $WORKERS --host 0.0.0.0 --port 8000
```

---

## 📚 Additional Resources

- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json
- **Health Check**: http://localhost:8000/status

---

## 🎯 Quick Reference

```bash
# Start server
python main.py

# Generate devices
curl -X POST "http://localhost:8000/devices/generate" -H "Content-Type: application/json" -d '{"key_type": "ed25519", "num_devices": 5}'

# Build accumulator
curl -X POST "http://localhost:8000/accumulator/recompute" -H "Content-Type: application/json" -d '{"primes": [prime1, prime2]}'

# Generate witness
curl -X POST "http://localhost:8000/accumulator/witness" -H "Content-Type: application/json" -d '{"primes": [p1, p2], "target_prime": p1}'

# Verify membership
curl -X POST "http://localhost:8000/accumulator/verify" -H "Content-Type: application/json" -d '{"witness": w, "prime": p, "accumulator": a}'

# Hash to prime
curl -X POST "http://localhost:8000/hash-to-prime" -H "Content-Type: application/json" -d '{"data": "SGVsbG8=", "max_attempts": 10000}'

# Trapdoor revocation
curl -X POST "http://localhost:8000/accumulator/trapdoor/remove" -H "Content-Type: application/json" -d '{"current_accumulator": 4, "prime_to_remove": 12345}'

curl -X POST "http://localhost:8000/accumulator/trapdoor/batch-remove" -H "Content-Type: application/json" -d '{"current_accumulator": 4, "primes_to_remove": [12345, 67890]}'

# Save/load devices
curl -X POST "http://localhost:8000/devices/save?filename=devices.json"
curl "http://localhost:8000/devices/load?filename=devices.json"
```

---

## 📈 Complete Endpoint Summary

### Server Management (2 endpoints)
- `GET /` - Root endpoint with API overview
- `GET /status` - Server status and accumulator state

### Key Management (2 endpoints)
- `POST /key/generate` - Generate Ed25519/RSA key pairs
- `POST /key/info` - Get key information and metadata

### Accumulator Operations (11 endpoints)
- `POST /accumulator/add` - Add member to accumulator
- `POST /accumulator/witness` - Generate membership witness
- `POST /accumulator/verify` - Verify membership proof
- `POST /accumulator/refresh` - Refresh witness after changes
- `POST /accumulator/recompute` - Recompute accumulator root
- `POST /accumulator/trapdoor/remove` - Remove member via trapdoor (p,q)
- `POST /accumulator/trapdoor/batch-remove` - Batch remove via trapdoor (p,q)
- `POST /accumulator/trapdoor/remove-lambda` - Remove member via trapdoor (lambda_n)
- `POST /accumulator/trapdoor/batch-remove-lambda` - Batch remove via trapdoor (lambda_n)
- `POST /accumulator/trapdoor/verify-removal` - Verify trapdoor removal

### Cryptographic Utilities (3 endpoints)
- `POST /hash-to-prime` - Convert data to prime numbers
- `POST /signature/generate` - Generate digital signatures
- `POST /signature/verify` - Verify digital signatures

### Device Management (3 endpoints)
- `POST /devices/generate` - Generate test IoT devices
- `GET /devices` - Get all registered devices
- `DELETE /devices` - Clear all device data
- `POST /devices/save` - Save devices to JSON file
- `GET /devices/load` - Load devices from JSON file

**Total: 21 endpoints** ✅

---

**🎉 Happy coding with the RSA Accumulator Server!**
