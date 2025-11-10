"""
Check enrollment status after multi-sig approval.

This script checks if a pending enrollment has been completed
after multi-sig approval and updates the local state.

Usage:
  python check_enrollment.py [BASE_URL]
Defaults:
  BASE_URL = http://127.0.0.1:8000
"""

import sys
import requests
from state import get, update_state


def check_and_update_enrollment(base_url: str) -> dict:
    """
    Check if pending enrollment has been completed and update local state.
    
    Args:
        base_url: Gateway base URL
        
    Returns:
        dict with keys: enrolled (bool), message (str), status (str|None)
        
    Raises:
        Exception: If request fails
    """
    base_url = base_url.rstrip('/')
    
    # Check if there's a pending enrollment
    pending = get("pending_enrollment")
    device_id_hex = get("device_id_hex")
    
    if not pending:
        return {
            "enrolled": True,
            "message": "No pending enrollment",
            "status": get("status")
        }
    
    if not device_id_hex:
        raise Exception("No device ID found in state")

    # First, try to get all devices to find our id_prime if missing
    id_prime = get("id_prime")
    
    # Try to get device witness (this will work only if device is enrolled)
    resp = requests.get(f"{base_url}/witness/{device_id_hex}", timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        
        # Get id_prime from devices endpoint if we don't have it
        if not id_prime:
            devices_resp = requests.get(f"{base_url}/devices", timeout=10)
            if devices_resp.status_code == 200:
                devices_data = devices_resp.json()
                for device in devices_data.get('devices', []):
                    if device.get('deviceIdHex') == device_id_hex:
                        id_prime = device.get('idPrime')
                        break
        
        # Update state with enrollment completion
        update_data = {
            "pending_enrollment": False,
            "witness_hex": data.get("witnessHex"),
            "status": data.get("status")
        }
        
        # Add id_prime if we found it
        if id_prime:
            update_data["id_prime"] = id_prime
        
        update_state(update_data)
        
        return {
            "enrolled": True,
            "message": "Enrollment completed",
            "status": data.get("status"),
            "witnessHex": data.get("witnessHex")
        }
    
    elif resp.status_code == 400:
        return {
            "enrolled": False,
            "message": "Enrollment still pending multi-sig approval",
            "status": "pending"
        }
    
    else:
        raise Exception(f"Unexpected response: HTTP {resp.status_code}")


def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

    device_id_hex = get("device_id_hex")
    if device_id_hex:
        print(f"📡 Checking enrollment status for device: {device_id_hex[:16]}...")
    
    try:
        result = check_and_update_enrollment(base_url)
        
        if result["enrolled"]:
            print("✅ Enrollment completed!")
            print(f"   • Device Status: {result.get('status')}")
            if result.get('witnessHex'):
                print(f"   • Witness: {result['witnessHex'][:32]}...")
            print("\n✅ Local state updated - device ready to authenticate!")
            
            # Try to get the full system status
            status_resp = requests.get(f"{base_url}/status", timeout=10)
            if status_resp.status_code == 200:
                status_data = status_resp.json()
                print(f"   • Total Devices: {status_data.get('totalDevices')}")
                print(f"   • Active Devices: {status_data.get('activeDevices')}")
        else:
            print("⚠️  Enrollment still pending")
            print("💡 Multi-sig transaction may not be executed yet")
            print("   1. Check if transaction has enough signatures (3 required)")
            print("   2. Execute the transaction on the multi-sig page")
            print("   3. Run this script again after execution")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
