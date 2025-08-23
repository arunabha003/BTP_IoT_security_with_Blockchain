"""
IoT Identity Gateway

FastAPI application for managing IoT device identities using RSA accumulators
and blockchain-based revocation.
"""

import logging
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from .config import get_settings
    from .database import init_database, close_database, get_db_session
    from .blockchain import init_blockchain, close_blockchain, blockchain_client
    from .logging_config import setup_logging, get_logger
    from .middleware import AdminAuthMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
    from .api_routes import router as api_router
except ImportError:
    from config import get_settings
    from database import init_database, close_database, get_db_session
    from blockchain import init_blockchain, close_blockchain, blockchain_client
    from logging_config import setup_logging, get_logger
    from middleware import AdminAuthMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
    from api_routes import router as api_router


# Setup logging first
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized")
        
        # Initialize blockchain client
        await init_blockchain()
        logger.info("Blockchain client initialized")
        
        yield
        
    finally:
        # Cleanup
        logger.info("Shutting down application")
        await close_blockchain()
        await close_database()
        logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="IoT Identity Gateway",
    description="Gateway for managing IoT device identities using RSA accumulators",
    version=get_settings().app_version,
    lifespan=lifespan
)

# Add middleware stack (order matters - last added is executed first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware) 
app.add_middleware(AdminAuthMiddleware)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to all requests."""
    request_id = str(uuid.uuid4())[:8]
    
    # Add to request state
    request.state.request_id = request_id
    
    # Add to logging context
    import logging
    old_factory = logging.getLogRecordFactory()
    
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.request_id = request_id
        return record
    
    logging.setLogRecordFactory(record_factory)
    
    try:
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
        
    finally:
        # Restore original factory
        logging.setLogRecordFactory(old_factory)


@app.get("/healthz", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns:
        dict: Health status information
    """
    logger.info("Health check requested")
    
    # Check database connection
    db_status = "unknown"
    try:
        async with get_db_session() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
            db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    # Check blockchain connection
    blockchain_status = "unknown"
    try:
        if blockchain_client.w3 and blockchain_client.w3.is_connected():
            blockchain_status = "connected"
        else:
            blockchain_status = "disconnected"
    except Exception as e:
        logger.error(f"Blockchain health check failed: {e}")
        blockchain_status = "error"
    
    health_data = {
        "ok": True,
        "service": "iot-identity-gateway",
        "version": get_settings().app_version,
        "database": db_status,
        "blockchain": blockchain_status,
        "contract_loaded": blockchain_client.contract is not None
    }
    
    logger.info(f"Health check result: {health_data}")
    return health_data


@app.get("/root", tags=["Accumulator"])
async def get_accumulator_root() -> Dict[str, str]:
    """
    Get current accumulator root.
    
    Returns the current RSA accumulator root value in hexadecimal format.
    This value represents the cryptographic accumulation of all active
    device identities.
    
    Returns:
        dict: Current accumulator root as hex string
    """
    logger.info("Accumulator root requested")
    
    try:
        current_root = await blockchain_client.get_current_root()
        
        logger.info(f"Returning accumulator root: {current_root}")
        
        return {
            "root": current_root,
            "format": "hex"
        }
        
    except Exception as e:
        logger.error(f"Failed to get accumulator root: {e}")
        return {
            "root": "0x",
            "format": "hex",
            "error": "Failed to retrieve current root"
        }


@app.get("/status", tags=["Status"])
async def get_system_status(
    session: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get detailed system status.
    
    Returns comprehensive status information including database
    and blockchain connectivity.
    
    Returns:
        dict: Detailed system status
    """
    logger.info("System status requested")
    
    settings = get_settings()
    
    status = {
        "service": settings.app_name,
        "version": settings.app_version,
        "config": {
            "rpc_url": settings.rpc_url,
            "contract_address": settings.contract_address,
            "database_url": settings.database_url.split("://")[0] + "://***",
            "log_level": settings.log_level
        },
        "blockchain": {
            "connected": False,
            "latest_block": None,
            "contract_loaded": False
        },
        "database": {
            "connected": False,
            "tables_exist": False
        }
    }
    
    # Check blockchain
    try:
        if blockchain_client.w3:
            status["blockchain"]["connected"] = blockchain_client.w3.is_connected()
            if status["blockchain"]["connected"]:
                status["blockchain"]["latest_block"] = blockchain_client.w3.eth.block_number
        
        status["blockchain"]["contract_loaded"] = blockchain_client.contract is not None
        
    except Exception as e:
        logger.error(f"Blockchain status check failed: {e}")
    
    # Check database
    try:
        from sqlalchemy import text
        await session.execute(text("SELECT 1"))
        status["database"]["connected"] = True
        status["database"]["tables_exist"] = True
        
    except Exception as e:
        logger.error(f"Database status check failed: {e}")
    
    logger.info(f"System status: {status}")
    return status


# Include API routes
app.include_router(api_router, prefix="", tags=["Extended API"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.error(f"Unhandled exception in request {request_id}: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": request_id,
            "detail": str(exc) if get_settings().log_level == "DEBUG" else "An error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "gateway.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None,  # Use our custom logging
        access_log=False,  # Disable default access logs
    )
