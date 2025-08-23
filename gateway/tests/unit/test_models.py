"""
Unit Tests for Database Models

Tests SQLAlchemy ORM models for database tables.
"""

import os
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

try:
    from gateway.models import Base, Device, AccumulatorRoot, EventLog
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from models import Base, Device, AccumulatorRoot, EventLog


class TestDatabaseModels:
    """Test database model definitions and relationships."""
    
    @pytest.fixture
    def engine(self):
        """Create in-memory SQLite database for testing."""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def session(self, engine):
        """Create database session for testing."""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()


class TestDeviceModel:
    """Test Device model functionality."""
    
    @pytest.fixture
    def engine(self):
        """Create in-memory SQLite database for testing."""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def session(self, engine):
        """Create database session for testing."""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    def test_device_creation(self, session):
        """Test creating a Device record."""
        device = Device(
            id="test_device_001",
            pubkey=b"test_public_key_bytes",
            prime_p="0x1a2b3c",
            status="active",
            last_witness="0x4d5e6f"
        )
        
        session.add(device)
        session.commit()
        
        # Verify device was created
        retrieved = session.query(Device).filter_by(id="test_device_001").first()
        assert retrieved is not None
        assert retrieved.id == "test_device_001"
        assert retrieved.pubkey == b"test_public_key_bytes"
        assert retrieved.prime_p == "0x1a2b3c"
        assert retrieved.status == "active"
        assert retrieved.last_witness == "0x4d5e6f"
    
    def test_device_default_status(self, session):
        """Test Device default status is 'active'."""
        device = Device(
            id="test_device_002",
            pubkey=b"test_key",
            prime_p="0xabc123"
        )
        
        session.add(device)
        session.commit()
        
        retrieved = session.query(Device).filter_by(id="test_device_002").first()
        assert retrieved.status == "active"
    
    def test_device_with_nonce(self, session):
        """Test Device with authentication nonce."""
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        device = Device(
            id="test_device_003",
            pubkey=b"test_key",
            prime_p="0xdef456",
            nonce="test_nonce_123",
            nonce_expires_at=expires_at
        )
        
        session.add(device)
        session.commit()
        
        retrieved = session.query(Device).filter_by(id="test_device_003").first()
        assert retrieved.nonce == "test_nonce_123"
        assert retrieved.nonce_expires_at == expires_at
    
    def test_device_nullable_fields(self, session):
        """Test Device nullable fields."""
        device = Device(
            id="test_device_004",
            pubkey=b"test_key",
            prime_p="0x789abc"
            # last_witness, nonce, nonce_expires_at should be nullable
        )
        
        session.add(device)
        session.commit()
        
        retrieved = session.query(Device).filter_by(id="test_device_004").first()
        assert retrieved.last_witness is None
        assert retrieved.nonce is None
        assert retrieved.nonce_expires_at is None
    
    def test_device_repr(self, session):
        """Test Device string representation."""
        device = Device(
            id="repr_test",
            pubkey=b"key",
            prime_p="0x123",
            status="revoked"
        )
        
        repr_str = repr(device)
        assert "repr_test" in repr_str
        assert "revoked" in repr_str
    
    def test_device_primary_key_constraint(self, session):
        """Test Device primary key constraint."""
        device1 = Device(id="duplicate", pubkey=b"key1", prime_p="0x111")
        device2 = Device(id="duplicate", pubkey=b"key2", prime_p="0x222")
        
        session.add(device1)
        session.commit()
        
        # Adding duplicate ID should fail
        session.add(device2)
        with pytest.raises(Exception):  # SQLAlchemy integrity error
            session.commit()
    
    def test_device_status_values(self, session):
        """Test various Device status values."""
        statuses = ["active", "revoked", "pending_revoke", "suspended"]
        
        for i, status in enumerate(statuses):
            device = Device(
                id=f"status_test_{i}",
                pubkey=b"test_key",
                prime_p=f"0x{i:06x}",
                status=status
            )
            session.add(device)
        
        session.commit()
        
        # Verify all statuses were stored
        for i, status in enumerate(statuses):
            device = session.query(Device).filter_by(id=f"status_test_{i}").first()
            assert device.status == status


