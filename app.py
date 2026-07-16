"""Analisador Organizacional — acesso por jornadas."""

from __future__ import annotations

import streamlit as st

from core.utils import LOGO_PATH
from jornadas import jornada_analise, jornada_ata, jornada_comparativa
from jornadas.comum import aplicar_tema, selecionar_jornada


st.set_page_config(
    page_title="Analisador Organizacional",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "🟩",
    layout="wide",
    initial_sidebar_state="expanded",
)

aplicar_tema()


def main() -> None:
    jornada = selecionar_jornada()
    if jornada == "ata":
        jornada_ata.render()
    elif jornada == "comparativa":
        jornada_comparativa.render()
    else:
        jornada_analise.render()


if __name__ == "__main__":
    main()
