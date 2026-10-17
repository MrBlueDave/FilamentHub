"""Pydantic v2 schemas and data validation models for FilamentHub 3D."""

import sqlite3
from datetime import datetime, timezone
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


# ==========================================
# Auth Models
# ==========================================

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str
    role: Literal["viewer", "editor", "admin"]
    is_active: bool
    created_at: str

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Admin & System Settings Models
# ==========================================

class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    role: Literal["viewer", "editor", "admin"] = "viewer"


class UserUpdateRequest(BaseModel):
    role: Optional[Literal["viewer", "editor", "admin"]] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6, max_length=128)


class ApiTokenCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    role: Literal["viewer", "editor", "admin"] = "editor"


class ApiTokenCreatedOut(BaseModel):
    id: int
    name: str
    token_prefix: str
    role: str
    created_at: str
    raw_token: str


class ApiTokenOut(BaseModel):
    id: int
    name: str
    token_prefix: str
    role: str
    last_used_at: Optional[str] = None
    created_at: str


class BrandTareCreate(BaseModel):
    brand_name: str = Field(..., min_length=1, max_length=100)
    spool_material: str = Field(default="Plastic", max_length=50)
    tare_weight_g: int = Field(..., ge=0, le=5000)
    notes: Optional[str] = ""


class BrandTareOut(BaseModel):
    id: int
    brand_name: str
    spool_material: str
    tare_weight_g: int
    notes: Optional[str] = ""

    model_config = ConfigDict(from_attributes=True)


class AuditLogOut(BaseModel):
    id: int
    timestamp: str
    client_ip: str
    username: Optional[str] = ""
    action: str
    details: Optional[str] = ""

    model_config = ConfigDict(from_attributes=True)


class SettingsUpdateRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    ha_webhook_url: Optional[str] = None
    show_ams_cockpit: Optional[bool] = None


class SettingsOut(BaseModel):
    gemini_configured: bool
    gemini_api_key_masked: str
    gemini_model: str
    ha_webhook_url: str
    show_ams_cockpit: bool


# ==========================================
# Spool Models
# ==========================================

class SpoolBase(BaseModel):
    brand: str = Field(default="Generico", min_length=1, max_length=100)
    material: str = Field(default="PLA", min_length=1, max_length=50)
    subtype: Optional[str] = Field(default="", max_length=50)
    color_name: str = Field(default="Standard", min_length=1, max_length=50)
    color_hex: str = Field(default="#3b82f6", max_length=20)
    color_hex_secondary: Optional[str] = Field(default="", max_length=20)
    initial_net_weight_g: Optional[float] = Field(default=1000.0, ge=1.0)
    tare_weight_g: Optional[float] = Field(default=250.0, ge=0.0)
    current_gross_g: Optional[float] = Field(default=1250.0, ge=0.0)
    low_stock_threshold_g: Optional[float] = Field(default=150.0, ge=0.0)
    price_eur: Optional[float] = Field(default=0.0, ge=0.0)
    location_shelf: Optional[str] = Field(default="", max_length=100)
    status: Optional[str] = Field(default="new", max_length=20)
    in_drybox: Optional[bool] = False
    in_use: Optional[bool] = False
    slot_location: Optional[str] = Field(default="", max_length=50)
    k_factor: Optional[float] = 0.020
    flow_ratio: Optional[float] = 0.98
    max_volumetric_speed: Optional[float] = 15.0
    retraction_length_mm: Optional[float] = 0.8
    retraction_speed_mms: Optional[float] = 30.0
    nozzle_temp_min: Optional[int] = 200
    nozzle_temp_max: Optional[int] = 220
    bed_temp: Optional[int] = 60
    chamber_temp: Optional[int] = 0
    opened_at: Optional[str] = ""
    last_dried_at: Optional[str] = ""
    drying_temp_c: Optional[int] = 55
    drying_hours: Optional[int] = 6
    humidity_alert: Optional[bool] = False
    notes: Optional[str] = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.brand or not self.brand.strip():
            self.brand = "Generico"
        if not self.material or not self.material.strip():
            self.material = "PLA"
        if not self.color_name or not self.color_name.strip():
            self.color_name = "Standard"
        if self.subtype is None:
            self.subtype = ""
        if self.color_hex_secondary is None:
            self.color_hex_secondary = ""
        if self.initial_net_weight_g is None:
            self.initial_net_weight_g = 1000.0
        if self.tare_weight_g is None:
            self.tare_weight_g = 250.0
        if self.current_gross_g is None:
            self.current_gross_g = self.initial_net_weight_g + self.tare_weight_g
        if self.low_stock_threshold_g is None:
            self.low_stock_threshold_g = 150.0
        if self.price_eur is None:
            self.price_eur = 0.0
        if self.location_shelf is None:
            self.location_shelf = ""
        if self.status is None:
            self.status = "new"
        if self.in_drybox is None:
            self.in_drybox = False
        if self.in_use is None:
            self.in_use = False
        if self.slot_location is None:
            self.slot_location = ""
        if self.k_factor is None:
            self.k_factor = 0.020
        if self.flow_ratio is None:
            self.flow_ratio = 0.98
        if self.max_volumetric_speed is None:
            self.max_volumetric_speed = 15.0
        if self.retraction_length_mm is None:
            self.retraction_length_mm = 0.8
        if self.retraction_speed_mms is None:
            self.retraction_speed_mms = 30.0
        if self.nozzle_temp_min is None:
            self.nozzle_temp_min = 200
        if self.nozzle_temp_max is None:
            self.nozzle_temp_max = 220
        if self.bed_temp is None:
            self.bed_temp = 60
        if self.chamber_temp is None:
            self.chamber_temp = 0
        if self.opened_at is None:
            self.opened_at = ""
        if self.last_dried_at is None:
            self.last_dried_at = ""
        if self.drying_temp_c is None:
            self.drying_temp_c = 55
        if self.drying_hours is None:
            self.drying_hours = 6
        if self.humidity_alert is None:
            self.humidity_alert = False
        if self.notes is None:
            self.notes = ""


