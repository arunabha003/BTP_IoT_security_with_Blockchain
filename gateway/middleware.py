"""
Middleware Components

Security middleware for authentication, rate limiting, and request validation.
"""

import logging
from typing import Callable, Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import get_settings
from .utils import constant_time_compare, ip_rate_limiter, device_rate_limiter

logger = logging.getLogger(__name__)


class AdminAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce admin authentication on protected routes.
    
    Requires 'x-admin-key' header to match configured ADMIN_KEY.
    """
    
    def __init__(self, app: Callable):
        super().__init__(app)
        self.settings = get_settings()
        
        # Routes that require admin auth
        self.protected_routes = {
            '/accumulator/update',
            '/enroll', 
            '/revoke'
        }
        
        # Routes that require admin auth (by prefix)
        self.protected_prefixes = [
            '/admin'
        ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request through admin auth middleware."""
        # Check if route requires admin auth
        if self._requires_admin_auth(request):
            if not self._validate_admin_key(request):
                logger.warning(f"Unauthorized admin access attempt: {request.url.path}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "Unauthorized",
                        "detail": "Valid admin key required",
                        "code": "ADMIN_KEY_REQUIRED"
                    }
                )
        
        # Continue to next middleware/handler
        response = await call_next(request)
        return response
    
    def _requires_admin_auth(self, request: Request) -> bool:
        """Check if request path requires admin authentication."""
        path = request.url.path
        
        # Skip GET requests to non-sensitive endpoints
        if request.method == "GET" and path not in {'/admin', '/accumulator'}:
            return False
        
        # Check exact matches
        if path in self.protected_routes:
            return True
        
        # Check prefixes
        for prefix in self.protected_prefixes:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _validate_admin_key(self, request: Request) -> bool:
        """Validate admin key from request headers."""
        if not self.settings.admin_key:
            logger.warning("Admin key not configured - rejecting admin request")
            return False
        
        # Get admin key from header
        provided_key = request.headers.get('x-admin-key')
        if not provided_key:
            return False
        
        # Constant-time comparison to prevent timing attacks
        return constant_time_compare(provided_key, self.settings.admin_key)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting requests by IP and device.
    """
    
    def __init__(self, app: Callable):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request through rate limiting middleware."""
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check IP rate limit
        if not ip_rate_limiter.is_allowed(client_ip):
            logger.warning(f"IP rate limit exceeded: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "detail": "Too many requests from this IP",
                    "code": "IP_RATE_LIMIT"
                }
            )
        
        # Check device-specific rate limit for auth endpoints
        if request.url.path.startswith('/auth') or request.url.path in {'/enroll', '/revoke'}:
            device_id = self._extract_device_id(request)
            if device_id:
                if not device_rate_limiter.is_allowed(device_id):
                    logger.warning(f"Device rate limit exceeded: {device_id}")
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "error": "Rate limit exceeded", 
                            "detail": "Too many requests for this device",
                            "code": "DEVICE_RATE_LIMIT"
                        }
                    )
        
        # Continue to next middleware/handler
        response = await call_next(request)
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for forwarded IP headers (reverse proxy)
        forwarded_ip = request.headers.get('x-forwarded-for')
        if forwarded_ip:
            return forwarded_ip.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip.strip()
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"
    
    def _extract_device_id(self, request: Request) -> Optional[str]:
        """Extract device ID from request for rate limiting."""
        # From query parameters
        device_id = request.query_params.get('device_id')
        if device_id:
            return device_id
        
        # From JSON body (for POST requests)
        if hasattr(request, '_json'):
            json_body = getattr(request, '_json', {})
            if isinstance(json_body, dict):
                return json_body.get('device_id')
        
        return None


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to responses.
    """
    
    def __init__(self, app: Callable):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add security headers
        response.headers.update({
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        })
        
        return response


def create_error_response(
    status_code: int,
    error: str,
    detail: str,
    code: Optional[str] = None,
    request_id: Optional[str] = None
) -> JSONResponse:
    """
    Create standardized error response.
    
    Args:
        status_code: HTTP status code
        error: Error type
        detail: Error description
        code: Error code for client handling
        request_id: Request ID for tracing
        
    Returns:
        JSONResponse: Formatted error response
    """
    content = {
        "error": error,
        "detail": detail
    }
    
    if code:
        content["code"] = code
    
    if request_id:
        content["request_id"] = request_id
    
    return JSONResponse(
        status_code=status_code,
        content=content
    )
