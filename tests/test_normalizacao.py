"""Testes da normalização de transcrição — só stdlib.

    python -m tests.test_normalizacao

Travam as duas regras que não podem regredir:
1. os três formatos de transcrição do projeto são segmentados com timestamp;
2. falante sem evidência suficiente permanece desconhecido (nunca é chutado).
"""

from __future__ import annotations

import sys

from modulos.ata_maker.normalizacao import (
    FALANTE_DESCONHECIDO,
    aplicar_sugestoes,
    contar_falas,
    corrigir_nomes_asr,
    detectar_formato,
    extrair_metadados_cabecalho,
    formatar_ancora,
    normalizar_transcricao,
    segmentar_turnos,
    sugerir_falantes,
    ts_para_segundos,
)

NOMES = ["Cristian", "Rogerio", "Lucas", "Gabriel Garcia", "Murilo", "Tais", "André"]

# Formato real do Meet: turno com '>>', timestamp em linha própria, sem nome.
AMOSTRA_SETA = """VLI - Alinhamento interno - 2026/07/15 09:00 GMT-03:00 - Recording

0:00
para esse cliente para explicar o que que tá acontecendo lá. A lista dos
0:04
tickets que tem ali, para mim vai ser fácil resolver.
0:48
>> Perfeito, Cris. Ótima colocação aqui. Acho que esse também foi o recado
0:53
deles, né?
1:30
>> Isso, isso é disso que eu tô falando também, tá?
"""

AMOSTRA_NOMEADA = """Cristian: a gente precisa mudar a forma de trabalho.
Rogerio: concordo, mas falta gente para atender.
Cristian: então vamos priorizar os tickets abertos.
"""

AMOSTRA_CORRIDA = """0:00
o cliente reclamou do tempo de resposta do suporte
0:15
e a gente não tinha ninguém disponível naquele dia
"""

_falhas: list[str] = []


def checar(condicao: bool, descricao: str) -> None:
    if condicao:
        print(f"  ok   {descricao}")
    else:
        print(f"  FALHA {descricao}")
        _falhas.append(descricao)


def test_timestamps() -> None:
    print("timestamps")
    checar(ts_para_segundos("12:34") == 754, "'12:34' vira 754 segundos")
    checar(ts_para_segundos("1:02:33") == 3753, "'1:02:33' vira 3753 segundos")
    checar(ts_para_segundos("abc") is None, "texto inválido não vira timestamp")
    checar(formatar_ancora(754) == "12:34", "âncora de 754s é '12:34'")
    checar(formatar_ancora(None) == "??:??", "âncora ausente é explícita")


def test_formato_seta() -> None:
    print("formato '>>' (ASR do Meet)")
    checar(detectar_formato(AMOSTRA_SETA) == "seta", "formato detectado como 'seta'")
    turnos = segmentar_turnos(AMOSTRA_SETA)
    checar(len(turnos) == 3, f"3 turnos segmentados (obtido: {len(turnos)})")
    checar(
        all(t.inicio_seg is not None for t in turnos),
        "todo turno carrega timestamp de início",
    )
    checar(turnos[1].inicio_seg == 48, "segundo turno começa em 0:48")
    checar(
        "Perfeito" in turnos[1].texto and "0:53" not in turnos[1].texto,
        "texto do turno é contínuo e sem timestamp embutido",
    )
    checar(
        "Recording" not in turnos[0].texto,
        "cabeçalho da gravação não entra como fala",
    )


def test_formato_nomeado() -> None:
    print("formato 'Nome:'")
    checar(detectar_formato(AMOSTRA_NOMEADA) == "nomeado", "formato detectado")
    turnos = segmentar_turnos(AMOSTRA_NOMEADA)
    checar(len(turnos) == 3, f"3 turnos segmentados (obtido: {len(turnos)})")
    checar(
        [t.falante for t in turnos] == ["Cristian", "Rogerio", "Cristian"],
        "falantes explícitos preservados na ordem",
    )
    checar(
        all(t.origem_falante == "explicito" for t in turnos),
        "origem marcada como explícita",
    )
    checar(contar_falas(turnos)[0] == {"falante": "Cristian", "falas": 2},
           "contagem de falas ordena por volume")


def test_formato_corrido() -> None:
    print("formato corrido (só timestamps)")
    checar(detectar_formato(AMOSTRA_CORRIDA) == "corrido", "formato detectado")
    turnos = segmentar_turnos(AMOSTRA_CORRIDA)
    checar(len(turnos) == 2, f"timestamp delimita o bloco (obtido: {len(turnos)})")
    checar(
        all(t.falante is None for t in turnos),
        "sem marca de turno, nenhum falante é inventado",
    )


def test_nao_chuta_falante() -> None:
    print("não chutar falante")
    turnos = segmentar_turnos(AMOSTRA_SETA)
    sugestoes = sugerir_falantes(turnos, NOMES)
    aplicar_sugestoes(turnos, sugestoes)
    checar(
        turnos[2].falante is None,
        "turno sem evidência nenhuma continua sem falante",
    )
    checar(
        all(t.confianca >= 0.6 for t in turnos if t.falante),
        "nenhum falante atribuído abaixo do limiar",
    )

    # Vocativo é evidência negativa: quem chama 'Rogerio' não é o Rogerio.
    turnos_voc = segmentar_turnos("Desculpa, Rogerio. E aí, como ficou?")
    sug = sugerir_falantes(turnos_voc, NOMES)
    checar(
        not any(s.indice_turno == 0 and s.falante == "Rogerio" for s in sug),
        "quem chama alguém não é sugerido como esse alguém",
    )


