"""Authentication, authorization, rate limiting, and security logging module for FilamentHub 3D."""

import hashlib
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status

from app.config import (
    SECRET_KEY,
    SECURITY_LOG_PATH,
)
from app.database import get_db

JWT_ALGORITHM = "HS256"
JWT_COOKIE_NAME = "fh_access_token"
JWT_EXPIRE_DAYS = 7

# Argon2 password hasher instance
_hasher = PasswordHasher()

# In-memory sliding window rate limiter: client_ip -> list of failure timestamps
_failed_login_attempts: dict[str, list[float]] = {}
RATE_LIMIT_WINDOW_SECONDS = 900  # 15 minutes
MAX_FAILED_ATTEMPTS = 5


def get_client_ip(request: Request) -> str:
    """Extract real client IP behind reverse proxy (e.g. Nginx Proxy Manager)."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # First IP in the comma-separated list is the client IP
        ip = forwarded_for.split(",")[0].strip()
        if ip:
            return ip

    real_ip = request.headers.get("X-Real-IP")
    if real_ip and real_ip.strip():
        return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host.strip()

    return "127.0.0.1"


def check_login_rate_limit(client_ip: str) -> None:
    """Check if the client IP has exceeded the allowed failed login attempts."""
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS

    attempts = _failed_login_attempts.get(client_ip, [])
    # Clean up expired timestamps
    recent_attempts = [ts for ts in attempts if ts > cutoff]
    _failed_login_attempts[client_ip] = recent_attempts

    if len(recent_attempts) >= MAX_FAILED_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too Many Requests - Troppi tentativi di login falliti. Riprova tra 15 minuti.",
        )


def record_login_failure(client_ip: str) -> None:
    """Record a failed login attempt for the client IP."""
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS
    attempts = _failed_login_attempts.get(client_ip, [])
    recent_attempts = [ts for ts in attempts if ts > cutoff]
    recent_attempts.append(now)
    _failed_login_attempts[client_ip] = recent_attempts


def clear_login_rate_limit(client_ip: str) -> None:
    """Clear failed login attempts for a client IP upon successful authentication."""
    if client_ip in _failed_login_attempts:
        _failed_login_attempts.pop(client_ip, None)


def log_security_event(
    conn: Any,
    client_ip: str,
    username: str,
    action: str,
    details: str = "",
    is_auth_fail: bool = False,
) -> None:
    """Log security events to database audit_logs table and append formatted auth fails to security.log and stdout."""
    # Insert structured event in audit_logs
    try:
        if conn is not None:
            conn.execute(
                """
                INSERT INTO audit_logs (client_ip, username, action, details)
                VALUES (?, ?, ?, ?);
                """,
                (client_ip, username, action, details),
            )
            conn.commit()
    except Exception as e:
        print(f"[ERROR] Failed to insert audit log: {e}", flush=True)

    # If auth failure, write structured syslog-style line to stdout and security.log
    if is_auth_fail:
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        log_line = (
            f"{now_iso} [FILAMENTHUB_AUTH_FAIL] [AUTH_FAIL] "
            f"ip={client_ip} client_ip={client_ip} "
            f"user={username} username={username} reason={details}"
        )
        print(log_line, flush=True)
        try:
            with open(SECURITY_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
        except Exception as e:
            print(f"[ERROR] Failed to write to {SECURITY_LOG_PATH}: {e}", flush=True)


def hash_password(password: str) -> str:
    """Hash password using Argon2id."""
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Verify password against Argon2 hash."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def hash_api_token(raw_token: str) -> str:
    """Hash raw API token using SHA-256."""
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=JWT_EXPIRE_DAYS)

    to_encode.update({"iat": now, "exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_current_user(
    request: Request,
    db: Any = Depends(get_db),
) -> dict[str, Any]:
    """FastAPI dependency to authenticate requests via JWT Cookie or X-API-Key header."""
    # 1. Check HttpOnly Cookie first
    cookie_token = request.cookies.get(JWT_COOKIE_NAME)
    if cookie_token:
        payload = decode_access_token(cookie_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token di sessione non valido o scaduto",
            )

        user_id = payload.get("user_id")
        cursor = db.execute(
            "SELECT id, username, role, is_active FROM users WHERE id = ?;",
            (user_id,),
        )
        user = cursor.fetchone()
        if not user or not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utente non trovato o account disattivato",
            )

        return {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "auth_type": "jwt",
        }

    # 2. Check X-API-Key Header fallback
    api_key_header = request.headers.get("X-API-Key")
    if api_key_header:
        token_hash = hash_api_token(api_key_header)
        cursor = db.execute(
            "SELECT id, name, role FROM api_tokens WHERE token_hash = ?;",
            (token_hash,),
        )
        token_row = cursor.fetchone()
        if token_row:
            # Update last_used_at with parameterized query
            db.execute(
                "UPDATE api_tokens SET last_used_at = datetime('now') WHERE id = ?;",
                (token_row["id"],),
            )
            db.commit()
            return {
                "id": token_row["id"],
                "username": token_row["name"],
                "role": token_row["role"],
                "auth_type": "api_key",
            }
        else:
            client_ip = get_client_ip(request)
            log_security_event(
                db,
                client_ip,
                "api_key",
                "API_AUTH_FAIL",
                "invalid_api_key",
                is_auth_fail=True,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API Key non valida",
            )

    # 3. No credentials provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autenticazione richiesta",
    )


def require_role(allowed_roles: list[str]) -> Callable[..., dict[str, Any]]:
    """Factory dependency to enforce Role-Based Access Control (RBAC)."""
    def role_dependency(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permessi insufficienti: richiesto uno dei seguenti ruoli {allowed_roles}",
            )
        return current_user

    return role_dependency


require_viewer = require_role(["viewer", "editor", "admin"])
require_editor = require_role(["editor", "admin"])
require_admin = require_role(["admin"])
