"""
Gateway Configuration

Environment-based configuration for the IoT identity gateway.
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # Blockchain connection
    rpc_url: str = Field(
        default="http://127.0.0.1:8545",
        env="RPC_URL",
        description="Ethereum RPC endpoint URL"
    )
    
    contract_address: Optional[str] = Field(
        default=None,
        env="CONTRACT_ADDRESS", 
        description="AccumulatorRegistry contract address"
    )
    
    # Authentication
    admin_key: Optional[str] = Field(
        default=None,
        env="ADMIN_KEY",
        description="Admin key for protected routes"
    )
    
    # Database
    database_url: str = Field(
        default="sqlite:///./gateway.db",
        env="DATABASE_URL",
        description="Database connection URL"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="Logging level"
    )
    
    log_format: str = Field(
        default="json",
        env="LOG_FORMAT", 
        description="Log format: json or text"
    )
    
    # Application
    app_name: str = Field(
        default="IoT Identity Gateway",
        env="APP_NAME"
    )
    
    app_version: str = Field(
        default="1.0.0",
        env="APP_VERSION"
    )
    
    # Event monitoring
    event_poll_interval: int = Field(
        default=5,
        env="EVENT_POLL_INTERVAL",
        description="Event polling interval in seconds"
    )
    
    # Contract ABI path
    contracts_out_dir: str = Field(
        default="./contracts/out",
        env="CONTRACTS_OUT_DIR",
        description="Directory containing contract build artifacts"
    )

    # Transaction mode
    simulate_transactions: bool = Field(
        default=True,
        env="SIMULATE_TRANSACTIONS",
        description="Whether to simulate blockchain transactions (for development)"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
