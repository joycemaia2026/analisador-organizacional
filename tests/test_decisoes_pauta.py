"""Testes das skills 4 e 5: decisões com critério, e pauta que cabe no tempo.

    python -m tests.test_decisoes_pauta
"""

from __future__ import annotations

import sys
from datetime import date

from modulos.ata_maker.decisoes import (
    INDEFINIDO,
    IRREVERSIVEL,
    REVERSIVEL,
    SEM_CRITERIO,
    Decisao,
    decisoes_para_markdown,
    relatorio_decisoes,
    validar_decisoes,
)
from modulos.ata_maker.normalizacao import blocos_de_tempo, segmentar_turnos
from modulos.ata_maker.proxima_reuniao import (
    ORIGEM_ADIADO,
    ORIGEM_PERGUNTA,
    ItemPauta,
    pauta_para_markdown,
    relatorio_pauta,
    resolver_data,
    sugerir_participantes,
    tempo_total,
    validar_pauta,
)

REUNIAO = date(2026, 7, 15)

_falhas: list[str] = []


def checar(condicao: bool, descricao: str) -> None:
    if condicao:
        print(f"  ok   {descricao}")
    else:
        print(f"  FALHA {descricao}")
        _falhas.append(descricao)


# --------------------------------------------------------------------------- #
# Skill 4 — decisões
# --------------------------------------------------------------------------- #


def test_decisao_sem_criterio() -> None:
    print("decisão sem critério")
    d = Decisao("Rogério assume a conta da VLI", ancora="12:26", sustentada_por="Cristian")
    checar(d.criterio == SEM_CRITERIO, "critério ausente é declarado, não vazio")
    checar(not d.tem_criterio, "tem_criterio identifica a falta")

    tipos = [a.tipo for a in validar_decisoes([d])]
    checar("sem_criterio" in tipos, "falta de critério vira aviso")

    com = Decisao(
        "Rogério assume a conta da VLI",
        criterio="é quem já tinha relação com o cliente antes dos tickets",
        ancora="12:26",
        sustentada_por="Cristian",
        tipo=REVERSIVEL,
    )
    checar(
        "sem_criterio" not in [a.tipo for a in validar_decisoes([com])],
        "decisão com critério não gera o aviso",
    )


def test_irreversivel_tem_prioridade() -> None:
    print("irreversível sem critério é o pior caso")
    decisoes = [
        Decisao("cancelar o contrato do fornecedor", ancora="30:00",
                sustentada_por="Monica", tipo=IRREVERSIVEL),
        Decisao("mudar a cor do botão", ancora="31:00",
                sustentada_por="Monica", tipo=REVERSIVEL),
    ]
    avisos = validar_decisoes(decisoes)
    checar(avisos[0].tipo == "irreversivel_sem_criterio", "aparece em primeiro lugar")
    checar(avisos[0].gravidade == "alta", "é classificado como gravidade alta")
    checar(
        "cancelar o contrato do fornecedor"[:40] in avisos[0].decisoes,
        "aponta a decisão certa",
    )
    # A reversível sem critério não é engolida pelo aviso da irreversível.
    checar(
        any(a.tipo == "sem_criterio" for a in avisos),
        "a reversível sem critério continua sendo reportada",
    )


def test_lacunas_de_decisao() -> None:
    print("lacunas de decisão")
    d = Decisao("algo foi definido")
    tipos = [a.tipo for a in validar_decisoes([d])]
    for esperado in ("sem_criterio", "sem_ancora", "sem_responsavel", "reversibilidade_indefinida"):
        checar(esperado in tipos, f"'{esperado}' é reportado")

    completa = Decisao(
        "abrir canal semanal com o cliente",
        criterio="o cliente reclamou de falta de retorno; canal direto custa 1h/semana",
        alternativas_descartadas=["manter só o suporte por ticket"],
        sustentada_por="Gabriel Pereira",
        ancora="12:26",
        tipo=REVERSIVEL,
    )
    checar(validar_decisoes([completa]) == [], "decisão completa não gera aviso")
    checar(
        relatorio_decisoes([completa]).startswith("Todas as decisões"),
        "relatório confirma quando está tudo registrado",
    )


def test_markdown_decisoes() -> None:
    print("markdown de decisões")
    checar(
        decisoes_para_markdown([]) == "Nenhuma decisão formalizada nesta reunião.",
        "lista vazia é declarada, não some",
    )
    d = Decisao(
        "priorizar os tickets por Pareto",
        criterio="resolver 3 ou 4 já mostra reação rápida ao cliente",
        alternativas_descartadas=["resolver na ordem de abertura"],
        sustentada_por="Gabriel Pereira",
        ancora="[t=2:40]",
        tipo=REVERSIVEL,
    )
    md = decisoes_para_markdown([d])
    checar("Critério:" in md, "critério aparece logo abaixo do enunciado")
    checar("Alternativas descartadas" in md, "alternativas aparecem")
    checar("fácil de desfazer" in md, "natureza é traduzida para português")
    checar("[t=2:40]" in md, "âncora aparece")

    sem_tipo = Decisao("x", tipo="chute_invalido")
    checar(
        sem_tipo.para_dict()["tipo"] == INDEFINIDO,
        "tipo fora do vocabulário vira indefinido",
    )


def test_blocos_de_tempo() -> None:
    print("blocos de tempo para ancorar temas")
    texto = (
        "0:00\n>> falando do cliente\n"
        "3:00\n>> ainda do cliente\n"
        "12:00\n>> agora sobre contratação\n"
        "25:00\n>> e sobre o roadmap\n"
    )
    blocos = blocos_de_tempo(segmentar_turnos(texto), minutos=10)
    checar(len(blocos) == 3, f"três janelas de 10 min (obtido: {len(blocos)})")
    checar(blocos[0]["inicio"] == "0:00" and blocos[0]["fim"] == "10:00", "primeira janela")
    checar(blocos[0]["total_turnos"] == 2, "agrupa os turnos da mesma janela")
    checar(blocos[2]["inicio"] == "20:00", "terceira janela começa em 20:00")
    checar(blocos_de_tempo([]) == [], "sem turnos, nenhuma janela")


