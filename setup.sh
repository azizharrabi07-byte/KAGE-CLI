#!/bin/bash
# KAGE OS — Setup Script
# Works on Termux, Ubuntu, Debian, macOS, and Linux environments.

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "═══ KAGE OS SETUP ═══"
echo "Directory: ${SCRIPT_DIR}"
echo ""

# System packages
if command -v pkg &> /dev/null; then
    echo "📦 Termux detected. Installing system packages..."
    pkg update -y || true
    pkg install python nodejs git nano -y || true
    pkg install termux-api -y 2>/dev/null || echo "⚠️ Termux API install failed (optional — health agent will use fallback)"
elif command -v apt-get &> /dev/null; then
    echo "📦 Debian/Ubuntu detected. Checking system packages..."
    sudo apt-get update -y || true
    sudo apt-get install -y python3 python3-pip nodejs npm git || true
fi

# Python dependencies
echo "🐍 Installing Python dependencies..."
python3 -m pip install requests pyyaml toml --break-system-packages 2>/dev/null || python3 -m pip install requests pyyaml toml || true

# WhatsApp bridge dependencies
echo "📱 Setting up WhatsApp bridge..."
if [ -d "${SCRIPT_DIR}/agents/whatsapp/bridge" ]; then
    cd "${SCRIPT_DIR}/agents/whatsapp/bridge"
    if command -v npm &> /dev/null; then
        npm install || echo "⚠️ npm install warning (WhatsApp agent will auto-install on wake if node is present)"
    fi
fi

# Config directory and file
echo "⚙️ Setting up config..."
mkdir -p ~/.kage
if [ ! -f ~/.kage/config.toml ] && [ ! -f "${SCRIPT_DIR}/config.toml" ]; then
    cat > "${SCRIPT_DIR}/config.toml" << 'TOML'
[llm]
provider = "gemini"
api_key = "YOUR_GEMINI_API_KEY_HERE"
model = "gemini-2.5-flash"
base_url = "https://generativelanguage.googleapis.com/v1beta"

[trilium]
url = "http://localhost:8080"
etapi_token = "YOUR_TRILIUM_ETAPI_TOKEN"

[system]
log_level = "info"
max_retries = 3
timeout = 30
TOML
fi

# Make scripts executable
chmod +x "${SCRIPT_DIR}/kage_cli.py"
chmod +x "${SCRIPT_DIR}/kage.py"

# Symlink setup
PREFIX_BIN="/data/data/com.termux/files/usr/bin"
LOCAL_BIN="${HOME}/.local/bin"

if [ -d "${PREFIX_BIN}" ]; then
    ln -sf "${SCRIPT_DIR}/kage_cli.py" "${PREFIX_BIN}/kage" 2>/dev/null || true
elif [ -d "/usr/local/bin" ] && [ -w "/usr/local/bin" ]; then
    ln -sf "${SCRIPT_DIR}/kage_cli.py" "/usr/local/bin/kage" 2>/dev/null || true
else
    mkdir -p "${LOCAL_BIN}"
    ln -sf "${SCRIPT_DIR}/kage_cli.py" "${LOCAL_BIN}/kage" 2>/dev/null || true
fi

# Initialize memory database
echo "💾 Initializing database..."
cd "${SCRIPT_DIR}" && PYTHONPATH="${SCRIPT_DIR}" python3 core/memory.py

echo ""
echo "═══ KAGE OS SETUP COMPLETE ═══"
echo ""
echo "Quick start:"
echo "  python3 kage_cli.py health"
echo "  python3 kage_cli.py chat 'hello'"
echo "  python3 kage_cli.py agent list"
echo "  python3 kage_cli.py daemon start"
echo ""
