"""Cliente OpenAI com configuração via .env e seletor da sessão Streamlit."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from core.modelos_llm import ids_validos

load_dotenv()

DEFAULT_MODEL = "gpt-4o-mini"
SESSION_MODEL_KEY = "openai_model"


def get_api_key() -> str | None:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key or key == "coloque_sua_chave_aqui":
        return None
    return key


def get_model_from_env() -> str:
    return os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def get_model() -> str:
    """Prefere o modelo da sessão Streamlit; senão OPENAI_MODEL / default."""
    try:
        import streamlit as st

        escolhido = (st.session_state.get(SESSION_MODEL_KEY) or "").strip()
        if escolhido and escolhido in ids_validos():
            return escolhido
    except Exception:  # noqa: BLE001 — fora do Streamlit ou sessão indisponível
        pass
    return get_model_from_env()


def get_image_model() -> str:
    return os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1").strip() or "gpt-image-1"


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
    model: str | None = None,
) -> str:
    client = get_client()
    kwargs: dict[str, Any] = {
        "model": (model or get_model()).strip() or get_model(),
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


def gerar_imagem_png(
    prompt: str,
    *,
    destino: Path | None = None,
    size: str = "1536x1024",
) -> bytes:
    """Gera PNG via Images API (ChatGPT / gpt-image / DALL·E)."""
    import base64

    client = get_client()
    model = get_image_model()
    kwargs: dict[str, Any] = {
        "model": model,
        "prompt": prompt[:32000],
        "n": 1,
    }
    # dall-e-3: 1792x1024; gpt-image-*: 1536x1024 (landscape ~16:9)
    if model.startswith("dall-e"):
        kwargs["size"] = "1792x1024"
        kwargs["quality"] = "hd"
        kwargs["response_format"] = "b64_json"
    else:
        kwargs["size"] = size

    response = client.images.generate(**kwargs)
    item = response.data[0]
    b64 = getattr(item, "b64_json", None)
    if b64:
        raw = base64.b64decode(b64)
    elif getattr(item, "url", None):
        import urllib.request

        with urllib.request.urlopen(item.url, timeout=120) as resp:  # noqa: S310
            raw = resp.read()
    else:
        raise RuntimeError("Images API não retornou imagem (b64 nem URL).")

    if destino is not None:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(raw)
    return raw
