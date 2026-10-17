"""Home Assistant REST API Router for FilamentHub 3D.
Provides overview telemetry and action endpoints for automated weigh, slot, and print consumption events.
Supports both session cookies and X-API-Key authentication.
"""

import sqlite3
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import require_editor, require_viewer
from app.database import get_db
from app.models import row_to_spool_dict
from app.routers.spools_router import _enforce_slot_exclusivity
from app.services.webhooks import send_ha_webhook

router = APIRouter(prefix="/api/ha", tags=["Home Assistant"])


class HAWeighRequest(BaseModel):
    uid_code: str = Field(..., min_length=1)
    gross_weight_g: float = Field(..., ge=0.0)
    note: Optional[str] = "Home Assistant weigh"


class HASlotRequest(BaseModel):
    uid_code: str = Field(..., min_length=1)
    slot_location: str = Field(..., min_length=1)
    in_use: Optional[bool] = True


class HAConsumeRequest(BaseModel):
    consumed_g: float = Field(..., gt=0.0)
    slot_location: Optional[str] = None
    uid_code: Optional[str] = None
    note: Optional[str] = "Bambu Lab print consumption"


@router.get("/overview")
def get_ha_overview(
    db: sqlite3.Connection = Depends(get_db),
    _user: Dict[str, Any] = Depends(require_viewer),
) -> Dict[str, Any]:
    """
    Returns an aggregated overview telemetry payload tailored for Home Assistant sensors.
    Includes inventory weights, alert counters, and printer slot occupants.
    """
    # 1. Fetch all spools
    cur = db.execute("SELECT * FROM spools;")
    rows = cur.fetchall()

    total_spools = len(rows)
    total_net_weight_g = 0.0
    low_stock_count = 0
    humidity_alert_count = 0
    in_drybox_count = 0
    low_stock_spools: List[Dict[str, Any]] = []

    # Initialize slot mappings
    slots: Dict[str, Optional[Dict[str, Any]]] = {
        "Slot 1": None,
        "Slot 2": None,
        "Slot 3": None,
        "Slot 4": None,
        "Esterno": None,
    }

    for r in rows:
        spool = row_to_spool_dict(r)
        total_net_weight_g += spool["net_remaining_g"]

        if spool["is_low_stock"]:
            low_stock_count += 1
            low_stock_spools.append({
                "id": spool["id"],
                "uid_code": spool["uid_code"],
                "brand": spool["brand"],
                "material": spool["material"],
                "color_name": spool["color_name"],
                "net_remaining_g": spool["net_remaining_g"],
            })

        if spool["humidity_alert"]:
            humidity_alert_count += 1

        if spool["in_drybox"]:
            in_drybox_count += 1

        if spool["in_use"] and spool["slot_location"] in slots:
            slots[spool["slot_location"]] = spool

    return {
        "total_spools": total_spools,
        "total_net_weight_g": round(total_net_weight_g, 1),
        "low_stock_count": low_stock_count,
        "humidity_alert_count": humidity_alert_count,
        "in_drybox_count": in_drybox_count,
        "slots": slots,
        "low_stock_spools": low_stock_spools,
    }


