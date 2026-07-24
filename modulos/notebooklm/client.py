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
    """Compat: gera com sessão existente; se não houver, conecta e gera."""
    paths = [Path(c) for c in caminhos]
    if sessao_valida():
        return gerar_produtos(paths, **kwargs)
    return login_e_gerar_produtos(paths, **kwargs)
