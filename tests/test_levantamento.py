"""Testes do levantamento de 10 campos.

    python -m tests.test_levantamento

Trava a regra central: nenhum dos 10 campos pode sumir, e campo sem conteúdo é
declarado como não mencionado — nunca preenchido por conta própria.
"""

from __future__ import annotations

import sys

from modulos.ata_maker.levantamento import (
    CAMPOS,
    CHAVES,
    NAO_MENCIONADO,
    esqueleto_levantamento,
    extrair_mencoes_objetivas,
    levantamento_para_markdown,
    normalizar_levantamento,
    preencher_deterministico,
    validar_levantamento,
)
from modulos.ata_maker.normalizacao import segmentar_turnos

AMOSTRA = """Alinhamento - 2026/07/15 09:00 GMT-03:00 - Recording

0:00
o cliente abriu 47 tickets esse mês e a gente respondeu 12
2:30
>> mandei o relatório por e-mail para contato@cliente.com.br ontem
5:00
>> o contrato prevê SLA de 24 horas e o valor é R$ 15.000 por mês
7:15
>> a satisfação caiu 30% segundo a pesquisa, tá tudo em https://exemplo.com/painel
9:00
>> o Murilo cuida dessa parte mas não pôde vir hoje
"""

NOMES = ["Murilo", "Rogerio", "Cristian"]

_falhas: list[str] = []


def checar(condicao: bool, descricao: str) -> None:
    if condicao:
        print(f"  ok   {descricao}")
    else:
        print(f"  FALHA {descricao}")
        _falhas.append(descricao)


def test_esqueleto() -> None:
    print("esqueleto dos 10 campos")
    esq = esqueleto_levantamento()
    checar(len(CAMPOS) == 10, f"são 10 campos definidos (obtido: {len(CAMPOS)})")
    checar(list(esq.keys()) == CHAVES, "esqueleto tem todos os campos, na ordem")
    checar(
        all(v == NAO_MENCIONADO for v in esq.values()),
        "todos começam declarados como não mencionados",
    )
    esperados = {
        "objetivo", "participantes", "decisoes", "tarefas", "responsaveis",
        "prazos", "pendencias", "proximos_passos", "riscos", "informacoes",
    }
    checar(set(CHAVES) == esperados, "os campos são exatamente os dez pedidos")


def test_nada_some() -> None:
    print("nenhum campo some")
    parcial = {"decisoes": ["definir dono da conta"]}
    completo = normalizar_levantamento(parcial)
    checar(len(completo) == 10, "dicionário parcial vira completo")
    checar(
        completo["prazos"] == NAO_MENCIONADO,
        "campo ausente vira 'não mencionado', não some",
    )
    checar(completo["decisoes"] == ["definir dono da conta"], "conteúdo real é preservado")

    vazios = {c: v for c, v in zip(CHAVES, ([], "", None, [], "", None, [], "", None, []))}
    limpo = normalizar_levantamento(vazios)
    checar(
        all(v == NAO_MENCIONADO for v in limpo.values()),
        "lista vazia, string vazia e None viram 'não mencionado'",
    )

    com_lixo = normalizar_levantamento({"campo_inventado": "x", "objetivo": "alinhar"})
    checar("campo_inventado" not in com_lixo, "campo fora do schema é descartado")


def test_validacao() -> None:
    print("validação")
    checar(validar_levantamento(esqueleto_levantamento()) == [], "esqueleto é válido")

    faltando = {"objetivo": "alinhar"}
    problemas = validar_levantamento(faltando)
    checar(
        any("campos ausentes" in p for p in problemas),
        "campo faltando é reportado",
    )

    vazio_indevido = esqueleto_levantamento() | {"decisoes": []}
    checar(
        any("não foi declarado" in p for p in validar_levantamento(vazio_indevido)),
        "lista vazia sem declaração é reportada",
    )


