"""Geração de infográfico via ChatGPT (prompt visual + Images API)."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from core.documentos import extrair_texto_arquivo
from core.openai_client import chat_completion, gerar_imagem_png, get_api_key
from core.prompt_infografico import (
    SYSTEM_EXTRAIR_CONTEUDO,
    montar_prompt_infografico,
)
from core.utils import OUTPUTS_DIR, ensure_dirs


def _extrair_json(texto: str) -> dict[str, Any]:
    texto = texto.strip()
    if texto.startswith("```"):
        texto = re.sub(r"^```(?:json)?\s*", "", texto)
        texto = re.sub(r"\s*```$", "", texto)
    return json.loads(texto)


def _texto_fontes(caminhos: list[Path], *, max_chars: int = 50000) -> str:
    partes: list[str] = []
    total = 0
    for path in caminhos:
        try:
            doc = extrair_texto_arquivo(path.name, path.read_bytes())
        except Exception as exc:  # noqa: BLE001
            partes.append(f"--- {path.name} (erro: {exc}) ---")
            continue
        bloco = f"--- {path.name} ---\n{doc.texto}"
        if total + len(bloco) > max_chars:
            resto = max_chars - total
            if resto > 500:
                partes.append(bloco[:resto] + "\n…")
            break
        partes.append(bloco)
        total += len(bloco)
    return "\n\n".join(partes)


def gerar_estrutura_infografico(
    caminhos: list[Path], especificacoes: str = ""
) -> dict[str, Any]:
    """Extrai conteúdo estruturado das fontes (para preencher o prompt visual)."""
    if not get_api_key():
        raise RuntimeError("OPENAI_API_KEY não configurada.")
    from core.especificacoes_llm import anexar_especificacoes

    fontes = _texto_fontes(caminhos)
    if not fontes.strip():
        raise ValueError("Fontes vazias.")
    user = anexar_especificacoes(
        "Com base nas fontes abaixo, preencha o JSON do infográfico "
        "(arquitetura de produto / análise organizacional).\n\n"
        f"{fontes}",
        especificacoes,
    )
    resp = chat_completion(
        [
            {"role": "system", "content": SYSTEM_EXTRAIR_CONTEUDO},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return _extrair_json(resp)


def montar_html_preview(dados: dict[str, Any], prompt_usado: str) -> str:
    """HTML leve com o conteúdo + prompt (referência; a entrega principal é o PNG)."""
    titulo = html.escape(str(dados.get("titulo") or "Infográfico"))
    prompt_esc = html.escape(prompt_usado)
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"/>
<title>{titulo}</title>
<style>
  body {{
    margin: 0; padding: 32px;
    font-family: "Segoe UI", system-ui, sans-serif;
    background: #F4F9FB; color: #001060;
    max-width: 960px;
  }}
  h1 {{ font-size: 28px; margin: 0 0 12px; }}
  pre {{
    white-space: pre-wrap; background: #fff; border: 1px solid #D7E3F0;
    border-radius: 12px; padding: 16px; font-size: 12px; line-height: 1.45;
  }}
  .brand {{ margin-top: 20px; font-size: 13px; color: #0050A0; }}
</style>
</head>
<body>
  <h1>{titulo}</h1>
  <p>Prompt enviado ao ChatGPT Images (16:9 corporativo).</p>
  <pre>{prompt_esc}</pre>
  <div class="brand">Gedanken · Analisador Organizacional</div>
</body>
</html>
"""


def gerar_infografico(
    caminhos: list[Path], especificacoes: str = ""
) -> tuple[Path, Path]:
    """
    1) ChatGPT extrai conteúdo das fontes
    2) Monta o prompt visual corporativo 16:9
    3) Images API gera o PNG

    Retorna (png_path, html_path_com_prompt).
    """
    ensure_dirs()
    dados = gerar_estrutura_infografico(caminhos, especificacoes=especificacoes)
    prompt = montar_prompt_infografico(dados)
    if (especificacoes or "").strip():
        prompt = (
            f"{prompt.rstrip()}\n\n"
            "ESPECIFICAÇÕES ADICIONAIS DO USUÁRIO:\n"
            f"{especificacoes.strip()}\n"
        )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_path = OUTPUTS_DIR / f"infografico_{stamp}.html"
    png_path = OUTPUTS_DIR / f"infografico_{stamp}.png"
    prompt_path = OUTPUTS_DIR / f"infografico_{stamp}_prompt.txt"

    prompt_path.write_text(prompt, encoding="utf-8")
    html_path.write_text(montar_html_preview(dados, prompt), encoding="utf-8")
    gerar_imagem_png(prompt, destino=png_path)
    return png_path, html_path
