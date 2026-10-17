#!/bin/bash
# ==============================================================================
# FilamentHub 3D v1.1 - LXC Installation & Update Script (Debian / Ubuntu)
# Designed for Proxmox LXC containers (Debian 12 / Ubuntu 22.04 - 24.04)
# ==============================================================================
set -e

REPO_URL="https://github.com/MrBlueDave/FilamentHub.git"
DEFAULT_INSTALL_DIR="/opt/filamenthub"
APP_NAME="FilamentHub 3D v1.1"
SERVICE_NAME="filamenthub"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}"
echo "======================================================================="
echo "        🧵 FilamentHub 3D v1.1 - Installer LXC (Debian/Ubuntu)         "
echo "======================================================================="
echo -e "${NC}"

# Check for root / sudo
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERRORE] Esegui questo script come root o con sudo: sudo bash $0${NC}"
    exit 1
fi

# Detect working directory
if [ -f "app/main.py" ] && [ -f "requirements.txt" ]; then
    APP_DIR="$(pwd)"
elif [ -f "../app/main.py" ] && [ -f "../requirements.txt" ]; then
    APP_DIR="$(cd .. && pwd)"
elif [ -d "$DEFAULT_INSTALL_DIR" ] && [ -f "$DEFAULT_INSTALL_DIR/app/main.py" ]; then
    APP_DIR="$DEFAULT_INSTALL_DIR"
else
    APP_DIR="$DEFAULT_INSTALL_DIR"
fi

# ==============================================================================
# Update Mode (--update or -u)
# ==============================================================================
if [ "$1" = "--update" ] || [ "$1" = "-u" ]; then
    echo -e "${YELLOW}>>> Modalità Aggiornamento Rapido rilevata...${NC}"
    if [ ! -d "$APP_DIR" ] || [ ! -f "$APP_DIR/app/main.py" ]; then
        echo -e "${RED}[ERRORE] Impossibile trovare l'installazione in $APP_DIR${NC}"
        exit 1
    fi

    cd "$APP_DIR"
    echo -e "${BLUE}1. Download aggiornamenti da Git...${NC}"
    if [ -d ".git" ]; then
        git pull origin main || git pull
    fi

    echo -e "${BLUE}2. Aggiornamento dipendenze Python...${NC}"
    VENV_PATH="$APP_DIR/.venv"
    if [ ! -d "$VENV_PATH" ] && [ -d "$APP_DIR/venv" ]; then
        VENV_PATH="$APP_DIR/venv"
    fi
    "$VENV_PATH/bin/pip" install --upgrade pip
    "$VENV_PATH/bin/pip" install -r "$APP_DIR/requirements.txt"

    echo -e "${BLUE}3. Riavvio servizio Systemd...${NC}"
    systemctl restart ${SERVICE_NAME}.service

    echo -e "${GREEN}${BOLD}✓ FilamentHub 3D aggiornato con successo alla v1.1!${NC}"
    systemctl status ${SERVICE_NAME}.service --no-pager -n 10
    exit 0
fi

# ==============================================================================
# Step 1: System Packages Installation
# ==============================================================================
echo -e "${BLUE}>>> [1/6] Installazione pacchetti di sistema (apt)...${NC}"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
    python3 \
    python3-venv \
    python3-pip \
    git \
    curl \
    openssl \
    ca-certificates \
    fonts-dejavu-core

# ==============================================================================
# Step 2: Clone or Setup Repository Directory
# ==============================================================================
echo -e "${BLUE}>>> [2/6] Verifica directory applicazione ($APP_DIR)...${NC}"
if [ ! -f "$APP_DIR/app/main.py" ]; then
    echo "Clonazione repository da $REPO_URL in $APP_DIR..."
    mkdir -p "$APP_DIR"
    git clone "$REPO_URL" "$APP_DIR" || {
        echo -e "${YELLOW}Clone fallito o repo privata. Creazione directory locale manuale...${NC}"
    }
fi
cd "$APP_DIR"

# ==============================================================================
# Step 3: Python Virtual Environment Setup
# ==============================================================================
echo -e "${BLUE}>>> [3/6] Creazione ambiente virtuale Python (.venv)...${NC}"
VENV_DIR="$APP_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt" -q
echo -e "${GREEN}✓ Dipendenze Python installate.${NC}"

# ==============================================================================
# Step 4: Data Directory & Environment Configuration
# ==============================================================================
echo -e "${BLUE}>>> [4/6] Configurazione storage persistente e variabili .env...${NC}"
mkdir -p "$APP_DIR/data"
chmod 750 "$APP_DIR/data"

