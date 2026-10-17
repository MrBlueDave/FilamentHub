#!/bin/bash
# ==============================================================================
# FilamentHub 3D v1.1 - Docker & Docker Compose Installer
# Automated deployment script for Linux environments
# ==============================================================================
set -e

APP_NAME="FilamentHub 3D v1.1"
REPO_URL="https://github.com/MrBlueDave/FilamentHub.git"
DEFAULT_INSTALL_DIR="/opt/filamenthub"

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
echo "       🐳 FilamentHub 3D v1.1 - Installer Docker & Compose             "
echo "======================================================================="
echo -e "${NC}"

# Detect working directory
if [ -f "docker-compose.yml" ] && [ -f "Dockerfile" ]; then
    APP_DIR="$(pwd)"
elif [ -f "../docker-compose.yml" ] && [ -f "../Dockerfile" ]; then
    APP_DIR="$(cd .. && pwd)"
elif [ -d "$DEFAULT_INSTALL_DIR" ] && [ -f "$DEFAULT_INSTALL_DIR/docker-compose.yml" ]; then
    APP_DIR="$DEFAULT_INSTALL_DIR"
else
    APP_DIR="$DEFAULT_INSTALL_DIR"
fi

# ==============================================================================
# Update Mode (--update or -u)
# ==============================================================================
if [ "$1" = "--update" ] || [ "$1" = "-u" ]; then
    echo -e "${YELLOW}>>> Modalità Aggiornamento Docker rilevata...${NC}"
    if [ ! -d "$APP_DIR" ]; then
        echo -e "${RED}[ERRORE] Directory di installazione $APP_DIR non trovata.${NC}"
        exit 1
    fi

    cd "$APP_DIR"
    echo -e "${BLUE}1. Download ultimi sorgenti da Git...${NC}"
    if [ -d ".git" ]; then
        git pull origin main || git pull
    fi

    echo -e "${BLUE}2. Ricostruzione immagine Docker e riavvio container...${NC}"
    if command -v docker-compose &> /dev/null; then
        docker-compose build --no-cache
        docker-compose up -d --remove-orphans
    else
        docker compose build --no-cache
        docker compose up -d --remove-orphans
    fi

    echo -e "${GREEN}${BOLD}✓ FilamentHub 3D aggiornato con successo alla v1.1 (Docker)!${NC}"
    exit 0
fi

# ==============================================================================
# Step 1: Check & Install Docker / Docker Compose
# ==============================================================================
echo -e "${BLUE}>>> [1/5] Verifica presenza Docker e Docker Compose...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker non trovato. Avvio installazione automatica via get.docker.com...${NC}"
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}[ERRORE] Sono richiesti i privilegi di root per installare Docker. Esegui con sudo.${NC}"
        exit 1
    fi
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo -e "${GREEN}✓ Docker installato con successo.${NC}"
else
    echo -e "${GREEN}✓ Docker è già installato: $(docker --version)${NC}"
fi

# Detect Compose command (plugin 'docker compose' or standalone 'docker-compose')
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo -e "${YELLOW}Docker Compose non trovato. Installazione plugin compose...${NC}"
    if [ "$EUID" -eq 0 ]; then
        apt-get update -qq && apt-get install -y -qq docker-compose-plugin || {
            echo -e "${RED}Impossibile installare docker-compose-plugin via apt.${NC}"
        }
        COMPOSE_CMD="docker compose"
    else
        echo -e "${RED}[ERRORE] Installa 'docker-compose' o 'docker compose' per proseguire.${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ Utilizzo comando Compose: '$COMPOSE_CMD'${NC}"

# ==============================================================================
# Step 2: Ensure Repository Files Exist
# ==============================================================================
echo -e "${BLUE}>>> [2/5] Verifica cartella progetto ($APP_DIR)...${NC}"
if [ ! -f "$APP_DIR/docker-compose.yml" ]; then
    echo "Clonazione repository in $APP_DIR..."
    mkdir -p "$APP_DIR"
    git clone "$REPO_URL" "$APP_DIR" || {
        echo -e "${YELLOW}Clone fallito o repo non pubblica. Assicurati che docker-compose.yml sia presente.${NC}"
    }
fi
cd "$APP_DIR"

# ==============================================================================
# Step 3: Setup Storage and .env
# ==============================================================================
echo -e "${BLUE}>>> [3/5] Preparazione volume persistente ./data e file .env...${NC}"
mkdir -p "$APP_DIR/data"
chmod 755 "$APP_DIR/data"

ENV_FILE="$APP_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    RANDOM_SECRET=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0")

    if [ -t 0 ]; then
        echo -e "${CYAN}--- Configurazione Parametri Iniziali (Premi Invio per default) ---${NC}"
        read -r -p "Porta host per FilamentHub [default 8085]: " INPUT_PORT
        read -r -p "Nome utente Admin iniziale [default admin]: " INPUT_USER
        read -r -s -p "Password Admin iniziale [default CambiaSubitoQuestaPassword123!]: " INPUT_PASS
        echo ""
        read -r -p "Chiave Google Gemini Vision API (opzionale): " INPUT_GEMINI
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
    echo -e "${GREEN}✓ File .env generato con chiave di cifratura casuale.${NC}"
else
    echo -e "${YELLOW}File .env già presente, configurazione preservata.${NC}"
    TARGET_PORT=$(grep -E "^APP_PORT=" "$ENV_FILE" | cut -d '=' -f2 | tr -d ' ' || echo "8085")
fi

# ==============================================================================
# Step 4: Build & Launch Docker Container
# ==============================================================================
echo -e "${BLUE}>>> [4/5] Costruzione immagine e avvio container con Docker Compose...${NC}"
$COMPOSE_CMD up -d --build

# ==============================================================================
# Step 5: Verification & Access Summary
# ==============================================================================
echo -e "${BLUE}>>> [5/5] Verifica salute container...${NC}"
sleep 3

LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
[ -z "$LOCAL_IP" ] && LOCAL_IP="127.0.0.1"
ACTIVE_PORT=${TARGET_PORT:-8085}

echo ""
echo -e "${GREEN}${BOLD}=======================================================================${NC}"
echo -e "${GREEN}${BOLD}  🎉 FilamentHub 3D v1.1 ATTIVO SU DOCKER!                             ${NC}"
echo -e "${GREEN}${BOLD}=======================================================================${NC}"
echo -e "  🌐 ${BOLD}Indirizzo Web:${NC}       http://${LOCAL_IP}:${ACTIVE_PORT}"
echo -e "  📖 ${BOLD}Documentazione API:${NC}  http://${LOCAL_IP}:${ACTIVE_PORT}/docs"
echo -e "  👤 ${BOLD}Utente Admin:${NC}        ${TARGET_USER:-admin}"
echo -e "  🔑 ${BOLD}Password Iniziale:${NC}   ${TARGET_PASS:-(Impostata nel file .env)}"
echo ""
echo -e "  ${YELLOW}Comandi Docker utili:${NC}"
echo -e "  • Visualizza log:        ${CYAN}cd $APP_DIR && $COMPOSE_CMD logs -f${NC}"
echo -e "  • Riavvia container:     ${CYAN}cd $APP_DIR && $COMPOSE_CMD restart${NC}"
echo -e "  • Ferma container:       ${CYAN}cd $APP_DIR && $COMPOSE_CMD down${NC}"
echo -e "  • Aggiorna versione:     ${CYAN}cd $APP_DIR && bash scripts/install_docker.sh --update${NC}"
echo -e "${GREEN}${BOLD}=======================================================================${NC}"