class TestAccumulatorRootModel:
    """Test AccumulatorRoot model functionality."""
    
    @pytest.fixture
    def engine(self):
        """Create in-memory SQLite database for testing."""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def session(self, engine):
        """Create database session for testing."""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    def test_accumulator_root_creation(self, session):
        """Test creating AccumulatorRoot record."""
        root = AccumulatorRoot(
            value="0x1234567890abcdef",
            block=12345,
            tx_hash="0xfedcba0987654321",
            event_name="AccumulatorUpdated",
            timestamp="2024-01-15T12:30:00Z"
        )
        
        session.add(root)
        session.commit()
        
        retrieved = session.query(AccumulatorRoot).first()
        assert retrieved is not None
        assert retrieved.value == "0x1234567890abcdef"
        assert retrieved.block == 12345
        assert retrieved.tx_hash == "0xfedcba0987654321"
        assert retrieved.event_name == "AccumulatorUpdated"
        assert retrieved.timestamp == "2024-01-15T12:30:00Z"
    
    def test_accumulator_root_auto_id(self, session):
        """Test AccumulatorRoot auto-incrementing ID."""
        root1 = AccumulatorRoot(
            value="0x111", block=1, tx_hash="0xaaa",
            event_name="Event1", timestamp="2024-01-01T00:00:00Z"
        )
        root2 = AccumulatorRoot(
            value="0x222", block=2, tx_hash="0xbbb",
            event_name="Event2", timestamp="2024-01-02T00:00:00Z"
        )
        
        session.add(root1)
        session.add(root2)
        session.commit()
        
        assert root1.id is not None
        assert root2.id is not None
        assert root1.id != root2.id
        assert root2.id > root1.id  # Auto-increment
    
    def test_accumulator_root_repr(self, session):
        """Test AccumulatorRoot string representation."""
        root = AccumulatorRoot(
            value="0x1234567890abcdef1234567890abcdef",
            block=99999,
            tx_hash="0xhash",
            event_name="TestEvent",
            timestamp="2024-01-01T00:00:00Z"
        )
        session.add(root)
        session.commit()
        
        repr_str = repr(root)
        assert "99999" in repr_str
        assert "0x1234567890" in repr_str  # Should show truncated value
    
    def test_accumulator_root_ordering(self, session):
        """Test AccumulatorRoot ordering by block number."""
        # Add roots in non-sequential order
        roots = [
            AccumulatorRoot(value="0x3", block=300, tx_hash="0x3", event_name="E", timestamp="T"),
            AccumulatorRoot(value="0x1", block=100, tx_hash="0x1", event_name="E", timestamp="T"),
            AccumulatorRoot(value="0x2", block=200, tx_hash="0x2", event_name="E", timestamp="T"),
        ]
        
        for root in roots:
            session.add(root)
        session.commit()
        
        # Query ordered by block
        ordered = session.query(AccumulatorRoot).order_by(AccumulatorRoot.block).all()
        assert len(ordered) == 3
        assert ordered[0].block == 100
        assert ordered[1].block == 200
        assert ordered[2].block == 300


class TestEventLogModel:
    """Test EventLog model functionality."""
    
    @pytest.fixture
    def engine(self):
        """Create in-memory SQLite database for testing."""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def session(self, engine):
        """Create database session for testing."""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    def test_event_log_creation(self, session):
        """Test creating EventLog record."""
        event = EventLog(
            event_name="AccumulatorUpdated",
            block_number=12345,
            transaction_hash="0xabcdef123456",
            log_index=0,
            data='{"newRoot": "0x123", "oldRoot": "0x456"}',
            processed_at="2024-01-15T12:30:00Z"
        )
        
        session.add(event)
        session.commit()
        
        retrieved = session.query(EventLog).first()
        assert retrieved is not None
        assert retrieved.event_name == "AccumulatorUpdated"
        assert retrieved.block_number == 12345
        assert retrieved.transaction_hash == "0xabcdef123456"
        assert retrieved.log_index == 0
        assert retrieved.data == '{"newRoot": "0x123", "oldRoot": "0x456"}'
        assert retrieved.processed_at == "2024-01-15T12:30:00Z"
    
    def test_event_log_auto_id(self, session):
        """Test EventLog auto-incrementing ID."""
        event1 = EventLog(
            event_name="Event1", block_number=1, transaction_hash="0x1",
            log_index=0, data="{}", processed_at="T1"
        )
        event2 = EventLog(
            event_name="Event2", block_number=2, transaction_hash="0x2",
            log_index=0, data="{}", processed_at="T2"
        )
        
        session.add(event1)
        session.add(event2)
        session.commit()
        
        assert event1.id is not None
        assert event2.id is not None
        assert event1.id != event2.id
        assert event2.id > event1.id
    
    def test_event_log_json_data(self, session):
        """Test EventLog with JSON data."""
        import json
        
        event_data = {
            "accumulator": "0x123456",
            "deviceId": "device_001",
            "operation": "register"
        }
        
        event = EventLog(
            event_name="DeviceRegistered",
            block_number=100,
            transaction_hash="0xhash",
            log_index=1,
            data=json.dumps(event_data),
            processed_at="2024-01-01T00:00:00Z"
        )
        
        session.add(event)
        session.commit()
        
        retrieved = session.query(EventLog).first()
        parsed_data = json.loads(retrieved.data)
        assert parsed_data["accumulator"] == "0x123456"
        assert parsed_data["deviceId"] == "device_001"
        assert parsed_data["operation"] == "register"
    
    def test_event_log_repr(self, session):
        """Test EventLog string representation."""
        event = EventLog(
            event_name="TestEvent",
            block_number=99999,
            transaction_hash="0xhash",
            log_index=5,
            data="{}",
            processed_at="T"
        )
        session.add(event)
        session.commit()
        
        repr_str = repr(event)
        assert "TestEvent" in repr_str
        assert "99999" in repr_str


