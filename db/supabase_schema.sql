-- ============================================
-- IoT Identity Gateway - Database Schema
-- For Supabase PostgreSQL
-- ============================================
-- 
-- This schema creates the necessary tables for the
-- IoT Identity Gateway using RSA Accumulators.
--
-- Usage:
-- 1. Go to Supabase Dashboard > SQL Editor
-- 2. Copy and paste this entire file
-- 3. Click "Run" to execute
-- ============================================

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- Table: devices
-- Stores IoT device information and credentials
-- ============================================
CREATE TABLE IF NOT EXISTS devices (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    device_id TEXT UNIQUE NOT NULL,  -- 64 char hex string (32 bytes)
    pubkey_pem TEXT NOT NULL,         -- Public key in PEM format
    id_prime TEXT NOT NULL,           -- Large integer stored as text
    witness TEXT NOT NULL,            -- Accumulator witness (hex string)
    key_type TEXT NOT NULL DEFAULT 'ed25519' CHECK (key_type IN ('ed25519', 'rsa')),
    status INTEGER NOT NULL DEFAULT 1 CHECK (status IN (1, 2)), -- 1=ACTIVE, 2=REVOKED
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_devices_device_id ON devices(device_id);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_key_type ON devices(key_type);
CREATE INDEX IF NOT EXISTS idx_devices_created_at ON devices(created_at);

-- Add comments for documentation
COMMENT ON TABLE devices IS 'IoT devices enrolled in the RSA accumulator system';
COMMENT ON COLUMN devices.device_id IS 'SHA3-256 hash of public key DER (64 hex chars)';
COMMENT ON COLUMN devices.id_prime IS 'Device identity prime number for accumulator';
COMMENT ON COLUMN devices.witness IS 'Membership witness for accumulator proof';
COMMENT ON COLUMN devices.status IS '1=ACTIVE, 2=REVOKED';

-- ============================================
-- Table: meta
-- Stores system metadata and accumulator state
-- ============================================
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for meta table
CREATE INDEX IF NOT EXISTS idx_meta_key ON meta(key);

-- Add comments
COMMENT ON TABLE meta IS 'System metadata and RSA accumulator parameters';
COMMENT ON COLUMN meta.key IS 'Metadata key (root_hex, version, N_hex, g_hex, lambda_n_hex)';
COMMENT ON COLUMN meta.value IS 'Metadata value (typically hex strings or numbers)';

-- ============================================
-- Function: Update updated_at timestamp
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Triggers: Auto-update timestamps
-- ============================================
DROP TRIGGER IF EXISTS update_devices_updated_at ON devices;
CREATE TRIGGER update_devices_updated_at
    BEFORE UPDATE ON devices
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_meta_updated_at ON meta;
CREATE TRIGGER update_meta_updated_at
    BEFORE UPDATE ON meta
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Row Level Security (RLS)
-- Enable RLS for secure access control
-- ============================================

-- Enable RLS on tables
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE meta ENABLE ROW LEVEL SECURITY;

-- Policy: Allow service role full access
CREATE POLICY "Service role has full access to devices"
    ON devices
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role has full access to meta"
    ON meta
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Policy: Allow authenticated users to read devices
CREATE POLICY "Authenticated users can read devices"
    ON devices
    FOR SELECT
    TO authenticated
    USING (true);

-- Policy: Allow authenticated users to read meta
CREATE POLICY "Authenticated users can read meta"
    ON meta
    FOR SELECT
    TO authenticated
    USING (true);

-- ============================================
-- Initial seed data (optional)
-- Uncomment if you want to initialize version
-- ============================================
-- INSERT INTO meta (key, value) VALUES ('version', '0')
-- ON CONFLICT (key) DO NOTHING;

-- ============================================
-- Verification queries
-- ============================================
-- Check tables were created
SELECT 
    table_name, 
    table_type 
FROM information_schema.tables 
WHERE table_schema = 'public' 
    AND table_name IN ('devices', 'meta')
ORDER BY table_name;

-- Check indexes
SELECT 
    tablename, 
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public' 
    AND tablename IN ('devices', 'meta')
ORDER BY tablename, indexname;

-- Check RLS is enabled
SELECT 
    schemaname,
    tablename,
    rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
    AND tablename IN ('devices', 'meta');

-- Show table structures
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
    AND table_name IN ('devices', 'meta')
ORDER BY table_name, ordinal_position;
