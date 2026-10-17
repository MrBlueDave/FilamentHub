"""Admin router for FilamentHub 3D.
Provides CRUD endpoints for users, API tokens, brand tares, and audit log auditing.
Enforces RBAC with require_admin (or require_editor / require_viewer where appropriate).
"""

import secrets
import sqlite3
from typing import Any, List
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth import (
    get_client_ip,
    hash_api_token,
    hash_password,
    log_security_event,
    require_admin,
    require_editor,
    require_viewer,
)
from app.database import get_db, get_setting, set_setting
from app.models import (
    ApiTokenCreatedOut,
    ApiTokenCreateRequest,
    ApiTokenOut,
    AuditLogOut,
    BrandTareCreate,
    BrandTareOut,
    SettingsOut,
    SettingsUpdateRequest,
    UserCreateRequest,
    UserOut,
    UserUpdateRequest,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ==========================================
# User Management (Admin Only)
# ==========================================

@router.get("/users", response_model=List[UserOut])
def list_users(
    _admin: dict[str, Any] = Depends(require_admin),
    db: sqlite3.Connection = Depends(get_db),
) -> List[dict[str, Any]]:
    """List all user accounts."""
    cursor = db.execute(
        "SELECT id, username, role, is_active, created_at FROM users ORDER BY id ASC;"
    )
    return [dict(row) for row in cursor.fetchall()]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    req: UserCreateRequest,
    request: Request,
    admin_user: dict[str, Any] = Depends(require_admin),
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    """Create a new user account with specified role."""
    client_ip = get_client_ip(request)
    username_clean = req.username.strip()

    # Check unique username
    cursor = db.execute("SELECT id FROM users WHERE username = ?;", (username_clean,))
    if cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lo username '{username_clean}' è già in uso",
        )

    pwd_hash = hash_password(req.password)
    cursor = db.execute(
        """
        INSERT INTO users (username, password_hash, role, is_active)
        VALUES (?, ?, ?, 1);
        """,
        (username_clean, pwd_hash, req.role),
    )
    db.commit()
    new_id = cursor.lastrowid

    log_security_event(
        db,
        client_ip,
        admin_user["username"],
        "USER_CREATE",
        f"Creato utente '{username_clean}' con ruolo '{req.role}' (id={new_id})",
    )

    fetch_cursor = db.execute(
        "SELECT id, username, role, is_active, created_at FROM users WHERE id = ?;",
        (new_id,),
    )
    return dict(fetch_cursor.fetchone())


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    req: UserUpdateRequest,
    request: Request,
    admin_user: dict[str, Any] = Depends(require_admin),
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    """Update user role, active status, or reset password."""
    client_ip = get_client_ip(request)

    cursor = db.execute(
        "SELECT id, username, role, is_active FROM users WHERE id = ?;",
        (user_id,),
    )
    user = cursor.fetchone()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Utente {user_id} non trovato",
        )

    # Protect last active admin from losing admin rights or being deactivated
    if user["role"] == "admin" and user["is_active"]:
        demoting = req.role is not None and req.role != "admin"
        deactivating = req.is_active is False
        if demoting or deactivating:
            count_cursor = db.execute(
                "SELECT COUNT(*) AS count FROM users WHERE role = 'admin' AND is_active = 1;"
            )
            active_admin_count = count_cursor.fetchone()["count"]
            if active_admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Impossibile disattivare o rimuovere il ruolo di amministratore all'ultimo admin attivo",
                )

    updates = []
    params = []

    if req.role is not None:
        updates.append("role = ?")
        params.append(req.role)

    if req.is_active is not None:
        updates.append("is_active = ?")
        params.append(1 if req.is_active else 0)

    if req.password is not None and req.password.strip():
        updates.append("password_hash = ?")
        params.append(hash_password(req.password.strip()))

    if updates:
        params.append(user_id)
        db.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = ?;",  # safe: column names are hardcoded
            params,
        )
        db.commit()

        log_security_event(
            db,
            client_ip,
            admin_user["username"],
            "USER_UPDATE",
            f"Aggiornato utente id={user_id} ({user['username']})",
        )

    fetch_cursor = db.execute(
        "SELECT id, username, role, is_active, created_at FROM users WHERE id = ?;",
        (user_id,),
    )
    return dict(fetch_cursor.fetchone())


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    admin_user: dict[str, Any] = Depends(require_admin),
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, str]:
    """Delete a user account. Cannot delete self or last remaining admin."""
    client_ip = get_client_ip(request)

    if admin_user.get("auth_type") == "jwt" and admin_user.get("id") == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Non puoi eliminare il tuo stesso account utente",
        )

    cursor = db.execute(
        "SELECT id, username, role, is_active FROM users WHERE id = ?;",
        (user_id,),
    )
    target = cursor.fetchone()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Utente {user_id} non trovato",
        )

    if target["role"] == "admin" and target["is_active"]:
        count_cursor = db.execute(
            "SELECT COUNT(*) AS count FROM users WHERE role = 'admin' AND is_active = 1;"
        )
        if count_cursor.fetchone()["count"] <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossibile eliminare l'ultimo amministratore attivo del sistema",
            )

    db.execute("DELETE FROM users WHERE id = ?;", (user_id,))
    db.commit()

    log_security_event(
        db,
        client_ip,
        admin_user["username"],
        "USER_DELETE",
        f"Eliminato utente id={user_id} ({target['username']})",
    )

    return {"message": f"Utente {user_id} eliminato con successo"}


