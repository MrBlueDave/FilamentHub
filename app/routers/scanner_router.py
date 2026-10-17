"""Scanner and AI Vision Router for FilamentHub 3D.
Provides smart barcode & SKU lookup (spool / catalog / Sunlu / Bambu Lab patterns),
catalog preset search API, and robust Gemini 2.5 Flash label vision analysis.
"""

import base64
import re
import sqlite3
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.auth import require_editor, require_viewer
from app.database import get_db
from app.models import row_to_spool_dict
from app.services.vision import analyze_spool_image

router = APIRouter(prefix="/api/scanner", tags=["Scanner"])


def _match_smart_patterns(code: str) -> Optional[Dict[str, Any]]:
    """
    Applies smart heuristic parsing for manufacturer codes when exact barcode is not in catalog:
    - Sunlu batch / serial / factory codes (e.g. '03451103A' -> Fuchsia PLA+ 2.0, 'SL-...')
    - Bambu Lab SKU / part numbers (e.g. 'A00-W0-1.75-1000-SPL', '10100', '11101')
    """
    clean = code.strip()

    # 1. Sunlu Pattern Matching
    # - 8-9 char factory code (e.g. 03451103A): ^0\d{7}[A-Za-z0-9]?$
    # - SL- prefix (e.g. SL-META-BK)
    # - Starts with '0345'
    # - Starts with Sunlu EAN prefix '6971928'
    is_sunlu = (
        bool(re.match(r"^0\d{7}[A-Za-z0-9]?$", clean))
        or clean.upper().startswith("SL-")
        or clean.startswith("0345")
        or clean.startswith("6971928")
    )
    if is_sunlu:
        subtype = "2.0" if clean.startswith("0345") else ""
        color_name = "Standard"
        color_hex = "#3b82f6"
        material = "PLA+"

        # Specific user photo code: 03451103A is Sunlu PLA+ 2.0 Fuchsia
        if "1103" in clean:
            color_name = "Fuchsia"
            color_hex = "#d946ef"
        elif "1101" in clean:
            color_name = "Black"
            color_hex = "#111111"
        elif "1102" in clean:
            color_name = "White"
            color_hex = "#ffffff"
        elif "1104" in clean:
            color_name = "Grey"
            color_hex = "#6b7280"
        elif "1105" in clean:
            color_name = "Red"
            color_hex = "#dc2626"
        elif "1106" in clean:
            color_name = "Blue"
            color_hex = "#2563eb"
        elif "1107" in clean:
            color_name = "Green"
            color_hex = "#16a34a"
        elif "1108" in clean:
            color_name = "Yellow"
            color_hex = "#eab308"
        elif "1109" in clean:
            color_name = "Orange"
            color_hex = "#ea580c"

        if "PETG" in clean.upper():
            material = "PETG"
            subtype = "Standard"
            nozzle_min, nozzle_max, bed = 230, 250, 75
            k, flow, mvs = 0.035, 0.96, 14.0
        else:
            nozzle_min, nozzle_max, bed = 205, 225, 60
            k, flow, mvs = 0.022, 0.98, 18.0

        return {
            "type": "smart_match",
            "found": True,
            "match_source": "Sunlu Smart Pattern",
            "template": {
                "barcode": clean,
                "brand": "Sunlu",
                "material": material,
                "subtype": subtype,
                "color_name": color_name,
                "color_hex": color_hex,
                "color_hex_secondary": "",
                "initial_net_weight_g": 1000,
                "tare_weight_g": 195,
                "nozzle_temp_min": nozzle_min,
                "nozzle_temp_max": nozzle_max,
                "bed_temp": bed,
                "chamber_temp": 0,
                "k_factor": k,
                "flow_ratio": flow,
                "max_volumetric_speed": mvs,
                "retraction_length_mm": 0.8,
                "retraction_speed_mms": 30.0,
            },
        }

    # 2. Bambu Lab Pattern Matching
    # - SKU format: A00-K0-1.75-1000-SPL, B00-..., G00-...
    # - Bambu 5-digit part code: 10100, 10101, 11101, etc.
    # - EAN starting with 697533703...
    is_bambu = (
        bool(re.match(r"^[A-Z0-9]{3}-[A-Z0-9]{2,3}-", clean, re.IGNORECASE))
        or bool(re.match(r"^[1345678]\d{4}$", clean))
        or clean.startswith("697533703")
    )
    if is_bambu:
        upper = clean.upper()
        material = "PLA"
        subtype = "Basic"
        nozzle_min, nozzle_max, bed = 190, 220, 55
        k, flow, mvs = 0.020, 0.98, 21.0
        color_name = "Standard"
        color_hex = "#3b82f6"

        if upper.startswith("A01") or upper.startswith("11"):
            subtype = "Matte"
            k, mvs = 0.022, 20.0
        elif upper.startswith("G00") or upper.startswith("30") or upper.startswith("31"):
            material = "PETG"
            subtype = "HF"
            nozzle_min, nozzle_max, bed = 230, 255, 75
            k, flow, mvs = 0.035, 0.96, 17.0
        elif upper.startswith("B00") or upper.startswith("40"):
            material = "ABS"
            subtype = "Standard"
            nozzle_min, nozzle_max, bed = 240, 270, 95
            k, flow, mvs = 0.030, 0.95, 16.0
        elif upper.startswith("N04") or upper.startswith("50"):
            material = "ASA"
            subtype = "Standard"
            nozzle_min, nozzle_max, bed = 240, 270, 95
            k, flow, mvs = 0.032, 0.95, 15.0
        elif upper.startswith("60"):
            material = "TPU"
            subtype = "95A HF"
            nozzle_min, nozzle_max, bed = 220, 240, 40
            k, flow, mvs = 0.060, 1.00, 8.0

        # Color hints
        if "-K0-" in upper or upper.endswith("101") or upper.endswith("01"):
            color_name = "Black"
            color_hex = "#111111"
        elif "-W0-" in upper or upper.endswith("100") or upper.endswith("00"):
            color_name = "White"
            color_hex = "#ffffff"
        elif "-R0-" in upper or upper.endswith("200"):
            color_name = "Red"
            color_hex = "#dc2626"
        elif "-B0-" in upper or upper.endswith("600") or upper.endswith("601"):
            color_name = "Blue"
            color_hex = "#2563eb"
        elif "-G0-" in upper or upper.endswith("500") or upper.endswith("501"):
            color_name = "Bambu Green"
            color_hex = "#00ae42"
        elif "-Y0-" in upper or upper.endswith("400"):
            color_name = "Yellow"
            color_hex = "#facc15"
        elif "-A0-" in upper or upper.endswith("102") or upper.endswith("103"):
            color_name = "Gray"
            color_hex = "#8e9297"

        return {
            "type": "smart_match",
            "found": True,
            "match_source": "Bambu Lab Smart Pattern",
            "template": {
                "barcode": clean,
                "brand": "Bambu Lab",
                "material": material,
                "subtype": subtype,
                "color_name": color_name,
                "color_hex": color_hex,
                "color_hex_secondary": "",
                "initial_net_weight_g": 1000,
                "tare_weight_g": 250,
                "nozzle_temp_min": nozzle_min,
                "nozzle_temp_max": nozzle_max,
                "bed_temp": bed,
                "chamber_temp": 0,
                "k_factor": k,
                "flow_ratio": flow,
                "max_volumetric_speed": mvs,
                "retraction_length_mm": 0.8,
                "retraction_speed_mms": 30.0,
            },
        }

    return None


