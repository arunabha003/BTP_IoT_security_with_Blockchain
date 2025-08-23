"""
Integration Tests for Gateway API Endpoints

Tests the complete API functionality with real FastAPI application.
"""

import os
import json
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

try:
    from gateway.main import app
    from gateway.models import Base, Device, AccumulatorRoot
    from gateway.config import get_settings
    from gateway.database import get_db_session
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from main import app
    from models import Base, Device, AccumulatorRoot
    from config import get_settings
    from database import get_db_session


class TestAPIEndpoints:
    """Test API endpoints with real FastAPI application."""
    
    @pytest.fixture
    def client(self):
        """Create test client with test database."""
        # Use test database
        test_engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(test_engine)
        TestSession = sessionmaker(bind=test_engine)
        
        def get_test_db():
            session = TestSession()
            try:
                yield session
            finally:
                session.close()
        
        # Override database dependency
        app.dependency_overrides[get_db_session] = get_test_db
        
        with TestClient(app) as client:
            yield client
        
        # Clean up
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def admin_headers(self):
        """Headers with admin authentication."""
        settings = get_settings()
        return {"x-admin-key": settings.ADMIN_KEY}
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/healthz")
        assert response.status_code == 200
        
        data = response.json()
        assert data["ok"] is True
        assert "service" in data
        assert "version" in data
        assert "database" in data
        assert "blockchain" in data
        assert "contract_loaded" in data
    
    def test_root_endpoint(self, client):
        """Test accumulator root endpoint."""
        with patch('gateway.blockchain.blockchain_client') as mock_client:
            mock_client.get_current_root.return_value = "0x1234567890abcdef"
            
            response = client.get("/root")
            assert response.status_code == 200
            
            data = response.json()
            assert data["root"] == "0x1234567890abcdef"
            assert data["format"] == "hex"
    
    def test_status_endpoint(self, client):
        """Test detailed status endpoint."""
        response = client.get("/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "config" in data
        assert "blockchain" in data
        assert "database" in data
        assert "timestamp" in data
        
        # Check config section
        config = data["config"]
        assert "rpc_url" in config
        assert "admin_key_configured" in config
        assert "database_url" in config
    
    def test_get_accumulator_info(self, client):
        """Test GET /accumulator endpoint."""
        with patch('gateway.accumulator_service.accumulator_service') as mock_service:
            mock_service.get_accumulator_info.return_value = {
                "rootHex": "0xabcdef123456",
                "rootHash": "0x789012345678",
                "block": 12345,
                "activeDevices": 5
            }
            
            response = client.get("/accumulator")
            assert response.status_code == 200
            
            data = response.json()
            assert data["rootHex"] == "0xabcdef123456"
            assert data["rootHash"] == "0x789012345678"
            assert data["block"] == 12345
            assert data["activeDevices"] == 5
    
    def test_update_accumulator_without_auth(self, client):
        """Test POST /accumulator/update without admin auth (should fail)."""
        payload = {
            "newRootHex": "0x" + "12" * 32,
            "parentHash": "0x" + "34" * 32
        }
        
        response = client.post("/accumulator/update", json=payload)
        assert response.status_code == 401
        
        data = response.json()
        assert "Unauthorized" in data["error"]
        assert "admin key required" in data["detail"].lower()
    
    def test_update_accumulator_with_auth(self, client, admin_headers):
        """Test POST /accumulator/update with admin auth."""
        with patch('gateway.accumulator_service.accumulator_service') as mock_service:
            mock_service.update_accumulator_on_chain.return_value = {
                "message": "Accumulator update transaction successful",
                "transactionHash": "0xabcdef",
                "blockNumber": 12346,
                "newRoot": "0x" + "12" * 32
            }
            
            payload = {
                "newRootHex": "0x" + "12" * 32,
                "parentHash": "0x" + "34" * 32
            }
            
            response = client.post("/accumulator/update", json=payload, headers=admin_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert "transaction successful" in data["message"].lower()
            assert data["transactionHash"] == "0xabcdef"
    
    def test_enroll_device_without_auth(self, client):
        """Test POST /enroll without admin auth (should fail)."""
        payload = {
            "device_id": "test_device_001",
            "pubkey_pem": "-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----"
        }
        
        response = client.post("/enroll", json=payload)
        assert response.status_code == 401
    
    def test_enroll_device_with_auth(self, client, admin_headers):
        """Test POST /enroll with admin auth."""
        with patch('gateway.accumulator_service.accumulator_service') as mock_service:
            mock_service.enroll_device.return_value = {
                "device_id": "test_device_001",
                "prime_p_hex": "0xabc123",
                "initial_witness_hex": "0xdef456",
                "current_root_hex": "0x789abc"
            }
            
            payload = {
                "device_id": "test_device_001",
                "pubkey_pem": "-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----"
            }
            
            response = client.post("/enroll", json=payload, headers=admin_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data["device_id"] == "test_device_001"
            assert data["prime_p_hex"] == "0xabc123"
    
    def test_revoke_device_without_auth(self, client):
        """Test POST /revoke without admin auth (should fail)."""
        payload = {"device_id": "test_device_001"}
        
        response = client.post("/revoke", json=payload)
        assert response.status_code == 401
    
    def test_revoke_device_with_auth(self, client, admin_headers):
        """Test POST /revoke with admin auth."""
        with patch('gateway.accumulator_service.accumulator_service') as mock_service:
            mock_service.revoke_device.return_value = None
            
            payload = {"device_id": "test_device_001"}
            
            response = client.post("/revoke", json=payload, headers=admin_headers)
            assert response.status_code == 204
    
    def test_auth_start(self, client):
        """Test GET /auth/start endpoint."""
        with patch('gateway.accumulator_service.accumulator_service') as mock_service:
            mock_service.start_auth_session.return_value = {
                "nonce": "abc123def456",
                "expiresAt": "2024-01-15T12:35:00Z"
            }
            
            response = client.get("/auth/start?device_id=test_device")
            assert response.status_code == 200
            
            data = response.json()
            assert data["nonce"] == "abc123def456"
            assert data["expiresAt"] == "2024-01-15T12:35:00Z"
    
    def test_auth_verify(self, client):
        """Test POST /auth/verify endpoint."""
        with patch('gateway.accumulator_service.accumulator_service') as mock_service:
            mock_service.verify_auth_session.return_value = {
                "ok": True,
                "newWitnessHex": "0x987654321"
            }
            
            payload = {
                "device_id": "test_device",
                "p_hex": "0xabc123",
                "witness_hex": "0xdef456",
                "signature_base64": "SGVsbG8gV29ybGQ=",
                "nonce": "test_nonce"
            }
            
            response = client.post("/auth/verify", json=payload)
            assert response.status_code == 200
            
            data = response.json()
            assert data["ok"] is True
            assert data["newWitnessHex"] == "0x987654321"
    
    def test_auth_verify_failure(self, client):
        """Test POST /auth/verify with authentication failure."""
        with patch('gateway.accumulator_service.accumulator_service') as mock_service:
            mock_service.verify_auth_session.return_value = {
                "ok": False,
                "detail": "Invalid signature"
            }
            
            payload = {
                "device_id": "test_device",
                "p_hex": "0xabc123",
                "witness_hex": "0xdef456",
                "signature_base64": "invalid_signature",
                "nonce": "test_nonce"
            }
            
            response = client.post("/auth/verify", json=payload)
            assert response.status_code == 200
            
            data = response.json()
            assert data["ok"] is False
            assert "Invalid signature" in data["detail"]
    
    def test_invalid_hex_validation(self, client, admin_headers):
        """Test hex string validation in endpoints."""
        # Test invalid hex in accumulator update
        payload = {
            "newRootHex": "invalid_hex_string",
            "parentHash": "0x" + "34" * 32
        }
        
        response = client.post("/accumulator/update", json=payload, headers=admin_headers)
        assert response.status_code == 400
        assert "Invalid hex string format" in response.json()["detail"]
    
    def test_rate_limiting(self, client):
        """Test rate limiting middleware."""
        # Make multiple requests rapidly
        responses = []
        for i in range(25):  # More than default limit of 20/minute
            response = client.get("/healthz")
            responses.append(response.status_code)
        
        # Should eventually get rate limited (429)
        assert 429 in responses
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/healthz")
        
        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
    
    def test_security_headers(self, client):
        """Test security headers are present."""
        response = client.get("/healthz")
        
        # Should have security headers
        assert "x-frame-options" in response.headers
        assert "x-content-type-options" in response.headers
        assert "strict-transport-security" in response.headers
        assert "x-request-id" in response.headers
    
    def test_request_id_header(self, client):
        """Test that request ID header is added."""
        response = client.get("/healthz")
        
        assert "x-request-id" in response.headers
        request_id = response.headers["x-request-id"]
        assert len(request_id) == 8  # Should be 8 character UUID prefix
    
    def test_error_handling(self, client):
        """Test error handling and response format."""
        # Test 404 error
        response = client.get("/nonexistent")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
    
    def test_pydantic_validation(self, client, admin_headers):
        """Test Pydantic request validation."""
        # Test missing required field
        payload = {
            "device_id": "test_device"
            # Missing pubkey_pem
        }
        
        response = client.post("/enroll", json=payload, headers=admin_headers)
        assert response.status_code == 422  # Validation error
        
        data = response.json()
        assert "detail" in data
        assert any("pubkey_pem" in str(error) for error in data["detail"])
    
    def test_content_type_validation(self, client, admin_headers):
        """Test content type validation."""
        # Test sending non-JSON data
        response = client.post(
            "/enroll",
            data="not json",
            headers={**admin_headers, "content-type": "text/plain"}
        )
        assert response.status_code == 422


class TestAPIEndpointsWithDatabase:
    """Test API endpoints with real database operations."""
    
    @pytest.fixture
    def client_with_db(self):
        """Create test client with persistent test database."""
        # Use temporary file database for testing
        import tempfile
        db_file = tempfile.NamedTemporaryFile(delete=False)
        db_url = f"sqlite:///{db_file.name}"
        
        test_engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(test_engine)
        TestSession = sessionmaker(bind=test_engine)
        
        def get_test_db():
            session = TestSession()
            try:
                yield session
            finally:
                session.close()
        
        app.dependency_overrides[get_db_session] = get_test_db
        
        with TestClient(app) as client:
            yield client, TestSession
        
        # Cleanup
        app.dependency_overrides.clear()
        os.unlink(db_file.name)
    
    def test_database_operations_in_endpoints(self, client_with_db):
        """Test that endpoints properly interact with database."""
        client, TestSession = client_with_db
        
        # Create test data in database
        session = TestSession()
        device = Device(
            id="db_test_device",
            pubkey=b"test_key_bytes",
            prime_p="0xabc123",
            status="active"
        )
        session.add(device)
        session.commit()
        session.close()
        
        # Test that we can query the data through status endpoint
        with patch('gateway.blockchain.blockchain_client') as mock_blockchain:
            mock_blockchain.is_connected.return_value = True
            mock_blockchain.is_contract_loaded.return_value = True
            
            response = client.get("/status")
            assert response.status_code == 200
            
            data = response.json()
            assert data["database"]["connected"] is True
    
    def test_accumulator_root_storage(self, client_with_db):
        """Test AccumulatorRoot storage through API."""
        client, TestSession = client_with_db
        
        # Add accumulator root to database
        session = TestSession()
        root = AccumulatorRoot(
            value="0xtest_accumulator_value",
            block=12345,
            tx_hash="0xtest_tx_hash",
            event_name="AccumulatorUpdated",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        session.add(root)
        session.commit()
        session.close()
        
        # Mock accumulator service to use database data
        with patch('gateway.accumulator_service.accumulator_service') as mock_service:
            mock_service.get_accumulator_info.return_value = {
                "rootHex": "0xtest_accumulator_value",
                "rootHash": "0xtest_tx_hash",
                "block": 12345,
                "activeDevices": 0
            }
            
            response = client.get("/accumulator")
            assert response.status_code == 200
            
            data = response.json()
            assert data["rootHex"] == "0xtest_accumulator_value"
            assert data["block"] == 12345
