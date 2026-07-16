"""Motor de análise organizacional (Tomador + Especialista IA)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from core.especialista_ia import ESPECIALISTA_IA
from core.openai_client import chat_completion, get_api_key
from core.prompts import (
    prompt_analise,
    prompt_analise_comparativa,
    prompt_avaliacao_especialista,
)
from core.utils import OUTPUTS_DIR, ensure_dirs


def validar_entrada(problema: str, documentos: str = "") -> str | None:
    if (not problema or not problema.strip()) and (not documentos or not documentos.strip()):
        return "Informe um problema ou anexe pelo menos um documento (ex.: ata de reunião)."
    return None


def _garantir_api() -> None:
    if not get_api_key():
        raise RuntimeError(
            "OPENAI_API_KEY não configurada. Copie .env.example para .env e preencha a chave."
        )


def _problema_efetivo(problema: str, documentos: str) -> str:
    if problema and problema.strip():
        return problema.strip()
    if documentos and documentos.strip():
        return (
            "Analise os documentos anexados (ex.: ata de reunião). "
            "Você não participou do evento; oriente decisões com base apenas no registro escrito "
            "e no seu perfil profissional."
        )
    return ""


def analisar_problema(
    perfil: dict[str, Any],
    problema: str,
    contexto: str = "",
    documentos: str = "",
    lentes: list[str] | None = None,
) -> str:
    """Análise sob a voz do Tomador de Decisão selecionado."""
    erro = validar_entrada(problema, documentos)
    if erro:
        raise ValueError(erro)
    _garantir_api()

    messages = prompt_analise(
        perfil,
        _problema_efetivo(problema, documentos),
        contexto,
        documentos=documentos,
        lentes=lentes,
    )
    return chat_completion(messages, temperature=0.4)


def avaliar_com_especialista_ia(
    perfil: dict[str, Any],
    problema: str,
    contexto: str,
    analise_tomador: str,
    documentos: str = "",
    lentes: list[str] | None = None,
) -> str:
    """
    Segunda passagem: Especialista IA Sênior digere e avalia a análise do tomador.
    """
    erro = validar_entrada(problema, documentos)
    if erro:
        raise ValueError(erro)
    if not analise_tomador or not analise_tomador.strip():
        raise ValueError("É necessário ter a análise do Tomador de Decisão antes da avaliação.")
    _garantir_api()

    messages = prompt_avaliacao_especialista(
        perfil=perfil,
        problema=_problema_efetivo(problema, documentos),
        contexto=contexto,
        analise_tomador=analise_tomador,
        especialista=ESPECIALISTA_IA,
        documentos=documentos,
        lentes=lentes,
    )
    return chat_completion(messages, temperature=0.35)


def gerar_analise_comparativa(
    nome_tomador: str,
    problema: str,
    contexto: str,
    analise_tomador: str,
    avaliacao_especialista: str,
    documentos: str = "",
) -> str:
    """Comparação técnica entre as duas análises + conceitos envolvidos."""
    if not analise_tomador.strip() or not avaliacao_especialista.strip():
        raise ValueError("As duas análises precisam existir para a comparação.")
    _garantir_api()

    messages = prompt_analise_comparativa(
        nome_tomador=nome_tomador,
        problema=_problema_efetivo(problema, documentos),
        contexto=contexto,
        analise_tomador=analise_tomador,
        avaliacao_especialista=avaliacao_especialista,
        documentos=documentos,
    )
    return chat_completion(messages, temperature=0.25)


def montar_markdown_completo(
    nome_tomador: str,
    problema: str,
    contexto: str,
    analise_tomador: str,
    avaliacao_especialista: str | None = None,
    analise_comparativa: str | None = None,
    documentos: str = "",
) -> str:
    partes = [
        f"**Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Tomador de Decisão:** {nome_tomador}",
        "",
        "## Problema",
        problema.strip() or "(não informado)",
        "",
        "## Contexto adicional",
        (contexto.strip() or "(nenhum)"),
        "",
    ]
    if documentos and documentos.strip():
        partes.extend(
            [
                "## Documentos anexos (atas / notas)",
                "",
                documentos.strip(),
                "",
            ]
        )
    partes.extend(
        [
            f"## Análise do Tomador de Decisão — {nome_tomador}",
            "",
            analise_tomador.strip(),
            "",
        ]
    )
    if avaliacao_especialista:
        partes.extend(
            [
                "## Avaliação do Especialista IA Sênior",
                "",
                avaliacao_especialista.strip(),
                "",
            ]
        )
    if analise_comparativa:
        partes.extend(
            [
                "## Análise comparativa técnica",
                "",
                analise_comparativa.strip(),
                "",
            ]
        )
    return "\n".join(partes)


def _slug_tomador(nome_tomador: str) -> str:
    slug = "".join(c if c.isalnum() else "_" for c in (nome_tomador or "tomador")).strip("_")
    return (slug[:40] or "tomador")


def salvar_analises(
    nome_tomador: str,
    problema: str,
    contexto: str,
    analise_tomador: str,
    avaliacao_especialista: str | None = None,
    analise_comparativa: str | None = None,
    documentos: str = "",
) -> Path:
    """Persiste o relatório completo em outputs/ como .docx."""
    from core.export_docx import salvar_markdown_como_docx

    ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slug_tomador(nome_tomador)
    caminho = OUTPUTS_DIR / f"analise_{slug}_{stamp}.docx"
    conteudo = montar_markdown_completo(
        nome_tomador=nome_tomador,
        problema=problema,
        contexto=contexto,
        analise_tomador=analise_tomador,
        avaliacao_especialista=avaliacao_especialista,
        analise_comparativa=analise_comparativa,
        documentos=documentos,
    )
    return salvar_markdown_como_docx(
        caminho,
        "Analisador Organizacional — Relatório",
        conteudo,
    )


def salvar_analise_comparativa(
    nome_tomador: str,
    problema: str,
    analise_comparativa: str,
    contexto: str = "",
    documentos: str = "",
) -> Path:
    """Persiste somente a análise comparativa em outputs/ como .docx."""
    from core.export_docx import salvar_markdown_como_docx

    if not analise_comparativa or not analise_comparativa.strip():
        raise ValueError("Não há análise comparativa para salvar.")

    ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slug_tomador(nome_tomador)
    caminho = OUTPUTS_DIR / f"comparativa_{slug}_{stamp}.docx"
    partes = [
        f"**Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Tomador de Decisão:** {nome_tomador}",
        "",
        "## Problema",
        problema.strip() or "(não informado)",
        "",
        "## Contexto adicional",
        (contexto.strip() or "(nenhum)"),
        "",
    ]
    if documentos and documentos.strip():
        partes.extend(["## Documentos anexos", "", documentos.strip(), ""])
    partes.extend(
        [
            "## Análise comparativa técnica",
            "",
            analise_comparativa.strip(),
            "",
        ]
    )
    return salvar_markdown_como_docx(
        caminho,
        "Análise Comparativa Técnica",
        "\n".join(partes),
    )
