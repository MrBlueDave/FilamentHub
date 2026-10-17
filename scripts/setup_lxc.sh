#!/bin/bash
# ==============================================================================
# FilamentHub 3D - Setup LXC Wrapper
# Redirects to scripts/install_lxc.sh
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/install_lxc.sh" "$@"
