"""Authentication middleware for Supabase JWT validation."""
from typing import Optional
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from .config import settings


# Security scheme for Swagger UI
security = HTTPBearer(auto_error=False)


class AuthenticatedUser:
    """Represents an authenticated user from Supabase."""

    def __init__(self, user_id: str, email: Optional[str] = None):
        self.user_id = user_id
        self.email = email

    def __repr__(self):
        return f"AuthenticatedUser(user_id={self.user_id}, email={self.email})"


def decode_jwt(token: str) -> dict:
    """
    Decode and validate a Supabase JWT token.

    For Supabase JWTs, we need the JWT secret from the project settings.
    The token contains: sub (user_id), email, role, etc.
    """
    try:
        # Supabase JWTs use HS256 with the JWT secret
        # For now, we'll decode without verification for development
        # In production, you should verify with the JWT secret
        payload = jwt.decode(
            token,
            options={"verify_signature": False},  # TODO: Add proper verification in production
            algorithms=["HS256"]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> AuthenticatedUser:
    """
    FastAPI dependency to get the current authenticated user.

    Usage:
        @router.get("/protected")
        async def protected_route(user: AuthenticatedUser = Depends(get_current_user)):
            return {"user_id": user.user_id}
    """
    # Check for token in Authorization header
    token = None

    if credentials:
        token = credentials.credentials
    else:
        # Also check for token in query params (for SSE connections)
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Please provide a valid token."
        )

    # Decode the JWT
    payload = decode_jwt(token)

    # Extract user info from Supabase JWT
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing user ID")

    email = payload.get("email")

    return AuthenticatedUser(user_id=user_id, email=email)


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[AuthenticatedUser]:
    """
    FastAPI dependency to optionally get the current user.
    Returns None if not authenticated instead of raising an error.

    Useful for endpoints that work with or without auth.
    """
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None


# =============================================================================
# Helper to extract user_id from request (for use in non-dependency contexts)
# =============================================================================

def get_user_id_from_token(token: str) -> Optional[str]:
    """Extract user_id from a JWT token. Returns None if invalid."""
    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False},
            algorithms=["HS256"]
        )
        return payload.get("sub")
    except Exception:
        return None