# ==========================================
# API Token Management (Admin Only)
# ==========================================

@router.get("/tokens", response_model=List[ApiTokenOut])
def list_api_tokens(
    _admin: dict[str, Any] = Depends(require_admin),
    db: sqlite3.Connection = Depends(get_db),
) -> List[dict[str, Any]]:
    """List all API tokens (hashes are never returned)."""
    cursor = db.execute(
        "SELECT id, name, token_prefix, role, last_used_at, created_at FROM api_tokens ORDER BY id DESC;"
    )
    return [dict(row) for row in cursor.fetchall()]


@router.post("/tokens", response_model=ApiTokenCreatedOut, status_code=status.HTTP_201_CREATED)
def create_api_token(
    req: ApiTokenCreateRequest,
    request: Request,
    admin_user: dict[str, Any] = Depends(require_admin),
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    """Generate a new API token. The raw token is returned once and cannot be retrieved again."""
    client_ip = get_client_ip(request)

    raw_secret = secrets.token_urlsafe(32)
    raw_token = f"fhub_{raw_secret}"
    token_prefix = f"{raw_token[:10]}..."
    token_hash = hash_api_token(raw_token)

    creator_id = admin_user.get("id") if admin_user.get("auth_type") == "jwt" else None

    cursor = db.execute(
        """
        INSERT INTO api_tokens (name, token_hash, token_prefix, role, created_by)
        VALUES (?, ?, ?, ?, ?);
        """,
        (req.name.strip(), token_hash, token_prefix, req.role, creator_id),
    )
    db.commit()
    new_id = cursor.lastrowid

    log_security_event(
        db,
        client_ip,
        admin_user["username"],
        "TOKEN_CREATE",
        f"Creato token API '{req.name}' con ruolo '{req.role}' (id={new_id})",
    )

    fetch_cursor = db.execute(
        "SELECT id, name, token_prefix, role, created_at FROM api_tokens WHERE id = ?;",
        (new_id,),
    )
    data = dict(fetch_cursor.fetchone())
    data["raw_token"] = raw_token
    return data


@router.delete("/tokens/{token_id}")
def delete_api_token(
    token_id: int,
    request: Request,
    admin_user: dict[str, Any] = Depends(require_admin),
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, str]:
    """Revoke and delete an API token."""
    client_ip = get_client_ip(request)

    cursor = db.execute("SELECT id, name FROM api_tokens WHERE id = ?;", (token_id,))
    target = cursor.fetchone()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Token {token_id} non trovato",
        )

    db.execute("DELETE FROM api_tokens WHERE id = ?;", (token_id,))
    db.commit()

    log_security_event(
        db,
        client_ip,
        admin_user["username"],
        "TOKEN_DELETE",
        f"Revocato token API id={token_id} ({target['name']})",
    )

    return {"message": f"Token {token_id} revocato con successo"}


