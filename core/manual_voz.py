"""Manual de voz Gedanken (docs/voz-gedanken.md) para injeção no LLM."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from core.utils import ROOT_DIR

MANUAL_VOZ_PATH = ROOT_DIR / "docs" / "voz-gedanken.md"


@lru_cache(maxsize=1)
def carregar_manual_voz() -> str:
    """Lê o manual normativo de voz. Cache em processo."""
    if not MANUAL_VOZ_PATH.is_file():
        raise FileNotFoundError(
            f"Manual de voz não encontrado: {MANUAL_VOZ_PATH}"
        )
    return MANUAL_VOZ_PATH.read_text(encoding="utf-8").strip()


def anexar_manual_voz_ao_sistema(system: str, incluir: bool) -> str:
    """Acrescenta o manual de voz ao system prompt quando solicitado."""
    if not incluir:
        return system
    try:
        manual = carregar_manual_voz()
    except FileNotFoundError:
        return system
    if not manual:
        return system
    return (
        f"{system.rstrip()}\n\n"
        "### MANUAL DE VOZ GEDANKEN (obrigatório)\n"
        "Aplique este manual em todo o texto gerado:\n\n"
        f"{manual}\n"
    )
