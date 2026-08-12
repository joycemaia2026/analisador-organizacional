"""Artefato canônico da transcrição processada — etapa obrigatória do fluxo.

A transcrição processada é a fonte de verdade de todas as skills seguintes. Elas
**não** devem trabalhar em cima da ata: a ata é um resumo, e resumir duas vezes
perde o que a segunda leitura precisaria ter visto.

O que este módulo garante:

1. Existe um lugar único onde a transcrição processada mora, por transcrição.
2. Quem consome sabe se o artefato corresponde ao arquivo atual — o hash do texto
   de origem viaja junto, então transcrição trocada não passa despercebida.
3. Skill seguinte que rodar sem o processamento falha com instrução, em vez de
   silenciosamente reprocessar o texto bruto do seu jeito.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from core.utils import OUTPUTS_DIR
from modulos.ata_maker.normalizacao import (
    normalizar_transcricao,
    segmentar_turnos,
    turnos_para_markdown,
)

VERSAO_ARTEFATO = "1"

NOME_JSON = "transcricao_processada.json"
NOME_MD = "transcricao_processada.md"

DIR_ANALISE = OUTPUTS_DIR / "analise_texto"


class ProcessamentoAusente(RuntimeError):
    """A etapa obrigatória de processamento não rodou para esta transcrição."""


class ProcessamentoDesatualizado(RuntimeError):
    """O artefato existe, mas foi gerado a partir de outro texto."""


@dataclass
class Processamento:
    stem: str
    dados: dict[str, Any]

    @property
    def turnos(self) -> list[dict]:
        return self.dados.get("turnos") or []

    @property
    def texto_ancorado(self) -> str:
        """A transcrição inteira, com falante e âncora — não é resumo."""
        return self.dados.get("texto_ancorado") or ""

    @property
    def metadados(self) -> dict:
        return self.dados.get("metadados") or {}

    @property
    def hash_origem(self) -> str:
        return self.dados.get("hash_origem", "")


def hash_texto(texto: str) -> str:
    return hashlib.sha256((texto or "").encode("utf-8")).hexdigest()[:16]


def pasta_do_stem(stem: str) -> Path:
    return DIR_ANALISE / stem


def stem_de(caminho: str | Path) -> str:
    return Path(caminho).stem


# --------------------------------------------------------------------------- #
# Produzir
# --------------------------------------------------------------------------- #


def processar(
    texto: str,
    nomes_conhecidos: list[str] | None = None,
    *,
    apelidos: dict[str, str] | None = None,
    origem: str = "",
) -> dict[str, Any]:
    """Roda a normalização e monta o artefato completo. Sem escrever em disco."""
    if not (texto or "").strip():
        raise ValueError("Transcrição vazia: não há o que processar.")

    resultado = normalizar_transcricao(texto, nomes_conhecidos, apelidos=apelidos)
    turnos = segmentar_turnos(texto)

    return {
        "versao": VERSAO_ARTEFATO,
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "origem": origem,
        "hash_origem": hash_texto(texto),
        "caracteres_origem": len(texto),
        "metadados": resultado["metadados"],
        "formato_detectado": resultado["formato_detectado"],
        "total_turnos": resultado["total_turnos"],
        "turnos_sem_falante": resultado["turnos_sem_falante"],
        "turnos": resultado["turnos"],
        "texto_ancorado": _texto_ancorado(resultado),
        "correcoes_asr": resultado["correcoes_asr"],
        "sugestoes_asr": resultado["sugestoes_asr"],
        "sugestoes_falante": resultado["sugestoes_falante"],
        "apelidos_aplicados": dict(apelidos or {}),
        "_turnos_brutos": len(turnos),
    }


def _texto_ancorado(resultado: dict[str, Any]) -> str:
    """Markdown com um bloco por turno: `**[t=mm:ss] Falante:** fala`."""
    linhas = []
    for t in resultado.get("turnos") or []:
        marca = "" if t.get("origem_falante") == "explicito" else f" ~{t.get('confianca', 0)}"
        linhas.append(f"**[t={t['ancora']}] {t['falante']}{marca}:** {t['texto']}")
    return "\n\n".join(linhas)


def salvar(stem: str, dados: dict[str, Any]) -> dict[str, Path]:
    """Grava JSON e Markdown em `outputs/analise_texto/<stem>/`."""
    pasta = pasta_do_stem(stem)
    pasta.mkdir(parents=True, exist_ok=True)

    caminho_json = pasta / NOME_JSON
    caminho_json.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    caminho_md = pasta / NOME_MD
    caminho_md.write_text(_montar_markdown(stem, dados), encoding="utf-8")
    return {"json": caminho_json, "markdown": caminho_md}


def _montar_markdown(stem: str, dados: dict[str, Any]) -> str:
    meta = dados.get("metadados") or {}
    cab = [
        f"# Transcrição processada — {stem}",
        "",
        f"- Origem: `{dados.get('origem') or 'não informada'}`",
        f"- Hash da origem: `{dados.get('hash_origem', '')}`",
        f"- Gerado em: {dados.get('gerado_em', '')}",
        f"- Título da gravação: {meta.get('titulo') or 'não informado'}",
        f"- Data/hora: {meta.get('data_reuniao') or 'não informada'}"
        + (f" ({meta['fuso']})" if meta.get("fuso") else ""),
        f"- Formato detectado: {dados.get('formato_detectado')}",
        f"- Turnos: {dados.get('total_turnos')} "
        f"({dados.get('turnos_sem_falante')} sem falante identificado)",
        "",
        "> Este arquivo é a fonte das demais skills. Não use a ata no lugar dele:",
        "> a ata é resumo, e o que ela cortou não volta.",
        "",
        "## Transcrição",
        "",
    ]
    return "\n".join(cab) + dados.get("texto_ancorado", "")


def processar_e_salvar(
    caminho_transcricao: str | Path,
    nomes_conhecidos: list[str] | None = None,
    *,
    apelidos: dict[str, str] | None = None,
) -> tuple[str, dict[str, Path]]:
    """Caminho completo: lê o arquivo, processa e grava. Devolve (stem, caminhos)."""
    caminho = Path(caminho_transcricao)
    texto = caminho.read_text(encoding="utf-8")
    stem = caminho.stem
    dados = processar(texto, nomes_conhecidos, apelidos=apelidos, origem=caminho.name)
    return stem, salvar(stem, dados)


# --------------------------------------------------------------------------- #
# Consumir
# --------------------------------------------------------------------------- #


def carregar(stem: str) -> Processamento | None:
    """Artefato já gravado, ou None se a etapa não rodou."""
    caminho = pasta_do_stem(stem) / NOME_JSON
    if not caminho.is_file():
        return None
    return Processamento(stem=stem, dados=json.loads(caminho.read_text(encoding="utf-8")))


def exigir(stem: str, texto_origem: str | None = None) -> Processamento:
    """Artefato válido, ou erro com a instrução do que fazer.

    É o guarda da etapa obrigatória: etapas seguintes chamam isto antes de
    qualquer coisa, em vez de reprocessar o texto bruto por conta própria.
    """
    proc = carregar(stem)
    if proc is None:
        raise ProcessamentoAusente(
            f"Transcrição '{stem}' ainda não foi preparada. "
            f"Reprocesse a transcrição (etapa automática do BriefBoard) — "
            f"o artefato fica em {pasta_do_stem(stem) / NOME_MD}."
        )
    if texto_origem is not None:
        atual = hash_texto(texto_origem)
        if atual != proc.hash_origem:
            raise ProcessamentoDesatualizado(
                f"A preparação de '{stem}' foi gerada de outro texto "
                f"(artefato {proc.hash_origem}, atual {atual}). "
                f"Reprocesse a transcrição (etapa automática do BriefBoard)."
            )
    return proc


def status(stem: str, texto_origem: str | None = None) -> dict[str, Any]:
    """Diagnóstico legível, sem levantar exceção. Para relatório e checkpoint."""
    proc = carregar(stem)
    if proc is None:
        return {"existe": False, "atualizado": False, "motivo": "não processado"}
    atualizado = True
    motivo = "ok"
    if texto_origem is not None and hash_texto(texto_origem) != proc.hash_origem:
        atualizado, motivo = False, "gerado a partir de outro texto"
    return {
        "existe": True,
        "atualizado": atualizado,
        "motivo": motivo,
        "versao": proc.dados.get("versao"),
        "gerado_em": proc.dados.get("gerado_em"),
        "total_turnos": proc.dados.get("total_turnos"),
        "turnos_sem_falante": proc.dados.get("turnos_sem_falante"),
    }