# --------------------------------------------------------------------------- #
# Skill 5 — próxima reunião
# --------------------------------------------------------------------------- #


def test_pauta_estourada() -> None:
    print("pauta que não cabe no tempo")
    itens = [
        ItemPauta(f"assunto {i}", objetivo="decidir", dono="Rogerio", minutos=10)
        for i in range(4)
    ]
    checar(tempo_total(itens) == 40, "soma os minutos")

    avisos = validar_pauta(itens, duracao_min=30)
    checar(
        any(a.tipo == "pauta_estourada" for a in avisos),
        "40 min de pauta em reunião de 30 min é sinalizado",
    )

    cabe = itens[:2]  # 20 min, teto útil de 30 min é 24
    checar(
        not any(a.tipo == "pauta_estourada" for a in validar_pauta(cabe, duracao_min=30)),
        "pauta dentro do teto não gera aviso",
    )
    # Folga obrigatória: 28 min numa reunião de 30 ainda estoura o teto de 80%.
    apertada = [ItemPauta("único", objetivo="decidir", dono="X", minutos=28)]
    checar(
        any(a.tipo == "pauta_estourada" for a in validar_pauta(apertada, duracao_min=30)),
        "pauta sem folga é sinalizada mesmo cabendo no relógio",
    )


def test_lacunas_de_pauta() -> None:
    print("lacunas de pauta")
    checar(
        validar_pauta([])[0].tipo == "pauta_vazia",
        "pauta vazia é declarada",
    )
    item = ItemPauta("falar sobre o cliente", minutos=0)
    tipos = [a.tipo for a in validar_pauta([item], duracao_min=60)]
    for esperado in ("sem_objetivo", "sem_dono", "sem_tempo"):
        checar(esperado in tipos, f"'{esperado}' é reportado")

    bom = ItemPauta(
        "prazo da homologação", objetivo="definir data com o fornecedor",
        dono="Lindia", minutos=10, origem=ORIGEM_PERGUNTA, ancora="[t=33:15]",
    )
    checar(
        relatorio_pauta([bom], duracao_min=30).startswith("Pauta cabe"),
        "pauta boa não inventa problema",
    )


def test_participantes() -> None:
    print("quem precisa estar")
    participantes = sugerir_participantes(
        donos_de_itens=["Rogerio", "[dono não definido]", "Lindia"],
        citados_ausentes=["Victor", "Tamara", "Rogerio"],
        presentes=["Tamara"],
    )
    nomes = [p.nome for p in participantes]

    checar("[dono não definido]" not in nomes, "placeholder não vira participante")
    checar("Tamara" not in nomes, "quem já estava presente não é sugerido de novo")
    checar("Victor" in nomes, "citado ausente é sugerido")

    por_nome = {p.nome: p for p in participantes}
    checar(por_nome["Rogerio"].obrigatorio, "dono de item é obrigatório")
    checar(
        por_nome["Rogerio"].motivo == "responsável por item da pauta",
        "dono de item ganha precedência sobre 'citado ausente'",
    )
    checar(not por_nome["Victor"].obrigatorio, "citado ausente é sugerido, não obrigatório")
    checar(
        [p.obrigatorio for p in participantes] == sorted(
            [p.obrigatorio for p in participantes], reverse=True
        ),
        "obrigatórios vêm primeiro",
    )


def test_data_da_proxima() -> None:
    print("data da próxima reunião")
    r = resolver_data("semana que vem", REUNIAO)
    checar(r["data"] == "2026-07-22", "resolve sobre a data da reunião atual")
    checar("semana que vem" in r["texto"], "mantém a expressão original")

    vago = resolver_data("a gente marca depois", REUNIAO)
    checar(vago["data"] is None, "expressão vaga não vira data")
    checar(vago["texto"] == "[data não combinada]", "ausência é declarada")


def test_markdown_pauta() -> None:
    print("markdown da pauta")
    itens = [
        ItemPauta("retorno do fornecedor", objetivo="definir prazo", dono="Lindia",
                  minutos=10, origem=ORIGEM_ADIADO, material="planilha de homologações"),
    ]
    participantes = sugerir_participantes(["Lindia"], ["Victor"], [])
    md = pauta_para_markdown(
        itens, participantes, data_texto="2026-07-22 (semana que vem)", duracao_min=30
    )
    checar("**Data:** 2026-07-22" in md, "cabeçalho traz a data")
    checar("Pauta:** 10 min" in md, "cabeçalho traz o tempo somado")
    checar("assunto adiado" in md, "origem é traduzida")
    checar("Materiais a preparar" in md, "materiais viram seção própria")
    checar("Quem precisa estar" in md, "participantes obrigatórios aparecem")
    checar("Sugeridos" in md, "sugeridos aparecem separados")

    vazia = pauta_para_markdown([], None, duracao_min=30)
    checar("Nenhum assunto pendente" in vazia, "pauta vazia é declarada no markdown")


def main() -> int:
    for teste in (
        test_decisao_sem_criterio,
        test_irreversivel_tem_prioridade,
        test_lacunas_de_decisao,
        test_markdown_decisoes,
        test_blocos_de_tempo,
        test_pauta_estourada,
        test_lacunas_de_pauta,
        test_participantes,
        test_data_da_proxima,
        test_markdown_pauta,
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
