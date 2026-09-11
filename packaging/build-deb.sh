#!/usr/bin/env bash
# Adapted from Wallace Martins' cc-cockpit packaging/build-deb.sh (MIT).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(cd "$ROOT" && python3 -c 'from codex_cockpit import __version__; print(__version__)')"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
install -d "$STAGE/DEBIAN" "$STAGE/usr/lib/python3/dist-packages/codex_cockpit" \
  "$STAGE/usr/bin" "$STAGE/usr/share/doc/codex-cockpit" "$STAGE/usr/share/applications"
# Copy only runtime sources/resources, never local cache or bytecode.
cp "$ROOT"/codex_cockpit/*.py "$STAGE/usr/lib/python3/dist-packages/codex_cockpit/"
cp -r "$ROOT/codex_cockpit/web" "$STAGE/usr/lib/python3/dist-packages/codex_cockpit/"
cat > "$STAGE/usr/bin/codex-cockpit" <<'PY'
#!/usr/bin/python3
from codex_cockpit.cli import main
raise SystemExit(main())
PY
chmod 755 "$STAGE/usr/bin/codex-cockpit"
install -m644 "$ROOT/README.md" "$STAGE/usr/share/doc/codex-cockpit/README.md"
install -m644 "$ROOT/LICENSE" "$STAGE/usr/share/doc/codex-cockpit/copyright"
install -m644 "$ROOT/packaging/codex-cockpit.desktop" "$STAGE/usr/share/applications/"
cat > "$STAGE/DEBIAN/control" <<CONTROL
Package: codex-cockpit
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-gi, python3-cairo, gir1.2-ayatanaappindicator3-0.1
Suggests: gnome-shell-extension-appindicator
Maintainer: Claudio Pereira <cpereiraweb@gmail.com>
Homepage: https://github.com/cpereiraweb/codex-cockpit
Description: Local Codex usage monitor for Linux
 GNOME tray with consumption ring, local dashboard and terminal reports.
 Reads Codex rollout files without accessing credentials or remote APIs.
 Includes automatic English and Brazilian Portuguese language detection.
 Inspired directly by Wallace Martins' cc-cockpit (MIT).
CONTROL
mkdir -p "$ROOT/dist"
OUT="$ROOT/dist/codex-cockpit_${VERSION}_all.deb"
find "$STAGE" -type d -exec chmod 755 {} +
find "$STAGE" -type f -exec chmod 644 {} +
chmod 755 "$STAGE/usr/bin/codex-cockpit"
dpkg-deb --root-owner-group --build "$STAGE" "$OUT" >/dev/null
printf '%s\n' "$OUT"
