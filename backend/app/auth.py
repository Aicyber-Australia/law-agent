"""Supabase JWT authentication for FastAPI endpoints.

Uses JWKS (JSON Web Key Set) for token verification, which automatically
handles key rotation and supports both ECC (ES256) and legacy HS256 keys.
Falls back to shared secret (HS256) if JWKS is unavailable.
"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient

from app.config import SUPABASE_URL, SUPABASE_JWT_SECRET, logger

security = HTTPBearer()

# JWKS client — fetches public keys from Supabase for asymmetric verification.
# Caches keys and refreshes automatically when needed.
_jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient | None:
    """Lazily initialize the JWKS client."""
    global _jwks_client
    if _jwks_client is None:
        try:
            _jwks_client = PyJWKClient(_jwks_url, cache_keys=True)
            logger.info(f"JWKS client initialized: {_jwks_url}")
        except Exception as e:
            logger.warning(f"Failed to initialize JWKS client: {e}")
    return _jwks_client


def _decode_jwt(token: str) -> dict:
    """Decode and verify a Supabase JWT token.

    Tries JWKS (for ECC/RSA keys) first, falls back to HS256 shared secret.
    """
    # Try JWKS first (handles ECC P-256 and RSA keys)
    jwks = _get_jwks_client()
    if jwks:
        try:
            signing_key = jwks.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256"],
                options={"verify_aud": False},
            )
        except jwt.exceptions.PyJWKClientError as e:
            logger.debug(f"JWKS verification skipped: {e}")
        except jwt.ExpiredSignatureError:
            raise
        except jwt.InvalidTokenError as e:
            logger.debug(f"JWKS token verification failed: {e}")

    # Fall back to HS256 shared secret
    if SUPABASE_JWT_SECRET:
        return jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )

    raise jwt.InvalidTokenError("No valid verification method available")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Validate Supabase JWT and return user info.

    Returns dict with: { "user_id": str, "email": str }
    Raises 401 if token is invalid or expired.
    """
    try:
        payload = _decode_jwt(credentials.credentials)

        user_id = payload.get("sub")
        email = payload.get("email")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        return {"user_id": user_id, "email": email}

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def get_optional_user(request: Request) -> dict | None:
    """
    Extract user from Authorization header if present, otherwise return None.
    Use for endpoints that work both authenticated and unauthenticated.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    try:
        token = auth_header.split(" ", 1)[1]
        payload = _decode_jwt(token)
        return {"user_id": payload.get("sub"), "email": payload.get("email")}
    except Exception:
        return None
