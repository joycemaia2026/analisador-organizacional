#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Sempre usar o interpretador deste projeto (não depender de activate / VIRTUAL_ENV alheio)
if [[ ! -x .venv/bin/python ]]; then
  echo "Criando ambiente virtual…"
  python3 -m venv .venv
fi
PY="$ROOT/.venv/bin/python"

# Garante deps mínimas no venv deste projeto
if ! "$PY" -c "import streamlit, playwright" 2>/dev/null; then
  echo "Instalando dependências…"
  "$PY" -m pip install -U pip
  "$PY" -m pip install -r requirements.txt
fi

# Browser do Playwright (idempotente)
"$PY" -m playwright install chromium

# Libs do Chromium: usa extract local sem sudo se o SO não tiver libnspr4
export LD_LIBRARY_PATH="$("$PY" - <<'PY'
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
exec "$PY" -m streamlit run app.py --server.runOnSave true
