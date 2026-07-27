#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

# Browser do Playwright (idempotente)
python -m playwright install chromium

# Libs do Chromium: usa extract local sem sudo se o SO não tiver libnspr4
export LD_LIBRARY_PATH="$(python - <<'PY'
from modulos.notebooklm.browser import ensure_syslibs, apply_ld_library_path, prepare_browser_env
import os
try:
    ensure_syslibs()
    apply_ld_library_path()
    prepare_browser_env()
    print(os.environ.get("LD_LIBRARY_PATH", ""))
except Exception as exc:
    import sys
    print(f"AVISO Playwright libs: {exc}", file=sys.stderr)
    print(f"Rode: ./scripts/install_playwright_deps.sh", file=sys.stderr)
    print(os.environ.get("LD_LIBRARY_PATH", ""))
PY
)"

# Chrome Linux para login NotebookLM (idempotente se já extraído)
if [[ ! -x .notebooklm/chrome/opt/google/chrome/google-chrome ]]; then
  echo "Instalando Google Chrome local (login NotebookLM)…"
  ./scripts/install_chrome_wsl.sh || echo "AVISO: Chrome local falhou — rode ./scripts/install_chrome_wsl.sh"
fi
export PATH="$(pwd)/.notebooklm/bin:${PATH}"

if [[ ! -f .env ]]; then
  echo "Arquivo .env não encontrado. Copie .env.example e preencha OPENAI_API_KEY."
  exit 1
fi

# Tema claro + hot reload; limpa cache de dados se necessário via UI
exec streamlit run app.py --server.runOnSave true
