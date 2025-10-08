"""
Minimal shared state handler for IoT device scripts.

Stores and retrieves:
- private_key (base64)
- public_key_pem (PEM string)
- device_id_hex (hex string)
- id_prime (int)
- witness_hex (hex string)
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional


STATE_DIR = Path(__file__).parent / "device_state"
STATE_DIR.mkdir(exist_ok=True)
STATE_FILE = STATE_DIR / "state.json"


def load_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(data: Dict[str, Any]) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def update_state(partial: Dict[str, Any]) -> Dict[str, Any]:
    data = load_state()
    data.update(partial)
    save_state(data)
    return data


def get(key: str, default: Optional[Any] = None) -> Any:
    return load_state().get(key, default)


def clear_state() -> None:
    if STATE_FILE.exists():
        STATE_FILE.unlink()


