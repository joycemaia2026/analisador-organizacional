"""Mostra o cabeçalho factual que a ata da VLI receberá, e o prompt montado.

    python -m tests.validar_ata_vli

Não chama o LLM: serve para conferir, antes de gastar chamada, que os fatos
injetados no prompt batem com a gravação.
"""

from __future__ import annotations

import sys

from modulos.ata_maker.nlp import nomes_do_cadastro
from modulos.ata_maker.normalizacao import bloco_fatos_reuniao
from modulos.ata_maker.prompts_catalog import fill_prompt, load_prompt_ata
from tests.validar_transcricao_real import PADRAO, nomes_conhecidos


def main() -> int:
    if not PADRAO.exists():
        print(f"Transcrição não encontrada: {PADRAO}")
        return 1
    texto = PADRAO.read_text(encoding="utf-8")

    print("=== cabeçalho factual (só do cadastro, como o app faz) ===")
    print(bloco_fatos_reuniao(texto, nomes_do_cadastro()))

    print("\n=== cabeçalho factual (com os citados da reunião) ===")
    fatos = bloco_fatos_reuniao(texto, nomes_conhecidos())
    print(fatos)

    template = load_prompt_ata("reuniao")
    prompt = fill_prompt(template, texto, CABECALHO_FATOS=fatos)
    print("\n=== prompt montado ===")
    print(f"placeholders restantes: {'{{' in prompt}")
    print(f"tamanho do prompt: {len(prompt)} chars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
