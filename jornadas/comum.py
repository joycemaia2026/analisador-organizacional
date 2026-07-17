"""Helpers compartilhados entre jornadas."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from core.utils import LOGO_PATH, ensure_dirs
from core.outputs_collector import contar_docx_jornadas

JORNADAS = {
    "ata": "1 · Gerar Ata",
    "analise": "2 · Análise Organizacional",
    "comparativa": "3 · Análise Comparativa",
    "resumo": "4 · Resumo",
    "studio": "5 · Studio / NotebookLM",
}

INFO_JORNADAS = {
    "ata": {
        "titulo": "Gerar Ata",
        "objetivo": (
            "Registrar decisões e pendências com clareza — base da continuidade "
            "organizacional após a reunião."
        ),
        "fundamento": (
            "Documentação formal · accountability · memória organizacional "
            "(Weber / governance)."
        ),
        "lentes": (
            "Fato × opinião × decisão · dono + prazo · ambiguidade explícita."
        ),
        "passos": [
            "Envie ou cole a transcrição",
            "Faça perguntas rápidas (opcional)",
            "Escolha especialistas e/ou NLP e gere a ata",
            "Leve o registro à jornada 2",
        ],
        "entrada": "Transcrição informal",
        "saida": "Respostas rápidas + ata acionável",
    },
    "analise": {
        "titulo": "Análise Organizacional",
        "objetivo": (
            "Decidir e priorizar sob o olhar do Tomador; o Especialista IA "
            "faz o stress-test da solução."
        ),
        "fundamento": (
            "Tomada de decisão (Simon) · contingência · PDCA / melhoria contínua · "
            "RACI e ownership."
        ),
        "lentes": (
            "Planejador (sequência) · Analítico (causa-raiz) · "
            "Técnico (viabilidade) · Financista (ROI)."
        ),
        "passos": [
            "Escolha um ou mais Tomadores e as lentes",
            "Problema e/ou várias atas (.txt/.csv/.docx)",
            "Analisar (diagnóstico + plano por pessoa)",
            "Revise riscos e próximos passos",
        ],
        "entrada": "Problema + atas + perfis + lentes",
        "saida": "Diagnóstico, plano e avaliação crítica (por Tomador)",
    },
    "comparativa": {
        "titulo": "Análise Comparativa",
        "objetivo": (
            "Confrontar duas visões para reduzir viés e chegar a um consenso "
            "técnico-executivo."
        ),
        "fundamento": (
            "Dialética organizacional · double-loop learning (Argyris) · "
            "sensemaking (Weick)."
        ),
        "lentes": (
            "Convergência × divergência · gaps · conceitos compartilhados."
        ),
        "passos": [
            "Use a análise da jornada 2",
            "Gere o contraste técnico",
            "Veja conceitos e trade-offs",
            "Salve o relatório se precisar",
        ],
        "entrada": "Voz do Tomador + voz do Especialista",
        "saida": "Síntese comparativa e conceitos",
    },
    "resumo": {
        "titulo": "Resumo",
        "objetivo": (
            "Consolidar ata, personas e Especialista IA em um documento "
            "enxuto — problema e o que fazer no topo, com fonte em cada seção."
        ),
        "fundamento": (
            "Síntese executiva · rastreabilidade · continuidade organizacional."
        ),
        "lentes": (
            "Problema · ações · registro da ata · vozes das personas · stress-test IA."
        ),
        "passos": [
            "Confira o material das jornadas 1–2 (e 3 se houver)",
            "Gere o resumo consolidado",
            "Revise problema e o que fazer",
            "Baixe o .docx se precisar",
        ],
        "entrada": "Ata + análise do Tomador + Especialista IA",
        "saida": "Resumo markdown/DOCX com fontes",
    },
    "studio": {
        "titulo": "Studio / NotebookLM",
        "objetivo": (
            "Reunir os .docx das jornadas anteriores, enviar ao NotebookLM e gerar "
            "apresentação PPTX e infográfico para comunicação executiva."
        ),
        "fundamento": (
            "Síntese visual · storytelling de decisão · grounding em fontes "
            "(NotebookLM)."
        ),
        "lentes": (
            "Seleção de artefatos · upload de fontes · PPTX · infográfico."
        ),
        "passos": [
            "Selecione os .docx gerados nas jornadas anteriores",
            "Clique em Gerar no NotebookLM e faça login Google no Chrome",
            "Aguarde upload + slide deck + infográfico",
            "Ou use PPTX/infográfico locais (OpenAI) sem Google",
        ],
        "entrada": ".docx de ata, análise, comparativa e resumo em outputs/",
        "saida": "Slide deck + infográfico NotebookLM (e/ou locais)",
    },
}


def aplicar_tema() -> None:
    st.markdown(
        """
