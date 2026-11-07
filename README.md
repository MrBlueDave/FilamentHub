<div align="center">

# 🧵 FilamentHub 3D
### Progressive Web App for 3D Filament Spool Management, Slicer Calibrations & Vision AI

[![Version](https://img.shields.io/badge/version-2.2-emerald.svg?style=for-the-badge)](https://github.com/MrBlueDave/FilamentHub)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![Proxmox LXC](https://img.shields.io/badge/Proxmox_LXC-Optimized-E57000.svg?style=for-the-badge&logo=proxmox&logoColor=white)](https://proxmox.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

<p align="center">
  <b>FilamentHub 3D</b> is a modern, mobile-first, and desktop-ready multi-user Progressive Web App (PWA) crafted for FDM 3D printing makers and print farm operators. It allows each user to manage their private spool inventory, slicer calibration parameters (K-Factor, Flow Ratio, Max Volumetric Speed), plan future spool purchases via a dedicated Shopping List, and extract label specs automatically using their own personal <b>Google Gemini Vision AI</b> key.
</p>

</div>

---

## ⚡ Key Features

- 👤 **Multi-User Isolation & Personal Gemini API Keys:** Each registered user maintains an isolated spool database and can configure their own personal Google Gemini API key directly from Settings.
- ⚖️ **Dynamic Weight & Consumption Tracking:** Automatic remaining net weight calculation (`net = max(0, gross - tare)`). Keep a database of brand spool tare weights and track usage history automatically.
- 🤖 **Vision AI Label Recognition (Gemini Flash):** Snap or upload a photo of a spool label. Neural AI extracts brand, material (PLA, PETG, ASA, TPU, PA-CF, etc.), recommended printing temperatures, color, tare weight, and EAN/code barcodes.
- 🎨 **Filament Color Eyedropper:** Tap directly on the photo canvas to sample the exact `#RRGGBB` hex color and apply it to the spool record.
- 🛒 **Filament Shopping List (Wishlist):** Dedicated section to track future spool purchases, view estimated budget totals, and convert bought items into active inventory spools with 1 tap.
- 🔀 **1-Tap Quick Sort & Instant Filters:** Toggle sorting directly between **Brand (A–Z)**, **Material (A–Z)**, and **Color Scale (Chromatic)** from the bottom bar across both Spools and Shopping List views, or filter by Brand and Material.
- 📱 **Mobile-First PWA:** Native-feeling touch gestures, swipeable cards, dark tech theme, and quick mobile action views.
- 🔒 **Enterprise-Grade Security:**
  - Zero public sign-up: accounts are created strictly by Administrators.
  - Dual roles: **Standard User** (isolated inventory) and **Administrator** (user management, tare dictionary, security audit logs).
  - Session cookies configured as `HttpOnly; SameSite=Lax` with signed JWT tokens.
  - Sliding-window rate limiting against brute-force attacks with structured security logging (`[AUTH_FAIL]`) compatible with CrowdSec and Fail2ban.
  - Strict HTTP security headers (`nosniff`, `SAMEORIGIN`, `strict-origin-when-cross-origin`).

---

## 🚀 Quick Installation

You can install **FilamentHub 3D v2.2** using either a **Native Proxmox LXC Container** or **Docker & Docker Compose**.

### Option 1: Proxmox LXC Container (Debian 12 / Ubuntu 22.04–24.04) — *Recommended*

Create an unprivileged LXC container on Proxmox VE, open the console, and run:

```bash
# Clone repository and launch the automated installer
git clone https://github.com/MrBlueDave/FilamentHub.git /opt/filamenthub
cd /opt/filamenthub
sudo bash scripts/install_lxc.sh
```

The script installs system dependencies, creates a Python virtual environment, generates a secure `.env` file, and configures the systemd service `filamenthub.service`.

#### Fast LXC Update:
```bash
cd /opt/filamenthub && sudo bash scripts/install_lxc.sh --update
```

---

### Option 2: Docker & Docker Compose

If you are running Docker on Linux, a NAS (Synology, TrueNAS, unRAID), or a VM:

```bash
git clone https://github.com/MrBlueDave/FilamentHub.git
cd FilamentHub
bash scripts/install_docker.sh
```

Or manually using Docker Compose:

```bash
cp .env.example .env
# Edit .env with a secure 64-character SECRET_KEY
docker compose up -d --build
```

#### Fast Docker Update:
```bash
bash scripts/install_docker.sh --update
```

---

### Master Installation Script (`install.sh`)

You can also run the root installer script to choose the installation mode interactively:

```bash
bash install.sh
```

Supported flags:
- `bash install.sh --lxc` (Force LXC installation)
- `bash install.sh --docker` (Force Docker installation)
- `bash install.sh --update` (Update the detected installation)

---

## ⚙️ Configuration (`.env`)

Base server configuration is stored in the `.env` file (see `.env.example` as a template):

```ini
APP_PORT=8085
SECRET_KEY=your_random_64_character_hex_secret_key
COOKIE_SECURE=false

# Initial Administrator account created on first startup if database is empty
INITIAL_ADMIN_USER=admin
INITIAL_ADMIN_PASSWORD=ChangeThisPasswordPromptly123!
```

> [!TIP]
> Each user can configure their free **Google Gemini Vision API** key directly within the app under **Settings & Vision AI**:
> 1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey).
> 2. Click **Create API key** and copy the generated key.
> 3. Paste it into your personal Settings in FilamentHub.

---

## 🛡️ Architecture & Tech Stack

- **Backend:** Python 3.12+, FastAPI, Uvicorn, native SQLite 3 in **WAL** mode (`PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;`).
- **Authentication:** Password hashing with **Argon2id**, JWT sessions in `HttpOnly; SameSite=Lax` cookies.
- **Frontend:** Lightweight Single Page Application (HTML5, modular ES6+ JavaScript, Tailwind CSS, Lucide Icons, html5-qrcode).
- **Data Isolation:** User inventories, wishlists, and Gemini API keys are strictly partitioned per user ID.

---

## 📄 License

Released under the MIT License. Free for personal and commercial use.
Crafted with passion for the 3D printing community.
