#!/usr/bin/env bash
# Instala Google Chrome Linux no projeto (extract do .deb, sem sudo).
# Necessário para `notebooklm login --browser chrome` no WSL.
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
DEST="$ROOT/.notebooklm/chrome"
BIN="$ROOT/.notebooklm/bin"
DEB_URL="https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
TMP="$(mktemp -d)"

cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

mkdir -p "$DEST" "$BIN"

if [[ -x "$DEST/opt/google/chrome/google-chrome" ]]; then
  echo "Chrome já presente em $DEST"
else
  echo "Baixando Google Chrome…"
  curl -fsSL -o "$TMP/chrome.deb" "$DEB_URL"
  echo "Extraindo…"
  dpkg-deb -x "$TMP/chrome.deb" "$DEST"
fi

ln -sfn "$DEST/opt/google/chrome/google-chrome" "$BIN/google-chrome"
ln -sfn "$DEST/opt/google/chrome/chrome" "$BIN/chrome" 2>/dev/null || true

# Libs compartilhadas (nspr/nss) — reutiliza o helper Python se existir
if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python - <<'PY' || true
from modulos.notebooklm.browser import ensure_syslibs, apply_ld_library_path
ensure_syslibs()
apply_ld_library_path()
print("syslibs OK")
PY
fi

echo "OK. Binário: $BIN/google-chrome"
echo "O app adiciona .notebooklm/bin ao PATH no login."
"$BIN/google-chrome" --version 2>/dev/null || echo "(rode com LD_LIBRARY_PATH se faltar lib)"
