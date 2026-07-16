"""Jornada 3 — Análise Comparativa técnica entre Tomador e Especialista IA."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from core.analisador import gerar_analise_comparativa, salvar_analise_comparativa
from core.especialista_ia import nome_especialista
from core.lentes_continuidade import DEFAULT_LENTES, LENTES
from core.openai_client import get_api_key
from jornadas.comum import render_cabecalho


def render() -> None:
    render_cabecalho(
        "Jornada Comparativa: contraste técnico entre as duas análises "
        "e lista de conceitos envolvidos."
    )

    if not st.session_state.get("analise_tomador") or not st.session_state.get(
        "avaliacao_especialista"
    ):
        st.warning(
            "Execute antes a jornada **2 · Análise Organizacional** "
            "(é preciso ter as duas vozes)."
        )
        return

    nome_tomador = st.session_state.get("nome_tomador", "Tomador")
    avaliacao = st.session_state["avaliacao_especialista"]
    problema = st.session_state.get("problema_atual", "")
    contexto = st.session_state.get("contexto_atual", "")
    docs = st.session_state.get("documentos_atual", "")
    lentes = st.session_state.get("lentes_atual") or list(DEFAULT_LENTES)

    st.caption(f"Tomador: **{nome_tomador}**")
    st.caption(
        "Lentes: " + ", ".join(LENTES[i]["nome"] for i in lentes if i in LENTES)
    )
    if st.session_state.get("nomes_docs"):
        st.caption("Documentos: " + ", ".join(st.session_state["nomes_docs"]))

    with st.expander("Ver análise do Tomador", expanded=False):
        st.markdown(st.session_state["analise_tomador"])
    with st.expander(f"Ver avaliação — {nome_especialista()}", expanded=False):
        st.markdown(avaliacao)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Gerar análise comparativa", type="primary", use_container_width=True):
            if not get_api_key():
                st.error("OPENAI_API_KEY não configurada.")
            else:
                with st.spinner("Gerando comparação técnica…"):
                    try:
                        st.session_state["analise_comparativa"] = gerar_analise_comparativa(
                            nome_tomador=nome_tomador,
                            problema=problema,
                            contexto=contexto,
                            analise_tomador=st.session_state["analise_tomador"],
                            avaliacao_especialista=avaliacao,
                            documentos=docs,
                        )
                        st.success("Comparativa gerada.")
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Erro: {exc}")

    comparativa = st.session_state.get("analise_comparativa")
    with c2:
        if st.button(
            "Salvar comparativa (.docx)",
            use_container_width=True,
            disabled=not bool(comparativa),
        ):
            try:
                caminho = salvar_analise_comparativa(
                    nome_tomador=nome_tomador,
                    problema=problema,
                    contexto=contexto,
                    analise_comparativa=comparativa,
                    documentos=docs,
                )
                st.session_state["ultimo_comparativa_salva"] = str(caminho)
                st.success(f"Salvo em `outputs/{caminho.name}`")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Erro ao salvar: {exc}")

    if st.session_state.get("ultimo_comparativa_salva"):
        path = Path(st.session_state["ultimo_comparativa_salva"])
        if path.exists():
            st.download_button(
                "Baixar comparativa (.docx)",
                data=path.read_bytes(),
                file_name=path.name,
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
            )

    if comparativa:
        st.markdown(
            '<div class="voz-comparativa"><h3>Análise comparativa técnica</h3></div>',
            unsafe_allow_html=True,
        )
        st.markdown(comparativa)