<style>
  .stApp {
    background: linear-gradient(180deg, #F4F7FB 0%, #E8F5EE 100%);
    color: #001060;
  }
  section[data-testid="stSidebar"] {
    background: #FFFFFF !important;
    border-right: 1px solid #D7E3F0;
  }
  section[data-testid="stSidebar"] [data-testid="stImage"] {
    position: sticky;
    top: 0;
    z-index: 20;
    background: #FFFFFF;
    padding-bottom: 0.5rem;
  }
  [data-testid="stSidebar"] * {
    color: #001060;
  }
  h1, h2, h3, h4 {
    color: #001060 !important;
  }
  .stButton > button[kind="primary"] {
    background-color: #00B040;
    border-color: #00B040;
    color: white;
  }
  .stButton > button[kind="primary"]:hover {
    background-color: #009936;
    border-color: #009936;
    color: white;
  }
  .stButton > button {
    border-radius: 8px;
  }
  div[data-baseweb="select"] > div {
    border-color: #00B04033;
  }
  .gedanken-badge {
    display: inline-block;
    background: #E8F5EE;
    color: #001060;
    border: 1px solid #00B04055;
    border-radius: 999px;
    padding: 0.2rem 0.75rem;
    font-size: 0.8rem;
    margin-bottom: 1rem;
  }
  .voz-tomador {
    border-left: 4px solid #001060;
    padding-left: 0.75rem;
    margin: 1rem 0 0.5rem;
  }
  .voz-especialista {
    border-left: 4px solid #00B040;
    padding-left: 0.75rem;
    margin: 1.5rem 0 0.5rem;
  }
  .voz-comparativa {
    border-left: 4px solid #0050A0;
    padding-left: 0.75rem;
    margin: 1.5rem 0 0.5rem;
  }
  .jornada-card {
    border: 1px solid #D7E3F0;
    border-radius: 10px;
    padding: 0.75rem 1rem;
    background: #FFFFFF;
    margin-bottom: 1rem;
  }
  .marca-topo {
    margin: 0 0 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #D7E3F0;
  }
  .marca-topo h1 {
    margin: 0 !important;
    font-size: 2rem !important;
    line-height: 1.2 !important;
    color: #001060 !important;
  }
  .marca-slogan {
    margin: 0.35rem 0 0.5rem;
    color: #003080;
    font-size: 1.05rem;
    font-weight: 500;
  }
  .nav-jornadas-fixa {
    position: sticky;
    top: 0;
    z-index: 999;
    background: linear-gradient(180deg, #F4F7FB 0%, #F4F7FB 90%, transparent 100%);
    padding: 0.5rem 0 0.75rem;
    margin-bottom: 0.5rem;
  }
</style>
""",
        unsafe_allow_html=True,
    )


SLOGAN = "Da ata à decisão — com a lente de quem lidera."


def render_marca() -> None:
    """Título e slogan fixos no topo de todas as jornadas."""
    ensure_dirs()
    st.markdown(
        f"""
<div class="marca-topo">
  <h1>Analisador Organizacional</h1>
  <p class="marca-slogan">{SLOGAN}</p>
  <span class="gedanken-badge">Gedanken</span>
</div>
""",
        unsafe_allow_html=True,
    )


def render_cabecalho(subtitulo: str) -> None:
    """Subtítulo da jornada ativa (a marca global já está no topo)."""
    st.caption(subtitulo)


def lista_bullets(itens: list[str]) -> None:
    for item in itens:
        st.markdown(f"- {item}")


def _render_info_jornada(jornada: str) -> None:
    info = INFO_JORNADAS.get(jornada) or INFO_JORNADAS["analise"]
    st.markdown(f"**{info['titulo']}**")
    st.caption(info["objetivo"])
    st.markdown("**Fundamento**")
    st.caption(info.get("fundamento", ""))
    st.markdown("**Foco analítico**")
    st.caption(info.get("lentes", ""))
    st.markdown("**Passos**")
    for i, passo in enumerate(info["passos"], start=1):
        st.markdown(f"{i}. {passo}")
    st.markdown(f"**Entrada:** {info['entrada']}")
    st.markdown(f"**Saída:** {info['saida']}")


def _barra_jornadas_topo() -> str:
    """Botões de jornada fixos no topo."""
    if "jornada_ativa" not in st.session_state:
        st.session_state.jornada_ativa = "ata"

    st.markdown('<div class="nav-jornadas-fixa">', unsafe_allow_html=True)
    cols = st.columns(len(JORNADAS))
    for col, (key, label) in zip(cols, JORNADAS.items()):
        with col:
            ativo = st.session_state.jornada_ativa == key
            if st.button(
                label,
                key=f"btn_jornada_{key}",
                type="primary" if ativo else "secondary",
                use_container_width=True,
            ):
                st.session_state.jornada_ativa = key
                st.rerun()
    st.markdown(
        """
**Como usar os módulos**
1. **Gerar Ata** — transforma a transcrição em ata estruturada; permite perguntas rápidas, escolha de especialistas e análise NLP.
2. **Análise Organizacional** — o Tomador de Decisão interpreta o problema e as atas; o Especialista IA faz o stress-test da visão.
3. **Análise Comparativa** — confronta as duas vozes e sintetiza convergências, divergências, gaps e conceitos.
4. **Resumo** — consolida ata, personas e Especialista IA com foco em problema e o que fazer.
5. **Studio / NotebookLM** — envia os .docx ao NotebookLM e gera PPTX + infográfico.
"""
    )
    st.markdown("</div>", unsafe_allow_html=True)
    return st.session_state.jornada_ativa


def selecionar_jornada() -> str:
    """
    Topo: marca (título + slogan) e botões de jornada.
    Sidebar: logo + informações da jornada ativa + status.
    """
    ensure_dirs()
    logo = Path(LOGO_PATH)

    render_marca()
    jornada = _barra_jornadas_topo()

    atas = st.session_state.get("atas_anexadas") or []
    if not atas and st.session_state.get("ata_gerada_texto"):
        # Compatibilidade com sessão antiga (uma única ata).
        atas = [
            {
                "nome": st.session_state.get("ata_gerada_nome") or "ata_gerada.md",
                "texto": st.session_state["ata_gerada_texto"],
            }
        ]

    with st.sidebar:
        if logo.exists():
            st.image(str(logo), use_container_width=True)
        else:
            st.markdown("### Gedanken")

        st.subheader("Sobre esta jornada")
        _render_info_jornada(jornada)

        st.divider()
        st.caption("Status do fluxo")
        tem_analise = bool(st.session_state.get("analise_tomador"))
        tem_comp = bool(st.session_state.get("analise_comparativa"))
        tem_resumo = bool(st.session_state.get("resumo_consolidado"))

        st.markdown(f"- Atas anexadas: {len(atas)}")
        st.markdown(f"- Análise pronta: {'sim' if tem_analise else 'não'}")
        st.markdown(f"- Comparativa: {'sim' if tem_comp else 'não'}")
        st.markdown(f"- Resumo: {'sim' if tem_resumo else 'não'}")
        st.markdown(f"- .docx em outputs (1–3): {contar_docx_jornadas()}")

    return jornada