# ==========================================
# Brand Tares Management (Viewer/Editor/Admin)
# ==========================================

@router.get("/tares", response_model=List[BrandTareOut])
def list_brand_tares(
    _viewer: dict[str, Any] = Depends(require_viewer),
    db: sqlite3.Connection = Depends(get_db),
) -> List[dict[str, Any]]:
    """List all registered brand empty spool tare weights. Accessible to any authenticated user."""
    cursor = db.execute(
        "SELECT id, brand_name, spool_material, tare_weight_g, notes FROM brands_tare ORDER BY brand_name ASC, spool_material ASC;"
    )
    return [dict(row) for row in cursor.fetchall()]


@router.post("/tares", response_model=BrandTareOut)
def upsert_brand_tare(
    req: BrandTareCreate,
    request: Request,
    editor_user: dict[str, Any] = Depends(require_editor),
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    """Create or update a brand tare entry (upsert on brand_name + spool_material)."""
    client_ip = get_client_ip(request)
    brand_clean = req.brand_name.strip()
    spool_mat_clean = req.spool_material.strip() or "Plastic"

    db.execute(
        """
        INSERT INTO brands_tare (brand_name, spool_material, tare_weight_g, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(brand_name, spool_material) DO UPDATE SET
            tare_weight_g = excluded.tare_weight_g,
            notes = excluded.notes;
        """,
        (brand_clean, spool_mat_clean, req.tare_weight_g, req.notes or ""),
    )
    db.commit()

    log_security_event(
        db,
        client_ip,
        editor_user["username"],
        "TARE_UPSERT",
        f"Salvata tara {brand_clean} ({spool_mat_clean}) -> {req.tare_weight_g}g",
    )

    cursor = db.execute(
        "SELECT id, brand_name, spool_material, tare_weight_g, notes FROM brands_tare WHERE brand_name = ? AND spool_material = ?;",
        (brand_clean, spool_mat_clean),
    )
    return dict(cursor.fetchone())


@router.delete("/tares/{tare_id}")
def delete_brand_tare(
    tare_id: int,
    request: Request,
    admin_user: dict[str, Any] = Depends(require_admin),
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, str]:
    """Delete a brand tare entry (Admin only)."""
    client_ip = get_client_ip(request)

    cursor = db.execute("SELECT id, brand_name FROM brands_tare WHERE id = ?;", (tare_id,))
    target = cursor.fetchone()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tara {tare_id} non trovata",
        )

    db.execute("DELETE FROM brands_tare WHERE id = ?;", (tare_id,))
    db.commit()

    log_security_event(
        db,
        client_ip,
        admin_user["username"],
        "TARE_DELETE",
        f"Eliminata tara id={tare_id} ({target['brand_name']})",
    )

    return {"message": f"Tara {tare_id} eliminata con successo"}


# ==========================================
# Audit Logs (Admin Only)
# ==========================================

@router.get("/audit-logs", response_model=List[AuditLogOut])
def get_audit_logs(
    _admin: dict[str, Any] = Depends(require_admin),
    db: sqlite3.Connection = Depends(get_db),
) -> List[dict[str, Any]]:
    """Retrieve the latest 200 security and audit logs."""
    cursor = db.execute(
        "SELECT id, timestamp, client_ip, username, action, details FROM audit_logs ORDER BY id DESC LIMIT 200;"
    )
    return [dict(row) for row in cursor.fetchall()]


# ==========================================
# System Settings (Viewer / Editor / Admin)
# ==========================================

PLACEHOLDER_GEMINI_KEYS = (
    "",
    "la_tua_api_key_gemini",
    "YOUR_API_KEY",
    "your_gemini_api_key",
)


def _is_valid_gemini_key_format(key: str) -> bool:
    """Return True only if the key looks like a real unmasked Google Gemini API key."""
    clean = (key or "").strip()
    if not clean or clean in PLACEHOLDER_GEMINI_KEYS:
        return False
    if "..." in clean or "*" in clean:
        return False
    if not clean.startswith("AIza") or len(clean) < 30:
        return False
    return True


