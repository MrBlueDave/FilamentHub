"""Shopping List (Wishlist) Router for FilamentHub 3D.
Manages CRUD operations for filaments the user plans to purchase,
including tracking quantities, estimated budgets, external store URLs,
and 1-tap conversion into real spool inventory records.
All operations are strictly isolated per-user.
"""

import sqlite3
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import require_editor, require_viewer
from app.database import get_db
from app.models import (
    ShoppingItemConvertRequest,
    ShoppingItemCreate,
    ShoppingItemOut,
    ShoppingItemUpdate,
    row_to_spool_dict,
)
from app.routers.spools_router import _enforce_slot_exclusivity, _generate_next_uid_code

router = APIRouter(prefix="/api/shopping", tags=["Shopping List"])


def _row_to_shopping_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Converts a SQLite shopping_list row to a dictionary matching ShoppingItemOut."""
    d = dict(row)
    d["is_bought"] = bool(d.get("is_bought", 0))
    d["quantity"] = int(d.get("quantity", 1))
    d["weight_g"] = float(d.get("weight_g", 1000.0))
    d["price_eur"] = float(d.get("price_eur", 0.0) or 0.0)
    d["subtype"] = d.get("subtype") or ""
    d["color_hex_secondary"] = d.get("color_hex_secondary") or ""
    d["store_url"] = d.get("store_url") or ""
    d["notes"] = d.get("notes") or ""
    return d


@router.get("", response_model=List[ShoppingItemOut])
def get_shopping_list(
    is_bought: Optional[bool] = Query(None, description="Filtra per stato acquisto (true/false)"),
    search: Optional[str] = Query(None, description="Cerca per brand, materiale, colore o note"),
    db: sqlite3.Connection = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_viewer),
) -> List[Dict[str, Any]]:
    """Retrieve all shopping list items for the authenticated user."""
    query = "SELECT * FROM shopping_list WHERE user_id = ?"
    params: List[Any] = [current_user["id"]]

    if is_bought is not None:
        query += " AND is_bought = ?"
        params.append(1 if is_bought else 0)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query += " AND (brand LIKE ? OR material LIKE ? OR subtype LIKE ? OR color_name LIKE ? OR notes LIKE ?)"
        params.extend([term] * 5)

    query += " ORDER BY is_bought ASC, id DESC;"
    cursor = db.execute(query, params)
    return [_row_to_shopping_dict(r) for r in cursor.fetchall()]


@router.get("/{item_id}", response_model=ShoppingItemOut)
def get_shopping_item(
    item_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_viewer),
) -> Dict[str, Any]:
    """Get a specific shopping list item for the authenticated user."""
    cursor = db.execute(
        "SELECT * FROM shopping_list WHERE id = ? AND user_id = ?;",
        (item_id, current_user["id"]),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping list item {item_id} not found",
        )
    return _row_to_shopping_dict(row)


@router.post("", response_model=ShoppingItemOut, status_code=status.HTTP_201_CREATED)
def create_shopping_item(
    item_in: ShoppingItemCreate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_editor),
) -> Dict[str, Any]:
    """Add a new filament to the authenticated user's shopping list."""
    user_id = current_user["id"]
    cursor = db.execute(
        """
        INSERT INTO shopping_list (
            user_id, brand, material, subtype, color_name, color_hex, color_hex_secondary,
            quantity, weight_g, price_eur, store_url, notes, is_bought, created_at, updated_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now')
        );
        """,
        (
            user_id,
            item_in.brand.strip(),
            item_in.material.strip().upper(),
            (item_in.subtype or "").strip(),
            item_in.color_name.strip(),
            item_in.color_hex.strip(),
            (item_in.color_hex_secondary or "").strip(),
            max(1, item_in.quantity),
            max(1.0, float(item_in.weight_g)),
            max(0.0, float(item_in.price_eur or 0.0)),
            (item_in.store_url or "").strip(),
            (item_in.notes or "").strip(),
            1 if item_in.is_bought else 0,
        ),
    )
    db.commit()
    new_id = cursor.lastrowid
    row = db.execute("SELECT * FROM shopping_list WHERE id = ?;", (new_id,)).fetchone()
    return _row_to_shopping_dict(row)


@router.put("/{item_id}", response_model=ShoppingItemOut)
def update_shopping_item(
    item_id: int,
    item_in: ShoppingItemUpdate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_editor),
) -> Dict[str, Any]:
    """Update a shopping list item for the authenticated user."""
    user_id = current_user["id"]
    cursor = db.execute(
        "SELECT * FROM shopping_list WHERE id = ? AND user_id = ?;",
        (item_id, user_id),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping list item {item_id} not found",
        )

    updates: List[str] = []
    params: List[Any] = []

    if item_in.brand is not None:
        updates.append("brand = ?")
        params.append(item_in.brand.strip())
    if item_in.material is not None:
        updates.append("material = ?")
        params.append(item_in.material.strip().upper())
    if item_in.subtype is not None:
        updates.append("subtype = ?")
        params.append(item_in.subtype.strip())
    if item_in.color_name is not None:
        updates.append("color_name = ?")
        params.append(item_in.color_name.strip())
    if item_in.color_hex is not None:
        updates.append("color_hex = ?")
        params.append(item_in.color_hex.strip())
    if item_in.color_hex_secondary is not None:
        updates.append("color_hex_secondary = ?")
        params.append(item_in.color_hex_secondary.strip())
    if item_in.quantity is not None:
        updates.append("quantity = ?")
        params.append(max(1, item_in.quantity))
    if item_in.weight_g is not None:
        updates.append("weight_g = ?")
        params.append(max(1.0, float(item_in.weight_g)))
    if item_in.price_eur is not None:
        updates.append("price_eur = ?")
        params.append(max(0.0, float(item_in.price_eur)))
    if item_in.store_url is not None:
        updates.append("store_url = ?")
        params.append(item_in.store_url.strip())
    if item_in.notes is not None:
        updates.append("notes = ?")
        params.append(item_in.notes.strip())
    if item_in.is_bought is not None:
        updates.append("is_bought = ?")
        params.append(1 if item_in.is_bought else 0)

    if updates:
        updates.append("updated_at = datetime('now')")
        params.extend([item_id, user_id])
        sql = f"UPDATE shopping_list SET {', '.join(updates)} WHERE id = ? AND user_id = ?;"
        db.execute(sql, params)
        db.commit()

    updated_row = db.execute("SELECT * FROM shopping_list WHERE id = ?;", (item_id,)).fetchone()
    return _row_to_shopping_dict(updated_row)


