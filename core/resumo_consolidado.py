"""Resumo consolidado e pacote DOCX com todas as etapas da sessão."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from core.especialista_ia import nome_especialista
from core.export_docx import (
    criar_documento,
    markdown_para_docx,
    salvar_markdown_como_docx,
)
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
    comparativa = (session.get("analise_comparativa") or "").strip()
    problema = (
        session.get("problema_atual")
        or session.get("jornada_analise_problema")
        or ""
    ).strip()
    nomes = session.get("nome_tomador") or ""
    resumo_llm = (session.get("resumo_consolidado") or "").strip()

    return {
        "atas": atas,
        "analises_multiplas": multi,
        "analise_tomador": tomador,
        "avaliacao_especialista": especialista,
        "analise_comparativa": comparativa,
        "problema": problema,
        "nome_tomador": nomes,
        "nome_especialista": nome_especialista(),
        "resumo_llm": resumo_llm,
        "tem_ata": bool(atas),
        "tem_personas": bool(multi) or bool(tomador),
        "tem_especialista": bool(especialista),
        "tem_comparativa": bool(comparativa),
        "tem_resumo": bool(resumo_llm),
        "contexto_atual": (session.get("contexto_atual") or "").strip(),
        "lentes_atual": list(session.get("lentes_atual") or []),
        "nomes_docs": list(session.get("nomes_docs") or []),
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
            "Comparativa (opcional)",
            entradas["tem_comparativa"],
            "pronta" if entradas["tem_comparativa"] else "pulada / não gerada",
        ),
        (
            "Problema / pedido",
            bool(entradas["problema"]),
            "preenchido" if entradas["problema"] else "vazio",
        ),
    ]


def pode_gerar(entradas: dict[str, Any]) -> bool:
    return (
        entradas["tem_ata"]
        or entradas["tem_personas"]
        or entradas["tem_especialista"]
        or entradas["tem_comparativa"]
    )


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

    if entradas["analise_comparativa"]:
        partes.append("\n### Análise comparativa")
        partes.append(entradas["analise_comparativa"][:20000])

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


def _secao(titulo: str, corpo: str) -> str:
    corpo = (corpo or "").strip()
    if not corpo:
        corpo = "_(etapa não executada nesta sessão)_"
    return f"# {titulo}\n\n{corpo}\n"


def montar_markdown_pacote_sessao(
    session: dict[str, Any],
    *,
    resumo_llm: str | None = None,
) -> str:
    """Um único Markdown com todas as etapas rodadas na sessão."""
    entradas = coletar_entradas(session)
    resumo = (resumo_llm if resumo_llm is not None else entradas["resumo_llm"]) or ""

    etapas_ok = []
    if entradas["tem_ata"]:
        etapas_ok.append("Ata")
    if entradas["tem_personas"] or entradas["tem_especialista"]:
        etapas_ok.append("Análise organizacional")
    if entradas["tem_comparativa"]:
        etapas_ok.append("Comparativa")
    if resumo.strip():
        etapas_ok.append("Resumo executivo")

    capa = [
        "# Pacote da sessão — Analisador Organizacional",
        "",
        f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "## Etapas incluídas",
        "",
    ]
    if etapas_ok:
        for e in etapas_ok:
            capa.append(f"- {e}")
    else:
        capa.append("- (nenhuma etapa com conteúdo)")

    if entradas["problema"]:
        capa.extend(["", "## Problema / pedido da sessão", "", entradas["problema"]])
    if entradas["contexto_atual"]:
        capa.extend(["", "## Contexto adicional", "", entradas["contexto_atual"]])
    if entradas["lentes_atual"]:
        capa.extend(
            [
                "",
                "## Lentes utilizadas",
                "",
                ", ".join(str(x) for x in entradas["lentes_atual"]),
            ]
        )
    if entradas["nomes_docs"]:
        capa.extend(
            [
                "",
                "## Documentos anexados na análise",
                "",
                ", ".join(entradas["nomes_docs"]),
            ]
        )

    blocos = ["\n".join(capa), ""]

    if resumo.strip():
        blocos.append(_secao("1 · Resumo executivo consolidado", resumo))

    # Atas
    if entradas["atas"]:
        partes_ata = []
        for i, a in enumerate(entradas["atas"], start=1):
            nome = a.get("nome") or f"ata_{i}"
            texto = (a.get("texto") or "").strip()
            partes_ata.append(f"## Ata {i}: {nome}\n\n{texto or '_(vazia)_'}")
        blocos.append(_secao("2 · Atas geradas", "\n\n".join(partes_ata)))
    else:
        blocos.append(_secao("2 · Atas geradas", ""))

    # Análise
    partes_an = []
    multi = entradas["analises_multiplas"]
    if multi:
        for item in multi:
            nome = item.get("nome") or item.get("id") or "Tomador"
            analise = (item.get("analise") or "").strip()
            partes_an.append(f"## Tomador: {nome}\n\n{analise or '_(vazia)_'}")
    elif entradas["analise_tomador"]:
        partes_an.append(
            f"## Tomador(es): {entradas['nome_tomador'] or 'Tomador'}\n\n"
            f"{entradas['analise_tomador']}"
        )
    if entradas["avaliacao_especialista"]:
        partes_an.append(
            f"## {entradas['nome_especialista']}\n\n"
            f"{entradas['avaliacao_especialista']}"
        )
    blocos.append(
        _secao("3 · Análise organizacional", "\n\n".join(partes_an) if partes_an else "")
    )

    # Comparativa — só inclui se a etapa foi executada
    if entradas["tem_comparativa"]:
        blocos.append(
            _secao("4 · Análise comparativa", entradas["analise_comparativa"])
        )

    return "\n\n".join(blocos).strip() + "\n"


def salvar_resumo_docx(markdown: str) -> Path:
    """Salva só o resumo LLM (legado / compatibilidade)."""
    ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = OUTPUTS_DIR / f"resumo_{stamp}.docx"
    salvar_markdown_como_docx(caminho, "Resumo consolidado", markdown or "")
    return caminho


def salvar_pacote_sessao_docx(
    session: dict[str, Any],
    *,
    resumo_llm: str | None = None,
) -> Path:
    """Um único .docx com resumo + etapas da sessão (padrão resumo_{stamp}.docx)."""
    ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = OUTPUTS_DIR / f"resumo_{stamp}.docx"
    md = montar_markdown_pacote_sessao(session, resumo_llm=resumo_llm)
    doc = criar_documento("Pacote da sessão — Analisador Organizacional")
    # Remove o H1 duplicado do markdown (já está no título do doc)
    linhas = md.split("\n")
    if linhas and linhas[0].startswith("# "):
        md_corpo = "\n".join(linhas[1:]).lstrip()
    else:
        md_corpo = md
    markdown_para_docx(md_corpo, doc)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(caminho))
    return caminho


def pacote_sessao_docx_bytes(
    session: dict[str, Any],
    *,
    resumo_llm: str | None = None,
) -> bytes:
    import io

    md = montar_markdown_pacote_sessao(session, resumo_llm=resumo_llm)
    doc = criar_documento("Pacote da sessão — Analisador Organizacional")
    linhas = md.split("\n")
    if linhas and linhas[0].startswith("# "):
        md_corpo = "\n".join(linhas[1:]).lstrip()
    else:
        md_corpo = md
    markdown_para_docx(md_corpo, doc)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
