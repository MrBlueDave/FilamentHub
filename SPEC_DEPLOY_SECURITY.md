# Security, LXC Development & Docker Production Spec

## 1. Requisiti di Sicurezza (Esposizione Online)
1. **Autenticazione & Sessioni:**
   - Password hashate con `argon2-cffi`.
   - Login rilascia un JWT firmato (`HS256` con `SECRET_KEY` a 64 caratteri) dentro un cookie `HttpOnly; SameSite=Lax` (e flag `Secure` attivabile da `.env` quando dietro HTTPS).
   - Tutte le rotte `/api/*` (eccetto `/api/auth/login` e `/api/health`) richiedono autenticazione valida via Cookie JWT o Header `X-API-Key`.
2. **Controllo Accessi basato sui Ruoli (RBAC):**
   - `viewer`: può solo leggere bobine, pesi e catalogo.
   - `editor`: può creare/modificare bobine, pesi, slot, usare lo scanner AI e stampare etichette.
   - `admin`: accesso completo + gestione utenti (`/api/admin/users`), gestione token API (`/api/admin/tokens`), gestione dizionario tare e visualizzazione `audit_logs`.
3. **Rate Limiting & Anti-BruteForce (CrowdSec Friendly):**
   - Tracker in-memory per IP reale (`X-Forwarded-For`): massimo **5 tentativi di login falliti in 15 minuti**, poi risponde con `HTTP 429 Too Many Requests`.
   - Ogni login fallito scrive una riga standardizzata su file `/app/data/security.log` e stdout:
     `2026-10-16T16:00:00Z [FILAMENTHUB_AUTH_FAIL] client_ip=1.2.3.4 username=test reason=invalid_credentials`
4. **Security Headers Middleware:**
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: SAMEORIGIN`
   - `Referrer-Policy: strict-origin-when-cross-origin`

## 2. Variabili d'Ambiente (`.env.example`)
```ini
APP_PORT=8085
SECRET_KEY=genera_una_chiave_esadecimale_casuale_di_64_caratteri
COOKIE_SECURE=false

# Primo utente Admin creato automaticamente se il DB è vuoto
INITIAL_ADMIN_USER=admin
INITIAL_ADMIN_PASSWORD=CambiaSubitoQuestaPassword123!

# Google Gemini Vision API (per riconoscimento etichette quando il barcode non è nel DB)
GEMINI_API_KEY=la_tua_api_key_gemini
GEMINI_MODEL=gemini-2.5-flash

# Integrazione Home Assistant (Opzionale)
HA_WEBHOOK_URL=[http://homeassistant.local:8123/api/webhook/filamenthub_events](http://homeassistant.local:8123/api/webhook/filamenthub_events)