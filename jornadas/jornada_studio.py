"""Jornada 5 — Studio: NotebookLM (login + produtos) + PPTX/infográfico locais."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from core.export_infografico import gerar_infografico
from core.export_pptx import gerar_apresentacao_pptx
from core.openai_client import get_api_key
from core.outputs_collector import listar_docx_jornadas
from jornadas.comum import render_cabecalho
from modulos.notebooklm import login_e_gerar_produtos
from modulos.notebooklm.browser import chrome_instalado, chrome_real_path


def render() -> None:
    render_cabecalho(
        "Jornada Studio: sobe os .docx no NotebookLM (login Google a cada pedido) "
        "e gera slide deck + infográfico; também há export local via OpenAI."
    )

    st.markdown(
        '<div class="jornada-card">'
        "<b>NotebookLM (consumer):</b> API não oficial (<code>notebooklm-py</code>). "
        "Ao gerar, abre o <b>Chrome real</b> — faça login Google nessa janela. "
        "Depois o app sobe as fontes e baixa slide deck + infográfico sozinho."
        "</div>",
        unsafe_allow_html=True,
    )

    artefatos = listar_docx_jornadas()
    if not artefatos:
        st.warning(
            "Nenhum `.docx` de ata/análise/comparativa em `outputs/`. "
            "Gere e salve nas jornadas 1–3 primeiro."
        )
        return

    opcoes = {str(a.caminho): a.rotulo for a in artefatos}
    selecionados = st.multiselect(
        "Documentos das jornadas anteriores",
        options=list(opcoes.keys()),
        default=list(opcoes.keys()),
        format_func=lambda p: opcoes[p],
        key="studio_docs_sel",
    )
    caminhos = [Path(p) for p in selecionados]
    if not caminhos:
        st.warning("Selecione ao menos um documento.")
        return

    st.divider()
    st.subheader("NotebookLM")
    chrome = chrome_real_path()
    if chrome_instalado():
        st.caption(f"Chrome Linux: `{chrome}`")
    else:
        st.warning(
            "Chrome Linux não encontrado. Rode `./scripts/install_chrome_wsl.sh` "
            "antes de gerar no NotebookLM."
        )

    if st.button(
        "Gerar no NotebookLM",
        type="primary",
        use_container_width=True,
        disabled=not chrome_instalado(),
        help="Abre o Chrome para login e em seguida gera slide deck + infográfico.",
    ):
        st.info("Abrindo Chrome — conclua o login Google na janela que aparecer.")
        with st.spinner(
            "Login → upload das fontes → slide deck + infográfico (pode levar vários minutos)…"
        ):
            try:
                result = login_e_gerar_produtos(caminhos, language="pt")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Falha NotebookLM: {exc}")
                result = None

        if result is not None:
            if result.ok:
                st.success(result.mensagem)
            else:
                st.warning(result.mensagem)
            if result.fontes:
                st.write("Fontes:", ", ".join(result.fontes))
            if result.falhas:
                st.error("Detalhes:\n- " + "\n- ".join(result.falhas))
            if result.notebook_url:
                st.markdown(f"[Abrir notebook]({result.notebook_url})")
                st.session_state["notebooklm_url"] = result.notebook_url
            if result.slides and result.slides.exists():
                st.session_state["nlm_slides"] = str(result.slides)
            if result.infografico and result.infografico.exists():
                st.session_state["nlm_infografico"] = str(result.infografico)

    if st.session_state.get("notebooklm_url"):
        st.caption(f"Último notebook: {st.session_state['notebooklm_url']}")

    if st.session_state.get("nlm_slides"):
        path = Path(st.session_state["nlm_slides"])
        if path.exists():
            mime = (
                "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                if path.suffix.lower() == ".pptx"
                else "application/pdf"
            )
            st.download_button(
                "Baixar slides NotebookLM",
                data=path.read_bytes(),
                file_name=path.name,
                mime=mime,
                key="dl_nlm_slides",
            )

    if st.session_state.get("nlm_infografico"):
        path = Path(st.session_state["nlm_infografico"])
        if path.exists():
            st.image(str(path), use_container_width=True)
            st.download_button(
                "Baixar infográfico NotebookLM (PNG)",
                data=path.read_bytes(),
                file_name=path.name,
                mime="image/png",
                key="dl_nlm_png",
            )

    st.divider()
    st.subheader("Artefatos locais (OpenAI — sem NotebookLM)")
    if not get_api_key():
        st.warning("Configure `OPENAI_API_KEY` para PPTX e infográfico locais.")

    p1, p2 = st.columns(2)
    with p1:
        if st.button(
            "Gerar PPTX local",
            use_container_width=True,
            disabled=not get_api_key(),
        ):
            with st.spinner("Gerando apresentação local…"):
                try:
                    pptx = gerar_apresentacao_pptx(caminhos)
                    st.session_state["studio_pptx"] = str(pptx)
                    st.success(f"Salvo: `{pptx.name}`")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Falha PPTX: {exc}")
    with p2:
        if st.button(
            "Gerar infográfico local",
            use_container_width=True,
            disabled=not get_api_key(),
        ):
            with st.spinner("Gerando infográfico local…"):
                try:
                    png, html_path = gerar_infografico(caminhos)
                    st.session_state["studio_infografico"] = str(png)
                    st.session_state["studio_infografico_html"] = str(html_path)
                    st.success(f"Salvo: `{png.name}`")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Falha infográfico: {exc}")

    if st.session_state.get("studio_pptx"):
        path = Path(st.session_state["studio_pptx"])
        if path.exists():
            st.download_button(
                "Baixar PPTX local",
                data=path.read_bytes(),
                file_name=path.name,
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "presentationml.presentation"
                ),
                key="dl_studio_pptx",
            )

    if st.session_state.get("studio_infografico"):
        path = Path(st.session_state["studio_infografico"])
        if path.exists():
            st.image(str(path), use_container_width=True)
            st.download_button(
                "Baixar infográfico local (PNG)",
                data=path.read_bytes(),
                file_name=path.name,
                mime="image/png",
                key="dl_studio_png",
            )
