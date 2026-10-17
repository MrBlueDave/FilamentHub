# Backend & Database Specification

## 1. Struttura Directory del Progetto
```text
filament-hub/
├── app/
│   ├── __init__.py
│   ├── main.py              # Entrypoint FastAPI, middleware CORS/Proxy, mount static
│   ├── config.py            # Caricamento .env e costanti
│   ├── database.py          # Connessione SQLite WAL, init schema, seed tare
│   ├── auth.py              # Argon2id, JWT Cookie, X-API-Key, Rate Limiter login
│   ├── models.py            # Schemi Pydantic v2 (Request/Response)
│   ├── services/
│   │   ├── vision.py        # Integrazione Gemini 2.5 Flash API per analisi foto etichetta
│   │   ├── webhooks.py      # Invio eventi push asincroni a Home Assistant
│   │   └── label_gen.py     # Generazione PNG monocromatico Code128/QR per Brother
│   ├── routers/
│   │   ├── auth_router.py   # Login, Logout, Me, Cambio password
│   │   ├── admin_router.py  # CRUD Utenti, API Tokens, Tare Brand, Audit Logs
│   │   ├── spools_router.py # CRUD Bobine, Quick Weigh, Quick Slot Swap, Quick Dry
│   │   ├── scanner_router.py# Lookup Barcode -> Catalogo -> Fallback Vision AI
│   │   ├── labels_router.py # Endpoint generazione PNG Brother e dati griglia A4
│   │   └── ha_router.py     # Endpoint REST Home Assistant (/api/ha/overview e actions)
│   └── static/              # Frontend SPA (index.html, quick.html, print_a4.html, js, css)
├── data/                    # Persistenza SQLite (filaments.db) e log
├── scripts/
│   └── setup_lxc.sh         # Script provisioning automatico su LXC Debian/Ubuntu
├── .env.example
├── requirements.txt
├── Dockerfile
└── docker-compose.yml