"""Módulo NotebookLM via notebooklm-py (API não oficial consumer)."""

from modulos.notebooklm.client import (
    ProdutosResultado,
    gerar_produtos,
    limpar_sessao,
    login_e_gerar_produtos,
    login_interativo,
    sessao_valida,
    state_path,
    storage_path,
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
