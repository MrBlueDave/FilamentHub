# Project Context & Agent Rules: FilamentHub 3D

## 1. Project Overview
FilamentHub 3D è una Progressive Web App (PWA) multi-utente, mobile-first e desktop-ready per la gestione completa dell'inventario bobine di stampa 3D, parametri di calibrazione Slicer (K-Factor, Flow Ratio, MVS), stampa etichette (Brother Bluetooth + Laser A4) e integrazione bidirezionale con Home Assistant.

## 2. Tech Stack & Architectural Constraints
- **Backend:** Python 3.12+, FastAPI, Uvicorn, Pydantic v2, SQLite3 nativo (con `PRAGMA journal_mode=WAL;` e `PRAGMA foreign_keys=ON;`).
- **Sicurezza & Auth:** `argon2-cffi` per hashing password, `pyjwt` per token JWT in cookie `HttpOnly`, header `X-API-Key` per automazioni esterne (Home Assistant).
- **Vision & HTTP Client:** `httpx` asincrono per chiamate a Google Gemini Vision API (`gemini-2.5-flash`) e invio Webhook verso Home Assistant.
- **Generazione Codici & Immagini:** `Pillow` (PIL), `python-barcode` (Code128) e `qrcode` per la generazione lato server/client di etichette monocromatiche ad alto contrasto per etichettatrici termiche Brother.
- **Frontend:** Architettura SPA leggera senza build step complessi (HTML5, Vanilla JS ES6+ modulare, Tailwind CSS via CDN o CLI, Lucide Icons, `html5-qrcode` per scansione live Barcode/QR da fotocamera).
- **Ambienti:** Sviluppo nativo su container Linux LXC (Debian/Ubuntu con Python `venv` e `systemd`), distribuzione finale tramite Docker (`Dockerfile` + `docker-compose.yml`).

## 3. Coding Standards & Non-Negotiable Rules
1. **Zero Registrazione Pubblica:** Non deve esistere alcun endpoint pubblico di sign-up. Gli utenti vengono creati solo dagli Admin. Al primo avvio con DB vuoto, il sistema crea un utente Admin iniziale leggendo `INITIAL_ADMIN_USER` e `INITIAL_ADMIN_PASSWORD` dal file `.env`.
2. **SQL Injection Prevention:** Tutte le query SQLite devono usare esclusivamente placeholder parametrizzati (`?`). Vietata qualsiasi interpolazione di stringhe nelle query.
3. **Proxy & Security Logging:** L'app sarà esposta su Internet dietro Reverse Proxy (Nginx Proxy Manager). Leggi sempre `X-Forwarded-For` o `X-Real-IP` per identificare l'IP client reale. Registra ogni tentativo di login fallito in formato strutturato (`[AUTH_FAIL] ip=... user=...`) sia su stdout/file che nella tabella `audit_logs`.
4. **Esclusività Slot Stampante:** Quando una bobina viene segnata come `in_use = True` su uno specifico `slot_location` (`Slot 1`, `Slot 2`, `Slot 3`, `Slot 4`, `Esterno`), qualsiasi altra bobina precedentemente assegnata a quello stesso slot deve passare automaticamente a `in_use = False` e `slot_location = ''`.
5. **Calcolo Pesi:** Il peso netto residuo non viene mai inserito a mano, ma calcolato dinamicamente: `net_remaining_g = max(0, current_gross_g - tare_weight_g)`.
6. **UI Responsive & Dark Tech:** Tema predefinito Slate/Zinc scuro (`#0f172a` / `#1e293b`), accenti Emerald per bobine montate, Amber per scorte basse o umidità elevata, Indigo per azioni primarie.