"""Jornada 4 — Resumo consolidado (ata + personas + Especialista IA)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from core.export_docx import markdown_para_docx_bytes
from core.openai_client import get_api_key
from core.resumo_consolidado import (
    coletar_entradas,
    gerar_resumo_consolidado,
    pode_gerar,
    salvar_resumo_docx,
    status_entradas,
)
from jornadas.comum import render_cabecalho


def render() -> None:
    render_cabecalho(
        "Jornada Resumo: consolida ata, personas e Especialista IA — "
        "foco em problema e o que fazer, com fonte em cada seção."
    )

    entradas = coletar_entradas(st.session_state)
    st.subheader("Material disponível")
    for label, ok, detalhe in status_entradas(entradas):
        marca = "sim" if ok else "não"
        st.markdown(f"- **{label}:** {marca} — {detalhe}")

    if not pode_gerar(entradas):
        st.warning(
            "Gere pelo menos uma **ata** (jornada 1) ou a **análise organizacional** "
            "(jornada 2) antes de consolidar."
        )
        return

    faltando = [l for l, ok, _ in status_entradas(entradas) if not ok and l != "Problema / pedido"]
    if faltando:
        st.info(
            "Resumo parcial possível. Ainda faltam: " + ", ".join(faltando) + "."
        )

    if not get_api_key():
        st.warning("Configure `OPENAI_API_KEY` para gerar o resumo.")

    if st.button(
        "Gerar resumo consolidado",
        type="primary",
        use_container_width=True,
        disabled=not get_api_key(),
    ):
        with st.spinner("Consolidando…"):
            try:
                texto = gerar_resumo_consolidado(dict(st.session_state))
                st.session_state["resumo_consolidado"] = texto
                caminho = salvar_resumo_docx(texto)
                st.session_state["ultimo_resumo_docx"] = str(caminho)
                st.success(f"Resumo gerado e salvo em `{caminho.name}`.")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Falha ao gerar resumo: {exc}")

    resumo = st.session_state.get("resumo_consolidado")
    if not resumo:
        return

    st.divider()
    st.subheader("Pré-visualização")
    st.markdown(resumo)

    docx_bytes = markdown_para_docx_bytes("Resumo consolidado", resumo)
    st.download_button(
        "Baixar resumo (.docx)",
        data=docx_bytes,
        file_name="resumo_consolidado.docx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        key="dl_resumo_docx",
    )

    if st.session_state.get("ultimo_resumo_docx"):
        path = Path(st.session_state["ultimo_resumo_docx"])
        if path.exists():
            st.caption(f"Arquivo em disco: `{path}`")