ENV_FILE="$APP_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    # Generate cryptographic random SECRET_KEY
    RANDOM_SECRET=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")

    # Interactive prompts if terminal is available
    if [ -t 0 ] && [ "$DEBIAN_FRONTEND" != "noninteractive" ]; then
        echo -e "${CYAN}--- Configurazione Parametri Iniziali (Premi Invio per default) ---${NC}"
        read -r -p "Porta server HTTP [default 8085]: " INPUT_PORT
        read -r -p "Nome utente Amministratore iniziale [default admin]: " INPUT_USER
        read -r -s -p "Password Amministratore iniziale [default CambiaSubitoQuestaPassword123!]: " INPUT_PASS
        echo ""
        read -r -p "Chiave Google Gemini Vision API (opzionale, premi Invio se non ne hai una ora): " INPUT_GEMINI
    fi

    TARGET_PORT=${INPUT_PORT:-8085}
    TARGET_USER=${INPUT_USER:-admin}
    TARGET_PASS=${INPUT_PASS:-CambiaSubitoQuestaPassword123!}
    TARGET_GEMINI=${INPUT_GEMINI:-la_tua_api_key_gemini}

    cat <<EOF > "$ENV_FILE"
APP_PORT=${TARGET_PORT}
SECRET_KEY=${RANDOM_SECRET}
COOKIE_SECURE=false

# Primo utente Admin creato automaticamente se il DB è vuoto
INITIAL_ADMIN_USER=${TARGET_USER}
INITIAL_ADMIN_PASSWORD=${TARGET_PASS}

# Google Gemini Vision API (per riconoscimento etichette quando il barcode non è nel DB)
GEMINI_API_KEY=${TARGET_GEMINI}
GEMINI_MODEL=gemini-2.5-flash

# Integrazione Home Assistant (Opzionale)
HA_WEBHOOK_URL=http://homeassistant.local:8123/api/webhook/filamenthub_events
EOF
    chmod 600 "$ENV_FILE"
    echo -e "${GREEN}✓ File .env generato con successo.${NC}"
else
    echo -e "${YELLOW}File .env già esistente, le credenziali e configurazioni attuali sono state preservate.${NC}"
    # Read port from .env if present
    TARGET_PORT=$(grep -E "^APP_PORT=" "$ENV_FILE" | cut -d '=' -f2 | tr -d ' ' || echo "8085")
fi

# ==============================================================================
# Step 5: Systemd Service Configuration
# ==============================================================================
echo -e "${BLUE}>>> [5/6] Configurazione e avvio servizio Systemd (${SERVICE_NAME}.service)...${NC}"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

cat <<EOF > "$SERVICE_PATH"
[Unit]
Description=FilamentHub 3D Spool Management Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$VENV_DIR/bin/uvicorn app.main:app --host 0.0.0.0 --port ${TARGET_PORT:-8085} --proxy-headers --forwarded-allow-ips=*
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=filamenthub

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"
systemctl restart "${SERVICE_NAME}.service"

# ==============================================================================
# Step 6: Health Verification & Summary
# ==============================================================================
echo -e "${BLUE}>>> [6/6] Verifica avvio applicazione...${NC}"
sleep 2

LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
[ -z "$LOCAL_IP" ] && LOCAL_IP="127.0.0.1"
ACTIVE_PORT=${TARGET_PORT:-8085}

if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
    echo ""
    echo -e "${GREEN}${BOLD}=======================================================================${NC}"
    echo -e "${GREEN}${BOLD}  🎉 FilamentHub 3D v1.1 INSTALLATO ED AVVIATO CON SUCCESSO!           ${NC}"
    echo -e "${GREEN}${BOLD}=======================================================================${NC}"
    echo -e "  🌐 ${BOLD}Indirizzo Web:${NC}       http://${LOCAL_IP}:${ACTIVE_PORT}"
    echo -e "  📖 ${BOLD}Documentazione API:${NC}  http://${LOCAL_IP}:${ACTIVE_PORT}/docs"
    echo -e "  👤 ${BOLD}Utente Admin:${NC}        ${TARGET_USER:-admin}"
    echo -e "  🔑 ${BOLD}Password Iniziale:${NC}   ${TARGET_PASS:-(Impostata nel file .env)}"
    echo ""
    echo -e "  ${YELLOW}Comandi utili di gestione:${NC}"
    echo -e "  • Stato servizio:        ${CYAN}systemctl status ${SERVICE_NAME}${NC}"
    echo -e "  • Log in tempo reale:    ${CYAN}journalctl -u ${SERVICE_NAME} -f${NC}"
    echo -e "  • Riavvio servizio:      ${CYAN}systemctl restart ${SERVICE_NAME}${NC}"
    echo -e "  • Aggiornamento futuro:  ${CYAN}cd $APP_DIR && bash scripts/install_lxc.sh --update${NC}"
    echo -e "${GREEN}${BOLD}=======================================================================${NC}"
else
    echo -e "${RED}[ATTENZIONE] Il servizio non sembra attivo. Controlla i log con:${NC}"
    echo "journalctl -u ${SERVICE_NAME} -n 50 --no-pager"
    exit 1
fi
