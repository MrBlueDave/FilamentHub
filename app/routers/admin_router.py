"""Admin router for FilamentHub 3D.
Provides CRUD endpoints for users, brand tares, per-user AI settings, and audit log auditing.
Enforces RBAC with require_admin (or require_editor / require_viewer where appropriate).
"""

import sqlite3
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth import (
    get_client_ip,
    hash_password,
    log_security_event,
    require_admin,
    require_editor,
    require_viewer,
)
from app.database import get_db, get_setting, set_setting
from app.models import (
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


def _normalize_role(role: str) -> str:
    """Normalize role string so 'user' or 'viewer' maps to 'editor' (Utente Standard)."""
    r = (role or "editor").strip().lower()
    if r == "admin":
        return "admin"
    return "editor"


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
    """Create a new user account with specified role ('editor' or 'admin')."""
    client_ip = get_client_ip(request)
    username_clean = req.username.strip()
    normalized_role = _normalize_role(req.role)

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
        INSERT INTO users (username, password_hash, role, is_active, gemini_api_key, gemini_model)
        VALUES (?, ?, ?, 1, '', 'gemini-3.5-flash-lite');
        """,
        (username_clean, pwd_hash, normalized_role),
    )
    db.commit()
    new_id = cursor.lastrowid

    log_security_event(
        db,
        client_ip,
        admin_user["username"],
        "USER_CREATE",
        f"Creato utente '{username_clean}' con ruolo '{normalized_role}' (id={new_id})",
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

    normalized_role = _normalize_role(req.role) if req.role is not None else None

    # Protect last active admin from losing admin rights or being deactivated
    if user["role"] == "admin" and user["is_active"]:
        demoting = normalized_role is not None and normalized_role != "admin"
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

    if normalized_role is not None:
        updates.append("role = ?")
        params.append(normalized_role)

    if req.is_active is not None:
        updates.append("is_active = ?")
        params.append(1 if req.is_active else 0)

    if req.password is not None and req.password.strip():
        clean_pwd = req.password.strip()
        if len(clean_pwd) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La nuova password deve contenere almeno 8 caratteri",
            )
        updates.append("password_hash = ?")
        params.append(hash_password(clean_pwd))

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
    """Delete a user account and all their spools. Cannot delete self or last remaining admin."""
    client_ip = get_client_ip(request)

    if admin_user.get("id") == user_id:
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

    # Delete user's spools first, then the user row
    db.execute("DELETE FROM spools WHERE user_id = ?;", (user_id,))
    db.execute("DELETE FROM users WHERE id = ?;", (user_id,))
    db.commit()

    log_security_event(
        db,
        client_ip,
        admin_user["username"],
        "USER_DELETE",
        f"Eliminato utente id={user_id} ({target['username']}) e relativo archivio bobine",
    )

    return {"message": f"Utente {user_id} eliminato con successo"}


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
# Per-User & System Settings
# ==========================================

PLACEHOLDER_GEMINI_KEYS = (
    "",
    "la_tua_api_key_gemini",
    "YOUR_API_KEY",
    "your_gemini_api_key",
)


def _is_valid_gemini_key_format(key: str) -> bool:
    """Return True if the key is a non-empty, non-placeholder, unmasked API key."""
    clean = (key or "").strip()
    if not clean or clean in PLACEHOLDER_GEMINI_KEYS:
        return False
    if "..." in clean or clean.startswith("***"):
        return False
    if len(clean) < 12:
        return False
    return True


def _mask_api_key(key: str) -> str:
    """Mask sensitive API keys for safe display in UI."""
    clean = (key or "").strip()
    if not _is_valid_gemini_key_format(clean):
        return ""
    return f"{clean[:6]}...{clean[-4:]}"


def _build_user_settings_out(db: sqlite3.Connection, user_id: int) -> dict[str, Any]:
    """Read Gemini API key and model directly from the authenticated user's row in users table."""
    cur = db.execute(
        "SELECT gemini_api_key, gemini_model FROM users WHERE id = ?;",
        (user_id,),
    )
    row = cur.fetchone()
    gemini_key = (row["gemini_api_key"] if row and row["gemini_api_key"] else "").strip()
    gemini_model = (row["gemini_model"] if row and row["gemini_model"] else "").strip() or "gemini-3.5-flash-lite"
    is_configured = _is_valid_gemini_key_format(gemini_key)

    return {
        "gemini_configured": is_configured,
        "gemini_api_key_masked": _mask_api_key(gemini_key) if is_configured else "",
        "gemini_model": gemini_model,
        "show_ams_cockpit": get_setting("show_ams_cockpit", "false").strip().lower() in ("true", "1", "yes"),
    }


@router.get("/settings", response_model=SettingsOut)
def get_system_settings(
    current_user: dict[str, Any] = Depends(require_viewer),
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve per-user Gemini settings and system settings with masked API key."""
    return _build_user_settings_out(db, current_user["id"])


@router.put("/settings", response_model=SettingsOut)
def update_system_settings(
    req: SettingsUpdateRequest,
    request: Request,
    current_user: dict[str, Any] = Depends(require_editor),
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    """Update per-user Gemini API Key & model on the current user's row, plus cockpit display."""
    client_ip = get_client_ip(request)
    user_id = current_user["id"]
    updated_fields = []

    if req.gemini_api_key is not None:
        raw_key = req.gemini_api_key.strip()
        if raw_key == "__clear__" or raw_key == "":
            db.execute("UPDATE users SET gemini_api_key = '' WHERE id = ?;", (user_id,))
            db.commit()
            updated_fields.append("gemini_api_key_cleared")
        elif raw_key != "__keep__" and not raw_key.startswith("***"):
            if not _is_valid_gemini_key_format(raw_key):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Chiave API non valida (troppo corta o formato placeholder).",
                )
            db.execute("UPDATE users SET gemini_api_key = ? WHERE id = ?;", (raw_key, user_id))
            db.commit()
            updated_fields.append("gemini_api_key")

    if req.gemini_model is not None:
        model_clean = req.gemini_model.strip() or "gemini-3.5-flash-lite"
        db.execute("UPDATE users SET gemini_model = ? WHERE id = ?;", (model_clean, user_id))
        db.commit()
        updated_fields.append("gemini_model")

    if req.show_ams_cockpit is not None:
        set_setting("show_ams_cockpit", "true" if req.show_ams_cockpit else "false")
        updated_fields.append("show_ams_cockpit")

    log_security_event(
        db,
        client_ip,
        current_user.get("username", "system"),
        "SETTINGS_UPDATE",
        f"Aggiornate impostazioni utente: {', '.join(updated_fields) if updated_fields else 'nessuna modifica'}",
    )

    return _build_user_settings_out(db, user_id)


@router.delete("/settings/gemini-key", response_model=SettingsOut)
def delete_user_gemini_key(
    request: Request,
    current_user: dict[str, Any] = Depends(require_viewer),
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    """Explicitly clear and remove the Gemini API key for the current authenticated user."""
    client_ip = get_client_ip(request)
    user_id = current_user["id"]

    db.execute("UPDATE users SET gemini_api_key = '' WHERE id = ?;", (user_id,))
    db.commit()

    log_security_event(
        db,
        client_ip,
        current_user.get("username", "system"),
        "SETTINGS_UPDATE",
        "Rimossa chiave API Gemini personale",
    )

    return _build_user_settings_out(db, user_id)