@router.get("/lookup/{code}")
def lookup_code(
    code: str,
    db: sqlite3.Connection = Depends(get_db),
    _user: Dict[str, Any] = Depends(require_viewer),
) -> Dict[str, Any]:
    """
    Look up a scanned barcode or UID code:
    1. Exact match on an existing spool's uid_code (e.g. SP-0001) owned by current user.
    2. Exact or partial match on existing spools by manufacturer barcode owned by current user.
    3. Exact match in the built-in filament catalog presets.
    4. Smart pattern matching for Sunlu and Bambu Lab internal factory codes & SKUs.
    5. Returns 'not_found' if unknown.
    """
    clean_code = code.strip()
    user_id = _user["id"]

    # 1. Exact match on spool uid_code (case-insensitive) for current user
    cur = db.execute(
        "SELECT * FROM spools WHERE user_id = ? AND UPPER(uid_code) = UPPER(?);",
        (user_id, clean_code),
    )
    spool_row = cur.fetchone()
    if spool_row:
        spool_dict = row_to_spool_dict(spool_row)
        return {
            "type": "existing_spool",
            "found": True,
            "spool": spool_dict,
        }

    # 2. Match on existing spools by barcode for current user
    cur = db.execute(
        "SELECT * FROM spools WHERE user_id = ? AND barcode = ? ORDER BY id DESC;",
        (user_id, clean_code),
    )
    spool_rows = cur.fetchall()
    if spool_rows:
        spool_list = [row_to_spool_dict(r) for r in spool_rows]
        return {
            "type": "catalog_or_spool",
            "found": True,
            "existing_spools": spool_list,
            "template": spool_list[0],
        }

    # 3. Match on catalog table
    cur = db.execute("SELECT * FROM filament_catalog WHERE barcode = ?;", (clean_code,))
    cat_row = cur.fetchone()
    if cat_row:
        return {
            "type": "catalog",
            "found": True,
            "template": dict(cat_row),
        }

    # 4. Smart pattern matching for Sunlu & Bambu Lab
    smart_res = _match_smart_patterns(clean_code)
    if smart_res:
        return smart_res

    # 5. Not found
    return {
        "type": "not_found",
        "found": False,
        "code": clean_code,
    }


