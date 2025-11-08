"""
Supabase Database Layer for IoT Identity Gateway

PostgreSQL database via Supabase for storing device information, 
accumulator state, and metadata for the RSA accumulator system.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from supabase import create_client, Client
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SupabaseDatabaseManager:
    """Manages Supabase PostgreSQL database for IoT identity system."""
    
    def __init__(self, supabase_url: str, supabase_key: str):
        """
        Initialize Supabase client.
        
        Args:
            supabase_url: Your Supabase project URL
            supabase_key: Your Supabase anon/service role key
        """
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        
        try:
            self.client: Client = create_client(supabase_url, supabase_key)
            logger.info(f"Connected to Supabase: {supabase_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            raise
    
    # Metadata operations
    
    def get_meta(self, key: str) -> Optional[str]:
        """Get metadata value by key."""
        try:
            result = self.client.table('meta').select('value').eq('key', key).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]['value']
            return None
        except Exception as e:
            logger.error(f"Error getting meta key '{key}': {e}")
            return None
    
    def set_meta(self, key: str, value: str) -> None:
        """Set metadata key-value pair (upsert)."""
        try:
            # Upsert operation
            self.client.table('meta').upsert({
                'key': key,
                'value': value,
                'updated_at': datetime.utcnow().isoformat()
            }).execute()
            logger.info(f"Set meta: {key}")
        except Exception as e:
            logger.error(f"Error setting meta key '{key}': {e}")
            raise
    
    def get_all_meta(self) -> Dict[str, str]:
        """Get all metadata as dictionary."""
        try:
            result = self.client.table('meta').select('key, value').execute()
            return {row['key']: row['value'] for row in result.data}
        except Exception as e:
            logger.error(f"Error getting all meta: {e}")
            return {}
    
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
        try:
            # Convert device_id bytes to hex string for PostgreSQL storage
            device_id_hex = device_id.hex()
            
            self.client.table('devices').insert({
                'device_id': device_id_hex,
                'pubkey_pem': pubkey_pem,
                'id_prime': str(id_prime),  # Store as text to handle large integers
                'witness': witness,
                'key_type': key_type,
                'status': status
            }).execute()
            
            logger.info(f"Inserted device: {device_id_hex}")
        except Exception as e:
            logger.error(f"Error inserting device: {e}")
            raise
    
    def get_device(self, device_id: bytes) -> Optional[Dict[str, Any]]:
        """Get device by ID."""
        try:
            device_id_hex = device_id.hex()
            result = self.client.table('devices').select('*').eq('device_id', device_id_hex).execute()
            
            if result.data and len(result.data) > 0:
                row = result.data[0]
                return {
                    'device_id': bytes.fromhex(row['device_id']),
                    'pubkey_pem': row['pubkey_pem'],
                    'id_prime': int(row['id_prime']),
                    'witness': row['witness'],
                    'key_type': row['key_type'],
                    'status': row['status'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
            return None
        except Exception as e:
            logger.error(f"Error getting device: {e}")
            return None
    
    def update_device_witness(self, device_id: bytes, new_witness: str) -> bool:
        """Update device witness."""
        try:
            device_id_hex = device_id.hex()
            result = self.client.table('devices').update({
                'witness': new_witness,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('device_id', device_id_hex).execute()
            
            updated = len(result.data) > 0
            if updated:
                logger.info(f"Updated witness for device: {device_id_hex}")
            return updated
        except Exception as e:
            logger.error(f"Error updating device witness: {e}")
            return False
    
    def update_device_status(self, device_id: bytes, status: int) -> bool:
        """Update device status."""
        try:
            device_id_hex = device_id.hex()
            result = self.client.table('devices').update({
                'status': status,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('device_id', device_id_hex).execute()
            
            updated = len(result.data) > 0
            if updated:
                logger.info(f"Updated status for device {device_id_hex} to {status}")
            return updated
        except Exception as e:
            logger.error(f"Error updating device status: {e}")
            return False
    
    def get_all_devices(self, status: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all devices, optionally filtered by status."""
        try:
            query = self.client.table('devices').select('*')
            
            if status is not None:
                query = query.eq('status', status)
            
            result = query.order('created_at').execute()
            
            devices = []
            for row in result.data:
                devices.append({
                    'device_id': bytes.fromhex(row['device_id']),
                    'pubkey_pem': row['pubkey_pem'],
                    'id_prime': int(row['id_prime']),
                    'witness': row['witness'],
                    'key_type': row['key_type'],
                    'status': row['status'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                })
            
            return devices
        except Exception as e:
            logger.error(f"Error getting all devices: {e}")
            return []
    
    def get_active_devices(self) -> List[Dict[str, Any]]:
        """Get all active devices (status = 1)."""
        return self.get_all_devices(status=1)
    
    def get_active_primes(self) -> List[int]:
        """Get list of id_primes for all active devices."""
        try:
            result = self.client.table('devices').select('id_prime').eq('status', 1).execute()
            return [int(row['id_prime']) for row in result.data]
        except Exception as e:
            logger.error(f"Error getting active primes: {e}")
            return []
    
    def device_exists(self, device_id: bytes) -> bool:
        """Check if device exists in database."""
        try:
            device_id_hex = device_id.hex()
            result = self.client.table('devices').select('device_id').eq('device_id', device_id_hex).limit(1).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error checking device existence: {e}")
            return False
    
    def get_device_count(self, status: Optional[int] = None) -> int:
        """Get count of devices, optionally filtered by status."""
        try:
            query = self.client.table('devices').select('device_id', count='exact')
            
            if status is not None:
                query = query.eq('status', status)
            
            result = query.execute()
            return result.count if result.count is not None else 0
        except Exception as e:
            logger.error(f"Error getting device count: {e}")
            return 0
    
    # Utility methods
    
    def clear_all_devices(self) -> int:
        """Clear all devices (for testing). Returns count of deleted devices."""
        try:
            # Get count before deletion
            count = self.get_device_count()
            
            # Delete all
            self.client.table('devices').delete().neq('device_id', '').execute()
            
            logger.warning(f"Cleared {count} devices from database")
            return count
        except Exception as e:
            logger.error(f"Error clearing devices: {e}")
            return 0
    
    def clear_all_meta(self) -> int:
        """Clear all metadata (for testing). Returns count of deleted entries."""
        try:
            # Get count before deletion
            result = self.client.table('meta').select('key', count='exact').execute()
            count = result.count if result.count is not None else 0
            
            # Delete all
            self.client.table('meta').delete().neq('key', '').execute()
            
            logger.warning(f"Cleared {count} metadata entries from database")
            return count
        except Exception as e:
            logger.error(f"Error clearing meta: {e}")
            return 0
    
    def get_db_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats = {
            'total_devices': self.get_device_count(),
            'active_devices': self.get_device_count(status=1),
            'revoked_devices': self.get_device_count(status=2),
            'meta_entries': len(self.get_all_meta()),
            'db_url': self.supabase_url,
            'db_type': 'Supabase PostgreSQL'
        }
        
        # Add key type distribution
        try:
            result = self.client.table('devices').select('key_type').execute()
            key_types = {}
            for row in result.data:
                key_type = row['key_type']
                key_types[key_type] = key_types.get(key_type, 0) + 1
            stats['key_type_distribution'] = key_types
        except Exception as e:
            logger.error(f"Error getting key type distribution: {e}")
            stats['key_type_distribution'] = {}
        
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
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    print("Testing Supabase Database Operations")
    print("=" * 40)
    
    # Get credentials from environment
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("⚠️  Please set SUPABASE_URL and SUPABASE_KEY in .env file")
        return
    
    # Create database manager
    db = SupabaseDatabaseManager(supabase_url, supabase_key)
    
    # Test metadata operations
    db.set_meta(MetaKeys.ROOT_HEX, "0x123456")
    db.set_meta(MetaKeys.VERSION, "1")
    
    print(f"Root hex: {db.get_meta(MetaKeys.ROOT_HEX)}")
    print(f"Version: {db.get_meta(MetaKeys.VERSION)}")
    
    # Test stats
    stats = db.get_db_stats()
    print(f"Database stats: {stats}")
    
    print("\n✅ Test complete")


if __name__ == "__main__":
    main()