def test_auto_apresentacao() -> None:
    print("auto-apresentação")
    turnos = segmentar_turnos(">> aqui é o Cristian, só complementando o ponto.")
    aplicar_sugestoes(turnos, sugerir_falantes(turnos, NOMES))
    checar(turnos[0].falante == "Cristian", "'aqui é o Cristian' atribui o turno")
    checar(turnos[0].origem_falante == "sugerido", "origem marcada como sugerida")


def test_correcao_asr() -> None:
    print("correção de nomes do ASR")
    r = corrigir_nomes_asr("o cliente Veli abriu o ticket e a Veli cobrou", ["Lucas"])
    checar("VLI" in r.texto, "'Veli' corrigido para 'VLI'")
    checar(
        any(c.original == "Veli" and c.ocorrencias == 2 for c in r.correcoes),
        "correção registrada com contagem de ocorrências",
    )

    r2 = corrigir_nomes_asr("Perfeito, Cris. Vamos seguir.", ["Cristian"])
    checar("Cris." in r2.texto, "apelido não é reescrito automaticamente")
    checar(
        any(s.original == "Cris" and s.corrigido == "Cristian" for s in r2.sugestoes),
        "apelido vira sugestão para decisão de contexto",
    )

    r3 = corrigir_nomes_asr("O Marcelo trouxe o relatório.", ["Rogerio"])
    checar(
        not r3.correcoes and r3.texto.count("Marcelo") == 1,
        "nome distante de qualquer conhecido é deixado intacto",
    )


def test_vocativo_com_acento() -> None:
    print("vocativo com acento")
    # O ASR escreve 'Mônica'; o cadastro tem 'Monica'. Tem que casar mesmo assim.
    turnos = segmentar_turnos(">> primeiro ponto\n>> Isso mesmo, Mônica. Concordo.")
    sug = sugerir_falantes(turnos, ["Monica", "Rogerio"])
    checar(
        any(s.indice_turno == 0 and s.falante == "Monica" for s in sug),
        "vocativo acentuado casa com o nome sem acento do cadastro",
    )


def test_apelido_confirmado() -> None:
    print("apelido confirmado pela skill")
    texto = ">> temos que mudar a forma de trabalho\n>> Perfeito, Cris. Ótima colocação."
    sem = normalizar_transcricao(texto, ["Cristian"])
    checar(
        sem["turnos"][0]["falante"] == FALANTE_DESCONHECIDO,
        "sem o apelido resolvido, o falante segue desconhecido",
    )
    checar(
        any(s["original"] == "Cris" for s in sem["sugestoes_asr"]),
        "o apelido é reportado para decisão",
    )
    com = normalizar_transcricao(texto, ["Cristian"], apelidos={"Cris": "Cristian"})
    checar(
        com["turnos"][0]["falante"] == "Cristian",
        "com o apelido confirmado, o vocativo atribui o turno anterior",
    )
    checar(
        any(c["original"] == "Cris" for c in com["correcoes_asr"]),
        "apelido confirmado é registrado como correção aplicada",
    )


def test_metadados_e_pipeline() -> None:
    print("metadados e pipeline")
    meta = extrair_metadados_cabecalho(AMOSTRA_SETA)
    checar(meta["data_reuniao"] == "2026-07-15T09:00", "data da reunião extraída")
    checar(meta["fuso"] == "GMT-03:00", "fuso extraído")

    r = normalizar_transcricao(AMOSTRA_SETA, NOMES)
    checar(r["total_turnos"] == 3, "pipeline devolve os turnos")
    checar(r["formato_detectado"] == "seta", "pipeline reporta o formato")
    checar(
        r["turnos"][0]["falante"] in {*NOMES, FALANTE_DESCONHECIDO},
        "falante do dict é conhecido ou explicitamente não identificado",
    )
    checar("ancora" in r["turnos"][0], "cada turno exporta a âncora")


def test_nlp_nao_inventa_falante() -> None:
    print("integração com nlp.py")
    from modulos.ata_maker.nlp import _detectar_falantes

    checar(
        _detectar_falantes(AMOSTRA_NOMEADA)[0]["falante"] == "Cristian",
        "formato 'Nome:' continua sendo contado",
    )

    # Quebra de linha no meio da frase de um ASR: o regex antigo lia
    # 'estruturada e falar' e 'pra gente' como se fossem participantes.
    ruido = (
        ">> a gente precisa de uma comunicação mais\n"
        "estruturada e falar: isso não pode continuar\n"
        ">> concordo, e o retorno\n"
        "pra gente: tem que ser mais rápido\n"
    )
    falantes = [f["falante"] for f in _detectar_falantes(ruido)]
    checar(
        "estruturada e falar" not in falantes and "pra gente" not in falantes,
        "trecho de frase quebrada não vira falante",
    )


def main() -> int:
    for teste in (
        test_timestamps,
        test_formato_seta,
        test_formato_nomeado,
        test_formato_corrido,
        test_nao_chuta_falante,
        test_auto_apresentacao,
        test_correcao_asr,
        test_vocativo_com_acento,
        test_apelido_confirmado,
        test_nlp_nao_inventa_falante,
        test_metadados_e_pipeline,
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
