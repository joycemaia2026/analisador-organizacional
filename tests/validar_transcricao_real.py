"""Roda a normalização sobre uma transcrição real e imprime o resultado para conferência.

    python -m tests.validar_transcricao_real ["transcrições/arquivo.txt"]

Não é teste automatizado: é a inspeção manual exigida antes de confiar na
atribuição de falantes de uma transcrição nova.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from core.utils import PERFIS_JSON, ROOT_DIR
from modulos.ata_maker.normalizacao import normalizar_transcricao

PADRAO = ROOT_DIR / "transcrições" / "VLI - Alinhamento interno - 2026071.txt"

# Participantes citados na reunião que ainda não têm currículo em pessoas/.
NOMES_EXTRA = ["Monica", "Gabriel Pereira", "Victor", "Cecilia", "Tamara", "Lindia"]


def nomes_conhecidos() -> list[str]:
    nomes = list(NOMES_EXTRA)
    if PERFIS_JSON.exists():
        dados = json.loads(PERFIS_JSON.read_text(encoding="utf-8"))
        registros = dados if isinstance(dados, list) else list(dados.values())
        nomes += [str(p.get("nome") or "").strip() for p in registros if isinstance(p, dict)]
    return [n for n in nomes if n]


def main() -> int:
    caminho = Path(sys.argv[1]) if len(sys.argv) > 1 else PADRAO
    if not caminho.exists():
        print(f"Transcrição não encontrada: {caminho}")
        return 1

    resultado = normalizar_transcricao(caminho.read_text(encoding="utf-8"), nomes_conhecidos())

    print(f"arquivo: {caminho.name}")
    print(f"formato detectado: {resultado['formato_detectado']}")
    print(f"metadados: {resultado['metadados']}")
    print(
        f"turnos: {resultado['total_turnos']} "
        f"| sem falante: {resultado['turnos_sem_falante']}"
    )

    print("\ncorreções de ASR aplicadas:")
    for c in resultado["correcoes_asr"][:10] or [None]:
        print(f"  {c}" if c else "  (nenhuma)")

    print("\nsugestões de ASR (exigem julgamento):")
    for c in resultado["sugestoes_asr"][:10] or [None]:
        print(f"  {c}" if c else "  (nenhuma)")

    print("\nprimeiros 8 turnos:")
    for t in resultado["turnos"][:8]:
        print(
            f"  [t={t['ancora']}] {t['falante']} "
            f"({t['origem_falante']} {t['confianca']}) :: {t['texto'][:90]}"
        )

    print("\nturnos com falante atribuído:")
    atribuidos = [t for t in resultado["turnos"] if t["origem_falante"] != "desconhecido"]
    for t in atribuidos[:15]:
        print(f"  [t={t['ancora']}] {t['falante']} ({t['confianca']}) :: {t['texto'][:70]}")
    print(f"  total atribuídos: {len(atribuidos)}")

    _checar_nlp(caminho)
    _mostrar_levantamento(caminho)
    return 0


def _mostrar_levantamento(caminho: Path) -> None:
    """O que o preenchimento determinístico entrega dos 10 campos."""
    from modulos.ata_maker.levantamento import (
        levantamento_para_markdown,
        preencher_deterministico,
        validar_levantamento,
    )

    dados = preencher_deterministico(caminho.read_text(encoding="utf-8"), nomes_conhecidos())
    print("\n--- levantamento (10 campos) ---")
    print(f"  problemas de schema: {validar_levantamento(dados) or 'nenhum'}")
    info = dados.get("informacoes")
    print(f"  menções objetivas encontradas: {len(info) if isinstance(info, list) else 0}")
    if isinstance(info, list):
        for m in info[:8]:
            print(f"    [{m['ancora']}] {m['tipo']}: {m['valor']}")
    print("\n  markdown (cabeçalhos e estado):")
    for linha in levantamento_para_markdown(dados).splitlines():
        if linha.startswith("###") or linha.startswith("_não mencionado"):
            print(f"    {linha}")


def _checar_nlp(caminho: Path) -> None:
    """Regressão: a seção 'Falantes detectados' da ata não pode sair vazia."""
    from modulos.ata_maker.nlp import nlp_para_markdown, run_nlp_analysis

    nlp = run_nlp_analysis(caminho.read_text(encoding="utf-8"))
    stats = nlp["estatisticas"]
    print("\n--- integração com nlp.py ---")
    print(f"  estatisticas.turnos: {stats.get('turnos')}")
    print(f"  estatisticas.falantes: {stats.get('falantes')}")
    md = nlp_para_markdown(nlp)
    inicio = md.find("### Falantes detectados")
    print("  seção da ata:")
    for linha in md[inicio : inicio + 400].splitlines()[:6]:
        print(f"    {linha}")


if __name__ == "__main__":
    sys.exit(main())
