"""Brother P-Touch Thermal Label generator service.

Produces crisp, high-contrast monochrome 1-bit PNG images at 300 DPI
proportioned for 12mm, 18mm, and 24mm Brother thermal continuous/die-cut tapes.
"""

import io
import os
from typing import Any, Dict, Tuple
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
import qrcode

# Label tape dimensions in pixels at 300 DPI (approx 12mm, 18mm, 24mm)
TAPE_DIMENSIONS: Dict[int, Tuple[int, int]] = {
    12: (560, 142),
    18: (680, 212),
    24: (800, 284),
}

CANDIDATE_FONT_PATHS = [
    # Linux Debian / Ubuntu (fonts-dejavu-core)
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    # Windows paths
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
]


def _get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Attempts to load a clean TrueType font, falling back to default if unavailable."""
    for path in CANDIDATE_FONT_PATHS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    # Fallback to default PIL bitmap font
    return ImageFont.load_default()


def generate_brother_label_png(
    spool: Dict[str, Any],
    tape_mm: int = 24,
    code_type: str = "barcode"
) -> bytes:
    """
    Generates a pure monochrome (1-bit B&W) 300 DPI PNG label for Brother printers.

    Args:
        spool: Dict containing spool data (uid_code, material, subtype, brand, color_name, etc.)
        tape_mm: Tape width in mm (12, 18, or 24). Defaults to 24.
        code_type: Either 'barcode' (Code128) or 'qr'.

    Returns:
        Raw bytes of the monochrome PNG file.
    """
    width, height = TAPE_DIMENSIONS.get(tape_mm, TAPE_DIMENSIONS[24])

    # Canvas in 8-bit grayscale for drawing
    img = Image.new("L", (width, height), color=255)
    draw = ImageDraw.Draw(img)

    uid_code = str(spool.get("uid_code") or "SP-0000").strip().upper()
    material = str(spool.get("material") or "PLA").strip().upper()
    subtype = str(spool.get("subtype") or "").strip().upper()
    brand = str(spool.get("brand") or "Generic").strip()
    color_name = str(spool.get("color_name") or "Standard").strip()

    nozzle = spool.get("nozzle_temp_max") or spool.get("nozzle_temp_min") or 220
    bed = spool.get("bed_temp") or 60
    try:
        k_val = float(spool.get("k_factor") or 0.0)
    except (ValueError, TypeError):
        k_val = 0.0

    try:
        tare_val = int(round(float(spool.get("tare_weight_g") or 0.0)))
    except (ValueError, TypeError):
        tare_val = 0

    # Layout partitions
    margin_x = 10
    margin_y = 10
    left_width = int(width * 0.35)
    x_divider = left_width + 12

    # Draw outer bounding border
    draw.rectangle([(2, 2), (width - 3, height - 3)], outline=0, width=2)
    # Draw vertical divider line
    draw.line([(x_divider, margin_y), (x_divider, height - margin_y)], fill=0, width=2)

    # 1. Render Left Code (Barcode or QR)
    code_area_w = left_width - margin_x
    code_area_h = height - (2 * margin_y)

    if code_type.lower() == "qr":
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=1
        )
        qr.add_data(uid_code)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("L")

        # Make square and fit inside code area
        target_size = min(code_area_w, code_area_h)
        qr_resized = qr_img.resize((target_size, target_size), resample=Image.Resampling.NEAREST)

        # Center vertically and horizontally in left partition
        paste_x = margin_x + (code_area_w - target_size) // 2
        paste_y = margin_y + (code_area_h - target_size) // 2
        img.paste(qr_resized, (paste_x, paste_y))
    else:
        # Default: Code128 Barcode
        try:
            code128_cls = barcode.get_barcode_class("code128")
            bc = code128_cls(uid_code, writer=ImageWriter())
            writer_options = {
                "module_width": 0.4,
                "module_height": 14.0,
                "quiet_zone": 1.0,
                "write_text": False
            }
            bc_bio = io.BytesIO()
            bc.write(bc_bio, options=writer_options)
            bc_bio.seek(0)
            bc_img = Image.open(bc_bio).convert("L")

            # Scale to fit code area crisply
            # Maintain proportions or scale to fit nicely
            scale_w = code_area_w / max(1, bc_img.width)
            scale_h = code_area_h / max(1, bc_img.height)
            scale = min(scale_w, scale_h)
            new_w = max(10, int(bc_img.width * scale))
            new_h = max(10, int(bc_img.height * scale))

            bc_resized = bc_img.resize((new_w, new_h), resample=Image.Resampling.NEAREST)
            paste_x = margin_x + (code_area_w - new_w) // 2
            paste_y = margin_y + (code_area_h - new_h) // 2
            img.paste(bc_resized, (paste_x, paste_y))
        except Exception:
            # Fallback if barcode fails: draw text code
            fb_font = _get_font(20, bold=True)
            draw.text((margin_x + 10, height // 2 - 10), uid_code, fill=0, font=fb_font)

    # 2. Render Right Side (3 Lines of technical specs)
    x_text = x_divider + 14
    max_text_w = width - x_text - 10

    # Line texts
    mat_part = f"{material} {subtype}".strip()
    line1 = f"{uid_code} | {mat_part}"
    line2 = f"{brand} - {color_name}"
    line3 = f"{nozzle}/{bed}°C | K:{k_val:.3f} | T:{tare_val}g"

    # Font sizing adapted per tape height
    if tape_mm == 12:
        f1_size = 19
        f2_size = 16
        f3_size = 15
        y1, y2, y3 = 12, 50, 88
    elif tape_mm == 18:
        f1_size = 28
        f2_size = 23
        f3_size = 21
        y1, y2, y3 = 18, 76, 134
    else:  # 24mm
        f1_size = 38
        f2_size = 31
        f3_size = 28
        y1, y2, y3 = 24, 102, 180

    font1 = _get_font(f1_size, bold=True)
    font2 = _get_font(f2_size, bold=False)
    font3 = _get_font(f3_size, bold=False)

    # Truncate strings gracefully if they exceed text area
    def _truncate_text(text: str, font: ImageFont.ImageFont, max_w: int) -> str:
        cur_text = text
        while cur_text:
            bbox = draw.textbbox((0, 0), cur_text, font=font)
            text_w = bbox[2] - bbox[0]
            if text_w <= max_w:
                return cur_text
            cur_text = cur_text[:-1].rstrip()
        return text

    line1_draw = _truncate_text(line1, font1, max_text_w)
    line2_draw = _truncate_text(line2, font2, max_text_w)
    line3_draw = _truncate_text(line3, font3, max_text_w)

    draw.text((x_text, y1), line1_draw, fill=0, font=font1)
    draw.text((x_text, y2), line2_draw, fill=0, font=font2)
    draw.text((x_text, y3), line3_draw, fill=0, font=font3)

    # 3. Convert to pure monochrome 1-bit (threshold at 128)
    mono_img = img.point(lambda p: 255 if p > 128 else 0, mode="1")

    # Save to PNG with 300 DPI metadata
    out_bio = io.BytesIO()
    mono_img.save(out_bio, format="PNG", dpi=(300, 300))
    return out_bio.getvalue()
