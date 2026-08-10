"""Módulo Ata Maker embarcado no BriefBoard - Gedanken."""

from modulos.ata_maker.engine import AtaGerada, gerar_ata, gerar_ata_completa, gerar_ata_prompt

__all__ = [
    "AtaGerada",
    "gerar_ata",
    "gerar_ata_prompt",
    "gerar_ata_completa",
]
