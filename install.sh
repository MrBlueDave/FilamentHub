#!/bin/bash
# ==============================================================================
# FilamentHub 3D v1.1 - Master Installation Script
# Unified launcher for Proxmox LXC and Docker environments
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}"
echo "======================================================================="
echo "                🧵 FilamentHub 3D v1.1 - Installazione                 "
echo "======================================================================="
echo -e "${NC}"

# Handle CLI flags
if [ "$1" = "--lxc" ]; then
    shift
    exec bash "$SCRIPT_DIR/scripts/install_lxc.sh" "$@"
elif [ "$1" = "--docker" ]; then
    shift
    exec bash "$SCRIPT_DIR/scripts/install_docker.sh" "$@"
elif [ "$1" = "--update" ] || [ "$1" = "-u" ]; then
    shift
    if systemctl is-active --quiet filamenthub 2>/dev/null; then
        echo -e "${GREEN}Rilevata installazione LXC / Systemd. Avvio aggiornamento...${NC}"
        exec bash "$SCRIPT_DIR/scripts/install_lxc.sh" --update "$@"
    elif [ -f "$SCRIPT_DIR/docker-compose.yml" ] && command -v docker &>/dev/null; then
        echo -e "${GREEN}Rilevata installazione Docker Compose. Avvio aggiornamento...${NC}"
        exec bash "$SCRIPT_DIR/scripts/install_docker.sh" --update "$@"
    else
        echo -e "${YELLOW}Seleziona quale ambiente aggiornare:${NC}"
        echo "1) LXC (systemd)"
        echo "2) Docker"
        read -r -p "Scelta [1-2]: " UP_CHOICE
        case "$UP_CHOICE" in
            1) exec bash "$SCRIPT_DIR/scripts/install_lxc.sh" --update "$@" ;;
            2) exec bash "$SCRIPT_DIR/scripts/install_docker.sh" --update "$@" ;;
            *) echo "Scelta non valida."; exit 1 ;;
        esac
    fi
fi

# Interactive Menu
echo -e "${YELLOW}Scegli la modalità di installazione desiderata:${NC}"
echo ""
echo -e "  ${BOLD}1)${NC} ${GREEN}Container LXC Nativo${NC} (Debian 12 / Ubuntu - Systemd + Python venv)"
echo -e "     ${CYAN}→ Prestazioni native massime, ideale per Proxmox VE.${NC}"
echo ""
echo -e "  ${BOLD}2)${NC} ${BLUE}Docker & Docker Compose${NC} (Container portatile)"
echo -e "     ${CYAN}→ Ambiente isolato, ideale per Synology, TrueNAS, VPS o Debian generico.${NC}"
echo ""
echo -e "  ${BOLD}3)${NC} Aggiorna installazione esistente (${BOLD}--update${NC})"
echo -e "  ${BOLD}4)${NC} Annulla ed esci"
echo ""

read -r -p "Digita l'opzione [1-4] (default: 1): " CHOICE
CHOICE=${CHOICE:-1}

case "$CHOICE" in
    1)
        echo -e "\n${GREEN}Avvio installatore LXC nativo...${NC}\n"
        exec bash "$SCRIPT_DIR/scripts/install_lxc.sh"
        ;;
    2)
        echo -e "\n${BLUE}Avvio installatore Docker & Docker Compose...${NC}\n"
        exec bash "$SCRIPT_DIR/scripts/install_docker.sh"
        ;;
    3)
        echo -e "\n${YELLOW}Avvio aggiornamento...${NC}\n"
        if systemctl is-active --quiet filamenthub 2>/dev/null; then
            exec bash "$SCRIPT_DIR/scripts/install_lxc.sh" --update
        else
            exec bash "$SCRIPT_DIR/scripts/install_docker.sh" --update
        fi
        ;;
    4)
        echo "Installazione annullata."
        exit 0
        ;;
    *)
        echo -e "${RED}Opzione non valida.${NC}"
        exit 1
        ;;
esac
