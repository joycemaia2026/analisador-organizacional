"""Coleta e classificação de artefatos em outputs/."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.utils import OUTPUTS_DIR, ensure_dirs


@dataclass
class ArtefatoOutput:
    caminho: Path
    categoria: str  # ata | analise | comparativa | apresentacao | infografico | outro
    rotulo: str


def _classificar(nome: str) -> str:
    n = nome.lower()
    if n.startswith("ata_"):
        return "ata"
    if n.startswith("analise_"):
        return "analise"
    if n.startswith("comparativa_"):
        return "comparativa"
    if n.startswith("resumo_"):
        return "resumo"
    if n.startswith("apresentacao_"):
        return "apresentacao"
    if n.startswith("infografico_"):
        return "infografico"
    return "outro"


def listar_docx_jornadas(
    *,
    categorias: tuple[str, ...] = ("ata", "analise", "comparativa", "resumo"),
) -> list[ArtefatoOutput]:
    """Lista .docx das jornadas (por prefixo), mais recentes primeiro."""
    ensure_dirs()
    itens: list[ArtefatoOutput] = []
    for path in OUTPUTS_DIR.glob("*.docx"):
        cat = _classificar(path.name)
        if cat not in categorias:
            continue
        itens.append(
            ArtefatoOutput(
                caminho=path,
                categoria=cat,
                rotulo=f"[{cat}] {path.name}",
            )
        )
    itens.sort(key=lambda a: a.caminho.stat().st_mtime, reverse=True)
    return itens


def contar_docx_jornadas() -> int:
    return len(listar_docx_jornadas())
