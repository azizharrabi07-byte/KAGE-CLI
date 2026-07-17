#!/bin/bash
# KAGE OS — One-click setup for Termux
# Run: bash setup.sh

set -e

echo "═══ KAGE OS SETUP ═══"
echo ""

# System packages
echo "📦 Installing system packages..."
pkg update -y && pkg upgrade -y
pkg install python nodejs git nano -y

# termux-api (for battery/storage/CPU)
echo "📱 Installing Termux API..."
pkg install termux-api -y 2>/dev/null || echo "⚠️  Termux API install failed (optional — health agent won't work)"

# Python packages
echo "🐍 Installing Python packages..."
pip install requests pyyaml toml --break-system-packages 2>/dev/null || pip install requests pyyaml toml

# WhatsApp bridge
echo "📱 Setting up WhatsApp bridge..."
cd ~/kage-os/agents/whatsapp/bridge 2>/dev/null || cd ~/kage-os/agents/whatsapp/bridge
npm install 2>/dev/null || echo "⚠️  npm install failed (WhatsApp agent won't work until Node is installed)"

# Config
echo "⚙️  Setting up config..."
mkdir -p ~/.kage
if [ ! -f ~/kage-os/config.toml ]; then
    cat > ~/kage-os/config.toml << 'TOML'
[llm]
provider = "openrouter"
api_key = "YOUR_KEY_HERE"
model = "anthropic/claude-3.5-sonnet"
base_url = "https://openrouter.ai/api/v1"

[obsidian]
url = "http://localhost:27123"
api_key = "YOUR_OBSIDIAN_KEY"

[system]
log_level = "info"
TOML
fi

# Make CLI executable
chmod +x ~/kage-os/kage_cli.py
chmod +x ~/kage-os/kage.py

# Create symlink
ln -sf ~/kage-os/kage_cli.py /data/data/com.termux/files/usr/bin/kage 2>/dev/null || true

# Init database
echo "💾 Initializing database..."
cd ~/kage-os && python3 core/memory.py

echo ""
echo "═══ KAGE OS SETUP COMPLETE ═══"
echo ""
echo "Quick start:"
echo "  kage health           Check phone status"
echo "  kage chat 'hello'     Chat with Kage"
echo "  kage agent list       See all agents"
echo "  kage agent wake system --task '{}'   Check phone health"
echo ""
echo "Edit ~/kage-os/config.toml to add your API keys."
echo "Edit ~/kage-os/agents/*/agent.py to customize agents."