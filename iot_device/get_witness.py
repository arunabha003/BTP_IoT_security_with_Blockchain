"""
Fetch current witness from the gateway and store it locally.

Usage:
  python get_witness.py [BASE_URL]
Defaults:
  BASE_URL = http://127.0.0.1:8000
"""

import sys
import requests
from state import get, update_state


def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

    device_id_hex = get("device_id_hex")
    if not device_id_hex:
        print("❌ No device_id_hex found. Enroll first: python enroll.py")
        sys.exit(1)

    resp = requests.get(f"{base_url}/witness/{device_id_hex}", timeout=10)

    if resp.status_code != 200:
        try:
            print(f"❌ Failed to fetch witness: {resp.json()}")
        except Exception:
            print(f"❌ Failed to fetch witness: HTTP {resp.status_code}")
        sys.exit(1)

    data = resp.json()
    update_state({"witness_hex": data["witnessHex"]})

    print("✅ Witness fetched and saved")
    print(f"   • status: {data['status']}")
    print(f"   • lastUpdated: {data['lastUpdated']}")
    print(f"   • witnessHex: {data['witnessHex'][:32]}...")


if __name__ == "__main__":
    main()


