"""Roda o fluxo obrigatório sobre a transcrição da VLI e mostra o resultado.

    python -m tests.validar_fluxo_vli

Simula o que a skill `processamento` faz e verifica que a skill seguinte encontra
o artefato. Não chama LLM: só a parte determinística.
"""

from __future__ import annotations

import sys

from modulos.ata_maker import processamento as proc
from modulos.ata_maker.levantamento import preencher_do_processamento
from tests.validar_transcricao_real import PADRAO, nomes_conhecidos


def main() -> int:
    if not PADRAO.exists():
        print(f"Transcrição não encontrada: {PADRAO}")
        return 1

    texto = PADRAO.read_text(encoding="utf-8")
    stem = PADRAO.stem
    nomes = nomes_conhecidos()

    print("=== antes do processamento ===")
    print(f"  status: {proc.status(stem, texto)}")
    try:
        proc.exigir(stem, texto)
        print("  exigir(): passou — já havia artefato")
    except proc.ProcessamentoAusente as exc:
        print(f"  exigir() barrou, como deve: {exc}")

    print("\n=== rodando o processamento ===")
    dados = proc.processar(texto, nomes, origem=PADRAO.name)
    caminhos = proc.salvar(stem, dados)
    print(f"  json: {caminhos['json']}")
    print(f"  markdown: {caminhos['markdown']}")
    print(f"  hash de origem: {dados['hash_origem']}")
    print(f"  turnos: {dados['total_turnos']} ({dados['turnos_sem_falante']} sem falante)")

    print("\n=== a transcrição inteira sobreviveu? ===")
    ancorado = dados["texto_ancorado"]
    print(f"  caracteres na origem:   {len(texto)}")
    print(f"  caracteres no artefato: {len(ancorado)}")
    print(f"  proporção: {len(ancorado) / max(len(texto), 1):.0%}")
    print(f"  blocos ancorados: {ancorado.count('**[t=')}")

    print("\n=== depois do processamento ===")
    print(f"  status: {proc.status(stem, texto)}")
    carregado = proc.exigir(stem, texto)
    print(f"  exigir(): passou, {len(carregado.turnos)} turnos carregados do disco")

    print("\n=== transcrição alterada é detectada? ===")
    try:
        proc.exigir(stem, texto + "\n50:00\n>> uma fala nova no fim")
        print("  FALHA: não detectou a mudança")
        return 1
    except proc.ProcessamentoDesatualizado as exc:
        print(f"  detectou: {str(exc)[:110]}…")

    print("\n=== levantamento a partir do artefato ===")
    lev = preencher_do_processamento(carregado.dados, nomes)
    info = lev.get("informacoes")
    print(f"  menções objetivas: {len(info) if isinstance(info, list) else 0}")
    participantes = lev.get("participantes")
    if isinstance(participantes, dict):
        print(f"  presentes: {participantes.get('presentes')}")
        print(f"  citados sem falar: {participantes.get('citados_sem_falar')}")

    print("\n=== primeiros blocos do markdown gravado ===")
    for linha in caminhos["markdown"].read_text(encoding="utf-8").splitlines()[:18]:
        print(f"  {linha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
