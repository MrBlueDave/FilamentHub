"""Authentication router for FilamentHub 3D.
Handles login, logout, current user profile, and password changes.
Strictly NO public registration endpoint.
"""

import sqlite3
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.auth import (
    JWT_COOKIE_NAME,
    check_login_rate_limit,
    clear_login_rate_limit,
    create_access_token,
    get_client_ip,
    get_current_user,
    hash_password,
    log_security_event,
    record_login_failure,
    verify_password,
)
from app.config import COOKIE_SECURE
from app.database import get_db
from app.models import LoginRequest, PasswordChangeRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    """Authenticate user with username and password, issuing an HttpOnly JWT cookie."""
    client_ip = get_client_ip(request)

    # Check sliding window rate limit
    check_login_rate_limit(client_ip)

    # Lookup user
    cursor = db.execute(
        "SELECT id, username, password_hash, role, is_active FROM users WHERE username = ?;",
        (req.username.strip(),),
    )
    user = cursor.fetchone()

    # Verify credentials
    if not user or not user["is_active"] or not verify_password(user["password_hash"], req.password):
        record_login_failure(client_ip)
        log_security_event(
            db,
            client_ip,
            req.username.strip(),
            "LOGIN_FAILED",
            "invalid_credentials",
            is_auth_fail=True,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenziali non valide o utente disattivato",
        )

    # Success: clear rate limit counter and log event
    clear_login_rate_limit(client_ip)
    log_security_event(
        db,
        client_ip,
        user["username"],
        "LOGIN_SUCCESS",
        "Autenticazione riuscita",
        is_auth_fail=False,
    )

    # Issue JWT token
    token = create_access_token(
        {
            "sub": user["username"],
            "user_id": user["id"],
            "role": user["role"],
        }
    )

    # Set HttpOnly SameSite=Lax cookie
    response.set_cookie(
        key=JWT_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=86400 * 7,  # 7 days
        path="/",
    )

    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "message": "Login effettuato con successo",
    }


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    """Log out current user by clearing the HttpOnly session cookie."""
    response.delete_cookie(
        key=JWT_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
    )
    return {"message": "Logout effettuato con successo"}


@router.get("/me")
def get_me(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Return profile details of the currently authenticated user or token."""
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "role": current_user["role"],
        "auth_type": current_user["auth_type"],
    }


@router.post("/change-password")
def change_password(
    req: PasswordChangeRequest,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, str]:
    """Allow an authenticated user to change their account password."""
    if current_user.get("auth_type") == "api_key":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossibile modificare la password utente tramite autenticazione con API Key",
        )

    client_ip = get_client_ip(request)

    cursor = db.execute(
        "SELECT id, username, password_hash FROM users WHERE id = ?;",
        (current_user["id"],),
    )
    user = cursor.fetchone()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utente non trovato",
        )

    if not verify_password(user["password_hash"], req.current_password):
        log_security_event(
            db,
            client_ip,
            current_user["username"],
            "PASSWORD_CHANGE_FAIL",
            "wrong_current_password",
            is_auth_fail=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La password attuale non è corretta",
        )

    new_hash = hash_password(req.new_password)
    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?;",
        (new_hash, current_user["id"]),
    )
    db.commit()

    log_security_event(
        db,
        client_ip,
        current_user["username"],
        "PASSWORD_CHANGE",
        "Password modificata con successo",
        is_auth_fail=False,
    )

    return {"message": "Password aggiornata con successo"}
