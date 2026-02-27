#!/usr/bin/env bash
set -e

INSTALL_DIR="$HOME/.local/share/anchovy"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"

echo "Installing Anchovy..."

# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 is required but not found."
    exit 1
fi

# Check PyQt6
if ! python3 -c "import PyQt6" &>/dev/null; then
    echo "PyQt6 not found. Installing via pip..."
    pip install --user PyQt6
fi

# Create install dir
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$APP_DIR"

# Copy app files
cp anchovy.py "$INSTALL_DIR/"
cp anchovy_settings.py "$INSTALL_DIR/"
cp -r icons "$INSTALL_DIR/"

# Write launcher script
cat > "$BIN_DIR/anchovy" <<EOF
#!/usr/bin/env bash
python3 "$INSTALL_DIR/anchovy.py" "\$@"
EOF
chmod +x "$BIN_DIR/anchovy"

# Write toggle script (for hotkey binding)
cat > "$BIN_DIR/anchovy-toggle" <<EOF
#!/usr/bin/env bash
# Bind this to a hotkey in your DE (e.g. Meta+Space)
PID=\$(cat "$INSTALL_DIR/anchovy.pid" 2>/dev/null)
if [ -n "\$PID" ] && kill -0 "\$PID" 2>/dev/null; then
    kill "\$PID"
else
    anchovy &
fi
EOF
chmod +x "$BIN_DIR/anchovy-toggle"

# Install desktop entry
cat > "$APP_DIR/anchovy.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Anchovy
Comment=Tiny but essential app launcher
Exec=$BIN_DIR/anchovy
Icon=anchovy
Terminal=false
Categories=Utility;
EOF

# Install icons into theme (so DE can find them)
for size in 16 24 32 48 64 128 256 512; do
    DARK_ICON="$INSTALL_DIR/icons/dark/anchovy-dark-${size}.png"
    TEAL_ICON="$INSTALL_DIR/icons/teal/anchovy-teal-${size}.png"
    ICON_DEST="$HOME/.local/share/icons/hicolor/${size}x${size}/apps"
    mkdir -p "$ICON_DEST"
    [ -f "$DARK_ICON" ] && cp "$DARK_ICON" "$ICON_DEST/anchovy.png"
done
gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo ""
echo "Anchovy installed!"
echo ""
echo "Run it:       anchovy"
echo "Toggle script: $BIN_DIR/anchovy-toggle"
echo ""
echo "To bind Meta+Space (KDE):"
echo "  System Settings → Shortcuts → Custom Shortcuts → Add Command"
echo "  Command: $BIN_DIR/anchovy-toggle"
echo ""
echo "Make sure $BIN_DIR is in your PATH."
