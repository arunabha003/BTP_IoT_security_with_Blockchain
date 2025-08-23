"""
Database Models

SQLAlchemy 2.x models for the IoT identity gateway.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, LargeBinary, Integer, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class Device(Base):
    """
    Device identity table.
    
    Stores device information including public keys, RSA prime mappings,
    and current membership status in the accumulator.
    """
    __tablename__ = "devices"
    
    # Primary key: device identifier
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    
    # Device public key (Ed25519, 32 bytes)
    pubkey: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    
    # RSA prime derived from pubkey
    prime_p: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Device status: active, revoked, pending
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    
    # Last known membership witness (hex string)
    last_witness: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    def __repr__(self) -> str:
        return f"<Device(id='{self.id}', status='{self.status}')>"


class AccumulatorRoot(Base):
    """
    Accumulator root history table.
    
    Stores the history of accumulator root values as they change
    due to device registrations and revocations.
    """
    __tablename__ = "accumulator_roots"
    
    # Primary key: auto-increment
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Accumulator root value (hex string)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Block number when this root was set
    block: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Parent hash used for replay protection
    hash: Mapped[str] = mapped_column(String(66), nullable=False)  # 0x + 64 hex chars
    
    # Transaction hash that created this root
    tx_hash: Mapped[Optional[str]] = mapped_column(String(66), nullable=True)
    
    # Timestamp when recorded
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    
    # Operation that caused this change
    operation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    def __repr__(self) -> str:
        return f"<AccumulatorRoot(id={self.id}, block={self.block}, value='{self.value[:20]}...')>"


class EventLog(Base):
    """
    Event processing log.
    
    Tracks which blockchain events have been processed to avoid
    duplicate processing and provide audit trail.
    """
    __tablename__ = "event_logs"
    
    # Primary key: auto-increment
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Event type (e.g., "AccumulatorUpdated")
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Block number
    block_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Transaction hash
    tx_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    
    # Log index within transaction
    log_index: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Event data (JSON string)
    event_data: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Processing status
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="processed")
    
    # Processing timestamp
    processed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    
    def __repr__(self) -> str:
        return f"<EventLog(id={self.id}, event_type='{self.event_type}', block={self.block_number})>"
