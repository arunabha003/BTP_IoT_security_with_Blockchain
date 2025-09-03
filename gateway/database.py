"""
Database Connection and Session Management

SQLAlchemy 2.x database setup with async support.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy import event, Engine

from .config import get_settings
from .models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self):
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None
        
    async def initialize(self) -> None:
        """Initialize database connection and create tables."""
        settings = get_settings()
        
        # Convert SQLite URL to async version
        database_url = settings.database_url
        if database_url.startswith("sqlite:///"):
            database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        elif database_url.startswith("sqlite://"):
            database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://")
            
        logger.info(f"Connecting to database: {database_url}")
        
        # Create async engine
        self.engine = create_async_engine(
            database_url,
            echo=settings.log_level == "DEBUG",
            future=True,
        )
        
        # Enable foreign keys for SQLite
        if "sqlite" in database_url:
            @event.listens_for(Engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        
        # Create session factory
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        # Create tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database initialized successfully")
    
    async def close(self) -> None:
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session."""
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")
            
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


# Global database manager instance
db_manager = DatabaseManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with db_manager.get_session() as session:
        yield session


async def init_database() -> None:
    """Initialize database - called on startup."""
    await db_manager.initialize()


async def close_database() -> None:
    """Close database - called on shutdown."""
    await db_manager.close()
