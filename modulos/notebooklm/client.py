"""Facade NotebookLM para a UI Streamlit."""

from __future__ import annotations

from pathlib import Path

from modulos.notebooklm.auth import (
    limpar_sessao,
    login_interativo,
    sessao_valida,
    state_path,
    storage_path,
)
from modulos.notebooklm.pipeline import (
    ProdutosResultado,
    gerar_produtos,
    login_e_gerar_produtos,
)

__all__ = [
    "ProdutosResultado",
    "gerar_produtos",
    "limpar_sessao",
    "login_e_gerar_produtos",
    "login_interativo",
    "sessao_valida",
    "state_path",
    "storage_path",
]


def upload_paths(caminhos: list[str | Path], **kwargs) -> ProdutosResultado:
    """Compat: gera produtos NotebookLM a partir dos caminhos."""
    return login_e_gerar_produtos([Path(c) for c in caminhos], **kwargs)
