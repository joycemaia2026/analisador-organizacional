"""Painel visual da análise NLP (métricas + gráficos Altair)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def render_painel_nlp(nlp: dict[str, Any] | None, *, key_prefix: str = "nlp") -> None:
    """Exibe números, tabelas e gráficos a partir do dict de `run_nlp_analysis`."""
    if not nlp:
        return

    sent = nlp.get("sentiment") or {}
    stats = nlp.get("estatisticas") or {}
    outras = nlp.get("outras") or {}
    palavras = nlp.get("word_frequencies") or []

    st.subheader("Análise NLP — números e gráficos")
    st.caption(
        f"Sentimento: **{sent.get('label', '—')}** · "
        f"compound {sent.get('compound', '—')} · "
        f"formalidade **{outras.get('nivel_formalidade', '—')}**"
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Palavras", stats.get("palavras_brutas", 0))
    c2.metric("Tokens úteis", stats.get("tokens_uteis", nlp.get("tokens_analisados", 0)))
    c3.metric("Vocabulário único", stats.get("vocabulario_unico", 0))
    c4.metric(
        "Diversidade lexical",
        f"{stats.get('diversidade_lexical_pct', 0)}%",
    )

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Frases", stats.get("frases", 0))
    c6.metric("Média palavras/frase", stats.get("media_palavras_por_frase", 0))
    c7.metric("Hits +", sent.get("pos_hits", 0))
    c8.metric("Hits −", sent.get("neg_hits", 0))

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**Distribuição de sentimento**")
        df_sent = pd.DataFrame(
            [
                {"categoria": "Positivo", "valor": float(sent.get("positive") or 0) * 100},
                {"categoria": "Negativo", "valor": float(sent.get("negative") or 0) * 100},
                {"categoria": "Neutro", "valor": float(sent.get("neutral") or 0) * 100},
            ]
        )
        st.bar_chart(df_sent.set_index("categoria"), height=220)

    with col_b:
        st.markdown("**Top palavras**")
        if palavras:
            df_w = pd.DataFrame(palavras[:12]).rename(
                columns={"word": "palavra", "count": "ocorrências"}
            )
            st.bar_chart(df_w.set_index("palavra"), height=220)
        else:
            st.caption("Sem palavras suficientes.")

    bigramas = stats.get("bigramas_top") or []
    falantes = stats.get("falantes") or []
    acoes = stats.get("verbos_acao_top") or []

    col_c, col_d = st.columns(2)
    with col_c:
        st.markdown("**Bigramas frequentes**")
        if bigramas:
            df_b = pd.DataFrame(bigramas[:10]).rename(
                columns={"bigrama": "par", "count": "ocorrências"}
            )
            st.bar_chart(df_b.set_index("par"), height=220)
        else:
            st.caption("Sem bigramas.")

    with col_d:
        if falantes:
            st.markdown("**Falantes detectados**")
            df_f = pd.DataFrame(falantes).rename(
                columns={"falante": "nome", "falas": "falas"}
            )
            st.bar_chart(df_f.set_index("nome"), height=220)
        elif acoes:
            st.markdown("**Verbos de ação**")
            df_a = pd.DataFrame(acoes).rename(
                columns={"palavra": "verbo", "count": "ocorrências"}
            )
            st.bar_chart(df_a.set_index("verbo"), height=220)
        else:
            st.markdown("**Informalidade**")
            taxa = float(outras.get("taxa_informalidade_pct") or 0)
            st.metric("Taxa de informalidade", f"{taxa:.1f}%")

    polarizadas = sent.get("polarized_sentences") or []
    if polarizadas:
        with st.expander("Frases polarizadas", expanded=False):
            for p in polarizadas[:6]:
                st.markdown(
                    f"- **{p.get('polarity')}** ({p.get('score')}): "
                    f"{p.get('sentence')}"
                )

    girias = outras.get("girias") or []
    if girias:
        with st.expander("Gírias detectadas", expanded=False):
            st.write(
                ", ".join(f"{g['palavra']} ({g['ocorrencias']})" for g in girias[:10])
            )
