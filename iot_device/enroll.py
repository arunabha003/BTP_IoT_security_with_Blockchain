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

    # Handle multi-sig mode (202 Accepted)
    if resp.status_code == 202:
        data = resp.json()
        print("⚠️  Enrollment requires multi-sig approval")
        print(f"   • Status: {data.get('status')}")
        print(f"   • Message: {data.get('message')}")
        print(f"   • Safe TX Hash: {data.get('safeTxHash')}")
        print(f"   • Device ID: {data.get('device_id')}")
        print(f"   • ID Prime: {data.get('idPrime', 'N/A')[:50]}...")
        print(f"   • Required Signatures: {data.get('required_signatures')}")
        print(f"   • Approve at: {data.get('multisig_url')}")
        print("\n💡 Next steps:")
        print("   1. Visit the multi-sig approval page")
        print("   2. Have 3 owners sign the transaction")
        print("   3. Execute the transaction")
        print("   4. Device will be enrolled automatically")
        print("   5. You can authenticate after execution completes")
        
        # Store complete state including id_prime and witness for later use
        update_state({
            "pending_enrollment": True,
            "safe_tx_hash": data.get("safeTxHash"),
            "device_id_hex": data.get("device_id") or data.get("deviceIdHex"),
            "id_prime": data.get("idPrime"),
            "witness_hex": data.get("witnessHex")
        })
        
        print("\n✅ Device credentials stored locally")
        print("   You can authenticate once the transaction is executed")
        sys.exit(0)
    
    # Unexpected response code
    try:
        print(f"❌ Enrollment failed: {resp.json()}")
    except Exception:
        print(f"❌ Enrollment failed: HTTP {resp.status_code}")
    sys.exit(1)


if __name__ == "__main__":
    main()


