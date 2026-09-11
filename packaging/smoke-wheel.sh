#!/usr/bin/env bash
# Verify wheel resources and the console script outside the source checkout.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECK="$(mktemp -d)"
trap 'rm -rf "$CHECK"' EXIT
python3 -m venv "$CHECK/venv"
"$CHECK/venv/bin/python" -m pip install --disable-pip-version-check --no-cache-dir --no-deps "$ROOT"/dist/*.whl
export CODEX_HOME="$CHECK/codex"
export XDG_CONFIG_HOME="$CHECK/config"
export XDG_DATA_HOME="$CHECK/data"
cd "$CHECK"
"$CHECK/venv/bin/codex-cockpit" --version
"$CHECK/venv/bin/codex-cockpit" collect
"$CHECK/venv/bin/codex-cockpit" --lang pt_BR json > summary.json
"$CHECK/venv/bin/python" - <<'PY'
import json
from codex_cockpit.server import WEB_DIR
assert (WEB_DIR / 'index.html').is_file(), WEB_DIR
with open('summary.json') as f:
    data = json.load(f)
assert data['i18n']['tag'] == 'pt-BR', data['i18n']
assert data['i18n']['catalog']['open_dashboard'] == 'Abrir dashboard'
assert data['totals']['all']['tokens'] == 0
print('Installed wheel, packaged dashboard and pt_BR: OK')
PY