@router.post("/action/weigh")
async def ha_action_weigh(
    req: HAWeighRequest,
    db: sqlite3.Connection = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_editor),
) -> Dict[str, Any]:
    """Updates spool gross weight from Home Assistant (e.g. smart balance integration)."""
    cur = db.execute("SELECT * FROM spools WHERE UPPER(uid_code) = UPPER(?);", (req.uid_code.strip(),))
    row = cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bobina con UID '{req.uid_code}' non trovata",
        )

    spool_id = row["id"]
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
        WHERE id = ?;
        """,
        (new_gross, spool_id),
    )

    recorded_by = f"ha:{current_user.get('username', 'automation')}"
    db.execute(
        """
        INSERT INTO weight_history (spool_id, gross_weight_g, net_weight_g, delta_g, recorded_by, recorded_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'));
        """,
        (spool_id, new_gross, new_net, delta_g, recorded_by),
    )
    db.commit()

    updated_cur = db.execute("SELECT * FROM spools WHERE id = ?;", (spool_id,))
    updated_spool = row_to_spool_dict(updated_cur.fetchone())

    if updated_spool["is_low_stock"]:
        await send_ha_webhook("spool_low_stock", updated_spool)

    await send_ha_webhook("spool_weighed", {"spool": updated_spool, "delta_g": delta_g})

    return {"spool": updated_spool, "delta_g": delta_g}


@router.post("/action/slot")
async def ha_action_slot(
    req: HASlotRequest,
    db: sqlite3.Connection = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_editor),
) -> Dict[str, Any]:
    """Assigns or unmounts a spool to/from a slot via Home Assistant automation."""
    cur = db.execute("SELECT * FROM spools WHERE UPPER(uid_code) = UPPER(?);", (req.uid_code.strip(),))
    row = cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bobina con UID '{req.uid_code}' non trovata",
        )

    spool_id = row["id"]
    target_slot = req.slot_location.strip()

    if req.in_use and target_slot:
        _enforce_slot_exclusivity(db, target_slot, spool_id)
        db.execute(
            """
            UPDATE spools
            SET in_use = 1, slot_location = ?, updated_at = datetime('now')
            WHERE id = ?;
            """,
            (target_slot, spool_id),
        )
    else:
        db.execute(
            """
            UPDATE spools
            SET in_use = 0, slot_location = '', updated_at = datetime('now')
            WHERE id = ?;
            """,
            (spool_id,),
        )

    db.commit()

    updated_cur = db.execute("SELECT * FROM spools WHERE id = ?;", (spool_id,))
    updated_spool = row_to_spool_dict(updated_cur.fetchone())

    await send_ha_webhook("slot_changed", {"spool": updated_spool, "slot_location": target_slot})

    return {"spool": updated_spool}


@router.post("/action/consume")
async def ha_action_consume(
    req: HAConsumeRequest,
    db: sqlite3.Connection = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_editor),
) -> Dict[str, Any]:
    """
    Deducts consumed filament weight in grams after a print finishes.
    Target spool can be specified by uid_code OR by slot_location (e.g. 'Slot 1').
    """
    row = None
    if req.uid_code and req.uid_code.strip():
        cur = db.execute("SELECT * FROM spools WHERE UPPER(uid_code) = UPPER(?);", (req.uid_code.strip(),))
        row = cur.fetchone()
    elif req.slot_location and req.slot_location.strip():
        cur = db.execute(
            "SELECT * FROM spools WHERE in_use = 1 AND slot_location = ? LIMIT 1;",
            (req.slot_location.strip(),),
        )
        row = cur.fetchone()

    if not row:
        target_id = req.uid_code or req.slot_location or "Nessun target specificato"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nessuna bobina trovata per il target: '{target_id}'",
        )

    spool_id = row["id"]
    old_gross = float(row["current_gross_g"])
    tare = float(row["tare_weight_g"])

    # Subtract consumption, never going below tare weight
    new_gross = max(tare, old_gross - req.consumed_g)
    old_net = max(0.0, old_gross - tare)
    new_net = max(0.0, new_gross - tare)
    delta_g = round(new_net - old_net, 1)

    db.execute(
        """
        UPDATE spools
        SET current_gross_g = ?, updated_at = datetime('now')
        WHERE id = ?;
        """,
        (new_gross, spool_id),
    )

    recorded_by = f"ha:print:{current_user.get('username', 'automation')}"
    db.execute(
        """
        INSERT INTO weight_history (spool_id, gross_weight_g, net_weight_g, delta_g, recorded_by, recorded_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'));
        """,
        (spool_id, new_gross, new_net, delta_g, recorded_by),
    )
    db.commit()

    updated_cur = db.execute("SELECT * FROM spools WHERE id = ?;", (spool_id,))
    updated_spool = row_to_spool_dict(updated_cur.fetchone())

    if updated_spool["is_low_stock"]:
        await send_ha_webhook("spool_low_stock", updated_spool)

    await send_ha_webhook(
        "spool_consumed",
        {"spool": updated_spool, "consumed_g": req.consumed_g, "delta_g": delta_g},
    )

    return {
        "status": "success",
        "spool": updated_spool,
        "consumed_g": req.consumed_g,
        "delta_g": delta_g,
    }
