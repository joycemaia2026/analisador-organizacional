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

SUGESTOES = [
    "Quais decisões foram tomadas?",
    "Quais são as pendências e donos?",
    "Qual o problema central da reunião?",
    "Há riscos ou bloqueios mencionados?",
    "O que precisa acontecer na próxima semana?",
]


def responder_pergunta_transcricao(
    transcricao: str,
    pergunta: str,
    *,
    historico: list[dict[str, str]] | None = None,
) -> str:
    """
    Responde com base na transcrição.
    `historico` opcional: [{"pergunta": "...", "resposta": "..."}, ...]
    """
    if not get_api_key():
        raise RuntimeError("Chave de API do provedor LLM não configurada no .env.")
    if not (transcricao or "").strip():
        raise ValueError("Transcrição vazia.")
    if not (pergunta or "").strip():
        raise ValueError("Pergunta vazia.")

    trecho_hist = ""
    if historico:
        blocos = []
        for i, item in enumerate(historico[-4:], start=1):
            blocos.append(
                f"Q{i}: {item.get('pergunta', '')}\n"
                f"A{i}: {item.get('resposta', '')}"
            )
        trecho_hist = "\n\n".join(blocos)

    user = f"""# Transcrição (fonte principal)
{transcricao.strip()[:100000]}

# Pergunta atual
{pergunta.strip()}
"""
    if trecho_hist:
        user += f"\n# Perguntas anteriores nesta sessão\n{trecho_hist}\n"

    user += (
        "\nResponda a pergunta atual. Estrutura sugerida:\n"
        "1) Resposta direta\n"
        "2) Evidências na transcrição (citações curtas, se houver)\n"
        "3) Inferências / ajustes (se houver)\n"
    )

    return chat_completion(
        [
            {"role": "system", "content": SYSTEM_QA},
            {"role": "user", "content": user},
        ],
        temperature=0.25,
    )
