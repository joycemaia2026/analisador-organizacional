#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

pip install -q -r requirements.txt

if [[ ! -f .env ]]; then
  echo "Arquivo .env não encontrado. Copie .env.example e preencha OPENAI_API_KEY."
  exit 1
fi

# Tema claro + hot reload; limpa cache de dados se necessário via UI
exec streamlit run app.py --server.runOnSave true
