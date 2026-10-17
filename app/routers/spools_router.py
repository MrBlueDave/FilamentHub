"""Spools router for FilamentHub 3D.
Manages CRUD operations, multi-quantity batch creation, spool cloning,
quick status transitions ('new', 'opened', 'in_use', 'empty'),
quick weigh, slot assignments (Rule #4), and drying updates.
All database queries use strictly parameterized SQLite placeholders (?) and are isolated per-user.
"""

import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import require_editor, require_viewer
from app.database import get_db
from app.models import (
    QuickDryRequest,
    QuickSlotRequest,
    QuickStatusRequest,
    QuickWeighRequest,
    SpoolCloneRequest,
    SpoolCreate,
    SpoolUpdate,
    row_to_spool_dict,
)

router = APIRouter(prefix="/api/spools", tags=["Spools"])


def _get_max_uid_number(db: sqlite3.Connection) -> int:
    """Finds the maximum numeric index among existing 'SP-XXXX' uid_codes."""
    cursor = db.execute("SELECT uid_code FROM spools WHERE uid_code LIKE 'SP-%';")
    rows = cursor.fetchall()

    max_num = 0
    pattern = re.compile(r"^SP-(\d+)$", re.IGNORECASE)
    for row in rows:
        code = str(row["uid_code"]).strip()
        match = pattern.match(code)
        if match:
            try:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
            except ValueError:
                pass
    return max_num


def _generate_next_uid_code(db: sqlite3.Connection, offset: int = 1) -> str:
    """Generates the next sequential UID code (e.g. SP-0001, SP-0002)."""
    max_num = _get_max_uid_number(db)
    return f"SP-{max_num + offset:04d}"


def _enforce_slot_exclusivity(
    db: sqlite3.Connection,
    user_id: int,
    slot_location: str,
    exclude_spool_id: Optional[int] = None,
) -> None:
    """
    Enforces Rule #4 (Esclusività Slot Stampante) per user:
    When a spool is placed into a slot ('Slot 1', 'Slot 2', 'Slot 3', 'Slot 4', 'Esterno'),
    any other spool belonging to the same user previously occupying that slot is automatically unmounted.
    """
    clean_slot = slot_location.strip()
    if clean_slot:
        if exclude_spool_id is not None:
            db.execute(
                """
                UPDATE spools
                SET in_use = 0, slot_location = '', status = 'opened', updated_at = datetime('now')
                WHERE user_id = ? AND slot_location = ? AND id != ?;
                """,
                (user_id, clean_slot, exclude_spool_id),
            )
        else:
            db.execute(
                """
                UPDATE spools
                SET in_use = 0, slot_location = '', status = 'opened', updated_at = datetime('now')
                WHERE user_id = ? AND slot_location = ?;
                """,
                (user_id, clean_slot),
            )


