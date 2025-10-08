"""
Enroll device with the Identity Gateway using stored public key.

Usage:
  python enroll.py [BASE_URL]
Defaults:
  BASE_URL = http://127.0.0.1:8000
"""

import sys
import requests
from state import get, update_state


def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

    public_key_pem = get("public_key_pem")
    if not public_key_pem:
        print("❌ No public key found. Run: python keygen.py")
        sys.exit(1)

    payload = {
        "publicKeyPEM": public_key_pem,
        "keyType": "ed25519"
    }

    resp = requests.post(f"{base_url}/enroll", json=payload, timeout=30)

    if resp.status_code != 201:
        try:
            print(f"❌ Enrollment failed: {resp.json()}")
        except Exception:
            print(f"❌ Enrollment failed: HTTP {resp.status_code}")
        sys.exit(1)

    data = resp.json()
    update_state({
        "device_id_hex": data["deviceIdHex"],
        "id_prime": data["idPrime"],
        "witness_hex": data["witnessHex"],
        "root_hex": data["rootHex"]
    })

    print("✅ Enrolled successfully")
    print(f"   • deviceIdHex: {data['deviceIdHex']}")
    print(f"   • idPrime: {data['idPrime']}")
    print(f"   • witnessHex: {data['witnessHex'][:32]}...")


if __name__ == "__main__":
    main()


