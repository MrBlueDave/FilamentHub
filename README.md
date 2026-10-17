<div align="center">

# 🧵 FilamentHub 3D
### Progressive Web App per la Gestione Bobine di Filamento 3D, Calibrazioni Slicer & Stampa Etichette

[![Version](https://img.shields.io/badge/version-1.2-emerald.svg?style=for-the-badge)](https://github.com/MrBlueDave/FilamentHub)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![Proxmox LXC](https://img.shields.io/badge/Proxmox_LXC-Optimized-E57000.svg?style=for-the-badge&logo=proxmox&logoColor=white)](https://proxmox.com)
[![Home Assistant](https://img.shields.io/badge/Home_Assistant-Ready-41BDF5.svg?style=for-the-badge&logo=home-assistant&logoColor=white)](https://www.home-assistant.io)

<p align="center">
  <b>FilamentHub 3D</b> è una PWA moderna, mobile-first e desktop-ready creata per maker e professionisti della stampa 3D FDM. Permette di tenere traccia dell'intero inventario di bobine, parametri di calibrazione avanzati per Slicer (K-Factor, Flow Ratio, Max Volumetric Speed), generare etichette termiche ad alto contrasto (Brother Bluetooth & Laser A4), campionare colori via AI Vision e sincronizzare tutto con <b>Home Assistant</b>.
</p>

</div>

---

## ⚡ Caratteristiche Principali

- 🖨️ **Cockpit Stampante Interattivo (Slot 1-4 + Esterno):** Monitora in tempo reale le bobine montate nell'AMS/drybox con anello SVG del livello residuo, colore effettivo e calibrazioni immediate. Regola di esclusività slot automatica.
- ⚖️ **Calcolo Dinamico dei Pesi & Quick Weigh:** Mai più calcoli a mano. Inserisci il peso lordo della bobina sulla bilancia: il sistema deduce la tara salvata e traccia lo storico esatto del consumo in grammi.
- 🤖 **Riconoscimento Etichette con Gemini 2.5 Flash:** Inquadra o fotografa l'etichetta del produttore: l'intelligenza artificiale estrae brand, materiale (PLA, PETG, ASA, TPU...), temperature ottimali, colore, tara consigliata e barcode EAN.
- 🎨 **Campionatore Colore Filamento:** Tocca qualsiasi punto del filamento nella foto per estrarre il codice HEX esatto `#RRGGBB` e visualizzarlo nell'interfaccia.
- 🏷️ **Modulo Stampa Etichette Brother & A4 Laser:**
  - **Brother Bluetooth (12mm, 18mm, 24mm):** Generazione lato server di PNG monocromatici 1-bit a 300 DPI con Barcode Code128 o QR code + 3 righe di parametri tecnici. Condivisione diretta con l'app mobile Brother via Web Share API.
  - **Foglio Laser Adesivo A4:** Generatore di griglie personalizzate con selettore "Salva-Foglio" per riutilizzare etichette residue.
- 📱 **PWA Mobile-First & Azioni Rapide NFC/QR (`/s/{uid_code}`):** Vista ultraleggera per smartphone e tag NFC posizionati sulle bobine: aggiorna il peso o carica la bobina in uno slot con un solo tocco.
- 🏠 **Integrazione Bidirezionale Home Assistant:**
  - Endpoint `/api/ha/overview` e webhook push asincroni su eventi (`spool_weighed`, `slot_changed`, `spool_low_stock`, `spool_dried`).
  - Endpoint di consumo `/api/ha/action/consume` per scalare automaticamente i grammi stampati al termine dei job di stampa (es. Bambu Lab / OctoPrint).
- 🔒 **Sicurezza Enterprise per Esposizione Online:**
  - Zero registrazione pubblica (gestione utenti solo da Admin con Argon2id).
  - Cookie di sessione `HttpOnly; SameSite=Lax` con token JWT.
  - Rate limiting sliding-window anti brute-force integrato (compatibile CrowdSec / Fail2ban).
  - Autenticazione esterna tramite header `X-API-Key` per Home Assistant.
  - Security headers HTTP (`nosniff`, `SAMEORIGIN`, `strict-origin-when-cross-origin`).

---

## 🚀 Installazione Rapida

Puoi installare **FilamentHub 3D v1.2** scegliendo tra due modalità: **Container Nativo Proxmox LXC** oppure **Docker & Docker Compose**.

### Opzione 1: Container Proxmox LXC (Debian 12 / Ubuntu 22.04-24.04) — *Consigliata*

Crea un container LXC unprivileged su Proxmox con Debian 12 o Ubuntu, accedi alla console ed esegui:

```bash
# Clone e avvio dell'installatore automatico
git clone https://github.com/MrBlueDave/FilamentHub.git /opt/filamenthub
cd /opt/filamenthub
sudo bash scripts/install_lxc.sh
```

Lo script installerà i pacchetti minimi di sistema, creerà il virtualenv Python, configurerà il file `.env` con credenziali personalizzate o sicure generate al volo e avvierà il servizio di sistema **systemd** `filamenthub.service`.

#### Aggiornamento Rapido LXC:
```bash
cd /opt/filamenthub && sudo bash scripts/install_lxc.sh --update
```

---

### Opzione 2: Docker & Docker Compose

Se disponi già di Docker su qualsiasi host Linux, NAS o macchina virtuale:

```bash
git clone https://github.com/MrBlueDave/FilamentHub.git
cd FilamentHub
bash scripts/install_docker.sh
```

Oppure manualmente tramite compose:

```bash
cp .env.example .env
# Modifica .env inserendo una SECRET_KEY sicura a 64 caratteri
docker compose up -d --build
```

#### Aggiornamento Rapido Docker:
```bash
bash scripts/install_docker.sh --update
```

---

### Script Master Unificato (`install.sh`)

Puoi anche eseguire lo script principale nella root per scegliere interattivamente la modalità:

```bash
bash install.sh
```

Flag disponibili:
- `bash install.sh --lxc` (Forza installazione LXC)
- `bash install.sh --docker` (Forza installazione Docker)
- `bash install.sh --update` (Aggiorna l'installazione rilevata)

---

## ⚙️ Configurazione (`.env`)

Tutte le impostazioni sono centralizzate nel file `.env` (puoi prendere come modello `.env.example`):

```ini
APP_PORT=8085
SECRET_KEY=inserisci_una_chiave_esadecimale_casuale_di_64_caratteri
COOKIE_SECURE=false

# Credenziali del primo utente Admin creato al primo avvio
INITIAL_ADMIN_USER=admin
INITIAL_ADMIN_PASSWORD=CambiaSubitoQuestaPassword123!

# Google Gemini Vision API (Gratuita su https://aistudio.google.com/)
GEMINI_API_KEY=la_tua_api_key_gemini
GEMINI_MODEL=gemini-2.5-flash

# Integrazione Home Assistant (Opzionale)
HA_WEBHOOK_URL=http://homeassistant.local:8123/api/webhook/filamenthub_events
```

> [!TIP]
> Per ottenere la chiave **Google Gemini Vision API** gratuita:
> 1. Vai su [Google AI Studio](https://aistudio.google.com/)
> 2. Clicca su **Get API key** e crea una nuova chiave.
> 3. Inseriscila nel tuo `.env` alla voce `GEMINI_API_KEY`.

---

## 🏠 Integrazione con Home Assistant

### 1. Telemetria e Sensori
Crea un sensore REST nel tuo `configuration.yaml` in Home Assistant:

```yaml
sensor:
  - platform: rest
    name: "FilamentHub Overview"
    resource: "http://<IP_FILAMENTHUB>:8085/api/ha/overview"
    headers:
      X-API-Key: "LA_TUA_API_KEY_GENERATA_NEL_PANNELLO_ADMIN"
    json_attributes:
      - total_spools
      - total_net_weight_g
      - low_stock_count
      - humidity_alert_count
      - in_drybox_count
      - slots
    value_template: "{{ value_json.total_spools }}"
    scan_interval: 60
```

### 2. Scalare il Filamento Consumato a Fine Stampa
Invia una richiesta POST da un'automazione di Home Assistant (ad esempio al completamento di una stampa sulla tua Bambu Lab / Klipper):

```yaml
service: rest_command.filamenthub_consume
data:
  slot_location: "Slot 1"
  consumed_g: "{{ trigger.event.data.spool_grams_used }}"
```

---

## 🏷️ Stampa Etichette Termiche Brother

FilamentHub supporta la stampa rapida su etichettatrici termiche Brother (**PT-P710BT Cube Plus, PT-P750W, PT-P900W, QL-800, ecc.**):
1. Dalla card della bobina o dalla visualizzazione dettagliata, tocca **Stampa Etichetta Brother**.
2. Seleziona la larghezza del nastro caricato (**12mm, 18mm, 24mm**).
3. Tocca **Invia all'app Brother**: su smartphone si aprirà automaticamente il menu di condivisione nativo (Web Share API) inviando l'immagine PNG monocromatica ad alta risoluzione direttamente a **Brother iPrint&Label** o **P-Touch Design&Print**!

---

## 🛡️ Architettura & Sicurezza

- **Backend:** Python 3.12+, FastAPI, SQLite 3 nativo in modalità **WAL** (`PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;`).
- **Autenticazione:** Password hashate con **Argon2id**, sessioni via Cookie JWT `HttpOnly; SameSite=Lax`.
- **API Token:** SHA-256 hash per token macchina dedicati a Home Assistant.
- **Rate Limiting:** Protezione anti brute-force integrata con ban automatico di 15 minuti dopo 5 tentativi falliti e registrazione strutturata `[AUTH_FAIL]` compatibile con CrowdSec / Fail2ban.

---

## 📄 Licenza

Rilasciato sotto licenza MIT. Libero per uso personale e commerciale.
Progetto sviluppato con dedizione per la community della stampa 3D.
