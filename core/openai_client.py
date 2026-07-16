"""Cliente OpenAI com configuração via .env."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DEFAULT_MODEL = "gpt-4o-mini"


def get_api_key() -> str | None:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key or key == "coloque_sua_chave_aqui":
        return None
    return key


def get_model() -> str:
    return os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def get_client() -> OpenAI:
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY não configurada. Copie .env.example para .env e preencha a chave."
        )
    return OpenAI(api_key=api_key)


def chat_completion(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.4,
    response_format: dict[str, Any] | None = None,
) -> str:
    client = get_client()
    kwargs: dict[str, Any] = {
        "model": get_model(),
        "messages": messages,
        "temperature": temperature,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format

    response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("A API da OpenAI retornou resposta vazia.")
    return content.strip()
