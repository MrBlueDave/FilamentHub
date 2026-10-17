<div align="center">

# 🧵 FilamentHub 3D
### Progressive Web App per la Gestione Bobine di Filamento 3D, Calibrazioni Slicer & Stampa Etichette

[![Version](https://img.shields.io/badge/version-1.4-emerald.svg?style=for-the-badge)](https://github.com/MrBlueDave/FilamentHub)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![Proxmox LXC](https://img.shields.io/badge/Proxmox_LXC-Optimized-E57000.svg?style=for-the-badge&logo=proxmox&logoColor=white)](https://proxmox.com)

<p align="center">
  <b>FilamentHub 3D</b> è una PWA multi-utente moderna, mobile-first e desktop-ready creata per maker e professionisti della stampa 3D FDM. Permette a ciascun utente di gestire il proprio archivio personale di bobine, parametri di calibrazione avanzati per Slicer (K-Factor, Flow Ratio, Max Volumetric Speed), generare etichette termiche ad alto contrasto (Brother Bluetooth & Laser A4) e analizzare etichette e colori con la propria chiave personale <b>Gemini Vision AI</b>.
</p>

</div>

---

## ⚡ Caratteristiche Principali

- 👤 **Archivio Personale Multi-Utente & Chiave Gemini Personale:** Ogni utente registrato dispone del proprio inventario bobine privato e può configurare la propria API Key Google Gemini personale direttamente dalle Impostazioni.
- ⚖️ **Calcolo Dinamico dei Pesi & Quick Weigh:** Mai più calcoli a mano. Inserisci il peso lordo della bobina sulla bilancia: il sistema deduce la tara salvata e traccia lo storico esatto del consumo in grammi.
- 🤖 **Riconoscimento Etichette con Gemini Flash:** Inquadra o fotografa l'etichetta del produttore: l'intelligenza artificiale estrae brand, materiale (PLA, PETG, ASA, TPU...), temperature ottimali, colore, tara consigliata e barcode EAN.
- 🎨 **Campionatore Colore Filamento:** Tocca qualsiasi punto del filamento nella foto per estrarre il codice HEX esatto `#RRGGBB` e visualizzarlo nell'interfaccia.
- 🏷️ **Modulo Stampa Etichette Brother & A4 Laser:**
  - **Brother Bluetooth (12mm, 18mm, 24mm):** Generazione lato server di PNG monocromatici 1-bit a 300 DPI con Barcode Code128 o QR code + 3 righe di parametri tecnici. Condivisione diretta con l'app mobile Brother via Web Share API.
  - **Foglio Laser Adesivo A4:** Generatore di griglie personalizzate con selettore "Salva-Foglio" per riutilizzare etichette residue.
- 📱 **PWA Mobile-First & Azioni Rapide NFC/QR (`/s/{uid_code}`):** Vista ultraleggera per smartphone e tag NFC posizionati sulle bobine: aggiorna il peso o lo stato della bobina con un solo tocco.
- 🔒 **Sicurezza Enterprise per Esposizione Online:**
  - Zero registrazione pubblica (gestione utenti e reset password da Admin con Argon2id).
  - Due ruoli chiari: **Utente Standard** (archivio personale) e **Amministratore** (gestione utenti, tare e log).
  - Cookie di sessione `HttpOnly; SameSite=Lax` con token JWT.
  - Rate limiting sliding-window anti brute-force integrato (compatibile CrowdSec / Fail2ban).
  - Security headers HTTP (`nosniff`, `SAMEORIGIN`, `strict-origin-when-cross-origin`).

---

## 🚀 Installazione Rapida

Puoi installare **FilamentHub 3D v1.4** scegliendo tra due modalità: **Container Nativo Proxmox LXC** oppure **Docker & Docker Compose**.

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

Tutte le impostazioni di base del server sono nel file `.env` (puoi prendere come modello `.env.example`):

```ini
APP_PORT=8085
SECRET_KEY=inserisci_una_chiave_esadecimale_casuale_di_64_caratteri
COOKIE_SECURE=false

# Credenziali del primo utente Admin creato al primo avvio
INITIAL_ADMIN_USER=admin
INITIAL_ADMIN_PASSWORD=CambiaSubitoQuestaPassword123!
```

> [!TIP]
> Ogni utente può inserire o rimuovere la propria chiave **Google Gemini Vision API** gratuita direttamente nell'app dal menu **Impostazioni & Gemini AI**:
> 1. Vai su [Google AI Studio](https://aistudio.google.com/app/apikey)
> 2. Clicca su **Create API key** e copia la chiave generata.
> 3. Incollala nelle Impostazioni del tuo profilo su FilamentHub.

---

## 🏷️ Stampa Etichette Termiche Brother

FilamentHub supporta la stampa rapida su etichettatrici termiche Brother (**PT-P710BT Cube Plus, PT-P750W, PT-P900W, QL-800, ecc.**):
1. Dalla scheda dettaglio della bobina, tocca **Etichetta**.
2. Seleziona la larghezza del nastro caricato (**12mm, 18mm, 24mm**).
3. Tocca **Invia a Brother Bluetooth / Scarica PNG**: su smartphone si aprirà automaticamente il menu di condivisione nativo (Web Share API) inviando l'immagine PNG monocromatica ad alta risoluzione direttamente a **Brother iPrint&Label** o **P-Touch Design&Print**!

---

## 🛡️ Architettura & Sicurezza

- **Backend:** Python 3.12+, FastAPI, SQLite 3 nativo in modalità **WAL** (`PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;`).
- **Autenticazione:** Password hashate con **Argon2id**, sessioni via Cookie JWT `HttpOnly; SameSite=Lax`.
- **Isolamento Dati:** Archivio bobine e chiave Gemini API isolati per singolo utente.
- **Rate Limiting:** Protezione anti brute-force integrata con ban automatico di 15 minuti dopo 5 tentativi falliti e registrazione strutturata `[AUTH_FAIL]` compatibile con CrowdSec / Fail2ban.

---

## 📄 Licenza

Rilasciato sotto licenza MIT. Libero per uso personale e commerciale.
Progetto sviluppato con dedizione per la community della stampa 3D.