@router.get("/catalog")
def search_catalog(
    brand: Optional[str] = Query(None, description="Filter presets by brand"),
    material: Optional[str] = Query(None, description="Filter presets by material (e.g. PLA, PETG)"),
    search: Optional[str] = Query(None, description="Search keyword in color, material, subtype, brand, or barcode"),
    db: sqlite3.Connection = Depends(get_db),
    _user: Dict[str, Any] = Depends(require_viewer),
) -> List[Dict[str, Any]]:
    """
    Search presets in the filament catalog.
    Prioritizes Bambu Lab and Sunlu at the top of results.
    """
    query = "SELECT * FROM filament_catalog WHERE 1=1"
    params: List[Any] = []

    if brand and brand.strip():
        query += " AND LOWER(brand) = LOWER(?)"
        params.append(brand.strip())

    if material and material.strip():
        query += " AND UPPER(material) = UPPER(?)"
        params.append(material.strip())

    if search and search.strip():
        term = f"%{search.strip()}%"
        query += """ AND (
            brand LIKE ? OR
            material LIKE ? OR
            subtype LIKE ? OR
            color_name LIKE ? OR
            barcode LIKE ?
        )"""
        params.extend([term] * 5)

    query += """
        ORDER BY
            CASE
                WHEN LOWER(brand) = 'bambu lab' THEN 1
                WHEN LOWER(brand) = 'sunlu' THEN 2
                ELSE 3
            END,
            brand ASC,
            material ASC,
            subtype ASC,
            color_name ASC;
    """

    cur = db.execute(query, params)
    return [dict(row) for row in cur.fetchall()]


