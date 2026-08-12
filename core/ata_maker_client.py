"""Facade do módulo Ata Maker (código local, sem HTTP externo)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from core.openai_client import get_api_key, get_model
from modulos.ata_maker.engine import AtaGerada, gerar_ata
from modulos.ata_maker.prompts_catalog import PERSONA_OPCOES, listar_modelos_ata
from modulos.ata_maker.skills_registry import SkillMeta, listar_skills
from modulos.ata_maker.skills_runner import (
    PipelineResultado,
    gerar_ata_fundida,
    rodar_pipeline,
)


@dataclass
class HealthStatus:
    online: bool
    openai_configured: bool = False
    model: str | None = None
    message: str = ""


def get_ata_maker_url() -> str:
    """Compat: módulo local (não usa URL)."""
    return "local://modulos/ata_maker"


def listar_especialistas() -> list[tuple[str, str]]:
    """Retorna [(id, rótulo), ...] dos especialistas disponíveis."""
    return list(PERSONA_OPCOES)


def listar_modelos_de_ata() -> list[tuple[str, str, str]]:
    """Compat: catálogo legado (a UI de Gerar Ata não escolhe mais modelo)."""
    return listar_modelos_ata()


def listar_skills_disponiveis() -> list[SkillMeta]:
    """Skills em `skills/` (sem ata-reuniao — fundida em Gerar Ata)."""
    return listar_skills()


def check_health() -> HealthStatus:
    key = get_api_key()
    if key:
        return HealthStatus(
            online=True,
            openai_configured=True,
            model=get_model(),
            message="Módulo ata_maker local pronto",
        )
    return HealthStatus(
        online=False,
        openai_configured=False,
        message=(
            "Configure OPENAI_API_KEY e/ou GEMINI_API_KEY no .env "
            "e escolha o provedor no topo."
        ),
    )


def gerar_ata_de_transcricao(
    texto: str,
    *,
    source_filename: str | None = None,
    modo: str = "prompt",
    personas: list[str] | None = None,
    incluir_nlp: bool = True,
    especificacoes: str = "",
    incluir_manual_voz: bool = False,
    modelo_ata: str = "reuniao",
    progress: Callable[[str], None] | None = None,
) -> AtaGerada:
    """Gera ata.

    - modo ``prompt`` (padrão): fusão assertiva = processamento + levantamento + ata
      (ex-skill ``ata-reuniao``). ``modelo_ata`` é ignorado nesta rota.
    - modo ``full``: visão de especialistas (personas).
    """
    _ = modelo_ata
    stem = Path(source_filename or "transcricao").stem or "transcricao"
    origem = Path(source_filename).name if source_filename else ""

    if modo == "full":
        return gerar_ata(
            texto,
            modo="full",
            prompt_custom=None,
            personas=personas,
            incluir_nlp=incluir_nlp,
            especificacoes=especificacoes,
            incluir_manual_voz=incluir_manual_voz,
        )

    return gerar_ata_fundida(
        texto,
        stem=stem,
        origem=origem,
        incluir_nlp=incluir_nlp,
        incluir_manual_voz=incluir_manual_voz,
        especificacoes=especificacoes,
        progress=progress,
    )


def aplicar_skills_na_transcricao(
    texto: str,
    *,
    source_filename: str | None = None,
    skills: list[str] | None = None,
    incluir_manual_voz: bool = True,
    progress: Callable[[str], None] | None = None,
) -> PipelineResultado:
    """Roda o pipeline de `skills/` (sem ata — use Gerar Ata)."""
    stem = Path(source_filename or "transcricao").stem or "transcricao"
    origem = Path(source_filename).name if source_filename else ""
    filtradas = None
    if skills is not None:
        filtradas = [
            s for s in skills if s not in {"ata-reuniao", "processamento"}
        ]
    return rodar_pipeline(
        texto,
        stem=stem,
        skills=filtradas,
        origem=origem,
        incluir_manual_voz=incluir_manual_voz,
        progress=progress,
    )