class SpoolCreate(SpoolBase):
    uid_code: Optional[str] = None
    barcode: Optional[str] = Field(default="", max_length=100)
    quantity: int = Field(default=1, ge=1, le=50)

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        if self.barcode is None:
            self.barcode = ""



class SpoolUpdate(BaseModel):
    brand: Optional[str] = None
    material: Optional[str] = None
    subtype: Optional[str] = None
    color_name: Optional[str] = None
    color_hex: Optional[str] = None
    color_hex_secondary: Optional[str] = None
    barcode: Optional[str] = None
    initial_net_weight_g: Optional[float] = None
    tare_weight_g: Optional[float] = None
    current_gross_g: Optional[float] = None
    low_stock_threshold_g: Optional[float] = None
    price_eur: Optional[float] = None
    location_shelf: Optional[str] = None
    status: Optional[str] = None
    in_drybox: Optional[bool] = None
    in_use: Optional[bool] = None
    slot_location: Optional[str] = None
    k_factor: Optional[float] = None
    flow_ratio: Optional[float] = None
    max_volumetric_speed: Optional[float] = None
    retraction_length_mm: Optional[float] = None
    retraction_speed_mms: Optional[float] = None
    nozzle_temp_min: Optional[int] = None
    nozzle_temp_max: Optional[int] = None
    bed_temp: Optional[int] = None
    chamber_temp: Optional[int] = None
    opened_at: Optional[str] = None
    last_dried_at: Optional[str] = None
    drying_temp_c: Optional[int] = None
    drying_hours: Optional[int] = None
    humidity_alert: Optional[bool] = None
    notes: Optional[str] = None


class SpoolOut(SpoolBase):
    id: int
    uid_code: str
    barcode: Optional[str] = ""
    created_at: str
    updated_at: str
    status: str
    net_remaining_g: float
    percent_remaining: float
    is_low_stock: bool
    needs_drying: bool

    model_config = ConfigDict(from_attributes=True)


class QuickWeighRequest(BaseModel):
    gross_weight_g: float = Field(..., ge=0.0)


class QuickSlotRequest(BaseModel):
    in_use: bool
    slot_location: str = ""


class QuickStatusRequest(BaseModel):
    status: Literal["new", "opened", "in_use", "empty"]
    slot_location: Optional[str] = ""


class SpoolCloneRequest(BaseModel):
    quantity: int = Field(default=1, ge=1, le=50)
    status: str = Field(default="new")


class QuickDryRequest(BaseModel):
    drying_temp_c: Optional[int] = None
    drying_hours: Optional[int] = None