class TestModelRelationships:
    """Test relationships and constraints between models."""
    
    @pytest.fixture
    def engine(self):
        """Create in-memory SQLite database for testing."""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def session(self, engine):
        """Create database session for testing."""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    def test_table_creation(self, engine):
        """Test that all tables are created correctly."""
        # Check that tables exist
        with engine.connect() as conn:
            # Query sqlite_master to check table existence
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ))
            tables = [row[0] for row in result]
        
        assert "devices" in tables
        assert "accumulator_roots" in tables
        assert "event_logs" in tables
    
    def test_device_table_schema(self, engine):
        """Test Device table schema."""
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(devices)"))
            columns = {row[1]: row[2] for row in result}  # name: type
        
        assert "id" in columns
        assert "pubkey" in columns
        assert "prime_p" in columns
        assert "status" in columns
        assert "last_witness" in columns
        assert "nonce" in columns
        assert "nonce_expires_at" in columns
    
    def test_accumulator_roots_table_schema(self, engine):
        """Test AccumulatorRoot table schema."""
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(accumulator_roots)"))
            columns = {row[1]: row[2] for row in result}
        
        assert "id" in columns
        assert "value" in columns
        assert "block" in columns
        assert "tx_hash" in columns
        assert "event_name" in columns
        assert "timestamp" in columns
    
    def test_event_logs_table_schema(self, engine):
        """Test EventLog table schema."""
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(event_logs)"))
            columns = {row[1]: row[2] for row in result}
        
        assert "id" in columns
        assert "event_name" in columns
        assert "block_number" in columns
        assert "transaction_hash" in columns
        assert "log_index" in columns
        assert "data" in columns
        assert "processed_at" in columns
    
    def test_multiple_model_operations(self, session):
        """Test operations across multiple models."""
        # Create a device
        device = Device(
            id="multi_test_device",
            pubkey=b"test_key",
            prime_p="0xabc123"
        )
        session.add(device)
        
        # Create accumulator root
        root = AccumulatorRoot(
            value="0xdef456",
            block=1000,
            tx_hash="0x789ghi",
            event_name="AccumulatorUpdated",
            timestamp="2024-01-01T00:00:00Z"
        )
        session.add(root)
        
        # Create event log
        event = EventLog(
            event_name="DeviceRegistered",
            block_number=1000,
            transaction_hash="0x789ghi",
            log_index=0,
            data='{"deviceId": "multi_test_device"}',
            processed_at="2024-01-01T00:00:01Z"
        )
        session.add(event)
        
        session.commit()
        
        # Verify all records exist
        assert session.query(Device).count() == 1
        assert session.query(AccumulatorRoot).count() == 1
        assert session.query(EventLog).count() == 1
        
        # Verify we can query related data
        device_count = session.query(Device).filter_by(status="active").count()
        assert device_count == 1
        
        recent_events = session.query(EventLog).filter(
            EventLog.block_number >= 1000
        ).count()
        assert recent_events == 1
