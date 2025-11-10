"""
Authenticate with the Identity Gateway using stored credentials.

Usage:
  python auth.py [BASE_URL]
Defaults:
  BASE_URL = http://127.0.0.1:8000
"""

import sys
import base64
import secrets
import requests
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

from state import get, update_state


def sign(private_key_b64: str, message: str) -> str:
    private_bytes = base64.b64decode(private_key_b64)
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
    sig = private_key.sign(message.encode())
    return base64.b64encode(sig).decode()


def authenticate_device(base_url: str) -> dict:
    """
    Authenticate device with gateway.
    
    Args:
        base_url: Gateway base URL
        
    Returns:
        dict with keys: success (bool), message (str), newWitnessHex (str|None)
        
    Raises:
        Exception: If state is invalid or request fails
    """
    base_url = base_url.rstrip('/')
    
    # Check if enrollment is pending
    pending = get("pending_enrollment")
    if pending:
        return {
            "success": False,
            "message": "Enrollment pending multi-sig approval",
            "safeTxHash": get('safe_tx_hash'),
            "deviceIdHex": get('device_id_hex')
        }

    required = ["device_id_hex", "id_prime", "witness_hex", "public_key_pem", "private_key"]
    missing = [k for k in required if get(k) is None]
    if missing:
        raise Exception(f"Missing required state fields: {', '.join(missing)}")

    nonce_hex = secrets.token_hex(16)
    signature_b64 = sign(get("private_key"), nonce_hex)

    payload = {
        "deviceIdHex": get("device_id_hex"),
        "idPrime": get("id_prime"),
        "witnessHex": get("witness_hex"),
        "signatureB64": signature_b64,
        "nonceHex": nonce_hex,
        "publicKeyPEM": get("public_key_pem"),
        "keyType": "ed25519"
    }

    resp = requests.post(f"{base_url}/auth", json=payload, timeout=15)

    if resp.status_code != 200:
        try:
            error_data = resp.json()
            return {
                "success": False,
                "message": error_data.get("detail", f"HTTP {resp.status_code}")
            }
        except Exception:
            return {
                "success": False,
                "message": f"HTTP {resp.status_code}"
            }

    data = resp.json()
    
    # Update witness if server sent new one
    new_witness = data.get("newWitnessHex")
    if new_witness:
        update_state({"witness_hex": new_witness})
    
    return {
        "success": True,
        "message": data.get("message", "Device authenticated"),
        "newWitnessHex": new_witness
    }


def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

    try:
        result = authenticate_device(base_url)
        
        if not result["success"]:
            if result.get("safeTxHash"):
                # Pending multi-sig
                print("⚠️  Enrollment is pending multi-sig approval")
                print(f"   • Safe TX Hash: {result['safeTxHash']}")
                print(f"   • Device ID: {result['deviceIdHex']}")
                print("\n💡 Next steps:")
                print("   1. Visit http://localhost:3000/multisig-approve")
                print("   2. Have 3 owners sign the transaction")
                print("   3. Execute the transaction")
                print("   4. Run: python check_enrollment.py")
                print("   5. Once enrolled, run this script again to authenticate")
            else:
                print(f"❌ Auth failed: {result['message']}")
            sys.exit(1)
        
        print(f"✅ {result['message']}")
        
        if result.get("newWitnessHex"):
            print("🔄 Witness updated from server response")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


