"""FilamentHub 3D - Main FastAPI Application Entrypoint.
Initializes SQLite database, seeds demo spools on empty DB, applies security headers,
mounts static assets, and registers all API routers.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.database import get_db_connection, init_db
from app.routers.admin_router import router as admin_router
from app.routers.auth_router import router as auth_router
from app.routers.ha_router import router as ha_router
from app.routers.labels_router import router as labels_router
from app.routers.scanner_router import router as scanner_router
from app.routers.spools_router import router as spools_router

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "app" / "static"


def _seed_demo_spools() -> None:
    """Seeds 4 realistic demo spools and weight histories if the database is newly initialized."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM spools;")
        count = cursor.fetchone()["count"]
        if count == 0:
            demo_spools = [
                (
                    "SP-0001", "6975337030117", "Bambu Lab", "PLA", "Matte", "Charcoal",
                    "#1c1d21", "", 1000.0, 250.0, 1120.0, 150.0, 19.99, "AMS 1", "in_use", 0, 1, "Slot 1",
                    0.022, 0.98, 21.0, 0.8, 30.0, 190, 220, 55, 0,
                    "2026-10-01", "2026-10-01", 55, 6, 0, "Bobina demo Bambu Lab montata nello Slot 1"
                ),
                (
                    "SP-0002", "6975337030224", "Bambu Lab", "PETG", "HF", "Emerald Green",
                    "#10b981", "", 1000.0, 250.0, 850.0, 150.0, 22.99, "AMS 1", "in_use", 0, 1, "Slot 2",
                    0.035, 0.96, 16.0, 0.8, 30.0, 230, 250, 75, 0,
                    "2026-10-05", "2026-10-05", 65, 8, 0, "Bobina demo PETG HF montata nello Slot 2"
                ),
                (
                    "SP-0003", "6922572219151", "eSUN", "PLA+", "Standard", "Fire Engine Red",
                    "#dc2626", "", 1000.0, 240.0, 780.0, 150.0, 18.50, "A1", "opened", 0, 0, "",
                    0.024, 0.98, 18.0, 0.8, 30.0, 205, 225, 60, 0,
                    "2026-09-20", "2026-09-20", 50, 6, 0, "Stoccata a magazzino scaffale A1"
                ),
                (
                    "SP-0004", "8402542001004", "Polymaker", "ASA", "PolyLite", "Black",
                    "#1e1e1e", "", 1000.0, 140.0, 270.0, 150.0, 27.00, "Drybox 1", "opened", 1, 0, "",
                    0.040, 0.95, 14.0, 1.0, 25.0, 240, 260, 95, 45,
                    "2026-08-15", "2026-08-15", 70, 8, 1, "Bobina con avviso umidità elevata e scorta residua bassa"
                ),
            ]

            cursor.executemany(
                """
                INSERT INTO spools (
                    uid_code, barcode, brand, material, subtype, color_name, color_hex, color_hex_secondary,
                    initial_net_weight_g, tare_weight_g, current_gross_g, low_stock_threshold_g, price_eur,
                    location_shelf, status, in_drybox, in_use, slot_location, k_factor, flow_ratio,
                    max_volumetric_speed, retraction_length_mm, retraction_speed_mms, nozzle_temp_min,
                    nozzle_temp_max, bed_temp, chamber_temp, opened_at, last_dried_at, drying_temp_c,
                    drying_hours, humidity_alert, notes, created_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, datetime('now'), datetime('now')
                );
                """,
                demo_spools,
            )

            # Insert initial weight history entries
            cursor.execute("SELECT id, current_gross_g, tare_weight_g FROM spools ORDER BY id ASC;")
            seeded_spools = cursor.fetchall()
            for sp in seeded_spools:
                net_w = max(0.0, sp["current_gross_g"] - sp["tare_weight_g"])
                cursor.execute(
                    """
                    INSERT INTO weight_history (spool_id, gross_weight_g, net_weight_g, delta_g, recorded_by, recorded_at)
                    VALUES (?, ?, ?, 0.0, 'system_init', datetime('now'));
                    """,
                    (sp["id"], sp["current_gross_g"], net_w),
                )

            conn.commit()
            print(f"[FilamentHub DB] Seeded {len(demo_spools)} demo spools successfully.", flush=True)
    finally:
        conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager: initializes database schema and seeds initial data."""
    init_db()
    _seed_demo_spools()
    yield


app = FastAPI(
    title="FilamentHub 3D",
    version="1.3",
    description="3D Printing Filament & Slicer Calibration Inventory Management",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Enforces non-negotiable HTTP security headers for online exposure behind reverse proxies."""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Public Health Check
@app.get("/api/health", tags=["Health"])
def health_check() -> Dict[str, str]:
    """Health check endpoint for Docker container checks, monitors, and load balancers."""
    return {"status": "ok", "app": "FilamentHub 3D", "version": "1.3"}


# Include API Routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(spools_router)
app.include_router(scanner_router)
app.include_router(labels_router)
app.include_router(ha_router)

# Mount static files directory if present
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# HTML Page routes
@app.get("/print-a4")
def serve_print_a4_page():
    """Serves the printable A4 sticker grid page."""
    page_path = STATIC_DIR / "print_a4.html"
    if page_path.exists():
        return FileResponse(page_path, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return HTMLResponse("<h1>FilamentHub 3D - Print A4 Page</h1>", status_code=200)


@app.get("/s/{uid_code}")
def serve_quick_view_page(uid_code: str):
    """Serves the mobile quick-action page for NFC tags or QR scan."""
    page_path = STATIC_DIR / "quick.html"
    if page_path.exists():
        return FileResponse(page_path, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return HTMLResponse(f"<h1>FilamentHub 3D - Quick View: {uid_code}</h1>", status_code=200)


@app.get("/")
def serve_index_page():
    """Serves the main Single Page Application (SPA)."""
    page_path = STATIC_DIR / "index.html"
    if page_path.exists():
        return FileResponse(page_path, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return HTMLResponse("<h1>FilamentHub 3D - SPA</h1>", status_code=200)
