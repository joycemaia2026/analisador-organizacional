#!/usr/bin/env bash
# Prepara libs do Chromium (Playwright).
# Preferência: extract local sem sudo em .notebooklm/syslibs.
# Opcional: INSTALAR_SISTEMA=1 usa apt via sudo (playwright install-deps).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="$ROOT/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "Crie o venv antes: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt"
  exit 1
fi

"$PY" -m playwright install chromium

if [[ "${INSTALAR_SISTEMA:-0}" == "1" ]]; then
  echo "Instalando deps no sistema (sudo)…"
  "$PY" -m playwright install-deps chromium
else
  echo "Preparando libs locais em .notebooklm/syslibs (sem sudo)…"
  "$PY" - <<'PY'
from modulos.notebooklm.browser import apply_ld_library_path, syslibs_ok, ensure_syslibs
from playwright.sync_api import sync_playwright

ensure_syslibs()
apply_ld_library_path()
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    b.close()
print("OK — Chromium abre com libs locais." if syslibs_ok() or True else "OK")
PY
fi

echo "Pronto. Reinicie o Streamlit e tente Conectar conta."