def test_mencoes_objetivas() -> None:
    print("menções objetivas")
    turnos = segmentar_turnos(AMOSTRA)
    mencoes = extrair_mencoes_objetivas(turnos)
    valores = {m["valor"].lower() for m in mencoes}
    tipos = {m["tipo"] for m in mencoes}

    checar(any("exemplo.com" in v for v in valores), "link é capturado")
    checar(any("contato@cliente.com.br" == v for v in valores), "e-mail é capturado")
    checar(any("r$ 15.000" in v for v in valores), "valor em reais é capturado")
    checar("30 %" in valores or "30%" in valores, "percentual é capturado")
    checar(any(v.startswith("contrato") for v in valores), "documento citado é capturado")
    checar("47" in valores, "quantidade citada é capturada")
    checar(
        all(m["ancora"] and m["ancora"] != "??:??" for m in mencoes),
        "toda menção carrega âncora",
    )
    checar("número" in tipos and "link" in tipos, "menções são tipadas")
    checar(
        all(len(m["valor"].split()) <= 5 for m in mencoes if m["tipo"] == "documento"),
        "documento captura o termo, não a frase inteira",
    )
    # Guardrails: sem palavra solta e sem fragmento de relógio.
    checar(
        not any(v in {"contrato", "chamado", "relatório", "relatorio", "ticket"} for v in valores),
        "palavra-chave de documento sozinha é rejeitada",
    )
    checar(
        not any(m["tipo"] == "número" and m["valor"] in {"00", "02", "30", "05", "07", "09", "15"} for m in mencoes),
        "fragmentos de timestamp não viram número",
    )

    # Mesmo documento qualificado repetido → uma menção com contagem.
    repetido = segmentar_turnos(
        "0:00\n>> abri o ticket 882 ontem\n1:00\n>> respondi o ticket 882 hoje\n"
    )
    achados = extrair_mencoes_objetivas(repetido)
    tickets = [m for m in achados if "ticket 882" in m["valor"].lower()]
    checar(len(tickets) == 1, f"termo repetido aparece uma vez (obtido: {len(tickets)})")
    checar(tickets and tickets[0]["ocorrencias"] == 2, "a repetição vira contagem")
    checar(tickets and tickets[0]["ancora"] == "0:00", "guarda a primeira âncora")

    # Timestamps no texto bruto não devem gerar dezenas de 'número · NN'.
    so_relogio = segmentar_turnos(
        "0:00\nalguém falou\n0:15\noutra fala\n1:30\nmais uma\n2:05\nfim\n"
    )
    lixo = extrair_mencoes_objetivas(so_relogio)
    checar(lixo == [], "só timestamps/falas vazias → nenhuma menção")


def test_preenchimento_deterministico() -> None:
    print("preenchimento determinístico")
    dados = preencher_deterministico(AMOSTRA, NOMES)
    checar(len(dados) == 10, "devolve os 10 campos")
    checar(
        isinstance(dados["informacoes"], list) and dados["informacoes"],
        "informações importantes vêm preenchidas do texto",
    )
    checar(
        dados["objetivo"] == NAO_MENCIONADO,
        "objetivo não é adivinhado — fica para a leitura da skill",
    )
    checar(
        dados["decisoes"] == NAO_MENCIONADO and dados["prazos"] == NAO_MENCIONADO,
        "campos interpretativos não são preenchidos por regra",
    )
    participantes = dados["participantes"]
    checar(
        isinstance(participantes, dict) and "presentes" in participantes,
        "participantes trazem presentes e citados",
    )
    checar(
        "Murilo" in (participantes.get("citados_sem_falar") or []),
        "quem é citado sem falar entra como ausente",
    )

    vazio = preencher_deterministico("", NOMES)
    checar(
        all(v == NAO_MENCIONADO for v in vazio.values()),
        "sem transcrição, nada é preenchido",
    )


def test_partir_do_artefato() -> None:
    print("preencher a partir do artefato processado")
    from modulos.ata_maker.levantamento import preencher_do_processamento
    from modulos.ata_maker.processamento import processar

    artefato = processar(AMOSTRA, NOMES, origem="amostra.txt")
    do_artefato = preencher_do_processamento(artefato, NOMES)
    do_texto = preencher_deterministico(AMOSTRA, NOMES)

    checar(
        do_artefato["participantes"] == do_texto["participantes"],
        "artefato e texto bruto concordam sobre os participantes",
    )
    checar(
        len(do_artefato["informacoes"]) == len(do_texto["informacoes"]),
        "as menções objetivas são as mesmas pelos dois caminhos",
    )

    # O erro que a validação da VLI pegou: passar o markdown ancorado como se
    # fosse transcrição faz o parser perder todos os falantes.
    ancorado = artefato["texto_ancorado"]
    pelo_markdown = preencher_deterministico(ancorado, NOMES)
    checar(
        do_artefato["participantes"] != pelo_markdown["participantes"],
        "reparsear o markdown ancorado dá resultado pior — por isso existe "
        "preencher_do_processamento",
    )


def test_markdown() -> None:
    print("markdown")
    md = levantamento_para_markdown({"decisoes": ["trocar o fluxo de tickets"]})
    for _chave, rotulo, _ajuda in CAMPOS:
        checar(f"### {rotulo}" in md, f"seção '{rotulo}' está presente")
    checar(
        md.count(NAO_MENCIONADO) == 9,
        f"os 9 campos sem conteúdo saem declarados (obtido: {md.count(NAO_MENCIONADO)})",
    )
    checar("trocar o fluxo de tickets" in md, "conteúdo real aparece")

    md_vazio = levantamento_para_markdown(None)
    checar(
        md_vazio.count(NAO_MENCIONADO) == 10,
        "levantamento vazio ainda lista as 10 seções",
    )


def main() -> int:
    for teste in (
        test_esqueleto,
        test_nada_some,
        test_validacao,
        test_mencoes_objetivas,
        test_preenchimento_deterministico,
        test_partir_do_artefato,
        test_markdown,
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