@router.get("", response_model=List[Dict[str, Any]])
def list_spools(
    search: Optional[str] = Query(None, description="Search term matching UID, brand, material, barcode, shelf"),
    material: Optional[str] = Query(None, description="Filter by material name (e.g. PLA, PETG)"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    status: Optional[str] = Query(None, description="Filter by status ('new', 'opened', 'in_use', 'empty')"),
    in_use: Optional[bool] = Query(None, description="Filter by mounted/in-use status"),
    low_stock: Optional[bool] = Query(None, description="Filter spools at or below low stock threshold"),
    humidity_alert: Optional[bool] = Query(None, description="Filter spools flagged with humidity alert"),
    sort_by: Optional[str] = Query("updated_at", description="Field to sort by"),
    sort_dir: Optional[str] = Query("desc", description="Sort direction (asc or desc)"),
    db: sqlite3.Connection = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_viewer),
) -> List[Dict[str, Any]]:
    """List all spools for the authenticated user with optional filters, search, status filtering, and sorting."""
    query = "SELECT * FROM spools WHERE user_id = ?"
    params: List[Any] = [current_user["id"]]

    if search and search.strip():
        term = f"%{search.strip()}%"
        query += """ AND (
            uid_code LIKE ? OR
            brand LIKE ? OR
            material LIKE ? OR
            subtype LIKE ? OR
            color_name LIKE ? OR
            barcode LIKE ? OR
            location_shelf LIKE ? OR
            notes LIKE ?
        )"""
        params.extend([term] * 8)

    if material and material.strip():
        query += " AND UPPER(material) = UPPER(?)"
        params.append(material.strip())

    if brand and brand.strip():
        query += " AND LOWER(brand) = LOWER(?)"
        params.append(brand.strip())

    if status and status.strip():
        query += " AND LOWER(status) = LOWER(?)"
        params.append(status.strip())

    if in_use is not None:
        query += " AND in_use = ?"
        params.append(1 if in_use else 0)

    if humidity_alert is not None:
        query += " AND humidity_alert = ?"
        params.append(1 if humidity_alert else 0)

    if low_stock is not None:
        if low_stock:
            query += " AND (current_gross_g - tare_weight_g) <= low_stock_threshold_g"
        else:
            query += " AND (current_gross_g - tare_weight_g) > low_stock_threshold_g"

    # Sorting
    allowed_sort_fields = {
        "id": "id",
        "uid_code": "uid_code",
        "brand": "brand",
        "material": "material",
        "subtype": "subtype",
        "color_name": "color_name",
        "status": "status",
        "created_at": "created_at",
        "updated_at": "updated_at",
        "current_gross_g": "current_gross_g",
        "price_eur": "price_eur",
        "k_factor": "k_factor",
        "flow_ratio": "flow_ratio",
        "slot_location": "slot_location",
        "net_remaining_g": "(current_gross_g - tare_weight_g)",
    }
    sort_col = allowed_sort_fields.get(sort_by, "updated_at")
    direction = "ASC" if sort_dir and sort_dir.lower() == "asc" else "DESC"
    query += f" ORDER BY {sort_col} {direction};"

    cursor = db.execute(query, params)
    rows = cursor.fetchall()
    return [row_to_spool_dict(row) for row in rows]


@router.get("/uid/{uid_code}")
def get_spool_by_uid(
    uid_code: str,
    db: sqlite3.Connection = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_viewer),
) -> Dict[str, Any]:
    """Get a single spool by its UID code (e.g. SP-0001) owned by the current user along with its recent weight history."""
    cursor = db.execute(
        "SELECT * FROM spools WHERE user_id = ? AND UPPER(uid_code) = UPPER(?);",
        (current_user["id"], uid_code.strip()),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bobina con UID '{uid_code}' non trovata",
        )

    spool = row_to_spool_dict(row)

    # Fetch recent weight history
    history_cursor = db.execute(
        """
        SELECT id, spool_id, gross_weight_g, net_weight_g, delta_g, recorded_by, recorded_at
        FROM weight_history
        WHERE spool_id = ?
        ORDER BY recorded_at DESC, id DESC
        LIMIT 50;
        """,
        (spool["id"],),
    )
    history_rows = history_cursor.fetchall()
    spool["weight_history"] = [dict(h) for h in history_rows]
    return spool


