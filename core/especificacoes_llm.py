"""Campo e injeção de especificações extras para o LLM."""

from __future__ import annotations

import streamlit as st


def campo_especificacoes_llm(key: str, *, height: int = 110) -> str:
    """Text area opcional (começa vazio). Retorna o texto digitado."""
    return st.text_area(
        "Especificações para o LLM (opcional)",
        height=height,
        key=key,
        placeholder=(
            "Ex.: foque em riscos financeiros; limite a 1 página; "
            "priorize próximos 7 dias; use tom consultivo Gedanken…"
        ),
        help=(
            "Instruções extras enviadas ao modelo nesta geração. "
            "Não substituem as fontes — apenas orientam o formato e o foco."
        ),
    )


def anexar_especificacoes(conteudo_user: str, especificacoes: str | None) -> str:
    """Acrescenta bloco de especificações ao final da mensagem user."""
    esp = (especificacoes or "").strip()
    if not esp:
        return conteudo_user
    return (
        f"{conteudo_user.rstrip()}\n\n"
        "### ESPECIFICAÇÕES ADICIONAIS DO USUÁRIO\n"
        "Siga estas orientações sem inventar fatos fora das fontes:\n"
        f"{esp}\n"
    )