@router.delete("/{item_id}")
def delete_shopping_item(
    item_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_editor),
) -> Dict[str, str]:
    """Delete a shopping list item for the authenticated user."""
    user_id = current_user["id"]
    cursor = db.execute(
        "SELECT id FROM shopping_list WHERE id = ? AND user_id = ?;",
        (item_id, user_id),
    )
    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping list item {item_id} not found",
        )

    db.execute("DELETE FROM shopping_list WHERE id = ? AND user_id = ?;", (item_id, user_id))
    db.commit()
    return {"message": f"Item {item_id} deleted from shopping list"}


@router.post("/{item_id}/convert")
def convert_to_spool(
    item_id: int,
    req: ShoppingItemConvertRequest,
    db: sqlite3.Connection = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_editor),
) -> Dict[str, Any]:
    """
    1-Tap Conversion: Converts a shopping list item into a brand-new Spool in the user's inventory!
    Prepopulates brand, material, subtype, color, initial weight and price, assigns next sequential SP-xxxx UID,
    initializes weight log, and either removes or marks the shopping item as purchased.
    """
    user_id = current_user["id"]
    cursor = db.execute(
        "SELECT * FROM shopping_list WHERE id = ? AND user_id = ?;",
        (item_id, user_id),
    )
    item = cursor.fetchone()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping list item {item_id} not found",
        )

    # Resolve tare weight from brands_tare or default 250g
    brand_clean = item["brand"].strip()
    tare_cur = db.execute(
        "SELECT tare_weight_g FROM brands_tare WHERE LOWER(brand_name) = LOWER(?) LIMIT 1;",
        (brand_clean,),
    )
    tare_row = tare_cur.fetchone()
    tare_weight = float(tare_row["tare_weight_g"]) if tare_row else 250.0

    net_weight = float(item["weight_g"] or 1000.0)
    current_gross = net_weight + tare_weight
    uid_code = _generate_next_uid_code(db)

    slot_loc = (req.slot_location or "").strip()
    if slot_loc:
        _enforce_slot_exclusivity(db, user_id, slot_loc)

    # Insert new spool
    spool_cur = db.execute(
        """
        INSERT INTO spools (
            user_id, uid_code, barcode, brand, material, subtype,
            color_name, color_hex, color_hex_secondary, initial_net_weight_g,
            tare_weight_g, current_gross_g, low_stock_threshold_g, price_eur,
            location_shelf, status, in_drybox, in_use, slot_location,
            k_factor, flow_ratio, max_volumetric_speed, retraction_length_mm,
            retraction_speed_mms, nozzle_temp_min, nozzle_temp_max,
            bed_temp, chamber_temp, opened_at, last_dried_at,
            drying_temp_c, drying_hours, humidity_alert, notes,
            created_at, updated_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, 150.0, ?,
            ?, ?, 0, ?, ?,
            0.020, 0.98, 15.0, 0.8,
            30.0, 200, 220,
            60, 0, '', '',
            55, 6, 0, ?,
            datetime('now'), datetime('now')
        );
        """,
        (
            user_id,
            uid_code,
            (req.barcode or "").strip(),
            brand_clean,
            item["material"].strip(),
            item["subtype"] or "",
            item["color_name"].strip(),
            item["color_hex"] or "#3b82f6",
            item["color_hex_secondary"] or "",
            net_weight,
            tare_weight,
            current_gross,
            float(item["price_eur"] or 0.0),
            (req.location_shelf or "").strip(),
            "in_use" if slot_loc else "new",
            1 if slot_loc else 0,
            slot_loc,
            (item["notes"] or "").strip(),
        ),
    )
    new_spool_id = spool_cur.lastrowid

    # Record initial weight log
    db.execute(
        """
        INSERT INTO weight_history (
            spool_id, gross_weight_g, net_weight_g, delta_g, recorded_by, recorded_at
        ) VALUES (?, ?, ?, 0.0, ?, datetime('now'));
        """,
        (new_spool_id, current_gross, net_weight, current_user.get("username", "user")),
    )

    # Either remove item or mark as bought
    if req.remove_from_list:
        db.execute("DELETE FROM shopping_list WHERE id = ? AND user_id = ?;", (item_id, user_id))
    else:
        db.execute(
            "UPDATE shopping_list SET is_bought = 1, updated_at = datetime('now') WHERE id = ? AND user_id = ?;",
            (item_id, user_id),
        )

    db.commit()

    created_row = db.execute("SELECT * FROM spools WHERE id = ?;", (new_spool_id,)).fetchone()
    return {
        "message": f"Spool {uid_code} created and added to inventory!",
        "spool": row_to_spool_dict(created_row),
    }
