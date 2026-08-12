"""Cobertura da análise estruturada: quanto da informação necessária veio da reunião.

Se menos de 50% dos slots esperados forem preenchidos com conteúdo real, a
reunião provavelmente não cabe no molde (contexto, temas, decisões, ações, pauta).
"""

from __future__ import annotations

from typing import Any

from modulos.ata_maker.acoes import Acao
from modulos.ata_maker.decisoes import Decisao
from modulos.ata_maker.levantamento import (
    CHAVES,
    NAO_MENCIONADO,
    campo_vazio,
)
from modulos.ata_maker.proxima_reuniao import ItemPauta

LIMITE_COBERTURA = 0.5

AVISO_ESTRUTURA_INADEQUADA = (
    "A estrutura desta reunião não cabe à análise estruturada: "
    "menos de 50% das informações necessárias foram recuperadas"
)


def _eh_ausencia(valor: Any) -> bool:
    if valor is None:
        return True
    if isinstance(valor, str):
        t = valor.strip().casefold()
        return (
            not t
            or t == NAO_MENCIONADO.casefold()
            or t in {"não informado", "nao informado", "n/a", "-", "nenhum", "nenhuma"}
            or t.startswith("[")
            and "não" in t
        )
    return campo_vazio(valor)


def mensagem_cobertura(preenchidos: int, total: int) -> str:
    pct = (preenchidos / total) if total else 0.0
    return f"Cobertura estruturada: {preenchidos}/{total} ({pct:.0%})"


def aviso_se_baixa(preenchidos: int, total: int) -> str | None:
    if total <= 0:
        return None
    if (preenchidos / total) < LIMITE_COBERTURA:
        pct = preenchidos / total
        return (
            f"{AVISO_ESTRUTURA_INADEQUADA} "
            f"({preenchidos}/{total}, {pct:.0%})."
        )
    return None


def cobertura_levantamento(dados: dict[str, Any] | None) -> tuple[int, int]:
    """Os 10 campos do levantamento — cada um preenchido conta 1."""
    d = dados or {}
    total = len(CHAVES)
    preenchidos = sum(1 for k in CHAVES if not _eh_ausencia(d.get(k)))
    return preenchidos, total


def cobertura_resumo_decisoes(
    contexto: str,
    temas: list[dict[str, str]],
    decisoes: list[Decisao],
) -> tuple[int, int]:
    """Contexto + temas (+ por decisão: enunciado, critério, âncora)."""
    preenchidos = 0
    total = 2
    if not _eh_ausencia(contexto):
        preenchidos += 1
    temas_reais = [
        t
        for t in temas
        if isinstance(t, dict) and not _eh_ausencia(t.get("tema"))
    ]
    if temas_reais:
        preenchidos += 1
    for d in decisoes:
        total += 3
        if d.enunciado and not _eh_ausencia(d.enunciado):
            preenchidos += 1
        if d.tem_criterio:
            preenchidos += 1
        if d.ancora and d.ancora not in {"", "??:??", "[t=??:??]"}:
            preenchidos += 1
    return preenchidos, total


def cobertura_pontos_acao(
    acoes: list[Acao],
    levantamento: dict[str, Any] | None = None,
) -> tuple[int, int]:
    """Por ação: descrição, dono, prazo, âncora. Sem tarefas esperadas → 1/1."""
    lev = levantamento or {}
    esperava = not _eh_ausencia(lev.get("tarefas"))
    if not acoes:
        if esperava:
            n = len(lev["tarefas"]) if isinstance(lev.get("tarefas"), list) else 1
            return 0, max(1, n)
        return 1, 1

    preenchidos = 0
    total = 0
    for a in acoes:
        total += 4
        if a.descricao and not _eh_ausencia(a.descricao):
            preenchidos += 1
        if a.dono and not _eh_ausencia(a.dono):
            preenchidos += 1
        if a.prazo is not None or (
            a.prazo_expressao and not _eh_ausencia(a.prazo_expressao)
        ):
            preenchidos += 1
        if a.ancora and a.ancora not in {"", "??:??", "[t=??:??]"}:
            preenchidos += 1
    return preenchidos, total


def cobertura_proxima_reuniao(
    itens: list[ItemPauta],
    *,
    data_ok: bool,
) -> tuple[int, int]:
    """Data + por item: assunto, objetivo, dono, minutos."""
    preenchidos = 1 if data_ok else 0
    total = 1
    if not itens:
        total += 1
        return preenchidos, total
    for item in itens:
        total += 4
        if item.assunto and not _eh_ausencia(item.assunto):
            preenchidos += 1
        if item.objetivo and not _eh_ausencia(item.objetivo):
            preenchidos += 1
        if item.dono and not _eh_ausencia(item.dono):
            preenchidos += 1
        if item.minutos and item.minutos > 0:
            preenchidos += 1
    return preenchidos, total


def aplicar_cobertura(
    avisos: list[str],
    markdown: str,
    preenchidos: int,
    total: int,
) -> tuple[list[str], str]:
    """Anexa métrica e, se < 50%, o aviso de estrutura inadequada no topo."""
    novos = list(avisos)
    novos.append(mensagem_cobertura(preenchidos, total))
    aviso = aviso_se_baixa(preenchidos, total)
    if aviso:
        novos.insert(0, aviso)
        markdown = f"> **Aviso:** {aviso}\n\n{markdown}"
    return novos, markdown
