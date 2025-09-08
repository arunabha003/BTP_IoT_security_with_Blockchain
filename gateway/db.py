"""
Database Layer for IoT Identity Gateway

SQLite database for storing device information, accumulator state,
and metadata for the RSA accumulator system.
"""

import sqlite3
import logging
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database for IoT identity system."""
    
    def __init__(self, db_path: str = "gateway.db"):
        self.db_path = Path(db_path)
        self.init_db()
    
    def init_db(self) -> None:
        """Initialize database with required tables."""
        logger.info(f"Initializing database: {self.db_path}")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create devices table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    device_id BLOB PRIMARY KEY,
                    pubkey_pem TEXT NOT NULL,
                    id_prime TEXT NOT NULL,
                    witness TEXT NOT NULL,
                    key_type TEXT NOT NULL DEFAULT 'ed25519',
                    status INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create metadata table for system state
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_devices_key_type ON devices(key_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_meta_key ON meta(key)")
            
            conn.commit()
        
        logger.info("Database initialized successfully")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        try:
            yield conn
        finally:
            conn.close()
    
    # Metadata operations
    
    def get_meta(self, key: str) -> Optional[str]:
        """Get metadata value by key."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM meta WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None
    
    def set_meta(self, key: str, value: str) -> None:
        """Set metadata key-value pair."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO meta (key, value, updated_at) 
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
            conn.commit()
    
    def get_all_meta(self) -> Dict[str, str]:
        """Get all metadata as dictionary."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM meta")
            return {row[0]: row[1] for row in cursor.fetchall()}
    
    # Device operations
    
    def insert_device(
        self, 
        device_id: bytes, 
        pubkey_pem: str, 
        id_prime: int, 
        witness: str,
        key_type: str = "ed25519",
        status: int = 1
    ) -> None:
        """Insert new device into database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO devices 
                (device_id, pubkey_pem, id_prime, witness, key_type, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (device_id, pubkey_pem, str(id_prime), witness, key_type, status))
            conn.commit()
        
        logger.info(f"Inserted device: {device_id.hex()}")
    
    def get_device(self, device_id: bytes) -> Optional[Dict[str, Any]]:
        """Get device by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT device_id, pubkey_pem, id_prime, witness, key_type, status, 
                       created_at, updated_at 
                FROM devices WHERE device_id = ?
            """, (device_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'device_id': row[0],
                    'pubkey_pem': row[1],
                    'id_prime': int(row[2]),
                    'witness': row[3],
                    'key_type': row[4],
                    'status': row[5],
                    'created_at': row[6],
                    'updated_at': row[7]
                }
            return None
    
    def update_device_witness(self, device_id: bytes, new_witness: str) -> bool:
        """Update device witness."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE devices 
                SET witness = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE device_id = ?
            """, (new_witness, device_id))
            conn.commit()
            
            updated = cursor.rowcount > 0
            if updated:
                logger.info(f"Updated witness for device: {device_id.hex()}")
            return updated
    
    def update_device_status(self, device_id: bytes, status: int) -> bool:
        """Update device status."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE devices 
                SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE device_id = ?
            """, (status, device_id))
            conn.commit()
            
            updated = cursor.rowcount > 0
            if updated:
                logger.info(f"Updated status for device {device_id.hex()} to {status}")
            return updated
    
    def get_all_devices(self, status: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all devices, optionally filtered by status."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if status is not None:
                cursor.execute("""
                    SELECT device_id, pubkey_pem, id_prime, witness, key_type, status, 
                           created_at, updated_at 
                    FROM devices WHERE status = ? 
                    ORDER BY created_at
                """, (status,))
            else:
                cursor.execute("""
                    SELECT device_id, pubkey_pem, id_prime, witness, key_type, status, 
                           created_at, updated_at 
                    FROM devices 
                    ORDER BY created_at
                """)
            
            devices = []
            for row in cursor.fetchall():
                devices.append({
                    'device_id': row[0],
                    'pubkey_pem': row[1],
                    'id_prime': row[2],
                    'witness': row[3],
                    'key_type': row[4],
                    'status': row[5],
                    'created_at': row[6],
                    'updated_at': row[7]
                })
            
            return devices
    
    def get_active_devices(self) -> List[Dict[str, Any]]:
        """Get all active devices (status = 1)."""
        return self.get_all_devices(status=1)
    
    def get_active_primes(self) -> List[int]:
        """Get list of id_primes for all active devices."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id_prime FROM devices WHERE status = 1")
            return [int(row[0]) for row in cursor.fetchall()]
    
    def device_exists(self, device_id: bytes) -> bool:
        """Check if device exists in database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM devices WHERE device_id = ? LIMIT 1", (device_id,))
            return cursor.fetchone() is not None
    
    def get_device_count(self, status: Optional[int] = None) -> int:
        """Get count of devices, optionally filtered by status."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if status is not None:
                cursor.execute("SELECT COUNT(*) FROM devices WHERE status = ?", (status,))
            else:
                cursor.execute("SELECT COUNT(*) FROM devices")
            
            return cursor.fetchone()[0]
    
    # Utility methods
    
    def clear_all_devices(self) -> int:
        """Clear all devices (for testing). Returns count of deleted devices."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM devices")
            deleted_count = cursor.rowcount
            conn.commit()
        
        logger.warning(f"Cleared {deleted_count} devices from database")
        return deleted_count
    
    def clear_all_meta(self) -> int:
        """Clear all metadata (for testing). Returns count of deleted entries."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM meta")
            deleted_count = cursor.rowcount
            conn.commit()
        
        logger.warning(f"Cleared {deleted_count} metadata entries from database")
        return deleted_count
    
    def get_db_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats = {
            'total_devices': self.get_device_count(),
            'active_devices': self.get_device_count(status=1),
            'revoked_devices': self.get_device_count(status=2),
            'meta_entries': len(self.get_all_meta()),
            'db_path': str(self.db_path),
            'db_exists': self.db_path.exists(),
            'db_size_bytes': self.db_path.stat().st_size if self.db_path.exists() else 0
        }
        
        # Add key type distribution
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key_type, COUNT(*) FROM devices GROUP BY key_type")
            stats['key_type_distribution'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        return stats


# Device status constants
class DeviceStatus:
    ACTIVE = 1
    REVOKED = 2


# Metadata keys constants
class MetaKeys:
    ROOT_HEX = "root_hex"
    VERSION = "version"
    N_HEX = "N_hex"
    G_HEX = "g_hex"
    LAMBDA_N_HEX = "lambda_n_hex"
    LAST_SYNC = "last_sync"


def main():
    """Test database operations."""
    print("Testing Database Operations")
    print("=" * 40)
    
    # Create test database
    db = DatabaseManager("test_gateway.db")
    
    # Test metadata operations
    db.set_meta(MetaKeys.ROOT_HEX, "0x123456")
    db.set_meta(MetaKeys.VERSION, "1")
    
    print(f"Root hex: {db.get_meta(MetaKeys.ROOT_HEX)}")
    print(f"Version: {db.get_meta(MetaKeys.VERSION)}")
    
    # Test device operations
    test_device_id = b"test_device_12345678901234567890"
    test_pubkey = "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAw...\n-----END PUBLIC KEY-----"
    
    db.insert_device(
        device_id=test_device_id,
        pubkey_pem=test_pubkey,
        id_prime=12345,
        witness="0xabcdef",
        key_type="ed25519"
    )
    
    device = db.get_device(test_device_id)
    print(f"Retrieved device: {device['device_id'].hex() if device else None}")
    
    # Test stats
    stats = db.get_db_stats()
    print(f"Database stats: {stats}")
    
    # Clean up
    import os
    if os.path.exists("test_gateway.db"):
        os.remove("test_gateway.db")
    print("Test complete")


if __name__ == "__main__":
    main()
