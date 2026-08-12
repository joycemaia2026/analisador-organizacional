"""Testes do seletor de modelo de ata e do cabeçalho factual — só stdlib.

    python -m tests.test_modelos_ata

Travam três coisas que quebram em silêncio:
1. o modelo de ata não pode vazar para o modo 'full' (substituiria o especialista de IA);
2. `## Em uma frase` precisa sobreviver, senão o handoff para a jornada 2 para de funcionar;
3. o cabeçalho da ata é medido, não estimado.
"""

from __future__ import annotations

import sys

from jornadas.jornada_ata import _extrair_resumo_ata
from modulos.ata_maker.normalizacao import bloco_fatos_reuniao, resumo_estrutural, segmentar_turnos
from modulos.ata_maker.prompts_catalog import listar_modelos_ata, load_prompt_ata

AMOSTRA = """Reunião de teste - 2026/07/15 09:00 GMT-03:00 - Recording

0:00
precisamos revisar os tickets abertos antes de sexta
5:30
>> Isso mesmo, Cristian. Eu abro a lista hoje.
12:00
>> o Murilo não pôde vir, mas ele cuida dessa parte
"""

NOMES = ["Cristian", "Murilo", "Rogerio"]

_falhas: list[str] = []


def checar(condicao: bool, descricao: str) -> None:
    if condicao:
        print(f"  ok   {descricao}")
    else:
        print(f"  FALHA {descricao}")
        _falhas.append(descricao)


def test_catalogo() -> None:
    print("catálogo de modelos (legado)")
    chaves = [c for c, _r, _d in listar_modelos_ata()]
    checar("reuniao" in chaves, f"modelo reuniao registrado (obtido: {chaves})")
    checar(
        "{{TRANSCRICAO}}" in load_prompt_ata("reuniao"),
        "template da ata tem o placeholder da transcrição",
    )
    checar(
        "{{CABECALHO_FATOS}}" in load_prompt_ata("reuniao"),
        "template da ata pede o cabeçalho factual",
    )
    checar(
        "{{LEVANTAMENTO}}" in load_prompt_ata("reuniao"),
        "template da ata usa o levantamento estruturado",
    )
    checar(
        "assertividade" in load_prompt_ata("reuniao").lower()
        or "assertiv" in load_prompt_ata("reuniao").lower(),
        "template prioriza assertividade para o leitor",
    )


def test_nao_vaza_para_modo_full() -> None:
    print("modo full segue nas personas; prompt usa ata fundida")
    import core.ata_maker_client as client

    capturado: dict = {}

    def _fake_gerar_ata(texto, **kwargs):
        capturado["via"] = "gerar_ata"
        capturado.update(kwargs)
        from modulos.ata_maker.engine import AtaGerada

        return AtaGerada(texto="x", fonte="fake")

    def _fake_fundida(texto, **kwargs):
        capturado["via"] = "fundida"
        capturado.update(kwargs)
        from modulos.ata_maker.engine import AtaGerada

        return AtaGerada(texto="fundida", fonte="fake")

    original = client.gerar_ata
    original_f = client.gerar_ata_fundida
    client.gerar_ata = _fake_gerar_ata
    client.gerar_ata_fundida = _fake_fundida
    try:
        client.gerar_ata_de_transcricao("x", modo="full", modelo_ata="reuniao")
        checar(capturado.get("via") == "gerar_ata", "modo full chama gerar_ata (personas)")
        checar(capturado.get("modo") == "full", "repassa modo full")
        capturado.clear()
        client.gerar_ata_de_transcricao("x", modo="prompt", source_filename="a.txt")
        checar(capturado.get("via") == "fundida", "modo prompt chama ata fundida")
        checar(capturado.get("stem") == "a", "stem vem do filename")
    finally:
        client.gerar_ata = original
        client.gerar_ata_fundida = original_f

def test_handoff_jornada_2() -> None:
    print("handoff para a jornada 2")
    ata = (
        "# Ata — Reunião de teste\n\n"
        "| Reunião | Data |\n|---|---|\n\n"
        "## Em uma frase\n"
        "O time revisou os tickets da VLI e definiu quem abre a lista.\n\n"
        "## Decisões\n- nada formalizado\n"
    )
    resumo = _extrair_resumo_ata(ata)
    checar(
        resumo.startswith("O time revisou os tickets"),
        f"'## Em uma frase' é encontrado pelo extrator (obtido: {resumo[:40]!r})",
    )


def test_cabecalho_factual() -> None:
    print("cabeçalho factual")
    turnos = segmentar_turnos(AMOSTRA)
    resumo = resumo_estrutural(turnos, NOMES)
    checar(
        resumo["duracao_seg"] == 720,
        f"duração vem do último timestamp (obtido: {resumo['duracao_seg']})",
    )
    checar(
        "pelo menos" in resumo["duracao_texto"],
        "duração é declarada como piso, não como valor exato",
    )
    checar(
        "Murilo" in resumo["citados_sem_falar"],
        "quem é citado mas não fala entra como ausente citado",
    )
    checar(
        "Murilo" not in resumo["participantes"],
        "citado ausente não é contado como participante",
    )

    bloco = bloco_fatos_reuniao(AMOSTRA, NOMES)
    checar("2026-07-15T09:00" in bloco, "data da reunião entra no bloco")
    checar("GMT-03:00" in bloco, "fuso entra no bloco")
    checar(
        "Citados que não falaram: Murilo" in bloco,
        "bloco declara os citados ausentes",
    )

    vazio = bloco_fatos_reuniao("", NOMES)
    checar(
        "não informada" in vazio and "nenhum identificado" in vazio,
        "sem transcrição, o bloco declara ausência em vez de inventar",
    )

    # O ASR escreve 'Cristiam'; o cabeçalho tem que reconhecer a mesma pessoa.
    com_erro = AMOSTRA.replace("Cristian", "Cristiam")
    bloco_erro = bloco_fatos_reuniao(com_erro, NOMES)
    checar(
        "Cristiam" not in bloco_erro,
        "nome errado do ASR não vaza para o cabeçalho",
    )


def main() -> int:
    for teste in (
        test_catalogo,
        test_nao_vaza_para_modo_full,
        test_handoff_jornada_2,
        test_cabecalho_factual,
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
