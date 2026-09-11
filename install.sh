#!/usr/bin/env bash
# Installs codex-cockpit for the current user (nothing under /usr).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$HOME/.local/bin"
AUTOSTART="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"

echo "==> codex-cockpit em $ROOT"

missing=()
python3 -c "import gi" 2>/dev/null || missing+=(python3-gi)
python3 -c "import cairo" 2>/dev/null || missing+=(python3-cairo)
python3 - <<'PY' 2>/dev/null || missing+=(gir1.2-ayatanaappindicator3-0.1)
import gi
try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
except ValueError:
    gi.require_version("AppIndicator3", "0.1")
PY

if [ ${#missing[@]} -gt 0 ]; then
  echo "!! Missing system packages. Run:"
  echo "   sudo apt install ${missing[*]}"
  echo "   (the dashboard and 'report' work without them; only the tray needs them)"
fi

mkdir -p "$BIN"
cat > "$BIN/codex-cockpit" <<EOF
#!/usr/bin/env bash
cd "$ROOT" && exec python3 -m codex_cockpit "\$@"
EOF
chmod +x "$BIN/codex-cockpit"
echo "==> $BIN/codex-cockpit"

mkdir -p "$AUTOSTART"
cat > "$AUTOSTART/codex-cockpit.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=codex-cockpit
Comment=Codex usage in the tray
Exec="$BIN/codex-cockpit" tray
Icon=utilities-system-monitor
Terminal=false
Categories=System;Monitor;
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=8
EOF
echo "==> autostart em $AUTOSTART/codex-cockpit.desktop"

echo "==> first collection"
(cd "$ROOT" && python3 -m codex_cockpit collect)

case ":$PATH:" in
  *":$BIN:"*) ;;
  *) echo "!! $BIN is not on PATH - add it to ~/.zshrc" ;;
esac

echo
echo "ready:"
echo "  codex-cockpit          tray (also starts the dashboard)"
echo "  codex-cockpit serve --open   dashboard only"
echo "  codex-cockpit report   terminal summary"
