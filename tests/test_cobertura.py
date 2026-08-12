"""Testes da cobertura estruturada (< 50% → aviso)."""

from __future__ import annotations

import sys

from modulos.ata_maker.acoes import Acao
from modulos.ata_maker.cobertura import (
    AVISO_ESTRUTURA_INADEQUADA,
    aplicar_cobertura,
    aviso_se_baixa,
    cobertura_levantamento,
    cobertura_pontos_acao,
    cobertura_proxima_reuniao,
    cobertura_resumo_decisoes,
)
from modulos.ata_maker.decisoes import Decisao, SEM_CRITERIO
from modulos.ata_maker.levantamento import NAO_MENCIONADO, esqueleto_levantamento
from modulos.ata_maker.proxima_reuniao import ItemPauta

_falhas: list[str] = []


def checar(condicao: bool, desc: str) -> None:
    if condicao:
        print(f"  ok   {desc}")
    else:
        print(f"  FALHA {desc}")
        _falhas.append(desc)


def test_levantamento() -> None:
    print("cobertura levantamento")
    vazio = esqueleto_levantamento()
    p, t = cobertura_levantamento(vazio)
    checar(p == 0 and t == 10, f"esqueleto vazio = 0/10 (obtido {p}/{t})")
    checar(aviso_se_baixa(p, t) is not None, "0/10 dispara aviso")

    parcial = dict(vazio)
    for k in list(vazio)[:4]:
        parcial[k] = "conteúdo real"
    p2, t2 = cobertura_levantamento(parcial)
    checar(p2 == 4 and t2 == 10, f"4 campos = 4/10 (obtido {p2}/{t2})")
    checar(aviso_se_baixa(p2, t2) is not None, "40% dispara aviso")

    for k in list(vazio)[4:6]:
        parcial[k] = "mais"
    p3, _ = cobertura_levantamento(parcial)
    checar(aviso_se_baixa(p3, 10) is None, "60% não dispara aviso")


def test_resumo() -> None:
    print("cobertura resumo decisões")
    p, t = cobertura_resumo_decisoes(NAO_MENCIONADO, [{"tema": NAO_MENCIONADO}], [])
    checar(p == 0 and t == 2, f"só ausência = 0/2 (obtido {p}/{t})")
    checar(aviso_se_baixa(p, t) is not None, "0/2 dispara aviso")

    d = Decisao(
        enunciado="priorizar tickets",
        criterio=SEM_CRITERIO,
        ancora="[t=1:00]",
    )
    p2, t2 = cobertura_resumo_decisoes(
        "Alinhar prioridade de suporte",
        [{"tema": "Tickets", "inicio": "0:00", "fim": "10:00"}],
        [d],
    )
    # contexto+temas+enunciado+ancora = 4; critério falta → 4/5 = 80%
    checar(p2 == 4 and t2 == 5, f"decisão parcial = 4/5 (obtido {p2}/{t2})")
    checar(aviso_se_baixa(p2, t2) is None, "80% ok")


def test_acoes_e_pauta() -> None:
    print("cobertura ações e pauta")
    p, t = cobertura_pontos_acao([], {"tarefas": NAO_MENCIONADO})
    checar((p, t) == (1, 1), "sem tarefas esperadas → 1/1")

    p2, t2 = cobertura_pontos_acao([], {"tarefas": ["fazer X"]})
    checar(p2 == 0 and t2 >= 1, "tarefas no lev. sem ações → baixa")
    checar(aviso_se_baixa(p2, t2) is not None, "dispara aviso")

    acao = Acao(descricao="fazer X", dono="Ana", ancora="[t=2:00]", prazo_expressao="sexta")
    p3, t3 = cobertura_pontos_acao([acao], {"tarefas": ["fazer X"]})
    checar(aviso_se_baixa(p3, t3) is None, "ação completa ≥ 50%")

    p4, t4 = cobertura_proxima_reuniao([], data_ok=False)
    checar(aviso_se_baixa(p4, t4) is not None, "pauta vazia sem data → aviso")

    item = ItemPauta(assunto="Revisar SLA", objetivo="fechar regra", dono="Bob", minutos=10)
    p5, t5 = cobertura_proxima_reuniao([item], data_ok=True)
    checar(aviso_se_baixa(p5, t5) is None, "item completo ok")


def test_aplicar() -> None:
    print("aplicar cobertura no markdown")
    avisos, md = aplicar_cobertura([], "# Título", 1, 10)
    checar(any(AVISO_ESTRUTURA_INADEQUADA in a for a in avisos), "aviso na lista")
    checar(md.startswith("> **Aviso:**"), "aviso no topo do markdown")
    checar(any(a.startswith("Cobertura estruturada") for a in avisos), "métrica presente")


def main() -> int:
    for t in (test_levantamento, test_resumo, test_acoes_e_pauta, test_aplicar):
        t()
    print()
    if _falhas:
        print(f"{len(_falhas)} falha(s)")
        return 1
    print("todos os testes passaram")
    return 0


if __name__ == "__main__":
    sys.exit(main())
