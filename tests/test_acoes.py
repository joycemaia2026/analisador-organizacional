"""Testes de resolução de prazo em pt-BR e de checagem de realismo.

    python -m tests.test_acoes
"""

from __future__ import annotations

import sys
from datetime import date

from modulos.ata_maker.acoes import (
    Acao,
    carga_semanal,
    dias_uteis,
    relatorio_realismo,
    resolver_prazo,
    validar_acoes,
)

# Quarta-feira, 15/07/2026 — a reunião da VLI.
REUNIAO = date(2026, 7, 15)

_falhas: list[str] = []


def checar(condicao: bool, descricao: str) -> None:
    if condicao:
        print(f"  ok   {descricao}")
    else:
        print(f"  FALHA {descricao}")
        _falhas.append(descricao)


def test_prazos_relativos() -> None:
    print("prazos relativos em pt-BR")
    casos = [
        ("hoje", date(2026, 7, 15)),
        ("amanhã", date(2026, 7, 16)),
        ("depois de amanhã", date(2026, 7, 17)),
        ("até sexta", date(2026, 7, 17)),
        ("na próxima sexta", date(2026, 7, 24)),
        ("segunda que vem", date(2026, 7, 27)),
        ("semana que vem", date(2026, 7, 22)),
        ("em 3 dias", date(2026, 7, 18)),
        ("em 2 semanas", date(2026, 7, 29)),
        ("até o fim do mês", date(2026, 7, 31)),
        ("fim da semana", date(2026, 7, 17)),
        ("mês que vem", date(2026, 8, 15)),
        ("dia 20", date(2026, 7, 20)),
        ("dia 20 de agosto", date(2026, 8, 20)),
        ("até 18/07", date(2026, 7, 18)),
        ("2026-08-01", date(2026, 8, 1)),
    ]
    for expressao, esperado in casos:
        obtido = resolver_prazo(expressao, REUNIAO).data
        checar(obtido == esperado, f"'{expressao}' → {esperado} (obtido: {obtido})")


def test_prazo_vago_nao_vira_data() -> None:
    print("prazo vago não vira data")
    for expressao in ("o quanto antes", "assim que der", "urgente", "", "logo"):
        r = resolver_prazo(expressao, REUNIAO)
        checar(r.data is None, f"'{expressao}' fica sem data")
        checar(
            r.texto == "[prazo não definido]",
            f"'{expressao}' é declarado indefinido na ata",
        )


def test_texto_do_prazo() -> None:
    print("formato do prazo")
    r = resolver_prazo("até sexta", REUNIAO)
    checar(
        r.texto == "2026-07-17 (até sexta)",
        f"mantém a expressão original junto da data (obtido: {r.texto})",
    )


def test_dias_uteis() -> None:
    print("dias úteis")
    # Quarta a sexta da mesma semana.
    checar(dias_uteis(REUNIAO, date(2026, 7, 17)) == 3, "quarta a sexta são 3 dias úteis")
    # Quarta à segunda seguinte: pula o fim de semana.
    checar(dias_uteis(REUNIAO, date(2026, 7, 20)) == 4, "fim de semana não é contado")
    checar(dias_uteis(date(2026, 7, 20), REUNIAO) == 0, "intervalo invertido é zero")


def test_sobrecarga() -> None:
    print("sobrecarga por pessoa")
    acoes = [
        Acao("mapear tickets", dono="Rogerio", prazo=date(2026, 7, 17),
             esforco_horas=6, ancora="12:00", id="A1"),
        Acao("montar relatório", dono="Rogerio", prazo=date(2026, 7, 16),
             esforco_horas=5, ancora="14:00", id="A2"),
        Acao("revisar contrato", dono="Monica", prazo=date(2026, 7, 17),
             esforco_horas=3, ancora="20:00", id="A3"),
    ]
    carga = carga_semanal(acoes)
    checar(carga["Rogerio"]["2026-S29"] == 11.0, "soma as horas do mesmo dono na semana")
    checar("Monica" in carga and carga["Monica"]["2026-S29"] == 3.0, "conta cada dono")

    tipos = [a.tipo for a in validar_acoes(acoes, REUNIAO)]
    checar("sobrecarga" in tipos, "11h numa semana de 8h vira aviso de sobrecarga")

    leves = [Acao("tarefa curta", dono="Rogerio", prazo=date(2026, 7, 17),
                  esforco_horas=4, ancora="12:00", id="B1")]
    checar(
        "sobrecarga" not in [a.tipo for a in validar_acoes(leves, REUNIAO)],
        "carga dentro da capacidade não gera aviso",
    )


def test_dependencia_invertida() -> None:
    print("dependência invertida")
    acoes = [
        Acao("levantar dados", dono="Monica", prazo=date(2026, 7, 24),
             esforco_horas=2, ancora="10:00", id="dados"),
        Acao("apresentar ao cliente", dono="Rogerio", prazo=date(2026, 7, 17),
             esforco_horas=2, depende_de=["dados"], ancora="11:00", id="apresentar"),
    ]
    avisos = validar_acoes(acoes, REUNIAO)
    checar(
        any(a.tipo == "dependencia_invertida" for a in avisos),
        "ação que vence antes da sua dependência é sinalizada",
    )

    fantasma = [
        Acao("fazer X", dono="Rogerio", prazo=date(2026, 7, 20),
             esforco_horas=1, depende_de=["nao_existe"], ancora="9:00", id="X")
    ]
    checar(
        any(a.tipo == "dependencia_inexistente" for a in validar_acoes(fantasma, REUNIAO)),
        "dependência que não está na lista é sinalizada",
    )


def test_lacunas() -> None:
    print("lacunas de dono, prazo e âncora")
    acoes = [
        Acao("alguém precisa falar com o cliente", esforco_horas=2, id="vago"),
    ]
    tipos = [a.tipo for a in validar_acoes(acoes, REUNIAO)]
    for esperado in ("sem_dono", "sem_prazo", "sem_ancora"):
        checar(esperado in tipos, f"'{esperado}' é reportado")

    passado = [
        Acao("já era", dono="Rogerio", prazo=date(2026, 7, 10),
             esforco_horas=1, ancora="5:00", id="P1")
    ]
    checar(
        "prazo_no_passado" in [a.tipo for a in validar_acoes(passado, REUNIAO)],
        "prazo anterior à reunião é sinalizado",
    )


def test_relatorio() -> None:
    print("relatório de realismo")
    ok = [
        Acao("tarefa viável", dono="Monica", prazo=date(2026, 7, 17),
             esforco_horas=3, ancora="8:00", id="OK1")
    ]
    checar(
        relatorio_realismo(ok, REUNIAO).startswith("Nenhum problema"),
        "plano viável não inventa problema",
    )
    ruim = [Acao("sem nada", id="R1")]
    checar("**sem_dono**" in relatorio_realismo(ruim, REUNIAO), "avisos saem em Markdown")


def main() -> int:
    for teste in (
        test_prazos_relativos,
        test_prazo_vago_nao_vira_data,
        test_texto_do_prazo,
        test_dias_uteis,
        test_sobrecarga,
        test_dependencia_invertida,
        test_lacunas,
        test_relatorio,
    ):
        teste()
    print()
    if _falhas:
        print(f"{len(_falhas)} falha(s):")
        for f in _falhas:
            print(f"  - {f}")
        return 1
    print("todos os testes passaram")
    return 0


if __name__ == "__main__":
    sys.exit(main())
