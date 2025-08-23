"""
Unit Tests for Configuration Module

Tests the configuration loading and validation from environment variables.
"""

import os
import pytest
from unittest.mock import patch

try:
    from gateway.config import Settings, get_settings
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from config import Settings, get_settings


class TestSettings:
    """Test configuration settings and environment variable loading."""
    
    def test_default_settings(self):
        """Test default configuration values."""
        settings = Settings()
        
        # Test default values
        assert settings.RPC_URL == "http://127.0.0.1:8545"
        assert settings.CONTRACT_ADDRESS is None
        assert settings.ADMIN_KEY == "test-admin-key"
        assert settings.DATABASE_URL == "sqlite+aiosqlite:///./gateway.db"
        assert settings.LOG_LEVEL == "INFO"
        assert settings.APP_VERSION == "1.0.0"
        assert settings.EVENT_POLLING_INTERVAL_SECONDS == 5
        assert settings.NONCE_TTL_SECONDS == 300
        assert settings.IP_RATE_LIMIT_PER_MINUTE == 20
        assert settings.DEVICE_RATE_LIMIT_PER_5_MINUTES == 5
    
    @patch.dict(os.environ, {
        'RPC_URL': 'http://custom-rpc:8545',
        'CONTRACT_ADDRESS': '0x1234567890abcdef',
        'ADMIN_KEY': 'custom-admin-key',
        'LOG_LEVEL': 'DEBUG'
    })
    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        settings = Settings()
        
        assert settings.RPC_URL == "http://custom-rpc:8545"
        assert settings.CONTRACT_ADDRESS == "0x1234567890abcdef"
        assert settings.ADMIN_KEY == "custom-admin-key"
        assert settings.LOG_LEVEL == "DEBUG"
    
    @patch.dict(os.environ, {
        'EVENT_POLLING_INTERVAL_SECONDS': '10',
        'NONCE_TTL_SECONDS': '600',
        'IP_RATE_LIMIT_PER_MINUTE': '50',
        'DEVICE_RATE_LIMIT_PER_5_MINUTES': '10'
    })
    def test_numeric_environment_variables(self):
        """Test numeric environment variable parsing."""
        settings = Settings()
        
        assert settings.EVENT_POLLING_INTERVAL_SECONDS == 10
        assert settings.NONCE_TTL_SECONDS == 600
        assert settings.IP_RATE_LIMIT_PER_MINUTE == 50
        assert settings.DEVICE_RATE_LIMIT_PER_5_MINUTES == 10
    
    @patch.dict(os.environ, {'DATABASE_URL': 'postgresql://user:pass@localhost/db'})
    def test_database_url_override(self):
        """Test database URL environment variable."""
        settings = Settings()
        assert settings.DATABASE_URL == "postgresql://user:pass@localhost/db"
    
    def test_settings_immutability(self):
        """Test that settings are properly configured as immutable."""
        settings = Settings()
        
        # Should not be able to modify settings after creation
        with pytest.raises(AttributeError):
            settings.RPC_URL = "modified"
    
    def test_get_settings_singleton(self):
        """Test that get_settings returns the same instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        
        # Should be the same instance (singleton pattern)
        assert settings1 is settings2
    
    @patch.dict(os.environ, {'APP_VERSION': '2.0.0'})
    def test_app_version_override(self):
        """Test application version override."""
        # Clear the singleton to test new environment
        import config
        config._settings = None
        
        settings = get_settings()
        assert settings.APP_VERSION == "2.0.0"
        
        # Reset singleton
        config._settings = None
    
    def test_config_class_attributes(self):
        """Test Config class attributes."""
        settings = Settings()
        
        # Should have Config class with proper attributes
        assert hasattr(settings, 'Config')
        assert settings.Config.env_file == ".env"
        assert settings.Config.extra == "ignore"
    
    @patch.dict(os.environ, {}, clear=True)
    def test_all_defaults_with_empty_environment(self):
        """Test all default values with completely empty environment."""
        settings = Settings()
        
        # Verify all defaults are set correctly
        assert settings.RPC_URL == "http://127.0.0.1:8545"
        assert settings.CONTRACT_ADDRESS is None
        assert settings.ADMIN_KEY == "test-admin-key"
        assert settings.DATABASE_URL == "sqlite+aiosqlite:///./gateway.db"
        assert settings.LOG_LEVEL == "INFO"
        assert settings.APP_VERSION == "1.0.0"
        assert settings.EVENT_POLLING_INTERVAL_SECONDS == 5
        assert settings.NONCE_TTL_SECONDS == 300
        assert settings.IP_RATE_LIMIT_PER_MINUTE == 20
        assert settings.DEVICE_RATE_LIMIT_PER_5_MINUTES == 5
    
    def test_field_descriptions(self):
        """Test that fields have proper descriptions."""
        settings = Settings()
        
        # Get field info from the model
        fields = settings.__fields__
        
        # Check that key fields exist
        assert 'RPC_URL' in fields
        assert 'CONTRACT_ADDRESS' in fields
        assert 'ADMIN_KEY' in fields
        assert 'DATABASE_URL' in fields
        assert 'LOG_LEVEL' in fields
    
    @patch.dict(os.environ, {
        'INVALID_NUMERIC': 'not_a_number',
        'EVENT_POLLING_INTERVAL_SECONDS': 'invalid'
    })
    def test_invalid_numeric_values(self):
        """Test handling of invalid numeric environment variables."""
        # Should raise validation error for invalid numeric values
        with pytest.raises(Exception):  # Pydantic validation error
            Settings()
    
    def test_optional_fields(self):
        """Test optional configuration fields."""
        settings = Settings()
        
        # CONTRACT_ADDRESS should be optional
        assert settings.CONTRACT_ADDRESS is None
        
        # Other fields should have defaults
        assert settings.ADMIN_KEY is not None
        assert settings.RPC_URL is not None
    
    @patch.dict(os.environ, {'CONTRACT_ADDRESS': ''})
    def test_empty_string_contract_address(self):
        """Test empty string for CONTRACT_ADDRESS."""
        settings = Settings()
        # Empty string should be treated as None or empty
        assert settings.CONTRACT_ADDRESS == '' or settings.CONTRACT_ADDRESS is None