@router.get("/{spool_id}")
def get_spool_by_id(
    spool_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_viewer),
) -> Dict[str, Any]:
    """Get a single spool by its primary ID owned by the current user along with its recent weight history."""
    cursor = db.execute(
        "SELECT * FROM spools WHERE id = ? AND user_id = ?;",
        (spool_id, current_user["id"]),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bobina ID {spool_id} non trovata",
        )

    spool = row_to_spool_dict(row)

    # Fetch recent weight history
    history_cursor = db.execute(
        """
        SELECT id, spool_id, gross_weight_g, net_weight_g, delta_g, recorded_by, recorded_at
        FROM weight_history
        WHERE spool_id = ?
        ORDER BY recorded_at DESC, id DESC
        LIMIT 50;
        """,
        (spool_id,),
    )
    history_rows = history_cursor.fetchall()
    spool["weight_history"] = [dict(h) for h in history_rows]
    return spool


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_spool(
    spool_in: SpoolCreate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_editor),
) -> Dict[str, Any]:
    """
    Create one or more new spools (multi-quantity support 1 to 50) for the current user,
    enforce per-user slot exclusivity, and record initial weight history.
    """
    user_id = current_user["id"]
    quantity = max(1, min(50, spool_in.quantity))

    # Tare auto-suggestion if not provided or 0
    tare_weight = spool_in.tare_weight_g
    if tare_weight <= 0:
        tare_cur = db.execute(
            "SELECT tare_weight_g FROM brands_tare WHERE LOWER(brand_name) = LOWER(?) LIMIT 1;",
            (spool_in.brand.strip(),),
        )
        tare_row = tare_cur.fetchone()
        if tare_row:
            tare_weight = float(tare_row["tare_weight_g"])
        else:
            tare_weight = 250.0

    slot_location = (spool_in.slot_location or "").strip()
    max_num = _get_max_uid_number(db)
    created_uids: List[str] = []
    first_spool_id: Optional[int] = None

    for i in range(quantity):
        if i == 0 and spool_in.uid_code and spool_in.uid_code.strip():
            uid_code = spool_in.uid_code.strip().upper()
            check_cur = db.execute("SELECT id FROM spools WHERE UPPER(uid_code) = UPPER(?);", (uid_code,))
            if check_cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Il codice UID '{uid_code}' è già utilizzato da un'altra bobina",
                )
        else:
            uid_code = f"SP-{max_num + i + 1:04d}"

        created_uids.append(uid_code)

        # Only the first spool can be mounted in_use or take non-default status
        if i == 0:
            this_in_use = bool(spool_in.in_use)
            this_slot = slot_location if this_in_use else ""
            this_status = "in_use" if this_in_use else (spool_in.status or "new")
            this_opened_at = spool_in.opened_at or ""
        else:
            this_in_use = False
            this_slot = ""
            this_status = "new"
            this_opened_at = ""

        cursor = db.execute(
            """
            INSERT INTO spools (
                user_id, uid_code, barcode, brand, material, subtype, color_name, color_hex, color_hex_secondary,
                initial_net_weight_g, tare_weight_g, current_gross_g, low_stock_threshold_g, price_eur,
                location_shelf, status, in_drybox, in_use, slot_location, k_factor, flow_ratio,
                max_volumetric_speed, retraction_length_mm, retraction_speed_mms, nozzle_temp_min,
                nozzle_temp_max, bed_temp, chamber_temp, opened_at, last_dried_at, drying_temp_c,
                drying_hours, humidity_alert, notes, created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, datetime('now'), datetime('now')
            );
            """,
            (
                user_id,
                uid_code,
                spool_in.barcode or "",
                spool_in.brand.strip(),
                spool_in.material.strip().upper(),
                (spool_in.subtype or "").strip(),
                spool_in.color_name.strip(),
                spool_in.color_hex or "#3b82f6",
                spool_in.color_hex_secondary or "",
                spool_in.initial_net_weight_g,
                tare_weight,
                spool_in.current_gross_g,
                spool_in.low_stock_threshold_g,
                spool_in.price_eur,
                spool_in.location_shelf or "",
                this_status,
                1 if spool_in.in_drybox else 0,
                1 if this_in_use else 0,
                this_slot,
                spool_in.k_factor,
                spool_in.flow_ratio,
                spool_in.max_volumetric_speed,
                spool_in.retraction_length_mm,
                spool_in.retraction_speed_mms,
                spool_in.nozzle_temp_min,
                spool_in.nozzle_temp_max,
                spool_in.bed_temp,
                spool_in.chamber_temp,
                this_opened_at,
                spool_in.last_dried_at or "",
                spool_in.drying_temp_c,
                spool_in.drying_hours,
                1 if spool_in.humidity_alert else 0,
                spool_in.notes or "",
            ),
        )
        spool_id = cursor.lastrowid
        if i == 0:
            first_spool_id = spool_id

        # Apply Rule #4: Slot exclusivity for mounted spool (scoped to user_id)
        if this_in_use and this_slot:
            _enforce_slot_exclusivity(db, user_id, this_slot, spool_id)

        # Record initial weight in weight_history
        initial_net = max(0.0, spool_in.current_gross_g - tare_weight)
        db.execute(
            """
            INSERT INTO weight_history (spool_id, gross_weight_g, net_weight_g, delta_g, recorded_by, recorded_at)
            VALUES (?, ?, ?, 0.0, ?, datetime('now'));
            """,
            (spool_id, spool_in.current_gross_g, initial_net, current_user.get("username", "system")),
        )

    # Optionally seed filament_catalog if barcode is non-empty and not yet in catalog
    if spool_in.barcode and spool_in.barcode.strip():
        db.execute(
            """
            INSERT OR IGNORE INTO filament_catalog (
                barcode, brand, material, subtype, color_name, color_hex, color_hex_secondary,
                initial_net_weight_g, tare_weight_g, nozzle_temp_min, nozzle_temp_max,
                bed_temp, chamber_temp, k_factor, flow_ratio, max_volumetric_speed,
                retraction_length_mm, retraction_speed_mms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                spool_in.barcode.strip(),
                spool_in.brand.strip(),
                spool_in.material.strip().upper(),
                (spool_in.subtype or "").strip(),
                spool_in.color_name.strip(),
                spool_in.color_hex or "#3b82f6",
                spool_in.color_hex_secondary or "",
                int(spool_in.initial_net_weight_g),
                int(tare_weight),
                spool_in.nozzle_temp_min,
                spool_in.nozzle_temp_max,
                spool_in.bed_temp,
                spool_in.chamber_temp,
                spool_in.k_factor,
                spool_in.flow_ratio,
                spool_in.max_volumetric_speed,
                spool_in.retraction_length_mm,
                spool_in.retraction_speed_mms,
            ),
        )

    db.commit()

    # Retrieve created primary record
    created_cur = db.execute("SELECT * FROM spools WHERE id = ? AND user_id = ?;", (first_spool_id, user_id))
    spool_data = row_to_spool_dict(created_cur.fetchone())
    spool_data["created_count"] = quantity
    spool_data["created_uids"] = created_uids

    return spool_data


@router.put("/{spool_id}")
async def update_spool(
    spool_id: int,
    spool_update: SpoolUpdate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_editor),
) -> Dict[str, Any]:
    """Full update of an existing spool owned by current user, with status synchronization, slot exclusivity, and weight delta tracking."""
    user_id = current_user["id"]
    cur = db.execute("SELECT * FROM spools WHERE id = ? AND user_id = ?;", (spool_id, user_id))
    existing = cur.fetchone()
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bobina ID {spool_id} non trovata",
        )

    fields_dict = spool_update.model_dump(exclude_unset=True)

    # Check for weight change
    old_gross = float(existing["current_gross_g"])
    old_tare = float(existing["tare_weight_g"])
    new_gross = float(fields_dict.get("current_gross_g", old_gross))
    new_tare = float(fields_dict.get("tare_weight_g", old_tare))

    if abs(new_gross - old_gross) > 0.05:
        old_net = max(0.0, old_gross - old_tare)
        new_net = max(0.0, new_gross - new_tare)
        delta_g = round(new_net - old_net, 1)
        db.execute(
            """
            INSERT INTO weight_history (spool_id, gross_weight_g, net_weight_g, delta_g, recorded_by, recorded_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'));
            """,
            (spool_id, new_gross, new_net, delta_g, current_user.get("username", "system")),
        )

    # Handle slot exclusivity and status synchronization
    target_in_use = fields_dict.get("in_use", bool(existing["in_use"]))
    target_slot = fields_dict.get("slot_location", existing["slot_location"] or "")
    target_status = fields_dict.get("status")

    if target_status == "in_use":
        target_in_use = True
        fields_dict["in_use"] = True
    elif target_status in ("new", "opened", "empty"):
        target_in_use = False
        fields_dict["in_use"] = False

    if not target_in_use:
        fields_dict["slot_location"] = ""
        if fields_dict.get("status") == "in_use":
            fields_dict["status"] = "opened"
    elif target_slot and target_slot.strip():
        _enforce_slot_exclusivity(db, user_id, target_slot, spool_id)
        if "status" not in fields_dict:
            fields_dict["status"] = "in_use"

    # Build dynamic update query with parameterized placeholders
    set_clauses: List[str] = []
    params: List[Any] = []

    allowed_columns = (
        "brand", "material", "subtype", "color_name", "color_hex", "color_hex_secondary",
        "barcode", "initial_net_weight_g", "tare_weight_g", "current_gross_g",
        "low_stock_threshold_g", "price_eur", "location_shelf", "status", "in_drybox", "in_use",
        "slot_location", "k_factor", "flow_ratio", "max_volumetric_speed",
        "retraction_length_mm", "retraction_speed_mms", "nozzle_temp_min", "nozzle_temp_max",
        "bed_temp", "chamber_temp", "opened_at", "last_dried_at", "drying_temp_c",
        "drying_hours", "humidity_alert", "notes"
    )

    for k, v in fields_dict.items():
        if k in allowed_columns:
            if k in ("in_drybox", "in_use", "humidity_alert"):
                val = 1 if v else 0
            elif k == "material" and v:
                val = str(v).strip().upper()
            else:
                val = v
            set_clauses.append(f"{k} = ?")
            params.append(val)

    set_clauses.append("updated_at = datetime('now')")
    params.extend([spool_id, user_id])

    db.execute(f"UPDATE spools SET {', '.join(set_clauses)} WHERE id = ? AND user_id = ?;", params)
    db.commit()

    updated_cur = db.execute("SELECT * FROM spools WHERE id = ? AND user_id = ?;", (spool_id, user_id))
    updated_spool = row_to_spool_dict(updated_cur.fetchone())

    return updated_spool


@router.delete("/{spool_id}")
async def delete_spool(
    spool_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_editor),
) -> Dict[str, Any]:
    """Delete a spool owned by current user and its weight history (via cascade delete)."""
    user_id = current_user["id"]
    cur = db.execute("SELECT id, uid_code FROM spools WHERE id = ? AND user_id = ?;", (spool_id, user_id))
    row = cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bobina ID {spool_id} non trovata",
        )

    uid_code = row["uid_code"]
    db.execute("DELETE FROM spools WHERE id = ? AND user_id = ?;", (spool_id, user_id))
    db.commit()

    return {"status": "deleted", "id": spool_id, "uid_code": uid_code}


@router.post("/{spool_id}/quick-status")
async def quick_status_spool(
    spool_id: int,
    req: QuickStatusRequest,
    db: sqlite3.Connection = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_editor),
) -> Dict[str, Any]:
    """
    Transitions spool status directly to 'new', 'opened', 'in_use', or 'empty'.
    Automatically updates opened_at, handles per-user slot exclusivity, and resets gross weight when empty.
    """
    user_id = current_user["id"]
    cur = db.execute("SELECT * FROM spools WHERE id = ? AND user_id = ?;", (spool_id, user_id))
    row = cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bobina ID {spool_id} non trovata",
        )

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    target_status = req.status.lower()

    if target_status == "new":
        db.execute(
            """
            UPDATE spools
            SET status = 'new', in_use = 0, slot_location = '', opened_at = '', updated_at = datetime('now')
            WHERE id = ? AND user_id = ?;
            """,
            (spool_id, user_id),
        )
    elif target_status == "opened":
        db.execute(
            """
            UPDATE spools
            SET status = 'opened',
                in_use = 0,
                slot_location = '',
                opened_at = CASE WHEN opened_at IS NULL OR opened_at = '' THEN ? ELSE opened_at END,
                updated_at = datetime('now')
            WHERE id = ? AND user_id = ?;
            """,
            (today_str, spool_id, user_id),
        )
    elif target_status == "in_use":
        slot = (req.slot_location or "").strip() or "Esterno"
        _enforce_slot_exclusivity(db, user_id, slot, spool_id)
        db.execute(
            """
            UPDATE spools
            SET status = 'in_use',
                in_use = 1,
                slot_location = ?,
                opened_at = CASE WHEN opened_at IS NULL OR opened_at = '' THEN ? ELSE opened_at END,
                updated_at = datetime('now')
            WHERE id = ? AND user_id = ?;
            """,
            (slot, today_str, spool_id, user_id),
        )
    elif target_status == "empty":
        tare = float(row["tare_weight_g"])
        db.execute(
            """
            UPDATE spools
            SET status = 'empty',
                in_use = 0,
                slot_location = '',
                current_gross_g = ?,
                updated_at = datetime('now')
            WHERE id = ? AND user_id = ?;
            """,
            (tare, spool_id, user_id),
        )

    db.commit()

    updated_cur = db.execute("SELECT * FROM spools WHERE id = ? AND user_id = ?;", (spool_id, user_id))
    updated_spool = row_to_spool_dict(updated_cur.fetchone())

    return {"spool": updated_spool}


@router.post("/{spool_id}/clone")
async def clone_spool(
    spool_id: int,
    req: SpoolCloneRequest,
    db: sqlite3.Connection = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_editor),
) -> Dict[str, Any]:
    """
    Duplicates an existing spool specification into one or more new spools for the current user in 1 click.
    Generates new sequential UIDs, calculates gross weight, and seeds initial weight history.
    """
    user_id = current_user["id"]
    cur = db.execute("SELECT * FROM spools WHERE id = ? AND user_id = ?;", (spool_id, user_id))
    source = cur.fetchone()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bobina ID {spool_id} non trovata",
        )

    qty = max(1, min(50, req.quantity))
    status_choice = req.status.lower() if req.status in ("new", "opened", "in_use", "empty") else "new"

    # For 'new' status, reset gross weight to full (initial_net + tare)
    if status_choice == "new":
        gross_w = float(source["initial_net_weight_g"]) + float(source["tare_weight_g"])
        opened_at = ""
    else:
        gross_w = float(source["current_gross_g"])
        opened_at = source["opened_at"] or ""

    max_num = _get_max_uid_number(db)
    created_uids: List[str] = []

    for i in range(qty):
        uid = f"SP-{max_num + i + 1:04d}"
        created_uids.append(uid)

        ins_cur = db.execute(
            """
            INSERT INTO spools (
                user_id, uid_code, barcode, brand, material, subtype, color_name, color_hex, color_hex_secondary,
                initial_net_weight_g, tare_weight_g, current_gross_g, low_stock_threshold_g, price_eur,
                location_shelf, status, in_drybox, in_use, slot_location, k_factor, flow_ratio,
                max_volumetric_speed, retraction_length_mm, retraction_speed_mms, nozzle_temp_min,
                nozzle_temp_max, bed_temp, chamber_temp, opened_at, last_dried_at, drying_temp_c,
                drying_hours, humidity_alert, notes, created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, 0, '', ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, 0, ?, datetime('now'), datetime('now')
            );
            """,
            (
                user_id,
                uid,
                source["barcode"] or "",
                source["brand"],
                source["material"],
                source["subtype"] or "",
                source["color_name"],
                source["color_hex"],
                source["color_hex_secondary"] or "",
                source["initial_net_weight_g"],
                source["tare_weight_g"],
                gross_w,
                source["low_stock_threshold_g"],
                source["price_eur"],
                source["location_shelf"] or "",
                status_choice,
                source["in_drybox"],
                source["k_factor"],
                source["flow_ratio"],
                source["max_volumetric_speed"],
                source["retraction_length_mm"],
                source["retraction_speed_mms"],
                source["nozzle_temp_min"],
                source["nozzle_temp_max"],
                source["bed_temp"],
                source["chamber_temp"],
                opened_at,
                source["last_dried_at"] or "",
                source["drying_temp_c"],
                source["drying_hours"],
                f"Clonata da {source['uid_code']}",
            ),
        )
        new_id = ins_cur.lastrowid
        net_w = max(0.0, gross_w - float(source["tare_weight_g"]))
        db.execute(
            """
            INSERT INTO weight_history (spool_id, gross_weight_g, net_weight_g, delta_g, recorded_by, recorded_at)
            VALUES (?, ?, ?, 0.0, ?, datetime('now'));
            """,
            (new_id, gross_w, net_w, current_user.get("username", "clone")),
        )

    db.commit()

    return {
        "message": f"Clonate con successo {qty} bobine",
        "created_count": qty,
        "created_uids": created_uids,
    }


@router.post("/{spool_id}/quick-weigh")
async def quick_weigh_spool(
    spool_id: int,
    req: QuickWeighRequest,
    db: sqlite3.Connection = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_editor),
) -> Dict[str, Any]:
    """Quickly weigh a spool: computes consumption delta and updates record."""
    user_id = current_user["id"]
    cur = db.execute("SELECT * FROM spools WHERE id = ? AND user_id = ?;", (spool_id, user_id))
    row = cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bobina ID {spool_id} non trovata",
        )

    old_gross = float(row["current_gross_g"])
    tare = float(row["tare_weight_g"])
    new_gross = float(req.gross_weight_g)

    old_net = max(0.0, old_gross - tare)
    new_net = max(0.0, new_gross - tare)
    delta_g = round(new_net - old_net, 1)

    db.execute(
        """
        UPDATE spools
        SET current_gross_g = ?, updated_at = datetime('now')
        WHERE id = ? AND user_id = ?;
        """,
        (new_gross, spool_id, user_id),
    )

    db.execute(
        """
        INSERT INTO weight_history (spool_id, gross_weight_g, net_weight_g, delta_g, recorded_by, recorded_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'));
        """,
        (spool_id, new_gross, new_net, delta_g, current_user.get("username", "quick-weigh")),
    )
    db.commit()

    updated_cur = db.execute("SELECT * FROM spools WHERE id = ? AND user_id = ?;", (spool_id, user_id))
    updated_spool = row_to_spool_dict(updated_cur.fetchone())

    return {"spool": updated_spool, "delta_g": delta_g}


@router.post("/{spool_id}/quick-slot")
async def quick_slot_spool(
    spool_id: int,
    req: QuickSlotRequest,
    db: sqlite3.Connection = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_editor),
) -> Dict[str, Any]:
    """
    Assigns or unmounts a spool to/from a printer slot (Slot 1, 2, 3, 4, Esterno).
    Enforces Rule #4 (Esclusività Slot Stampante) per user.
    """
    user_id = current_user["id"]
    cur = db.execute("SELECT * FROM spools WHERE id = ? AND user_id = ?;", (spool_id, user_id))
    row = cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bobina ID {spool_id} non trovata",
        )

    target_slot = (req.slot_location or "").strip()
    if req.in_use and target_slot:
        _enforce_slot_exclusivity(db, user_id, target_slot, spool_id)
        db.execute(
            """
            UPDATE spools
            SET in_use = 1, slot_location = ?, status = 'in_use', updated_at = datetime('now')
            WHERE id = ? AND user_id = ?;
            """,
            (target_slot, spool_id, user_id),
        )
    else:
        db.execute(
            """
            UPDATE spools
            SET in_use = 0, slot_location = '', status = 'opened', updated_at = datetime('now')
            WHERE id = ? AND user_id = ?;
            """,
            (spool_id, user_id),
        )

    db.commit()

    updated_cur = db.execute("SELECT * FROM spools WHERE id = ? AND user_id = ?;", (spool_id, user_id))
    updated_spool = row_to_spool_dict(updated_cur.fetchone())

    # Fetch all active slots for cockpit response (scoped to current user)
    active_cur = db.execute(
        """
        SELECT * FROM spools
        WHERE user_id = ? AND in_use = 1 AND slot_location != ''
        ORDER BY slot_location ASC;
        """,
        (user_id,),
    )
    active_slots = [row_to_spool_dict(r) for r in active_cur.fetchall()]

    return {"spool": updated_spool, "active_slots": active_slots}


@router.post("/{spool_id}/quick-dry")
async def quick_dry_spool(
    spool_id: int,
    req: QuickDryRequest,
    db: sqlite3.Connection = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_editor),
) -> Dict[str, Any]:
    """Marks a spool owned by current user as dried today, clears humidity alert, and updates drying parameters."""
    user_id = current_user["id"]
    cur = db.execute("SELECT * FROM spools WHERE id = ? AND user_id = ?;", (spool_id, user_id))
    row = cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bobina ID {spool_id} non trovata",
        )

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    clauses = ["last_dried_at = ?", "humidity_alert = 0", "updated_at = datetime('now')"]
    params: List[Any] = [today_str]

    if req.drying_temp_c is not None:
        clauses.append("drying_temp_c = ?")
        params.append(req.drying_temp_c)

    if req.drying_hours is not None:
        clauses.append("drying_hours = ?")
        params.append(req.drying_hours)

    params.extend([spool_id, user_id])
    db.execute(f"UPDATE spools SET {', '.join(clauses)} WHERE id = ? AND user_id = ?;", params)
    db.commit()

    updated_cur = db.execute("SELECT * FROM spools WHERE id = ? AND user_id = ?;", (spool_id, user_id))
    updated_spool = row_to_spool_dict(updated_cur.fetchone())

    return updated_spool
