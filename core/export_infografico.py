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
    PUBLICO_PADRAO,
    montar_prompt_visual,
    montar_system_roteiro,
    montar_user_roteiro,
    titulo_completo,
    validar_roteiro,
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
    caminhos: list[Path],
    especificacoes: str = "",
    *,
    publico: str = PUBLICO_PADRAO,
    idioma: str = "pt-BR",
) -> dict[str, Any]:
    """Extrai o roteiro das fontes, reancorado no arco canônico de 6 casas.

    Serve qualquer gênero de documento — a estrutura do poster vem do arco, não
    da estrutura da fonte.
    """
    if not get_api_key():
        raise RuntimeError("OPENAI_API_KEY não configurada.")
    from core.especificacoes_llm import anexar_especificacoes

    fontes = _texto_fontes(caminhos)
    if not fontes.strip():
        raise ValueError("Fontes vazias.")
    user = anexar_especificacoes(
        montar_user_roteiro(fontes, publico=publico), especificacoes
    )
    resp = chat_completion(
        [
            {"role": "system", "content": montar_system_roteiro(idioma)},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return _extrair_json(resp)


def montar_html_preview(
    dados: dict[str, Any],
    prompt_usado: str,
    problemas: list[str] | None = None,
) -> str:
    """HTML leve com o conteúdo + prompt (referência; a entrega principal é o PNG)."""
    titulo = html.escape(titulo_completo(dados))
    prompt_esc = html.escape(prompt_usado)
    avisos = ""
    if problemas:
        itens = "".join(f"<li>{html.escape(p)}</li>" for p in problemas)
        avisos = (
            '<div class="avisos"><strong>Roteiro com pendências</strong>'
            f"<ul>{itens}</ul></div>"
        )
    lacunas_lista = [str(x) for x in (dados.get("lacunas") or []) if str(x).strip()]
    if lacunas_lista:
        itens = "".join(f"<li>{html.escape(x)}</li>" for x in lacunas_lista)
        avisos += (
            '<div class="avisos"><strong>Lacunas da fonte</strong>'
            f"<ul>{itens}</ul></div>"
        )
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
  .avisos {{
    background: #FFF6E5; border: 1px solid #F0C97A; border-radius: 12px;
    padding: 12px 16px; margin-bottom: 16px; font-size: 13px;
  }}
  .avisos ul {{ margin: 8px 0 0; padding-left: 20px; }}
</style>
</head>
<body>
  <h1>{titulo}</h1>
  {avisos}
  <p>Prompt enviado ao ChatGPT Images (16:9 corporativo).</p>
  <pre>{prompt_esc}</pre>
  <div class="brand">Gedanken · BriefBoard</div>
</body>
</html>
"""


def gerar_infografico(
    caminhos: list[Path],
    especificacoes: str = "",
    *,
    publico: str = PUBLICO_PADRAO,
    idioma: str = "pt-BR",
) -> tuple[Path, Path]:
    """
    1) O LLM extrai o roteiro das fontes, reancorado no arco de 6 casas
    2) O roteiro é validado (texto repetido, grafia, limites) — pendências viram aviso
    3) O roteiro vira prompt visual 16:9
    4) Images API gera o PNG

    Retorna (png_path, html_path_com_prompt).

    Nota: modelo de imagem desenha letras, não escreve — o texto do PNG pode sair
    corrompido. Para texto literal, renderize o roteiro (`.json`) em HTML.
    """
    ensure_dirs()
    dados = gerar_estrutura_infografico(
        caminhos, especificacoes=especificacoes, publico=publico, idioma=idioma
    )
    problemas = validar_roteiro(dados)
    prompt = montar_prompt_visual(dados)
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
    roteiro_path = OUTPUTS_DIR / f"infografico_{stamp}_roteiro.json"

    prompt_path.write_text(prompt, encoding="utf-8")
    roteiro_path.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    html_path.write_text(
        montar_html_preview(dados, prompt, problemas), encoding="utf-8"
    )
    gerar_imagem_png(prompt, destino=png_path)
    return png_path, html_path
