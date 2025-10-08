"""
Generate an Ed25519 keypair and store in device_state/state.json

Usage:
  python keygen.py
"""

import base64
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

from state import update_state, load_state, STATE_FILE


def main():
    # Generate Ed25519 keypair
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    # Serialize private key (raw bytes → base64)
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    private_b64 = base64.b64encode(private_bytes).decode()

    # Serialize public key (PEM)
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    update_state({
        "private_key": private_b64,
        "public_key_pem": public_pem,
        "key_type": "ed25519"
    })

    print("✅ Keypair generated and saved")
    print(f"📄 State file: {STATE_FILE}")


if __name__ == "__main__":
    main()


