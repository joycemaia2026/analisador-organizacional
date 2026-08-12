"""Testes do artefato de transcrição processada.

    python -m tests.test_processamento

Trava o contrato da etapa obrigatória: o artefato guarda a transcrição inteira
(não um resumo), e quem consome descobre quando ele falta ou está velho.
"""

from __future__ import annotations

import shutil
import sys

from modulos.ata_maker import processamento as proc

AMOSTRA = """Alinhamento - 2026/07/15 09:00 GMT-03:00 - Recording

0:00
precisamos revisar os tickets abertos antes de sexta
5:30
>> Isso mesmo, Cristian. Eu abro a lista hoje.
12:00
>> aqui é o Murilo, eu cuido da homologação
"""

NOMES = ["Cristian", "Murilo", "Rogerio"]
STEM = "__teste_processamento__"

_falhas: list[str] = []


def checar(condicao: bool, descricao: str) -> None:
    if condicao:
        print(f"  ok   {descricao}")
    else:
        print(f"  FALHA {descricao}")
        _falhas.append(descricao)


def limpar() -> None:
    pasta = proc.pasta_do_stem(STEM)
    if pasta.exists():
        shutil.rmtree(pasta)


def test_processar() -> None:
    print("processar")
    dados = proc.processar(AMOSTRA, NOMES, origem="amostra.txt")
    checar(dados["total_turnos"] == 3, f"3 turnos (obtido: {dados['total_turnos']})")
    checar(dados["formato_detectado"] == "seta", "formato detectado")
    checar(
        dados["metadados"]["data_reuniao"] == "2026-07-15T09:00",
        "metadados preservados",
    )
    checar(len(dados["hash_origem"]) == 16, "hash da origem é gravado")
    checar(dados["versao"] == proc.VERSAO_ARTEFATO, "versão do artefato é gravada")

    try:
        proc.processar("   ", NOMES)
        checar(False, "transcrição vazia deve falhar")
    except ValueError:
        checar(True, "transcrição vazia falha com erro claro")


def test_texto_completo_nao_resumo() -> None:
    print("o artefato guarda a transcrição inteira")
    dados = proc.processar(AMOSTRA, NOMES, origem="amostra.txt")
    ancorado = dados["texto_ancorado"]

    for trecho in ("revisar os tickets abertos", "Eu abro a lista hoje", "homologação"):
        checar(trecho in ancorado, f"fala preservada: '{trecho[:30]}'")

    checar(ancorado.count("**[t=") == 3, "cada turno vira um bloco ancorado")
    checar("[t=5:30]" in ancorado, "âncora de tempo preservada")
    checar(
        "Murilo" in ancorado,
        "falante identificado por auto-apresentação aparece no texto",
    )
    # O corpo do texto não pode encolher: comparação grosseira de volume.
    palavras_origem = len(AMOSTRA.split())
    palavras_artefato = len(ancorado.split())
    checar(
        palavras_artefato >= palavras_origem * 0.7,
        f"volume preservado ({palavras_artefato} vs {palavras_origem} palavras)",
    )


def test_salvar_e_carregar() -> None:
    print("salvar e carregar")
    limpar()
    dados = proc.processar(AMOSTRA, NOMES, origem="amostra.txt")
    caminhos = proc.salvar(STEM, dados)

    checar(caminhos["json"].is_file(), "grava o JSON")
    checar(caminhos["markdown"].is_file(), "grava o Markdown")

    md = caminhos["markdown"].read_text(encoding="utf-8")
    checar("# Transcrição processada" in md, "markdown tem cabeçalho")
    checar("Eu abro a lista hoje" in md, "markdown contém a transcrição")
    checar("a ata é resumo" in md, "markdown avisa para não usar a ata no lugar")

    carregado = proc.carregar(STEM)
    checar(carregado is not None, "carrega o que foi gravado")
    checar(carregado.hash_origem == dados["hash_origem"], "hash sobrevive ao disco")
    checar(len(carregado.turnos) == 3, "turnos sobrevivem ao disco")
    checar("[t=0:00]" in carregado.texto_ancorado, "texto ancorado sobrevive ao disco")


def test_exigir() -> None:
    print("etapa obrigatória")
    limpar()
    checar(proc.carregar(STEM) is None, "sem processamento, carregar devolve None")

    try:
        proc.exigir(STEM)
        checar(False, "exigir deveria falhar sem artefato")
    except proc.ProcessamentoAusente as exc:
        checar(
            "preparada" in str(exc).lower() or "reprocesse" in str(exc).lower(),
            "erro pede preparação automática da transcrição",
        )

    proc.salvar(STEM, proc.processar(AMOSTRA, NOMES, origem="amostra.txt"))
    checar(proc.exigir(STEM, AMOSTRA) is not None, "com artefato válido, passa")

    try:
        proc.exigir(STEM, AMOSTRA + "\n13:00\n>> uma fala nova")
        checar(False, "exigir deveria detectar texto diferente")
    except proc.ProcessamentoDesatualizado as exc:
        checar(
            "reprocesse" in str(exc).lower(),
            "erro pede reprocessamento quando o texto mudou",
        )


def test_status() -> None:
    print("status")
    limpar()
    s = proc.status(STEM)
    checar(s["existe"] is False, "status sem artefato")
    checar(s["motivo"] == "não processado", "motivo declarado")

    proc.salvar(STEM, proc.processar(AMOSTRA, NOMES, origem="amostra.txt"))
    s = proc.status(STEM, AMOSTRA)
    checar(s["existe"] and s["atualizado"], "status com artefato válido")
    checar(s["total_turnos"] == 3, "status traz a contagem de turnos")

    s = proc.status(STEM, "outro texto qualquer")
    checar(
        s["existe"] and not s["atualizado"],
        "status detecta artefato gerado de outro texto",
    )


def test_apelidos_viajam() -> None:
    print("apelidos aplicados ficam registrados")
    dados = proc.processar(AMOSTRA, NOMES, apelidos={"Cris": "Cristian"})
    checar(
        dados["apelidos_aplicados"] == {"Cris": "Cristian"},
        "o mapa confirmado é gravado no artefato",
    )


def main() -> int:
    try:
        for teste in (
            test_processar,
            test_texto_completo_nao_resumo,
            test_salvar_e_carregar,
            test_exigir,
            test_status,
            test_apelidos_viajam,
        ):
            teste()
    finally:
        limpar()
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
