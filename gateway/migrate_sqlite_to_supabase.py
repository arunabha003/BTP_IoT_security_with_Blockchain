"""
Migrate existing SQLite data to Supabase PostgreSQL

This script migrates all devices and metadata from the local SQLite
database to the new Supabase PostgreSQL database.

Usage:
    python migrate_sqlite_to_supabase.py

Prerequisites:
    1. SUPABASE_URL and SUPABASE_KEY must be set in .env
    2. Supabase tables must be created (run supabase_schema.sql first)
    3. Existing gateway.db file with data to migrate
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path for importing modules
sys.path.append(os.path.dirname(__file__))

from db import DatabaseManager as SQLiteDB, MetaKeys
from supabase_db import SupabaseDatabaseManager as SupabaseDB

load_dotenv()


def migrate():
    """Perform the migration from SQLite to Supabase."""
    
    print("=" * 60)
    print("SQLite to Supabase Migration Tool")
    print("=" * 60)
    print()
    
    # Validate environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    sqlite_path = os.getenv("DB_PATH", "gateway.db")
    
    if not supabase_url:
        print("❌ Error: SUPABASE_URL not set in .env file")
        return False
    
    if not supabase_key:
        print("❌ Error: SUPABASE_KEY not set in .env file")
        return False
    
    if not os.path.exists(sqlite_path):
        print(f"❌ Error: SQLite database not found at {sqlite_path}")
        return False
    
    print(f"📁 SQLite database: {sqlite_path}")
    print(f"☁️  Supabase URL: {supabase_url}")
    print()
    
    try:
        # Connect to both databases
        print("Connecting to databases...")
        sqlite_db = SQLiteDB(sqlite_path)
        supabase_db = SupabaseDB(supabase_url, supabase_key)
        print("✅ Connected successfully")
        print()
        
        # Get statistics
        sqlite_stats = sqlite_db.get_db_stats()
        print("📊 SQLite Database Statistics:")
        print(f"   Total devices: {sqlite_stats['total_devices']}")
        print(f"   Active devices: {sqlite_stats['active_devices']}")
        print(f"   Revoked devices: {sqlite_stats['revoked_devices']}")
        print(f"   Metadata entries: {sqlite_stats['meta_entries']}")
        print()
        
        # Confirm migration
        response = input("⚠️  Do you want to proceed with migration? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("❌ Migration cancelled")
            return False
        
        print()
        print("Starting migration...")
        print("-" * 60)
        
        # Migrate metadata
        print("\n📝 Migrating metadata...")
        meta_data = sqlite_db.get_all_meta()
        migrated_meta = 0
        
        for key, value in meta_data.items():
            try:
                supabase_db.set_meta(key, value)
                print(f"   ✓ {key}: {value[:50]}..." if len(value) > 50 else f"   ✓ {key}: {value}")
                migrated_meta += 1
            except Exception as e:
                print(f"   ✗ Failed to migrate {key}: {e}")
        
        print(f"\n✅ Migrated {migrated_meta}/{len(meta_data)} metadata entries")
        
        # Migrate devices
        print("\n🔑 Migrating devices...")
        devices = sqlite_db.get_all_devices()
        migrated_devices = 0
        failed_devices = 0
        
        for idx, device in enumerate(devices, 1):
            device_id_hex = device['device_id'].hex()
            
            try:
                # Check if device already exists
                if supabase_db.device_exists(device['device_id']):
                    print(f"   ⚠️  Device {idx}/{len(devices)}: {device_id_hex[:16]}... (already exists, skipping)")
                    continue
                
                # Insert device
                supabase_db.insert_device(
                    device_id=device['device_id'],
                    pubkey_pem=device['pubkey_pem'],
                    id_prime=device['id_prime'],
                    witness=device['witness'],
                    key_type=device['key_type'],
                    status=device['status']
                )
                
                status_label = "ACTIVE" if device['status'] == 1 else "REVOKED"
                print(f"   ✓ Device {idx}/{len(devices)}: {device_id_hex[:16]}... ({device['key_type']}, {status_label})")
                migrated_devices += 1
                
            except Exception as e:
                print(f"   ✗ Device {idx}/{len(devices)}: {device_id_hex[:16]}... (FAILED: {e})")
                failed_devices += 1
        
        print(f"\n✅ Migrated {migrated_devices}/{len(devices)} devices")
        if failed_devices > 0:
            print(f"⚠️  {failed_devices} devices failed to migrate")
        
        # Verify migration
        print("\n🔍 Verifying migration...")
        supabase_stats = supabase_db.get_db_stats()
        print(f"   Supabase total devices: {supabase_stats['total_devices']}")
        print(f"   Supabase active devices: {supabase_stats['active_devices']}")
        print(f"   Supabase revoked devices: {supabase_stats['revoked_devices']}")
        print(f"   Supabase metadata entries: {supabase_stats['meta_entries']}")
        
        # Summary
        print()
        print("=" * 60)
        print("Migration Summary")
        print("=" * 60)
        print(f"✅ Metadata migrated: {migrated_meta}/{len(meta_data)}")
        print(f"✅ Devices migrated: {migrated_devices}/{len(devices)}")
        if failed_devices > 0:
            print(f"⚠️  Failed migrations: {failed_devices}")
        print()
        print("🎉 Migration completed successfully!")
        print()
        print("Next steps:")
        print("  1. Verify data in Supabase dashboard")
        print("  2. Update gateway/main.py to use supabase_db")
        print("  3. Test the gateway with Supabase")
        print("  4. Backup your SQLite database for safety")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_migration():
    """Verify the migration was successful."""
    print("\n🔍 Running verification...")
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    sqlite_path = os.getenv("DB_PATH", "gateway.db")
    
    sqlite_db = SQLiteDB(sqlite_path)
    supabase_db = SupabaseDB(supabase_url, supabase_key)
    
    # Compare counts
    sqlite_stats = sqlite_db.get_db_stats()
    supabase_stats = supabase_db.get_db_stats()
    
    print("\n📊 Comparison:")
    print(f"   SQLite devices: {sqlite_stats['total_devices']}")
    print(f"   Supabase devices: {supabase_stats['total_devices']}")
    
    if sqlite_stats['total_devices'] == supabase_stats['total_devices']:
        print("   ✅ Device counts match!")
    else:
        print("   ⚠️  Device counts differ!")
    
    print(f"\n   SQLite metadata: {sqlite_stats['meta_entries']}")
    print(f"   Supabase metadata: {supabase_stats['meta_entries']}")
    
    if sqlite_stats['meta_entries'] == supabase_stats['meta_entries']:
        print("   ✅ Metadata counts match!")
    else:
        print("   ⚠️  Metadata counts differ!")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate SQLite data to Supabase")
    parser.add_argument('--verify', action='store_true', help='Verify migration only')
    args = parser.parse_args()
    
    if args.verify:
        verify_migration()
    else:
        success = migrate()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