class WeightHistoryOut(BaseModel):
    id: int
    spool_id: int
    gross_weight_g: float
    net_weight_g: float
    delta_g: float
    recorded_by: Optional[str] = ""
    recorded_at: str

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Scanner Models
# ==========================================

class BarcodeLookupOut(BaseModel):
    found: bool
    type: Optional[str] = "not_found"
    catalog_item: Optional[dict[str, Any]] = None
    existing_spool: Optional[dict[str, Any]] = None
    existing_spools: Optional[list[dict[str, Any]]] = None
    template: Optional[dict[str, Any]] = None
    match_source: Optional[str] = None


class VisionAnalysisOut(BaseModel):
    brand: Optional[str] = None
    material: Optional[str] = None
    subtype: Optional[str] = None
    color_name: Optional[str] = None
    color_hex: Optional[str] = None
    barcode: Optional[str] = None
    net_weight_g: Optional[float] = None
    nozzle_temp_min: Optional[int] = None
    nozzle_temp_max: Optional[int] = None
    bed_temp: Optional[int] = None
    notes: Optional[str] = None
    raw_text: Optional[str] = None


# ==========================================
# Row Conversion & Computed Fields
# ==========================================

HYGROSCOPIC_MATERIALS = (
    "PETG",
    "TPU",
    "PA",
    "NYLON",
    "ABS",
    "ASA",
    "PC",
    "PVA",
    "BVOH",
    "CARBON",
    "CF",
    "GF",
    "POLYCARBONATE",
    "POLYAMIDE",
)


def row_to_spool_dict(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    """Convert an SQLite Row or dict into a full spool dict with dynamic computed fields."""
    d = dict(row)

    # Boolean fields conversion
    d["in_drybox"] = bool(d.get("in_drybox", 0))
    d["in_use"] = bool(d.get("in_use", 0))
    d["humidity_alert"] = bool(d.get("humidity_alert", 0))

    # Dynamic Weight calculations
    current_gross = float(d.get("current_gross_g") or 0.0)
    tare_weight = float(d.get("tare_weight_g") or 0.0)
    initial_net = max(1.0, float(d.get("initial_net_weight_g") or 1000.0))
    low_stock_threshold = float(d.get("low_stock_threshold_g") or 150.0)

    net_remaining = round(max(0.0, current_gross - tare_weight), 1)
    percent_remaining = round(min(100.0, max(0.0, (net_remaining / initial_net) * 100.0)), 1)
    is_low_stock = bool(net_remaining <= low_stock_threshold)

    # Dynamic status calculation
    raw_status = (d.get("status") or "").strip()
    if d["in_use"]:
        computed_status = "in_use"
    elif net_remaining <= 0:
        computed_status = "empty"
    elif raw_status in ("new", "opened", "in_use", "empty"):
        if raw_status == "in_use" and not d["in_use"]:
            computed_status = "opened"
        else:
            computed_status = raw_status
    else:
        if d.get("opened_at") or net_remaining < initial_net:
            computed_status = "opened"
        else:
            computed_status = "new"

    d["status"] = computed_status

    # Dynamic needs_drying check
    needs_drying = False
    if d["humidity_alert"]:
        needs_drying = True
    elif not d["in_drybox"]:
        mat_text = f"{d.get('material', '')} {d.get('subtype', '')}".strip().upper()
        if any(h in mat_text for h in HYGROSCOPIC_MATERIALS):
            ref_date = (d.get("last_dried_at") or "").strip() or (d.get("opened_at") or "").strip()
            if ref_date:
                try:
                    clean_date = ref_date.replace("Z", "+00:00")
                    if len(clean_date) == 10:
                        parsed_dt = datetime.fromisoformat(clean_date).replace(tzinfo=timezone.utc)
                    else:
                        parsed_dt = datetime.fromisoformat(clean_date)
                        if parsed_dt.tzinfo is None:
                            parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                    now_utc = datetime.now(timezone.utc)
                    if (now_utc - parsed_dt).days >= 30:
                        needs_drying = True
                except Exception:
                    needs_drying = False

    d["net_remaining_g"] = net_remaining
    d["percent_remaining"] = percent_remaining
    d["is_low_stock"] = is_low_stock
    d["needs_drying"] = needs_drying

    return d
