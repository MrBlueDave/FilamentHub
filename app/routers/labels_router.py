"""Labels router for FilamentHub 3D.
Generates Brother thermal labels (12mm, 18mm, 24mm PNG at 300 DPI)
and prepares data + encoded barcodes for laser A4 adhesive sheet printing.
"""

import base64
import io
import sqlite3
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from PIL import Image
import barcode
from barcode.writer import ImageWriter
import qrcode

from app.auth import require_viewer
from app.database import get_db
from app.models import row_to_spool_dict
from app.services.label_gen import generate_brother_label_png

router = APIRouter(prefix="/api/labels", tags=["Labels"])


class A4DataRequest(BaseModel):
    uid_codes: Optional[List[str]] = None
    code_type: Optional[str] = "barcode"


def _generate_code_b64(uid_code: str, code_type: str = "barcode") -> str:
    """Generates a small crisp base64 PNG string of Code128 barcode or QR code."""
    uid = uid_code.strip().upper()
    try:
        if code_type.lower() == "qr":
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=6,
                border=1,
            )
            qr.add_data(uid)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white").convert("1")
        else:
            code128_cls = barcode.get_barcode_class("code128")
            bc = code128_cls(uid, writer=ImageWriter())
            bio = io.BytesIO()
            bc.write(bio, options={"module_width": 0.35, "module_height": 12.0, "quiet_zone": 1.0, "write_text": False})
            bio.seek(0)
            img = Image.open(bio).convert("1")

        out_bio = io.BytesIO()
        img.save(out_bio, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(out_bio.getvalue()).decode('utf-8')}"
    except Exception:
        return ""


@router.get("/brother/{uid_code}")
def get_brother_label(
    uid_code: str,
    tape_mm: int = Query(24, description="Brother tape width in mm (12, 18, 24)"),
    code_type: str = Query("barcode", description="Code type ('barcode' or 'qr')"),
    db: sqlite3.Connection = Depends(get_db),
    _user: Dict[str, Any] = Depends(require_viewer),
) -> Response:
    """
    Generates a 300 DPI high-contrast monochrome Brother P-Touch PNG label.
    Supports 12mm, 18mm, and 24mm tape widths, with linear Code128 or QR code.
    """
    clean_code = uid_code.strip().upper()
    cur = db.execute("SELECT * FROM spools WHERE UPPER(uid_code) = UPPER(?);", (clean_code,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bobina con UID '{uid_code}' non trovata",
        )

    spool_dict = row_to_spool_dict(row)
    png_bytes = generate_brother_label_png(spool_dict, tape_mm=tape_mm, code_type=code_type)

    filename = f"label_{clean_code}_{tape_mm}mm.png"
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "public, max-age=30",
        },
    )


@router.post("/a4-data")
def get_a4_label_data(
    req: A4DataRequest,
    db: sqlite3.Connection = Depends(get_db),
    _user: Dict[str, Any] = Depends(require_viewer),
) -> Dict[str, Any]:
    """
    Returns spool data and generated base64 barcode/QR images for the A4 sticker grid page (/print-a4).
    If uid_codes is empty, returns all spools ordered by UID.
    """
    spools: List[Dict[str, Any]] = []

    if req.uid_codes and len(req.uid_codes) > 0:
        clean_uids = [u.strip().upper() for u in req.uid_codes if u.strip()]
        placeholders = ", ".join(["?"] * len(clean_uids))
        cur = db.execute(
            f"SELECT * FROM spools WHERE UPPER(uid_code) IN ({placeholders}) ORDER BY uid_code ASC;",
            clean_uids,
        )
    else:
        cur = db.execute("SELECT * FROM spools ORDER BY uid_code ASC;")

    rows = cur.fetchall()
    code_format = (req.code_type or "barcode").lower()

    for row in rows:
        item = row_to_spool_dict(row)
        # Generate base64 code image for crisp client-side printing
        item["code_image_b64"] = _generate_code_b64(item["uid_code"], code_type=code_format)
        spools.append(item)

    return {"spools": spools, "total": len(spools)}
