"""
Unit Tests for RSA Parameters Module

Tests the loading and validation of RSA parameters used in the accumulator.
"""

import json
import os
import tempfile
import pytest
from pathlib import Path

try:
    from accum.rsa_params import load_params, generate_demo_params, validate_params
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from rsa_params import load_params, generate_demo_params, validate_params


class TestRSAParams:
    """Test RSA parameter loading and validation."""
    
    def test_load_params_valid_file(self):
        """Test loading parameters from valid params.json file."""
        N, g = load_params()
        
        # Verify parameters are loaded correctly
        assert isinstance(N, int)
        assert isinstance(g, int)
        assert N > 0
        assert g > 0
        
        # Verify N is large enough for security (should be 2048+ bits)
        assert N.bit_length() >= 2048
        
        # Verify g is a small generator (typically 2, 3, or 4)
        assert g in [2, 3, 4]
    
    def test_generate_demo_params(self):
        """Test generation of demo parameters for testing."""
        N, g = generate_demo_params()
        
        # Demo params should be the toy values
        assert N == 209  # 11 * 19
        assert g == 4
    
    def test_validate_params_valid(self):
        """Test parameter validation with valid inputs."""
        N = 209  # 11 * 19
        g = 4
        
        # Should not raise any exception
        validate_params(N, g)
    
    def test_validate_params_invalid_n(self):
        """Test parameter validation with invalid N."""
        with pytest.raises(ValueError, match="N must be a positive integer"):
            validate_params(0, 4)
        
        with pytest.raises(ValueError, match="N must be a positive integer"):
            validate_params(-1, 4)
    
    def test_validate_params_invalid_g(self):
        """Test parameter validation with invalid g."""
        with pytest.raises(ValueError, match="g must be a positive integer"):
            validate_params(209, 0)
        
        with pytest.raises(ValueError, match="g must be a positive integer"):
            validate_params(209, -1)
    
    def test_validate_params_g_too_large(self):
        """Test parameter validation with g >= N."""
        with pytest.raises(ValueError, match="g must be less than N"):
            validate_params(209, 209)
        
        with pytest.raises(ValueError, match="g must be less than N"):
            validate_params(209, 300)
    
    def test_load_params_missing_file(self):
        """Test loading parameters when params.json is missing."""
        # Temporarily rename the params file
        params_file = Path(__file__).parent.parent.parent / "params.json"
        backup_file = params_file.with_suffix(".json.backup")
        
        if params_file.exists():
            params_file.rename(backup_file)
        
        try:
            # Should fall back to demo parameters
            N, g = load_params()
            assert N == 209
            assert g == 4
        finally:
            # Restore the params file
            if backup_file.exists():
                backup_file.rename(params_file)
    
    def test_load_params_invalid_json(self):
        """Test loading parameters from invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_file = f.name
        
        try:
            # Mock the params.json path to point to our temp file
            import accum.rsa_params as rsa_params_module
            original_file = rsa_params_module.PARAMS_FILE
            rsa_params_module.PARAMS_FILE = temp_file
            
            # Should fall back to demo parameters
            N, g = load_params()
            assert N == 209
            assert g == 4
            
            # Restore original path
            rsa_params_module.PARAMS_FILE = original_file
        finally:
            os.unlink(temp_file)
    
    def test_load_params_missing_keys(self):
        """Test loading parameters from JSON with missing keys."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"N": 209}, f)  # Missing 'g'
            temp_file = f.name
        
        try:
            # Mock the params.json path
            import accum.rsa_params as rsa_params_module
            original_file = rsa_params_module.PARAMS_FILE
            rsa_params_module.PARAMS_FILE = temp_file
            
            # Should fall back to demo parameters
            N, g = load_params()
            assert N == 209
            assert g == 4
            
            # Restore original path
            rsa_params_module.PARAMS_FILE = original_file
        finally:
            os.unlink(temp_file)
    
    def test_params_file_format(self):
        """Test that the actual params.json file has correct format."""
        params_file = Path(__file__).parent.parent.parent / "params.json"
        
        if params_file.exists():
            with open(params_file, 'r') as f:
                data = json.load(f)
            
            # Verify required keys exist
            assert 'N' in data
            assert 'g' in data
            
            # Verify types
            assert isinstance(data['N'], (int, str))  # Could be hex string
            assert isinstance(data['g'], int)
            
            # If N is hex string, verify it can be converted
            if isinstance(data['N'], str):
                assert data['N'].startswith('0x')
                int(data['N'], 16)
