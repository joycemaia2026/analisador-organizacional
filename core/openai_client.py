"""Cliente LLM (OpenAI ou Gemini) via .env e seletor da sessão Streamlit.

Gemini usa a API compatível com OpenAI:
https://generativelanguage.googleapis.com/v1beta/openai/
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from core.modelos_llm import ids_validos, lista_ids_ordenados

load_dotenv()

DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL_OPENAI = "gpt-4o-mini"
DEFAULT_MODEL_GEMINI = "gemini-2.0-flash"
SESSION_PROVIDER_KEY = "llm_provider"
SESSION_MODEL_KEY = "openai_model"  # mantido por compatibilidade da sessão

GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def get_provider() -> str:
    """Prefere o provedor da sessão Streamlit; senão LLM_PROVIDER / openai."""
    try:
        import streamlit as st

        escolhido = (st.session_state.get(SESSION_PROVIDER_KEY) or "").strip().lower()
        if escolhido in {"openai", "gemini"}:
            return escolhido
    except Exception:  # noqa: BLE001
        pass
    env = (os.getenv("LLM_PROVIDER") or DEFAULT_PROVIDER).strip().lower()
    return env if env in {"openai", "gemini"} else DEFAULT_PROVIDER


def get_openai_api_key() -> str | None:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key or key == "coloque_sua_chave_aqui":
        return None
    return key


def get_gemini_api_key() -> str | None:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or key == "coloque_sua_chave_aqui":
        return None
    return key


def get_api_key(provider: str | None = None) -> str | None:
    """Chave do provedor ativo (ou do informado)."""
    prov = (provider or get_provider()).strip().lower()
    if prov == "gemini":
        return get_gemini_api_key()
    return get_openai_api_key()


def provider_label(provider: str | None = None) -> str:
    return "Gemini" if (provider or get_provider()) == "gemini" else "OpenAI"


def get_model_from_env(provider: str | None = None) -> str:
    prov = (provider or get_provider()).strip().lower()
    if prov == "gemini":
        return (
            os.getenv("GEMINI_MODEL", DEFAULT_MODEL_GEMINI).strip()
            or DEFAULT_MODEL_GEMINI
        )
    return (
        os.getenv("OPENAI_MODEL", DEFAULT_MODEL_OPENAI).strip() or DEFAULT_MODEL_OPENAI
    )


def get_model() -> str:
    """Prefere o modelo da sessão Streamlit; senão env / default do provedor."""
    try:
        import streamlit as st

        escolhido = (st.session_state.get(SESSION_MODEL_KEY) or "").strip()
        if escolhido and escolhido in ids_validos(get_provider()):
            return escolhido
    except Exception:  # noqa: BLE001 — fora do Streamlit ou sessão indisponível
        pass
    return get_model_from_env()


def get_image_model() -> str:
    return os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1").strip() or "gpt-image-1"


def get_client(provider: str | None = None) -> OpenAI:
    prov = (provider or get_provider()).strip().lower()
    api_key = get_api_key(prov)
    if not api_key:
        label = provider_label(prov)
        env_name = "GEMINI_API_KEY" if prov == "gemini" else "OPENAI_API_KEY"
        raise RuntimeError(
            f"{env_name} não configurada para {label}. "
            "Copie .env.example para .env e preencha a chave."
        )
    if prov == "gemini":
        return OpenAI(api_key=api_key, base_url=GEMINI_OPENAI_BASE_URL)
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
        raise RuntimeError(
            f"A API de {provider_label()} retornou resposta vazia."
        )
    return content.strip()


def gerar_imagem_png(
    prompt: str,
    *,
    destino: Path | None = None,
    size: str = "1536x1024",
) -> bytes:
    """Gera PNG via Images API da OpenAI (independente do provedor de chat)."""
    import base64

    api_key = get_openai_api_key()
    if not api_key:
        raise RuntimeError(
            "Geração de imagem requer OPENAI_API_KEY no .env "
            "(não disponível via Gemini nesta app)."
        )
    client = OpenAI(api_key=api_key)
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


# Reexport útil para UI
def modelos_do_provedor_ativo() -> list[str]:
    return lista_ids_ordenados(get_provider())
