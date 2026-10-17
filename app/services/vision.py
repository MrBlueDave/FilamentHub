"""Google Gemini Vision integration for filament spool label and barcode recognition.
Uses automatic multi-model fallback (prioritizing fast, reliable models like gemini-3.5-flash-lite
and gemini-flash-lite-latest) and matches extracted barcodes against the built-in catalog.
"""

import base64
import json
import logging
import re
from typing import Any, Dict, List
import httpx

logger = logging.getLogger("filamenthub.vision")

SYSTEM_PROMPT = (
    "You are an expert 3D printing inventory & barcode/OCR vision assistant analyzing filament spool photos, labels, and boxes.\n"
    "Carefully inspect ALL text, barcodes (1D linear Code128, EAN-13, UPC, QR codes), numbers, temperature ranges, and the physical filament color visible in the image.\n\n"
    "CRITICAL BRAND & LABEL RECOGNITION RULES:\n"
    "1. SUNLU LABELS: Sunlu spools very often have a small white rectangular sticker with rounded corners showing:\n"
    "   - Material at top-left (e.g. 'PLA+2.0', 'PLA+', 'PETG', 'SILK', 'META')\n"
    "   - Color name at top-center (e.g. 'Fuchsia', 'Black', 'White', 'Grey', 'Bone White', 'Olive Green')\n"
    "   - Diameter at top-right ('Ø1.75mm')\n"
    "   - A linear barcode in the middle with a 8-9 character alphanumeric code below it (like '03451103A', '0345...') and '1kg' on the right\n"
    "   - Print Temp ranges (e.g. 'Print Temp: 195-205°C 50-100mm/s', 'Print Temp: 205-220°C 100-300mm/s', 'Bed temp: 50-60°C')\n"
    "   - 'Spool Temperature Resistance : <70°C' and 'MADE IN CHINA' below.\n"
    "   -> Even though the word 'SUNLU' is NOT printed on this white sticker, you MUST set brand='Sunlu'! If it says 'PLA+2.0', set material='PLA+' and subtype='2.0'.\n"
    "2. BAMBU LAB LABELS: Bambu Lab boxes/spools have 'Bambu Filament', RFID spool stickers, 5-digit codes (e.g. '10100', '10101', '11101'), SKUs like 'A00-W0-1.75-1000-SPL', or EAN '697533703...'. Set brand='Bambu Lab'.\n"
    "3. TEMPERATURES: If two print temperature ranges are printed (e.g. slow speed 195-205°C and high speed 205-220°C), use the overall min (195) or high-speed min (205) for nozzle_temp_min and the max (220) for nozzle_temp_max. For Bed temp '50-60°C', use 60.\n"
    "4. BARCODE: Always read the exact alphanumeric string printed directly under or above the barcode bars (e.g. '03451103A', '6975337030117', 'A00-K0-1.75-1000-SPL') and put it in 'barcode'.\n"
    "5. MISSING FIELDS: If a field (like brand, material, color_name) is genuinely NOT visible and cannot be inferred from the label style, return an empty string '' for that field (do NOT guess random values) and list the missing field names in 'missing_fields'.\n\n"
    "Return ONLY a strictly valid JSON object with these keys:\n"
    "- brand: string (e.g. 'Sunlu', 'Bambu Lab', 'eSUN', 'Polymaker', 'Prusament', 'Elegoo', 'Creality', 'Anycubic', or '' if unknown)\n"
    "- material: string (uppercase: 'PLA', 'PLA+', 'PETG', 'ABS', 'ASA', 'TPU', 'PA', 'PA-CF', 'PC', 'PVA', or '' if unknown)\n"
    "- subtype: string (e.g. '2.0', 'Basic', 'Matte', 'Silk', 'CF', 'HF', 'Meta', 'High Speed', or '')\n"
    "- color_name: string (exact color name read from label, e.g. 'Fuchsia', 'Charcoal', 'Jade White', or inferred color name in English/Italian)\n"
    "- color_hex: string (accurate '#RRGGBB' hex code matching the color name and/or visible filament in the photo, e.g. '#d946ef' for Fuchsia)\n"
    "- initial_net_weight_g: number (e.g. 1000 for 1kg, 250 for 250g, default 1000)\n"
    "- nozzle_temp_min: integer or null (e.g. 200)\n"
    "- nozzle_temp_max: integer or null (e.g. 220)\n"
    "- bed_temp: integer or null (e.g. 60)\n"
    "- barcode: string (exact barcode/SKU string read from the label, or '')\n"
    "- confidence: string ('high', 'medium', 'low')\n"
)


