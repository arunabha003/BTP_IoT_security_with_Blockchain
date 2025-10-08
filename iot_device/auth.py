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


def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

    required = ["device_id_hex", "id_prime", "witness_hex", "public_key_pem", "private_key"]
    missing = [k for k in required if get(k) is None]
    if missing:
        print(f"❌ Missing in state: {', '.join(missing)}")
        print("   Run: python keygen.py && python enroll.py")
        sys.exit(1)

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
            print(f"❌ Auth failed: {resp.json()}")
        except Exception:
            print(f"❌ Auth failed: HTTP {resp.status_code}")
        sys.exit(1)

    data = resp.json()
    print("✅ Authentication successful")

    if data.get("newWitnessHex"):
        update_state({"witness_hex": data["newWitnessHex"]})
        print("🔄 Witness updated from server response")


if __name__ == "__main__":
    main()


