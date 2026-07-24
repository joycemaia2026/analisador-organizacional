"""Resumo consolidado: ata + personas + Especialista IA."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from core.especialista_ia import nome_especialista
from core.export_docx import salvar_markdown_como_docx
from core.openai_client import chat_completion, get_api_key
from core.utils import OUTPUTS_DIR, ensure_dirs

PROMPT_SISTEMA = """\
Você consolida materiais de uma reunião/análise organizacional em um RESUMO EXECUTIVO.

Este documento pode ser a ÚNICA leitura de quem precisa agir. Por isso o TO-DO
deve ser autoexplicativo: quem lê só este arquivo precisa saber exatamente o que fazer.

REGRAS OBRIGATÓRIAS:
1. NÃO invente fatos, decisões, donos ou prazos que não estejam nas fontes.
2. Priorize no topo: o PROBLEMA e o TO-DO (ações concretas).
3. A seção TO-DO é obrigatória e deve ser uma checklist acionável:
   - cada item em uma linha começando com `- [ ]`
   - inclua dono e prazo quando constarem nas fontes; se faltar, marque "(dono a definir)" / "(prazo a definir)"
   - ordene por urgência (o que fazer primeiro no topo)
   - se Tomador e Especialista divergirem, indique no item: "(Tomador)" / "(Especialista)" / "(consenso)"
4. A seção "Resumo da ata" deve ser só registro (fatos, decisões, pendências) — SEM opinião analítica de personas ou do especialista.
5. Em CADA seção de conteúdo (exceto Fontes), termine com uma linha: `Fonte: …`.
6. Se uma fonte estiver ausente, escreva honestamente "(fonte não disponível nesta sessão)".
7. Seja conciso. Use listas. Português do Brasil.

ESTRUTURA EXATA (use estes títulos ##):

## 1. Problema
## 2. TO-DO (o que deve ser feito)
## 3. Resumo da ata
## 4. Resumo das personas consultadas
## 5. Resumo do Analista Sênior em IA
## 6. Fontes usadas
"""


def coletar_entradas(session: dict[str, Any]) -> dict[str, Any]:
    """Extrai blocos de texto da sessão Streamlit (dict-like)."""
    atas = list(session.get("atas_anexadas") or [])
    if not atas and session.get("ata_gerada_texto"):
        atas = [
            {
                "nome": session.get("ata_gerada_nome") or "ata_gerada.md",
                "texto": session["ata_gerada_texto"],
            }
        ]

    multi = list(session.get("analises_multiplas") or [])
    tomador = (session.get("analise_tomador") or "").strip()
    especialista = (session.get("avaliacao_especialista") or "").strip()
    problema = (
        session.get("problema_atual")
        or session.get("jornada_analise_problema")
        or ""
    ).strip()
    nomes = session.get("nome_tomador") or ""

    return {
        "atas": atas,
        "analises_multiplas": multi,
        "analise_tomador": tomador,
        "avaliacao_especialista": especialista,
        "problema": problema,
        "nome_tomador": nomes,
        "nome_especialista": nome_especialista(),
        "tem_ata": bool(atas),
        "tem_personas": bool(multi) or bool(tomador),
        "tem_especialista": bool(especialista),
    }


def status_entradas(entradas: dict[str, Any]) -> list[tuple[str, bool, str]]:
    return [
        ("Ata", entradas["tem_ata"], f"{len(entradas['atas'])} documento(s)"),
        (
            "Personas / Tomadores",
            entradas["tem_personas"],
            entradas["nome_tomador"] or "análise consolidada",
        ),
        (
            "Especialista IA",
            entradas["tem_especialista"],
            entradas["nome_especialista"],
        ),
        (
            "Problema / pedido",
            bool(entradas["problema"]),
            "preenchido" if entradas["problema"] else "vazio",
        ),
    ]


def pode_gerar(entradas: dict[str, Any]) -> bool:
    return entradas["tem_ata"] or entradas["tem_personas"] or entradas["tem_especialista"]


def _montar_contexto(entradas: dict[str, Any]) -> str:
    partes: list[str] = []

    partes.append("### Pedido de ajuda / problema da sessão")
    partes.append(entradas["problema"] or "(não informado)")

    partes.append("\n### Atas (registro — sem reanálise)")
    if not entradas["atas"]:
        partes.append("(nenhuma ata na sessão)")
    else:
        for a in entradas["atas"]:
            nome = a.get("nome") or "ata"
            texto = (a.get("texto") or "")[:20000]
            partes.append(f"---- ATA: {nome} ----\n{texto}")

    partes.append("\n### Análises das personas (Tomadores)")
    multi = entradas["analises_multiplas"]
    if multi:
        for item in multi:
            nome = item.get("nome") or item.get("id") or "Tomador"
            analise = (item.get("analise") or "")[:18000]
            partes.append(f"---- PERSONA: {nome} ----\n{analise}")
    elif entradas["analise_tomador"]:
        partes.append(
            f"---- PERSONA(S): {entradas['nome_tomador'] or 'Tomador'} ----\n"
            f"{entradas['analise_tomador'][:24000]}"
        )
    else:
        partes.append("(nenhuma análise de persona na sessão)")

    partes.append(f"\n### Avaliação — {entradas['nome_especialista']}")
    if entradas["avaliacao_especialista"]:
        partes.append(entradas["avaliacao_especialista"][:24000])
    else:
        partes.append("(avaliação do especialista ausente)")

    return "\n".join(partes)


def gerar_resumo_consolidado(session: dict[str, Any], especificacoes: str = "") -> str:
    if not get_api_key():
        raise RuntimeError("OPENAI_API_KEY não configurada.")

    from core.especificacoes_llm import anexar_especificacoes

    entradas = coletar_entradas(session)
    if not pode_gerar(entradas):
        raise RuntimeError(
            "Não há material para resumir. Gere ata e/ou análise organizacional antes."
        )

    contexto = _montar_contexto(entradas)
    user = anexar_especificacoes(
        "Com base EXCLUSIVAMENTE no material abaixo, produza o resumo consolidado "
        "no formato exigido.\n\n"
        f"{contexto}",
        especificacoes,
    )
    return chat_completion(
        [
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": user},
        ],
        temperature=0.25,
    )


def salvar_resumo_docx(markdown: str) -> Path:
    ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = OUTPUTS_DIR / f"resumo_{stamp}.docx"
    salvar_markdown_como_docx(caminho, "Resumo consolidado", markdown or "")
    return caminho