def _get_candidate_models(preferred_model: str) -> List[str]:
    """
    Returns an ordered list of Gemini models to try.
    Prioritizes fast, non-deprecated, high-availability Flash-Lite and Flash models.
    """
    # Fast and reliable models first
    defaults = [
        "gemini-3.5-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest",
    ]
    candidates: List[str] = []
    # If user explicitly picked a non-deprecated model, try it first;
    # if it's gemini-2.5-flash (which returns 404 on newer keys), try 3.5-flash-lite first!
    if preferred_model and preferred_model not in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"):
        candidates.append(preferred_model)
    for m in defaults:
        if m not in candidates:
            candidates.append(m)
    if preferred_model and preferred_model not in candidates:
        candidates.append(preferred_model)
    return candidates


async def analyze_spool_image(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    api_key: str = "",
    preferred_model: str = "",
) -> Dict[str, Any]:
    """
    Analyzes a spool label or barcode photo using Google Gemini Vision API with automatic multi-model fallback.
    Uses the per-user api_key and preferred_model without falling back to global .env keys.
    """
    clean_key = (api_key or "").strip()
    placeholder_keys = ("", "la_tua_api_key_gemini", "YOUR_API_KEY", "your_gemini_api_key")

    if not clean_key or clean_key in placeholder_keys:
        logger.info("Gemini Vision API called without a configured user API key.")
        return {
            "error": "GEMINI_API_KEY non configurata sul tuo profilo.",
            "configured": False,
            "success": False,
        }

    api_key = clean_key

    if not mime_type or mime_type == "application/octet-stream":
        mime_type = "image/jpeg"

    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    preferred_model = (preferred_model or "").strip() or "gemini-3.5-flash-lite"
    candidate_models = _get_candidate_models(preferred_model)

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": SYSTEM_PROMPT},
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": b64_image,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1,
        },
    }

    last_error = "Servizio Gemini temporaneamente occupato"
    used_model = ""

    async with httpx.AsyncClient(timeout=18.0) as client:
        for model_name in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            try:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    logger.warning(f"Gemini model {model_name} returned HTTP {resp.status_code}: {resp.text[:200]}")
                    last_error = f"HTTP {resp.status_code} su {model_name}"
                    continue

                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    continue

                text_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if not text_content:
                    continue

                clean_text = text_content.strip()
                if clean_text.startswith("```"):
                    clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text)
                    clean_text = re.sub(r"\s*```$", "", clean_text)

                parsed = json.loads(clean_text)
                used_model = model_name
                break
            except Exception as exc:
                logger.warning(f"Gemini model {model_name} failed: {exc}")
                last_error = str(exc)
                continue
        else:
            return {
                "error": f"Impossibile analizzare l'immagine ({last_error})",
                "configured": True,
                "success": False,
            }

    brand = str(parsed.get("brand") or "").strip()
    material = str(parsed.get("material") or "").strip().upper()
    subtype = str(parsed.get("subtype") or "").strip()
    color_name = str(parsed.get("color_name") or "").strip()
    barcode = str(parsed.get("barcode") or "").strip()

    color_hex = str(parsed.get("color_hex") or "").strip()
    if color_hex and not re.match(r"^#[0-9a-fA-F]{6}$", color_hex):
        color_hex = ""

    try:
        initial_net_weight_g = float(parsed.get("initial_net_weight_g") or 1000.0)
    except (ValueError, TypeError):
        initial_net_weight_g = 1000.0

    def _opt_int(val: Any) -> Any:
        try:
            return int(val) if val is not None and val != "" else None
        except (ValueError, TypeError):
            return None

    nozzle_temp_min = _opt_int(parsed.get("nozzle_temp_min"))
    nozzle_temp_max = _opt_int(parsed.get("nozzle_temp_max"))
    bed_temp = _opt_int(parsed.get("bed_temp"))

    # Determine which essential fields are still missing so the UI can ask the user
    missing_fields: List[str] = []
    if not brand:
        missing_fields.append("brand")
    if not material:
        missing_fields.append("material")
    if not color_name:
        missing_fields.append("color_name")

    return {
        "brand": brand,
        "material": material,
        "subtype": subtype,
        "color_name": color_name,
        "color_hex": color_hex,
        "initial_net_weight_g": initial_net_weight_g,
        "nozzle_temp_min": nozzle_temp_min,
        "nozzle_temp_max": nozzle_temp_max,
        "bed_temp": bed_temp,
        "barcode": barcode,
        "missing_fields": missing_fields,
        "model_used": used_model,
        "configured": True,
        "success": True,
    }