def _verify_gemini_key_online(key: str) -> bool:
    """Verify the Gemini API key against Google AI Studio models endpoint."""
    if not _is_valid_gemini_key_format(key):
        return False
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key.strip()}"
    try:
        with httpx.Client(timeout=6.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                return True
            if resp.status_code in (400, 401, 403):
                return False
            # On 5xx or transient network issue, fallback to strict format validation
            return True
    except httpx.RequestError:
        return _is_valid_gemini_key_format(key)


def _mask_api_key(key: str) -> str:
    """Mask sensitive API keys for safe display in UI."""
    clean = (key or "").strip()
    if not _is_valid_gemini_key_format(clean):
        return ""
    return f"{clean[:6]}...{clean[-4:]}"


@router.get("/settings", response_model=SettingsOut)
def get_system_settings(
    _user: dict[str, Any] = Depends(require_viewer),
) -> dict[str, Any]:
    """Retrieve system settings with masked API keys. Accessible to all authenticated users."""
    gemini_key = get_setting("gemini_api_key", "").strip()
    is_configured = _is_valid_gemini_key_format(gemini_key)

    return {
        "gemini_configured": is_configured,
        "gemini_api_key_masked": _mask_api_key(gemini_key) if is_configured else "",
        "gemini_model": get_setting("gemini_model", "gemini-2.5-flash").strip() or "gemini-2.5-flash",
        "ha_webhook_url": get_setting("ha_webhook_url", "").strip(),
        "show_ams_cockpit": get_setting("show_ams_cockpit", "false").strip().lower() in ("true", "1", "yes"),
    }


@router.put("/settings", response_model=SettingsOut)
def update_system_settings(
    req: SettingsUpdateRequest,
    request: Request,
    editor_user: dict[str, Any] = Depends(require_editor),
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    """Update system settings (Gemini API Key, model, Home Assistant webhook, cockpit display)."""
    client_ip = get_client_ip(request)
    updated_fields = []

    if req.gemini_api_key is not None:
        raw_key = req.gemini_api_key.strip()
        if raw_key == "__clear__":
            set_setting("gemini_api_key", "")
            updated_fields.append("gemini_api_key_cleared")
        elif raw_key and not raw_key.startswith("***") and raw_key != "__keep__":
            if not _is_valid_gemini_key_format(raw_key):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formato chiave API Gemini non valido. Deve iniziare con 'AIza' ed essere una chiave Google AI Studio completa.",
                )
            if not _verify_gemini_key_online(raw_key):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Chiave API Gemini rifiutata da Google (API_KEY_INVALID). Verifica di aver copiato una chiave valida da Google AI Studio.",
                )
            set_setting("gemini_api_key", raw_key)
            updated_fields.append("gemini_api_key")

    if req.gemini_model is not None:
        model_clean = req.gemini_model.strip() or "gemini-2.5-flash"
        set_setting("gemini_model", model_clean)
        updated_fields.append("gemini_model")

    if req.ha_webhook_url is not None:
        set_setting("ha_webhook_url", req.ha_webhook_url.strip())
        updated_fields.append("ha_webhook_url")

    if req.show_ams_cockpit is not None:
        set_setting("show_ams_cockpit", "true" if req.show_ams_cockpit else "false")
        updated_fields.append("show_ams_cockpit")

    log_security_event(
        db,
        client_ip,
        editor_user.get("username", "system"),
        "SETTINGS_UPDATE",
        f"Aggiornate impostazioni di sistema: {', '.join(updated_fields) if updated_fields else 'nessuna modifica'}",
    )

    gemini_key = get_setting("gemini_api_key", "").strip()
    is_configured = _is_valid_gemini_key_format(gemini_key)

    return {
        "gemini_configured": is_configured,
        "gemini_api_key_masked": _mask_api_key(gemini_key) if is_configured else "",
        "gemini_model": get_setting("gemini_model", "gemini-2.5-flash").strip() or "gemini-2.5-flash",
        "ha_webhook_url": get_setting("ha_webhook_url", "").strip(),
        "show_ams_cockpit": get_setting("show_ams_cockpit", "false").strip().lower() in ("true", "1", "yes"),
    }
