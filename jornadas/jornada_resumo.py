"""Jornada 4 — Resumo consolidado + pacote DOCX com todas as etapas da sessão."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from core.especificacoes_llm import campo_especificacoes_llm
from core.openai_client import get_api_key
from core.resumo_consolidado import (
    coletar_entradas,
    gerar_resumo_consolidado,
    pacote_sessao_docx_bytes,
    pode_gerar,
    salvar_pacote_sessao_docx,
    status_entradas,
)
from jornadas.comum import render_cabecalho


def render() -> None:
    render_cabecalho(
        "Jornada Resumo: consolida ata, personas e Especialista "
        "(comparativa opcional) em um único .docx em `outputs/resumo_*.docx`."
    )

    entradas = coletar_entradas(st.session_state)
    st.subheader("Material disponível na sessão")
    for label, ok, detalhe in status_entradas(entradas):
        marca = "sim" if ok else "não"
        st.markdown(f"- **{label}:** {marca} — {detalhe}")

    if not pode_gerar(entradas):
        st.warning(
            "Gere pelo menos uma **ata** (jornada 1) ou a **análise institucional** "
            "(jornada 2) antes de consolidar."
        )
        return

    faltando = [
        l
        for l, ok, _ in status_entradas(entradas)
        if not ok and "Comparativa" not in l and l != "Problema / pedido"
    ]
    if faltando:
        st.info(
            "Pacote parcial possível. Ainda faltam: " + ", ".join(faltando) + "."
        )
    if not entradas["tem_comparativa"]:
        st.caption(
            "Comparativa ausente — o arquivo final segue completo sem essa seção."
        )

    if not get_api_key():
        st.warning("Configure a chave do provedor LLM para gerar o resumo executivo.")

    especificacoes = campo_especificacoes_llm("jornada_resumo_especificacoes")

    if st.button(
        "Gerar resumo + pacote DOCX da sessão",
        type="primary",
        use_container_width=True,
        disabled=not get_api_key(),
    ):
        with st.spinner("Consolidando resumo e montando o pacote da sessão…"):
            try:
                texto = gerar_resumo_consolidado(
                    dict(st.session_state),
                    especificacoes=especificacoes,
                )
                st.session_state["resumo_consolidado"] = texto
                caminho = salvar_pacote_sessao_docx(
                    dict(st.session_state),
                    resumo_llm=texto,
                )
                st.session_state["ultimo_resumo_docx"] = str(caminho)
                st.success(f"Salvo em `outputs/{caminho.name}`.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Falha ao gerar pacote: {exc}")

    resumo = st.session_state.get("resumo_consolidado")
    path_salvo = None
    if st.session_state.get("ultimo_resumo_docx"):
        candidato = Path(st.session_state["ultimo_resumo_docx"])
        if candidato.exists():
            path_salvo = candidato

    if not resumo and not path_salvo and not pode_gerar(entradas):
        return

    st.divider()
    if resumo:
        st.subheader("Pré-visualização do resumo executivo")
        st.markdown(resumo)
    else:
        st.info(
            "Ainda não há resumo executivo. Gere acima para salvar "
            "`outputs/resumo_*.docx` com as etapas da sessão."
        )

    if path_salvo:
        st.download_button(
            f"Baixar {path_salvo.name}",
            data=path_salvo.read_bytes(),
            file_name=path_salvo.name,
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            type="primary",
            key="dl_resumo_salvo",
            use_container_width=True,
            help="Arquivo em outputs/ — mesmo padrão das demais jornadas.",
        )
        st.caption(f"Arquivo em disco: `{path_salvo}`")
    elif resumo or pode_gerar(entradas):
        # Fallback: monta bytes na hora (ainda não gravou nesta sessão)
        docx_bytes = pacote_sessao_docx_bytes(
            dict(st.session_state),
            resumo_llm=resumo,
        )
        st.download_button(
            "Baixar pacote da sessão (.docx)",
            data=docx_bytes,
            file_name="resumo_sessao.docx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            type="primary",
            key="dl_pacote_sessao_docx",
            use_container_width=True,
        )
