"""SQLite native database access layer for FilamentHub 3D.
Enforces WAL mode, foreign keys, and parameterized queries.
Includes system settings persistence, migrations, and comprehensive filament presets.
"""

import os
import re
import sqlite3
from typing import Generator
from argon2 import PasswordHasher

from app.config import (
    DB_PATH,
    ENV_PATH,
    INITIAL_ADMIN_USER,
    INITIAL_ADMIN_PASSWORD,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    HA_WEBHOOK_URL,
)
from app.catalog_seed import BRANDS_TARE_SEED, FILAMENT_CATALOG_SEED


def get_db_connection() -> sqlite3.Connection:
    """Create a new SQLite connection with WAL mode and foreign keys enabled."""
    conn = sqlite3.connect(str(DB_PATH), timeout=20.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency for database session management."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()


def get_setting(key: str, default: str = "") -> str:
    """
    Reads setting from system_settings table, falling back to app.config env variable if empty.
    """
    val: str = ""
    try:
        conn = get_db_connection()
        try:
            cur = conn.execute("SELECT value FROM system_settings WHERE key = ?;", (key,))
            row = cur.fetchone()
            if row and row["value"] is not None:
                val = str(row["value"]).strip()
        finally:
            conn.close()
    except Exception:
        val = ""

    if val:
        return val

    # Fallback to app.config / env defaults
    if key == "gemini_api_key":
        return (GEMINI_API_KEY or default).strip()
    elif key == "gemini_model":
        return (GEMINI_MODEL or default).strip() or "gemini-2.5-flash"
    elif key == "ha_webhook_url":
        return (HA_WEBHOOK_URL or default).strip()
    elif key == "show_ams_cockpit":
        return default or "false"

    return default


def set_setting(key: str, value: str) -> None:
    """
    Upserts setting into system_settings table and also updates .env file if writable,
    ensuring immediate runtime persistence across restarts.
    """
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO system_settings (key, value, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = datetime('now');
            """,
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()

    # Sync into runtime environment variables
    env_key_map = {
        "gemini_api_key": "GEMINI_API_KEY",
        "gemini_model": "GEMINI_MODEL",
        "ha_webhook_url": "HA_WEBHOOK_URL",
        "show_ams_cockpit": "SHOW_AMS_COCKPIT",
    }
    env_var = env_key_map.get(key, key.upper())
    os.environ[env_var] = value

    # Persist to .env file if available
    try:
        if ENV_PATH.exists():
            content = ENV_PATH.read_text(encoding="utf-8")
            pattern = re.compile(rf"^{re.escape(env_var)}=(.*)$", re.MULTILINE)
            if pattern.search(content):
                new_content = pattern.sub(f"{env_var}={value}", content)
            else:
                new_content = content.rstrip() + f"\n{env_var}={value}\n"
            ENV_PATH.write_text(new_content, encoding="utf-8")
    except Exception:
        # Even if .env cannot be written, system_settings in SQLite holds the persistent truth
        pass


def init_db() -> None:
    """Initialize database tables, indexes, safe migrations, and seed initial presets."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # 1. system_settings table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )

        # 2. users table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('viewer', 'editor', 'admin')) DEFAULT 'viewer',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )

        # 3. api_tokens table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS api_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                token_hash TEXT UNIQUE NOT NULL,
                token_prefix TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('viewer', 'editor', 'admin')) DEFAULT 'editor',
                created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                last_used_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )

        # 4. brands_tare table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS brands_tare (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand_name TEXT NOT NULL,
                spool_material TEXT NOT NULL DEFAULT 'Plastic',
                tare_weight_g INTEGER NOT NULL,
                notes TEXT DEFAULT '',
                UNIQUE(brand_name, spool_material)
            );
            """
        )

        # 5. filament_catalog table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS filament_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                barcode TEXT UNIQUE NOT NULL,
                brand TEXT NOT NULL,
                material TEXT NOT NULL,
                subtype TEXT DEFAULT '',
                color_name TEXT NOT NULL,
                color_hex TEXT NOT NULL DEFAULT '#ffffff',
                color_hex_secondary TEXT DEFAULT '',
                initial_net_weight_g INTEGER NOT NULL DEFAULT 1000,
                tare_weight_g INTEGER NOT NULL DEFAULT 250,
                nozzle_temp_min INTEGER DEFAULT 200,
                nozzle_temp_max INTEGER DEFAULT 220,
                bed_temp INTEGER DEFAULT 60,
                chamber_temp INTEGER DEFAULT 0,
                k_factor REAL DEFAULT 0.020,
                flow_ratio REAL DEFAULT 0.98,
                max_volumetric_speed REAL DEFAULT 15.0,
                retraction_length_mm REAL DEFAULT 0.8,
                retraction_speed_mms REAL DEFAULT 30.0
            );
            """
        )

        # 6. spools table (with status column)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS spools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid_code TEXT UNIQUE NOT NULL,
                barcode TEXT DEFAULT '',
                brand TEXT NOT NULL,
                material TEXT NOT NULL,
                subtype TEXT DEFAULT '',
                color_name TEXT NOT NULL,
                color_hex TEXT NOT NULL DEFAULT '#3b82f6',
                color_hex_secondary TEXT DEFAULT '',
                initial_net_weight_g REAL NOT NULL DEFAULT 1000.0,
                tare_weight_g REAL NOT NULL DEFAULT 250.0,
                current_gross_g REAL NOT NULL DEFAULT 1250.0,
                low_stock_threshold_g REAL NOT NULL DEFAULT 150.0,
                price_eur REAL DEFAULT 0.0,
                location_shelf TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'new',
                in_drybox INTEGER NOT NULL DEFAULT 0,
                in_use INTEGER NOT NULL DEFAULT 0,
                slot_location TEXT DEFAULT '',
                k_factor REAL DEFAULT 0.020,
                flow_ratio REAL DEFAULT 0.98,
                max_volumetric_speed REAL DEFAULT 15.0,
                retraction_length_mm REAL DEFAULT 0.8,
                retraction_speed_mms REAL DEFAULT 30.0,
                nozzle_temp_min INTEGER DEFAULT 200,
                nozzle_temp_max INTEGER DEFAULT 220,
                bed_temp INTEGER DEFAULT 60,
                chamber_temp INTEGER DEFAULT 0,
                opened_at TEXT DEFAULT '',
                last_dried_at TEXT DEFAULT '',
                drying_temp_c INTEGER DEFAULT 55,
                drying_hours INTEGER DEFAULT 6,
                humidity_alert INTEGER NOT NULL DEFAULT 0,
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )

        # 7. weight_history table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS weight_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spool_id INTEGER NOT NULL REFERENCES spools(id) ON DELETE CASCADE,
                gross_weight_g REAL NOT NULL,
                net_weight_g REAL NOT NULL,
                delta_g REAL NOT NULL DEFAULT 0.0,
                recorded_by TEXT DEFAULT '',
                recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )

        # 8. audit_logs table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                client_ip TEXT NOT NULL,
                username TEXT DEFAULT '',
                action TEXT NOT NULL,
                details TEXT DEFAULT ''
            );
            """
        )

        # Safe schema migration for spools: add status column if existing table lacks it
        cursor.execute("PRAGMA table_info(spools);")
        spool_columns = [row["name"] for row in cursor.fetchall()]
        if "status" not in spool_columns:
            cursor.execute("ALTER TABLE spools ADD COLUMN status TEXT NOT NULL DEFAULT 'new';")
            print("[FilamentHub DB] Migrated: added 'status' column to spools table.", flush=True)

        # Useful indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_spools_barcode ON spools(barcode);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_spools_in_use ON spools(in_use, slot_location);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_spools_uid ON spools(uid_code);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_spools_status ON spools(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_spools_brand_material ON spools(brand, material);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_weight_history_spool_id ON weight_history(spool_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_tokens_token_hash ON api_tokens(token_hash);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_catalog_brand_mat ON filament_catalog(brand, material);")

        conn.commit()

        # Synchronize status with in_use and opened_at for existing rows
        cursor.execute("UPDATE spools SET status = 'in_use' WHERE in_use = 1;")
        cursor.execute(
            """
            UPDATE spools SET status = 'empty'
            WHERE in_use = 0 AND (current_gross_g - tare_weight_g) <= 0;
            """
        )
        cursor.execute(
            """
            UPDATE spools SET status = 'opened'
            WHERE in_use = 0
              AND (current_gross_g - tare_weight_g) > 0
              AND (
                  (opened_at IS NOT NULL AND opened_at != '')
                  OR (current_gross_g - tare_weight_g) < initial_net_weight_g
              );
            """
        )
        cursor.execute(
            """
            UPDATE spools SET status = 'new'
            WHERE in_use = 0
              AND (current_gross_g - tare_weight_g) >= initial_net_weight_g
              AND (opened_at IS NULL OR opened_at = '');
            """
        )

        # Seed system_settings with defaults
        default_settings = [
            ("gemini_api_key", GEMINI_API_KEY or ""),
            ("gemini_model", GEMINI_MODEL or "gemini-2.5-flash"),
            ("ha_webhook_url", HA_WEBHOOK_URL or ""),
            ("show_ams_cockpit", "false"),
        ]
        cursor.executemany(
            """
            INSERT OR IGNORE INTO system_settings (key, value)
            VALUES (?, ?);
            """,
            default_settings,
        )

        # Seed initial admin user if users table is empty
        cursor.execute("SELECT COUNT(*) AS count FROM users;")
        user_count = cursor.fetchone()["count"]
        if user_count == 0:
            hasher = PasswordHasher()
            admin_pwd_hash = hasher.hash(INITIAL_ADMIN_PASSWORD)
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, role, is_active)
                VALUES (?, ?, 'admin', 1);
                """,
                (INITIAL_ADMIN_USER, admin_pwd_hash),
            )
            print(f"[FilamentHub DB] Created initial admin user '{INITIAL_ADMIN_USER}'.", flush=True)

        # Always INSERT OR IGNORE all entries from BRANDS_TARE_SEED
        cursor.executemany(
            """
            INSERT OR IGNORE INTO brands_tare (brand_name, spool_material, tare_weight_g, notes)
            VALUES (?, ?, ?, ?);
            """,
            BRANDS_TARE_SEED,
        )

        # Always INSERT OR IGNORE all entries from FILAMENT_CATALOG_SEED
        cursor.executemany(
            """
            INSERT OR IGNORE INTO filament_catalog (
                barcode, brand, material, subtype, color_name, color_hex, color_hex_secondary,
                initial_net_weight_g, tare_weight_g, nozzle_temp_min, nozzle_temp_max,
                bed_temp, chamber_temp, k_factor, flow_ratio, max_volumetric_speed,
                retraction_length_mm, retraction_speed_mms
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            FILAMENT_CATALOG_SEED,
        )

        conn.commit()
    finally:
        conn.close()
