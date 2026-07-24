"""Facade do módulo Ata Maker (código local, sem HTTP externo)."""

from __future__ import annotations

from dataclasses import dataclass

from core.openai_client import get_api_key, get_model
from modulos.ata_maker.engine import AtaGerada, gerar_ata
from modulos.ata_maker.prompts_catalog import PERSONA_OPCOES


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
        message="Configure OPENAI_API_KEY no .env para usar o módulo Ata.",
    )


def gerar_ata_de_transcricao(
    texto: str,
    *,
    source_filename: str | None = None,
    modo: str = "prompt",
    personas: list[str] | None = None,
    incluir_nlp: bool = True,
    especificacoes: str = "",
) -> AtaGerada:
    _ = source_filename
    return gerar_ata(
        texto,
        modo=modo,
        personas=personas,
        incluir_nlp=incluir_nlp,
        especificacoes=especificacoes,
    )