@router.post("/vision")
async def scan_label_vision(
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    editor_user: Dict[str, Any] = Depends(require_editor),
) -> Dict[str, Any]:
    """
    Analyzes a filament spool label photo using Gemini Vision with the current user's personal API key.
    Accepts either multipart form-data (file upload) or JSON with base64 encoded image.
    Enriches the extracted data with recommended tare weight from the database.
    """
    content_type = request.headers.get("content-type", "").lower()
    image_bytes: Optional[bytes] = None
    mime_type: str = "image/jpeg"

    # 1. Try multipart form-data
    if "multipart/form-data" in content_type:
        try:
            form = await request.form()
            upload_file = form.get("file")
            if upload_file is not None and hasattr(upload_file, "read"):
                image_bytes = await upload_file.read()
                mime_type = getattr(upload_file, "content_type", "image/jpeg") or "image/jpeg"
        except Exception:
            image_bytes = None

    # 2. Try JSON body (explicitly or as fallback)
    if image_bytes is None:
        try:
            body = await request.json()
            b64_raw = body.get("image_base64", "")
            if b64_raw:
                if "base64," in b64_raw:
                    prefix, b64_raw = b64_raw.split("base64,", 1)
                    match = re.search(r"data:(image\/[a-zA-Z0-9.+-]+);", prefix)
                    if match:
                        mime_type = match.group(1)
                image_bytes = base64.b64decode(b64_raw)
                if body.get("mime_type"):
                    mime_type = body.get("mime_type")
        except Exception:
            pass

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nessuna immagine valida fornita nella richiesta (richiesto file multipart o image_base64 JSON)",
        )

    # Fetch user's personal Gemini API Key and preferred model
    user_cur = db.execute(
        "SELECT gemini_api_key, gemini_model FROM users WHERE id = ?;",
        (editor_user["id"],),
    )
    user_row = user_cur.fetchone()
    user_api_key = (user_row["gemini_api_key"] if user_row and user_row["gemini_api_key"] else "").strip()
    user_model = (user_row["gemini_model"] if user_row and user_row["gemini_model"] else "").strip() or "gemini-3.5-flash-lite"

    # Call Gemini Vision service
    result = await analyze_spool_image(
        image_bytes=image_bytes,
        mime_type=mime_type,
        api_key=user_api_key,
        preferred_model=user_model,
    )
    if not result.get("success"):
        return result

    # 1. If Gemini read a barcode/SKU from the photo, check our 257-item catalog or smart patterns!
    detected_barcode = (result.get("barcode") or "").strip()
    if detected_barcode:
        cur = db.execute("SELECT * FROM filament_catalog WHERE UPPER(barcode) = UPPER(?);", (detected_barcode,))
        cat_row = cur.fetchone()
        tpl = dict(cat_row) if cat_row else None
        if not tpl:
            smart = _match_smart_patterns(detected_barcode)
            if smart and smart.get("template"):
                tpl = smart["template"]

        if tpl:
            result["brand"] = result.get("brand") or tpl.get("brand", "")
            result["material"] = result.get("material") or tpl.get("material", "")
            result["subtype"] = result.get("subtype") or tpl.get("subtype", "")
            if not result.get("color_name") or result.get("color_name") == "Standard":
                result["color_name"] = tpl.get("color_name", "")
            if not result.get("color_hex"):
                result["color_hex"] = tpl.get("color_hex", "")
            result["nozzle_temp_min"] = result.get("nozzle_temp_min") or tpl.get("nozzle_temp_min")
            result["nozzle_temp_max"] = result.get("nozzle_temp_max") or tpl.get("nozzle_temp_max")
            result["bed_temp"] = result.get("bed_temp") or tpl.get("bed_temp")
            result["k_factor"] = tpl.get("k_factor", 0.022)
            result["flow_ratio"] = tpl.get("flow_ratio", 0.98)
            result["max_volumetric_speed"] = tpl.get("max_volumetric_speed", 18.0)
            result["tare_weight_g"] = float(tpl.get("tare_weight_g") or 250.0)

    # 2. If brand + material + color_name are known, also check catalog for matching preset to get exact hex/slicer params
    detected_brand = (result.get("brand") or "").strip()
    detected_mat = (result.get("material") or "").strip()
    detected_color = (result.get("color_name") or "").strip()
    if detected_brand and detected_mat and detected_color and "k_factor" not in result:
        cur = db.execute(
            """
            SELECT * FROM filament_catalog
            WHERE LOWER(brand) = LOWER(?) AND UPPER(material) = UPPER(?) AND LOWER(color_name) = LOWER(?)
            LIMIT 1;
            """,
            (detected_brand, detected_mat, detected_color),
        )
        cat_match = cur.fetchone()
        if cat_match:
            cm = dict(cat_match)
            if not result.get("color_hex"):
                result["color_hex"] = cm.get("color_hex", "")
            if not result.get("barcode"):
                result["barcode"] = cm.get("barcode", "")
            result["k_factor"] = cm.get("k_factor", 0.022)
            result["flow_ratio"] = cm.get("flow_ratio", 0.98)
            result["max_volumetric_speed"] = cm.get("max_volumetric_speed", 18.0)
            result["tare_weight_g"] = float(cm.get("tare_weight_g") or 250.0)

    # 3. Auto-suggest tare weight based on detected brand if not already set
    if not result.get("tare_weight_g"):
        suggested_tare = 250.0
        if detected_brand:
            cur = db.execute(
                "SELECT tare_weight_g FROM brands_tare WHERE LOWER(brand_name) = LOWER(?) LIMIT 1;",
                (detected_brand,),
            )
            tare_row = cur.fetchone()
            if tare_row:
                suggested_tare = float(tare_row["tare_weight_g"])
        result["tare_weight_g"] = suggested_tare

    # 4. Recompute missing_fields after catalog enrichment
    missing: List[str] = []
    if not (result.get("brand") or "").strip():
        missing.append("brand")
    if not (result.get("material") or "").strip():
        missing.append("material")
    if not (result.get("color_name") or "").strip():
        missing.append("color_name")
    result["missing_fields"] = missing

    return result

