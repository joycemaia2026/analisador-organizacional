"""Jornada 5 — Studio: NotebookLM (auth → artefatos → gerar) + export local."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from core.especificacoes_llm import campo_especificacoes_llm
from core.export_infografico import gerar_infografico
from core.export_pptx import gerar_apresentacao_pptx
from core.openai_client import get_api_key
from core.outputs_collector import listar_docx_jornadas
from core.utils import OUTPUTS_DIR, ensure_dirs
from jornadas.comum import render_cabecalho
from modulos.notebooklm import gerar_produtos, login_interativo, sessao_valida
from modulos.notebooklm.browser import chrome_instalado, chrome_real_path

UPLOADS_STUDIO_DIR = OUTPUTS_DIR / "uploads_studio"
TIPOS_UPLOAD_STUDIO = ["docx", "pdf", "txt", "md"]


def _mime_slides(path: Path) -> str:
    if path.suffix.lower() == ".pptx":
        return (
            "application/vnd.openxmlformats-officedocument."
            "presentationml.presentation"
        )
    return "application/pdf"


def _persistir_uploads(files: list) -> list[Path]:
    """Salva uploads do computador em outputs/uploads_studio/ (uma vez por arquivo)."""
    if not files:
        return []
    ensure_dirs()
    UPLOADS_STUDIO_DIR.mkdir(parents=True, exist_ok=True)

    cache: dict = st.session_state.setdefault("studio_uploads_cache", {})
    caminhos: list[Path] = []
    for i, f in enumerate(files):
        nome = Path(getattr(f, "name", None) or f"upload_{i}.bin")
        raw = f.getvalue()
        chave = f"{nome.name}:{len(raw)}"
        existente = cache.get(chave)
        if existente and Path(existente).exists():
            caminhos.append(Path(existente))
            continue
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = nome.stem[:80] or f"upload_{i}"
        destino = UPLOADS_STUDIO_DIR / f"{stem}_{stamp}_{i}{nome.suffix.lower()}"
        destino.write_bytes(raw)
        cache[chave] = str(destino)
        caminhos.append(destino)
    return caminhos


def _painel_downloads_notebooklm() -> None:
    """Botões de download na própria app."""
    slides = st.session_state.get("nlm_slides")
    info = st.session_state.get("nlm_infografico")
    url = st.session_state.get("notebooklm_url")

    tem_slides = bool(slides and Path(slides).exists())
    tem_info = bool(info and Path(info).exists())
    if not tem_slides and not tem_info and not url:
        return

    st.divider()
    st.subheader("Downloads (nesta aplicação)")
    st.caption("Arquivos em `outputs/` — baixe pelos botões abaixo.")

    if url:
        st.caption(f"Notebook no Google (opcional): {url}")

    if tem_slides:
        path = Path(slides)
        st.download_button(
            label=f"Baixar apresentação — {path.name}",
            data=path.read_bytes(),
            file_name=path.name,
            mime=_mime_slides(path),
            type="primary",
            use_container_width=True,
            key="dl_nlm_slides",
        )

    if tem_info:
        path = Path(info)
        st.image(str(path), use_container_width=True)
        st.download_button(
            label=f"Baixar infográfico — {path.name}",
            data=path.read_bytes(),
            file_name=path.name,
            mime="image/png",
            type="primary",
            use_container_width=True,
            key="dl_nlm_png",
        )


def _painel_downloads_locais() -> None:
    pptx = st.session_state.get("studio_pptx")
    info = st.session_state.get("studio_infografico")
    tem_pptx = bool(pptx and Path(pptx).exists())
    tem_info = bool(info and Path(info).exists())
    if not tem_pptx and not tem_info:
        return

    st.subheader("Downloads locais")
    if tem_pptx:
        path = Path(pptx)
        st.download_button(
            label=f"Baixar PPTX local — {path.name}",
            data=path.read_bytes(),
            file_name=path.name,
            mime=_mime_slides(path),
            type="primary",
            use_container_width=True,
            key="dl_studio_pptx",
        )
    if tem_info:
        path = Path(info)
        st.image(str(path), use_container_width=True)
        st.download_button(
            label=f"Baixar infográfico local — {path.name}",
            data=path.read_bytes(),
            file_name=path.name,
            mime="image/png",
            type="primary",
            use_container_width=True,
            key="dl_studio_png",
        )


def render() -> None:
    render_cabecalho(
        "Jornada Studio: autenticar no Google → selecionar artefatos "
        "(sessão ou computador) → gerar no NotebookLM → baixar nesta tela."
    )

    st.markdown(
        '<div class="jornada-card">'
        "<b>NotebookLM:</b> "
        "1) <b>Autenticar (nova janela)</b> — login Google no Chrome. "
        "2) <b>Selecionar</b> documentos de <code>outputs/</code> e/ou "
        "enviar arquivos do computador. "
        "3) <b>Gerar no NotebookLM</b> — o download aparece nesta aplicação."
        "</div>",
        unsafe_allow_html=True,
    )

    _painel_downloads_notebooklm()

    artefatos = listar_docx_jornadas()
    if not artefatos:
        st.info(
            "Nenhum `.docx` das jornadas em `outputs/` ainda. "
            "Você pode **enviar arquivos do computador** na seção 2 "
            "ou gerar/salvar nas jornadas 1–4."
        )

    st.divider()
    st.subheader("1 · Autenticar")
    chrome = chrome_real_path()
    if chrome_instalado():
        st.caption(f"Chrome Linux: `{chrome}`")
    else:
        st.warning(
            "Chrome Linux não encontrado. Rode `./scripts/install_chrome_wsl.sh`."
        )

    if sessao_valida():
        st.success("Autenticado — pode selecionar artefatos e gerar.")
    else:
        st.info("Ainda não autenticado. Abra a nova janela do Chrome abaixo.")

    if st.button(
        "Autenticar (nova janela)",
        use_container_width=True,
        disabled=not chrome_instalado(),
        help="Abre uma nova janela do Chrome para login Google.",
    ):
        st.info(
            "Abrindo nova janela do Chrome — conclua o Google Sign-In "
            "até o NotebookLM aparecer (até ~2 min)."
        )
        with st.spinner("Aguardando login na nova janela…"):
            try:
                login_interativo(fresh=True)
                st.success("Autenticado. Selecione os artefatos e gere.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Falha ao autenticar: {exc}")

    st.divider()
    st.subheader("2 · Selecionar artefatos")
    caminhos: list[Path] = []

    if artefatos:
        opcoes = {str(a.caminho): a.rotulo for a in artefatos}
        selecionados = st.multiselect(
            "Documentos das jornadas anteriores (`outputs/`)",
            options=list(opcoes.keys()),
            default=[],
            format_func=lambda p: opcoes[p],
            key="studio_docs_sel_v2",
            help="Escolha um ou mais .docx gerados na sessão.",
        )
        caminhos.extend(Path(p) for p in selecionados)
    else:
        st.caption("Sem artefatos em `outputs/` — use o upload abaixo.")

    uploads = st.file_uploader(
        "Ou envie arquivos do computador",
        type=TIPOS_UPLOAD_STUDIO,
        accept_multiple_files=True,
        key="studio_upload_local",
        help=(
            "Útil se a sessão não salvou artefatos ou para usar NotebookLM "
            "com documentos externos (.docx, .pdf, .txt, .md)."
        ),
    )
    if uploads:
        persistidos = _persistir_uploads(list(uploads))
        caminhos.extend(persistidos)
        st.caption(
            "Uploads salvos em `outputs/uploads_studio/`: "
            + ", ".join(p.name for p in persistidos)
        )

    # Dedup por path resolvido
    vistos: set[str] = set()
    unicos: list[Path] = []
    for p in caminhos:
        chave = str(p.resolve())
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(p)
    caminhos = unicos

    st.markdown("**O que gerar**")
    g1, g2 = st.columns(2)
    with g1:
        quer_slides = st.checkbox(
            "Apresentação (PPTX / PDF)",
            value=True,
            key="studio_nlm_gerar_slides",
        )
    with g2:
        quer_info = st.checkbox(
            "Infográfico (PNG)",
            value=False,
            key="studio_nlm_gerar_info",
        )

    st.divider()
    st.subheader("3 · Rodar solicitação")
    pode_gerar = (
        chrome_instalado()
        and bool(caminhos)
        and (quer_slides or quer_info)
    )
    if not caminhos:
        st.caption("Selecione documentos de `outputs/` e/ou envie arquivos acima.")
    if not quer_slides and not quer_info:
        st.caption("Marque apresentação e/ou infográfico.")

    if st.button(
        "Gerar no NotebookLM",
        type="primary",
        use_container_width=True,
        disabled=not pode_gerar,
    ):
        if not sessao_valida():
            st.error("Autentique primeiro (botão Autenticar — nova janela).")
        elif not caminhos:
            st.error("Selecione ou envie ao menos um documento.")
        elif not quer_slides and not quer_info:
            st.error("Selecione apresentação e/ou infográfico.")
        else:
            partes = []
            if quer_slides:
                partes.append("apresentação")
            if quer_info:
                partes.append("infográfico")
            with st.spinner(
                "Upload → " + " + ".join(partes) + " (pode levar vários minutos)…"
            ):
                try:
                    result = gerar_produtos(
                        caminhos,
                        language="pt",
                        gerar_slides=quer_slides,
                        gerar_infografico=quer_info,
                    )
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Falha NotebookLM: {exc}")
                    result = None

            if result is not None:
                if result.notebook_url:
                    st.session_state["notebooklm_url"] = result.notebook_url
                if result.slides and result.slides.exists():
                    st.session_state["nlm_slides"] = str(result.slides)
                if result.infografico and result.infografico.exists():
                    st.session_state["nlm_infografico"] = str(result.infografico)

                if result.ok:
                    st.success(result.mensagem)
                    st.rerun()
                else:
                    st.warning(result.mensagem)
                    if result.fontes:
                        st.write("Fontes:", ", ".join(result.fontes))
                    if result.falhas:
                        st.error("Detalhes:\n- " + "\n- ".join(result.falhas))
                    if any("infográfico" in f for f in result.falhas):
                        st.info(
                            "O infográfico do NotebookLM costuma esbarrar em quota "
                            "diária da conta Google. Use **Gerar infográfico local** "
                            "logo abaixo — mesmas fontes, imagem 16:9 via ChatGPT."
                        )

    st.divider()
    st.subheader("Artefatos locais (OpenAI — sem NotebookLM)")
    st.caption(
        "Infográfico local usa o prompt corporativo 16:9 via ChatGPT Images. "
        "Prefira .docx/.txt/.md para o export local."
    )
    if not get_api_key():
        st.warning("Configure `OPENAI_API_KEY` para PPTX e infográfico locais.")

    if not caminhos:
        st.caption(
            "Selecione ou envie documentos na seção 2 para gerar artefatos locais."
        )
        _painel_downloads_locais()
        return

    especificacoes = campo_especificacoes_llm("jornada_studio_especificacoes")

    p1, p2 = st.columns(2)
    with p1:
        if st.button(
            "Gerar PPTX local",
            use_container_width=True,
            disabled=not get_api_key(),
        ):
            with st.spinner("Gerando apresentação local…"):
                try:
                    pptx = gerar_apresentacao_pptx(
                        caminhos, especificacoes=especificacoes
                    )
                    st.session_state["studio_pptx"] = str(pptx)
                    st.success(f"Salvo: `{pptx.name}`")
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Falha PPTX: {exc}")
    with p2:
        if st.button(
            "Gerar infográfico local",
            use_container_width=True,
            disabled=not get_api_key(),
        ):
            with st.spinner("Extraindo conteúdo → prompt 16:9 → imagem ChatGPT…"):
                try:
                    png, html_path = gerar_infografico(
                        caminhos, especificacoes=especificacoes
                    )
                    st.session_state["studio_infografico"] = str(png)
                    st.session_state["studio_infografico_html"] = str(html_path)
                    st.success(f"Salvo: `{png.name}`")
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Falha infográfico: {exc}")

    _painel_downloads_locais()
