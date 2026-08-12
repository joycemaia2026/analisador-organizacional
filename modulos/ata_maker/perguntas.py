"""Perguntas rápidas sobre a transcrição (fonte principal + ajuste LLM)."""

from __future__ import annotations

from core.openai_client import chat_completion, get_api_key

SYSTEM_QA = """Você responde perguntas rápidas sobre reuniões.

Fonte principal: a TRANSCRIÇÃO fornecida.
Você pode organizar, sintetizar e esclarecer com o LLM, mas:
- Priorize o que está escrito na transcrição.
- Se algo for inferência ou interpretação, diga explicitamente (ex.: "Inferência: …").
- Se a transcrição não permitir responder, diga o que falta — não invente falas ou decisões.
- Seja curto, objetivo e em português do Brasil.
- Quando útil, cite trechos curtos entre aspas.
"""

# Sugestões exibidas na UI (multiseleção). Ordem = relevância típica pós-reunião.
SUGESTOES = [
    "Qual o problema central da reunião?",
    "Quais decisões foram tomadas?",
    "O que precisa acontecer na próxima semana?",
    "Quais são as pendências?",
    "Quais prazos foram combinados?",
]


def responder_pergunta_transcricao(
    transcricao: str,
    pergunta: str,
    *,
    historico: list[dict[str, str]] | None = None,
) -> str:
    """Compat: uma pergunta. Preferir `responder_perguntas_transcricao` na UI."""
    return responder_perguntas_transcricao(
        transcricao, [pergunta], historico=historico
    )


def responder_perguntas_transcricao(
    transcricao: str,
    perguntas: list[str],
    *,
    historico: list[dict[str, str]] | None = None,
) -> str:
    """
    Responde uma ou mais perguntas com base na transcrição.
    `historico` opcional: [{"pergunta": "...", "resposta": "..."}, ...]
    """
    if not get_api_key():
        raise RuntimeError("Chave de API do provedor LLM não configurada no .env.")
    if not (transcricao or "").strip():
        raise ValueError("Transcrição vazia.")

    limpas = [p.strip() for p in perguntas if (p or "").strip()]
    # Remove duplicatas preservando ordem.
    vistas: set[str] = set()
    unicas: list[str] = []
    for p in limpas:
        chave = p.casefold()
        if chave in vistas:
            continue
        vistas.add(chave)
        unicas.append(p)
    if not unicas:
        raise ValueError("Nenhuma pergunta selecionada.")

    trecho_hist = ""
    if historico:
        blocos = []
        for i, item in enumerate(historico[-4:], start=1):
            blocos.append(
                f"Q{i}: {item.get('pergunta', '')}\n"
                f"A{i}: {item.get('resposta', '')}"
            )
        trecho_hist = "\n\n".join(blocos)

    if len(unicas) == 1:
        bloco_perguntas = f"# Pergunta atual\n{unicas[0]}\n"
        instrucao = (
            "\nResponda a pergunta atual. Estrutura sugerida:\n"
            "1) Resposta direta\n"
            "2) Evidências na transcrição (citações curtas, se houver)\n"
            "3) Inferências / ajustes (se houver)\n"
        )
    else:
        listadas = "\n".join(f"{i}. {p}" for i, p in enumerate(unicas, start=1))
        bloco_perguntas = f"# Perguntas atuais ({len(unicas)})\n{listadas}\n"
        instrucao = (
            "\nResponda **cada** pergunta na ordem, com este formato Markdown:\n"
            "## 1. <texto da pergunta>\n"
            "Resposta direta + evidências curtas. Marque inferências.\n\n"
            "## 2. …\n"
            "Não misture respostas. Se a transcrição não cobrir um item, diga o que falta.\n"
        )

    user = f"""# Transcrição (fonte principal)
{transcricao.strip()[:100000]}

{bloco_perguntas}"""
    if trecho_hist:
        user += f"\n# Perguntas anteriores nesta sessão\n{trecho_hist}\n"
    user += instrucao

    return chat_completion(
        [
            {"role": "system", "content": SYSTEM_QA},
            {"role": "user", "content": user},
        ],
        temperature=0.25,
    )
