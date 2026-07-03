#!/usr/bin/env bash
# WebForge Setup Script
#
# Run this once to install WebForge on your machine.
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh

set -e

WEBFORGE_HOME="$HOME/webforge"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "WebForge Setup"
echo "=========================================="
echo

# 1. Check Python version
echo "[1/5] Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "  ERROR: Python 3 not found. Install Python 3.10+ first."
    exit 1
fi
PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  ✓ Python $PY_VERSION found"

# 2. Install WebForge to ~/webforge
echo
echo "[2/5] Installing WebForge to $WEBFORGE_HOME..."
if [ -d "$WEBFORGE_HOME" ]; then
    echo "  $WEBFORGE_HOME already exists."
    read -p "  Overwrite? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "  Skipping install. Existing files kept."
    else
        rm -rf "$WEBFORGE_HOME"
        cp -r "$SCRIPT_DIR" "$WEBFORGE_HOME"
        echo "  ✓ WebForge installed to $WEBFORGE_HOME"
    fi
else
    cp -r "$SCRIPT_DIR" "$WEBFORGE_HOME"
    echo "  ✓ WebForge installed to $WEBFORGE_HOME"
fi

# 3. Make webforge CLI executable
echo
echo "[3/5] Making webforge CLI executable..."
chmod +x "$WEBFORGE_HOME/webforge"
echo "  ✓ webforge CLI is executable"

# 4. Add to PATH (optional)
echo
echo "[4/5] Adding webforge to PATH..."
SHELL_NAME=$(basename "$SHELL")
if [[ "$SHELL_NAME" == "bash" ]]; then
    RC_FILE="$HOME/.bashrc"
elif [[ "$SHELL_NAME" == "zsh" ]]; then
    RC_FILE="$HOME/.zshrc"
else
    RC_FILE="$HOME/.profile"
fi

if ! grep -q "webforge" "$RC_FILE" 2>/dev/null; then
    echo "" >> "$RC_FILE"
    echo "# WebForge CLI" >> "$RC_FILE"
    echo "export PATH=\"\$PATH:$WEBFORGE_HOME\"" >> "$RC_FILE"
    echo "  ✓ Added to $RC_FILE"
    echo "  Run 'source $RC_FILE' or restart your terminal to use 'webforge' command."
else
    echo "  Already in $RC_FILE"
fi

# 5. Create global ~/.webforge folder (for global rules + preferences)
echo
echo "[5/5] Creating global ~/.webforge/ folder..."
mkdir -p "$HOME/.webforge/global-rules"
if [ ! -f "$HOME/.webforge/global-preferences.md" ]; then
    cat > "$HOME/.webforge/global-preferences.md" << 'EOF'
# Global Preferences

These apply to ALL projects.

---

EOF
    echo "  ✓ Created global-preferences.md"
else
    echo "  global-preferences.md already exists"
fi

echo
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo
echo "WebForge is installed at: $WEBFORGE_HOME"
echo
echo "Next steps:"
echo "  1. Restart your terminal (or run: source $RC_FILE)"
echo "  2. Test: webforge status"
echo "  3. Initialize a project: cd /path/to/project && webforge init"
echo "  4. Activate: webforge on"
echo "  5. In OpenCode, type /resume to start a session"
echo
echo "To use WebForge slash commands (/probe, /build, etc.) in OpenCode:"
echo "  - Copy .opencode/opencode.json to your project root"
echo "  - Or symlink: ln -s $WEBFORGE_HOME/.opencode /path/to/project/.opencode"
