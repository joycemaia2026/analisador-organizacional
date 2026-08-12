"""Jornada 1 — Gerar Ata (módulo ata_maker embarcado)."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import streamlit as st

from core.ata_maker_client import (
    aplicar_skills_na_transcricao,
    check_health,
    gerar_ata_de_transcricao,
    listar_especialistas,
    listar_skills_disponiveis,
)
from core.documentos import TIPOS_UPLOAD, anexar_documento_sessao, extrair_texto_arquivo
from core.especificacoes_llm import campo_especificacoes_llm
from core.export_docx import markdown_para_docx_bytes, salvar_markdown_como_docx
from core.export_pdf import markdown_para_pdf_bytes
from core.nlp_painel import render_painel_nlp
from core.openai_client import get_api_key
from core.utils import OUTPUTS_DIR, ensure_dirs
from jornadas.comum import render_cabecalho
from modulos.ata_maker.perguntas import SUGESTOES, responder_perguntas_transcricao
from modulos.ata_maker.nlp import run_nlp_analysis


def _stem_ata(nome: str) -> str:
    return Path(nome or "ata").stem


def _extrair_resumo_ata(texto: str, *, max_chars: int = 1200) -> str:
    """Puxa o resumo executivo da ata, se existir; senão, o início do texto."""
    padroes = [
        r"##\s*Resumo\s+[Ee]xecutivo\s*\n+(.*?)(?=\n##\s|\Z)",
        r"##\s*Em uma frase\s*\n+(.*?)(?=\n##\s|\Z)",
        r"##\s*1\.\s*Resumo\s+[Ee]xecutivo\s*\n+(.*?)(?=\n##\s|\Z)",
    ]
    for pat in padroes:
        m = re.search(pat, texto, flags=re.DOTALL)
        if m:
            resumo = m.group(1).strip()
            if resumo:
                return resumo[:max_chars]
    limpo = re.sub(r"^#+\s*", "", texto.strip(), count=1)
    return limpo[:max_chars].strip()


def _atas_sessao() -> list[dict]:
    atas = st.session_state.get("atas_anexadas")
    if isinstance(atas, list):
        return atas
    # Migração de sessão antiga (uma única ata).
    if st.session_state.get("ata_gerada_texto"):
        return [
            {
                "nome": st.session_state.get("ata_gerada_nome") or "ata_gerada.md",
                "texto": st.session_state["ata_gerada_texto"],
            }
        ]
    return []


def _registrar_ata(nome: str, texto: str) -> Path | None:
    atas = anexar_documento_sessao(_atas_sessao(), nome=nome, texto=texto)
    st.session_state["atas_anexadas"] = atas
    st.session_state["ata_gerada_texto"] = texto
    st.session_state["ata_gerada_nome"] = nome

    # Persiste .docx em outputs/ para a jornada 4.
    ensure_dirs()
    stem = _stem_ata(nome)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = OUTPUTS_DIR / f"ata_{stem}_{stamp}.docx"
    titulo = stem.replace("_", " ").title()
    salvar_markdown_como_docx(caminho, titulo, texto or "")
    st.session_state["ultimo_ata_docx"] = str(caminho)
    paths = list(st.session_state.get("outputs_ata") or [])
    paths.append(str(caminho))
    st.session_state["outputs_ata"] = paths
    return caminho


def _preparar_para_analise(ata_texto: str, nome_arquivo: str) -> None:
    """Anexa a ata e preenche o pedido de ajuda — sem trocar de jornada."""
    _registrar_ata(nome_arquivo, ata_texto)
    resumo = _extrair_resumo_ata(ata_texto)
    n = len(_atas_sessao())
    prefixo = (
        f"Com base na(s) ata(s) anexada(s) ({n}), oriente as decisões "
        "e a continuidade organizacional.\n\n"
    )
    st.session_state["jornada_analise_problema"] = (
        prefixo + f"**Resumo da última ata ({nome_arquivo}):**\n{resumo}"
    )
    st.session_state["veio_da_ata"] = True


def _enviar_para_analise(ata_texto: str, nome_arquivo: str) -> None:
    """Prepara a Análise e abre a jornada 2 (ação explícita do usuário)."""
    _preparar_para_analise(ata_texto, nome_arquivo)
    st.session_state["jornada_ativa"] = "analise"
    st.rerun()


def _resolver_transcricao(transcricao_file, transcricao_texto: str) -> tuple[str, str]:
    """Retorna (texto, nome_fonte) a partir do upload ou do texto colado."""
    if transcricao_file is not None:
        doc = extrair_texto_arquivo(transcricao_file.name, transcricao_file.getvalue())
        return doc.texto, doc.nome
    if (transcricao_texto or "").strip():
        return transcricao_texto.strip(), "transcricao.txt"
    return "", "transcricao.txt"


def _painel_perguntas_rapidas(transcricao: str, *, online: bool) -> None:
    """Q&A rápido ancorado na transcrição (multiseleção de sugestões)."""
    st.divider()
    st.subheader("Perguntas rápidas sobre a transcrição")
    st.caption(
        "A resposta usa a transcrição como fonte principal e o LLM para "
        "organizar, sintetizar e esclarecer — sem inventar o que não foi dito."
    )

    if "qa_historico" not in st.session_state:
        st.session_state.qa_historico = []
    if "qa_sugestoes_sel" not in st.session_state:
        st.session_state.qa_sugestoes_sel = []

    if not transcricao.strip():
        st.info("Envie ou cole a transcrição acima para liberar as perguntas.")
        return

    selecionadas = st.multiselect(
        "Sugestões (pode marcar várias)",
        options=list(SUGESTOES),
        key="qa_sugestoes_sel",
        help="Marque uma ou mais. A resposta cobre todas de uma vez.",
    )

    pergunta_livre = st.text_input(
        "Pergunta extra (opcional)",
        placeholder="Ex.: Quem ficou responsável pelo prazo do projeto?",
        key="qa_pergunta_input",
    )

    perguntas_envio = list(selecionadas)
    livre = (pergunta_livre or "").strip()
    if livre and livre not in perguntas_envio:
        perguntas_envio.append(livre)

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        perguntar = st.button(
            "Perguntar",
            type="primary",
            disabled=not online or not perguntas_envio,
            key="qa_btn_perguntar",
        )
    with c2:
        if st.button("Limpar seleção", key="qa_btn_limpar_sel"):
            st.session_state.qa_sugestoes_sel = []
            st.session_state.qa_pergunta_input = ""
            st.rerun()
    with c3:
        if st.button("Limpar histórico de perguntas", key="qa_btn_limpar"):
            st.session_state.qa_historico = []
            st.rerun()

    if perguntar:
        rotulo = (
            perguntas_envio[0]
            if len(perguntas_envio) == 1
            else f"{len(perguntas_envio)} perguntas selecionadas"
        )
        with st.spinner("Respondendo com base na transcrição…"):
            try:
                resposta = responder_perguntas_transcricao(
                    transcricao,
                    perguntas_envio,
                    historico=st.session_state.qa_historico,
                )
                st.session_state.qa_historico.append(
                    {
                        "pergunta": rotulo
                        if len(perguntas_envio) == 1
                        else " · ".join(perguntas_envio),
                        "resposta": resposta,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"Falha ao responder: {exc}")
                return

    historico = st.session_state.get("qa_historico") or []
    if historico:
        st.markdown(f"**Histórico ({len(historico)})**")
        for i, item in enumerate(reversed(historico), start=1):
            with st.expander(
                f"P{len(historico) - i + 1}: {item['pergunta'][:80]}",
                expanded=(i == 1),
            ):
                st.markdown(item["resposta"])


def _botoes_download_ata(nome: str, texto: str, *, key_prefix: str) -> None:
    """Dois botões no topo: DOCX e PDF."""
    stem = _stem_ata(nome)
    titulo = stem.replace("_", " ").title()
    docx_bytes = markdown_para_docx_bytes(titulo, texto or "")
    pdf_bytes = markdown_para_pdf_bytes(titulo, texto or "")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "Baixar DOCX",
            data=docx_bytes,
            file_name=f"{stem}.docx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            key=f"{key_prefix}_docx",
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "Baixar PDF",
            data=pdf_bytes,
            file_name=f"{stem}.pdf",
            mime="application/pdf",
            key=f"{key_prefix}_pdf",
            use_container_width=True,
        )


def render() -> None:
    render_cabecalho(
        "Jornada Ata: transforme a transcrição em ata estruturada "
        "(módulo ata_maker clonado neste projeto)."
    )

    health = check_health()
    if health.online:
        st.success(
            f"Módulo ata_maker local pronto"
            + (f" · modelo `{health.model}`" if health.model else "")
        )
    else:
        st.warning(health.message)
        if not get_api_key():
            st.info("Configure a chave do provedor LLM no `.env` e recarregue.")

    st.markdown(
        '<div class="jornada-card">'
        "<b>Fluxo:</b> transcrição → perguntas rápidas e/ou ata → Análise. "
        "Você pode gerar várias atas; todas ficam anexadas na jornada 2."
        "</div>",
        unsafe_allow_html=True,
    )

    col_up, col_paste = st.columns(2)
    with col_up:
        transcricao_file = st.file_uploader(
            "Transcrição (.txt / .csv / .docx)",
            type=TIPOS_UPLOAD,
            accept_multiple_files=False,
            key="jornada_ata_upload",
        )
    with col_paste:
        transcricao_texto = st.text_area(
            "Ou cole a transcrição",
            height=160,
            placeholder="Cole aqui o texto bruto da reunião…",
            key="jornada_ata_texto",
        )

    try:
        bruto_atual, _nome_atual = _resolver_transcricao(
            transcricao_file, transcricao_texto
        )
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Não foi possível ler a transcrição: {exc}")
        bruto_atual = ""

    _painel_perguntas_rapidas(bruto_atual, online=health.online)

    st.divider()
    st.subheader("Gerar ata")

    st.markdown("#### Etapas da geração")
    opt_gerar = st.checkbox(
        "1. Gerar Ata",
        value=True,
        key="jornada_ata_opt_gerar",
        help=(
            "Ata assertiva para o leitor: levantamento + registro factual "
            "(decisões, donos, prazos). A preparação da transcrição roda automaticamente."
        ),
    )
    if opt_gerar:
        st.caption(
            "Formato: em uma frase → decisões → pendências com dono/prazo → "
            "leitura de startup. Prioriza assertividade (400–600 palavras)."
        )

    opt_skills = st.checkbox(
        "2. Aplicar Skills",
        value=False,
        key="jornada_ata_opt_skills",
        help=(
            "Pipeline complementar: levantamento, pontos de ação, "
            "resumo de decisões, próxima reunião. "
            "A preparação da transcrição roda automaticamente; a ata está em Gerar Ata."
        ),
    )

    skills_catalogo = listar_skills_disponiveis()
    skills_ids = [s.name for s in skills_catalogo]
    skills_rotulos = {s.name: s.rotulo for s in skills_catalogo}
    skills_sel: list[str] = []
    if opt_skills:
        if not skills_ids:
            st.warning("Nenhuma skill encontrada em `skills/`.")
        else:
            st.markdown("#### Skills do BriefBoard")
            c_sk_all, c_sk_clear = st.columns(2)
            with c_sk_all:
                if st.button(
                    "Selecionar todas",
                    key="btn_skills_todos",
                    use_container_width=True,
                ):
                    st.session_state["jornada_ata_skills_sel"] = list(skills_ids)
                    st.rerun()
            with c_sk_clear:
                if st.button(
                    "Limpar skills",
                    key="btn_skills_limpar",
                    use_container_width=True,
                ):
                    st.session_state["jornada_ata_skills_sel"] = []
                    st.rerun()
            if "jornada_ata_skills_sel" not in st.session_state:
                st.session_state["jornada_ata_skills_sel"] = []
            # Remove infra/fundidas de sessões antigas; não pré-seleciona nada.
            st.session_state["jornada_ata_skills_sel"] = [
                n
                for n in st.session_state.get("jornada_ata_skills_sel", [])
                if n in skills_ids
            ]
            skills_sel = st.multiselect(
                "Selecione as skills",
                options=skills_ids,
                format_func=lambda n: skills_rotulos.get(n, n),
                key="jornada_ata_skills_sel",
            )
            if not skills_sel:
                st.warning("Selecione ao menos uma skill.")

    opt_especialistas = st.checkbox(
        "3. Visão de Especialistas",
        value=False,
        key="jornada_ata_opt_especialistas",
    )
    incluir_nlp = st.checkbox(
        "4. Análise de Sentimento com NLP",
        value=True,
        key="jornada_ata_opt_nlp",
        help="Sentimento, palavras frequentes e perfil linguístico.",
    )

    especialistas_sel: list[str] = []
    if opt_especialistas:
        st.markdown("#### Tipos de especialistas")
        opcoes_esp = listar_especialistas()
        ids_esp = [k for k, _ in opcoes_esp]
        rotulos = {k: label for k, label in opcoes_esp}

        c_sel, c_limpar = st.columns(2)
        with c_sel:
            if st.button("Selecionar todos", key="btn_esp_todos", use_container_width=True):
                st.session_state["jornada_ata_especialistas_v2"] = list(ids_esp)
                st.rerun()
        with c_limpar:
            if st.button("Limpar", key="btn_esp_limpar", use_container_width=True):
                st.session_state["jornada_ata_especialistas_v2"] = []
                st.rerun()

        especialistas_sel = st.multiselect(
            "Selecione um ou mais especialistas",
            options=ids_esp,
            default=[],
            format_func=lambda k: rotulos.get(k, k),
            key="jornada_ata_especialistas_v2",
            help="Use Selecionar todos ou escolha individualmente.",
        )
        if not especialistas_sel:
            st.warning("Selecione ao menos um especialista para a visão de especialistas.")

    # A voz da marca vale para qualquer saída, não só para as personas.
    incluir_manual_voz = st.checkbox(
        "Incluir Manual de Voz Gedanken",
        value=True,
        key="jornada_ata_opt_manual_voz",
        help="Injeta docs/voz-gedanken.md no system prompt da geração.",
    )

    modo_ata = "full" if opt_especialistas else "prompt"

    preparar_analise = st.checkbox(
        "Após gerar, preparar Análise Institucional (anexar ata e preencher pedido — sem mudar de jornada)",
        value=False,
        key="ata_preparar_analise",
    )

    especificacoes = campo_especificacoes_llm("jornada_ata_especificacoes")

    gerar_ok = (
        health.online
        and (opt_gerar or opt_skills)
        and (not opt_gerar or not opt_especialistas or bool(especialistas_sel))
        and (not opt_skills or bool(skills_sel))
    )
    if st.button(
        "Executar etapas",
        type="primary",
        disabled=not gerar_ok,
    ):
        try:
            bruto, nome_fonte = _resolver_transcricao(
                transcricao_file, transcricao_texto
            )
        except Exception as exc:  # noqa: BLE001
            st.error(f"Falha ao ler arquivo: {exc}")
            return

        if not bruto.strip():
            st.error("Envie ou cole uma transcrição.")
            return

        if opt_skills and skills_sel:
            status_box = st.empty()

            def _prog(msg: str) -> None:
                status_box.info(msg)

            with st.spinner("Aplicando skills…"):
                try:
                    pipe = aplicar_skills_na_transcricao(
                        bruto,
                        source_filename=nome_fonte,
                        skills=skills_sel,
                        incluir_manual_voz=incluir_manual_voz,
                        progress=_prog,
                    )
                    st.session_state["ultimo_skills_pipeline"] = {
                        "stem": pipe.stem,
                        "pasta": pipe.pasta,
                        "erros": pipe.erros,
                        "skills": [
                            {
                                "name": s.name,
                                "ok": s.ok,
                                "erro": s.erro,
                                "avisos": s.avisos,
                                "caminhos": s.caminhos,
                                "markdown": s.markdown,
                            }
                            for s in pipe.skills
                        ],
                    }
                    ok_n = sum(1 for s in pipe.skills if s.ok)
                    st.success(
                        f"Skills: {ok_n}/{len(pipe.skills)} ok · "
                        f"artefatos em `{pipe.pasta}`."
                    )
                    avisos_estrutura = [
                        e
                        for e in (pipe.erros or [])
                        if "não cabe à análise estruturada" in e
                    ]
                    if avisos_estrutura:
                        st.error(
                            "A estrutura desta reunião não cabe à análise estruturada "
                            "(menos de 50% das informações necessárias). "
                            + " · ".join(avisos_estrutura)
                        )
                    elif pipe.erros:
                        st.warning("Avisos skills: " + "; ".join(pipe.erros))
                    if pipe.ata_markdown:
                        nome_skill_ata = f"ata_skills_{pipe.stem}.md"
                        if preparar_analise and not opt_gerar:
                            _preparar_para_analise(pipe.ata_markdown, nome_skill_ata)
                        else:
                            _registrar_ata(nome_skill_ata, pipe.ata_markdown)
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Falha ao aplicar skills: {exc}")
                    return
                finally:
                    status_box.empty()

        if opt_gerar:
            status_ata = st.empty()

            def _prog_ata(msg: str) -> None:
                status_ata.info(msg)

            with st.spinner("Gerando ata assertiva…"):
                try:
                    ata = gerar_ata_de_transcricao(
                        bruto,
                        source_filename=nome_fonte,
                        modo=modo_ata,
                        personas=especialistas_sel if opt_especialistas else None,
                        incluir_nlp=incluir_nlp,
                        especificacoes=especificacoes,
                        incluir_manual_voz=incluir_manual_voz,
                        progress=_prog_ata if modo_ata != "full" else None,
                    )
                    nome_ata = f"ata_gerada_{Path(nome_fonte).stem}.md"
                    if ata.nlp:
                        st.session_state["ultimo_nlp"] = ata.nlp
                    if preparar_analise:
                        _preparar_para_analise(ata.texto, nome_ata)
                        st.success(
                            "Ata gerada e preparada para a Análise "
                            "(permanece nesta jornada). Use **2 · Análise Institucional** quando quiser."
                        )
                    else:
                        _registrar_ata(nome_ata, ata.texto)
                        st.success(
                            "Ata assertiva gerada, anexada e salva em `outputs/`. "
                            "Use o botão abaixo ou a jornada **2 · Análise Institucional**."
                        )
                    if ata.saved_report:
                        st.caption(f"Cópia canônica: `{ata.saved_report}`")
                    if ata.erros:
                        estrutura = [
                            e
                            for e in ata.erros
                            if "não cabe à análise estruturada" in e
                        ]
                        if estrutura:
                            st.error(" · ".join(estrutura))
                        outros = [e for e in ata.erros if e not in estrutura]
                        if outros:
                            st.warning("Avisos: " + "; ".join(outros))
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Falha ao gerar ata: {exc}")
                finally:
                    status_ata.empty()

    pipe_sessao = st.session_state.get("ultimo_skills_pipeline")
    if isinstance(pipe_sessao, dict) and pipe_sessao.get("skills"):
        st.divider()
        st.subheader("Resultado das skills")
        st.caption(f"Pasta: `{pipe_sessao.get('pasta')}`")
        for item in pipe_sessao["skills"]:
            marca = "ok" if item.get("ok") else "erro"
            estrutura_baixa = any(
                "não cabe à análise estruturada" in (a or "")
                for a in (item.get("avisos") or [])
            )
            if estrutura_baixa:
                marca = "estrutura inadequada"
            with st.expander(f"{item.get('name')} · {marca}", expanded=estrutura_baixa):
                if estrutura_baixa:
                    st.error(
                        next(
                            a
                            for a in item["avisos"]
                            if "não cabe à análise estruturada" in a
                        )
                    )
                if item.get("erro"):
                    st.error(item["erro"])
                if item.get("avisos"):
                    st.warning("; ".join(item["avisos"]))
                caminhos = item.get("caminhos") or {}
                if caminhos:
                    st.markdown(
                        "Arquivos:\n"
                        + "\n".join(f"- `{v}`" for v in caminhos.values())
                    )
                if item.get("markdown"):
                    st.markdown(item["markdown"][:8000])

    atas = _atas_sessao()
    if atas:
        st.divider()
        st.subheader(f"Atas geradas nesta sessão ({len(atas)})")

        nomes = [a.get("nome") or f"ata_{i+1}" for i, a in enumerate(atas)]
        idx_padrao = len(atas) - 1
        escolhida = st.selectbox(
            "Ata para visualizar / baixar",
            options=list(range(len(atas))),
            index=idx_padrao,
            format_func=lambda i: nomes[i],
            key="ata_download_selecionada",
        )
        ata_sel = atas[escolhida]
        _botoes_download_ata(
            ata_sel.get("nome", "ata_gerada.md"),
            ata_sel.get("texto", ""),
            key_prefix="dl_ata_selecionada",
        )

        nlp = st.session_state.get("ultimo_nlp")
        if nlp:
            st.divider()
            render_painel_nlp(nlp)
        elif incluir_nlp:
            if st.button("Exibir gráficos NLP da transcrição atual"):
                try:
                    bruto_preview, _ = _resolver_transcricao(
                        transcricao_file, transcricao_texto
                    )
                    base = bruto_preview.strip()
                    if not base:
                        st.warning("Envie ou cole a transcrição para analisar.")
                    else:
                        with st.spinner("Calculando NLP…"):
                            st.session_state["ultimo_nlp"] = run_nlp_analysis(base)
                        st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Falha no NLP: {exc}")

        with st.expander("Ver conteúdo da ata", expanded=True):
            st.markdown(ata_sel.get("texto", ""))

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Enviar esta ata para Análise", type="primary"):
                _enviar_para_analise(
                    ata_sel.get("texto", ""),
                    ata_sel.get("nome", "ata_gerada.md"),
                )
        with c2:
            if st.button("Limpar atas geradas"):
                for k in (
                    "atas_anexadas",
                    "ata_gerada_texto",
                    "ata_gerada_nome",
                    "ata_gerada_report",
                    "veio_da_ata",
                    "qa_historico",
                    "ultimo_nlp",
                ):
                    st.session_state.pop(k, None)
                st.rerun()
