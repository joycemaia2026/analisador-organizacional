"""Geração de infográfico (HTML + screenshot PNG via Playwright)."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from core.documentos import extrair_texto_arquivo
from core.openai_client import chat_completion, get_api_key
from core.utils import OUTPUTS_DIR, ensure_dirs

SYSTEM_INFO = """Você extrai insights para um infográfico executivo em português do Brasil.
Responda SOMENTE JSON válido:
{
  "titulo": "...",
  "subtitulo": "...",
  "blocos": [
    {"rotulo": "...", "texto": "..."}
  ],
  "destaque": "..."
}
Regras: 4 a 6 blocos; textos curtos; não invente fora das fontes."""


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


def gerar_estrutura_infografico(caminhos: list[Path]) -> dict[str, Any]:
    if not get_api_key():
        raise RuntimeError("OPENAI_API_KEY não configurada.")
    fontes = _texto_fontes(caminhos)
    if not fontes.strip():
        raise ValueError("Fontes vazias.")
    resp = chat_completion(
        [
            {"role": "system", "content": SYSTEM_INFO},
            {
                "role": "user",
                "content": f"Com base nas fontes, monte o infográfico.\n\n{fontes}",
            },
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return _extrair_json(resp)


def montar_html_infografico(dados: dict[str, Any]) -> str:
    titulo = html.escape(str(dados.get("titulo") or "Infográfico"))
    sub = html.escape(str(dados.get("subtitulo") or ""))
    destaque = html.escape(str(dados.get("destaque") or ""))
    cards = []
    for b in dados.get("blocos") or []:
        rotulo = html.escape(str(b.get("rotulo") or ""))
        texto = html.escape(str(b.get("texto") or ""))
        cards.append(
            f'<div class="card"><h3>{rotulo}</h3><p>{texto}</p></div>'
        )
    cards_html = "\n".join(cards)
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"/>
<title>{titulo}</title>
<style>
  body {{
    margin: 0; padding: 40px;
    font-family: Georgia, "Times New Roman", serif;
    background: linear-gradient(160deg, #F4F7FB 0%, #E8F5EE 100%);
    color: #001060;
    width: 1200px;
  }}
  h1 {{ font-size: 42px; margin: 0 0 8px; color: #001060; }}
  .sub {{ font-size: 20px; color: #003080; margin-bottom: 28px; }}
  .destaque {{
    background: #00B040; color: white; padding: 16px 22px;
    border-radius: 10px; font-size: 18px; margin-bottom: 28px;
  }}
  .grid {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 18px;
  }}
  .card {{
    background: white; border: 1px solid #D7E3F0; border-radius: 12px;
    padding: 18px 20px; min-height: 120px;
  }}
  .card h3 {{ margin: 0 0 8px; color: #00B040; font-size: 18px; }}
  .card p {{ margin: 0; font-size: 16px; line-height: 1.4; }}
  .brand {{ margin-top: 28px; font-size: 14px; color: #0050A0; }}
</style>
</head>
<body>
  <h1>{titulo}</h1>
  <div class="sub">{sub}</div>
  {f'<div class="destaque">{destaque}</div>' if destaque else ''}
  <div class="grid">
    {cards_html}
  </div>
  <div class="brand">Gedanken · Analisador Organizacional</div>
</body>
</html>
"""


def html_para_png(html_path: Path, png_path: Path) -> Path:
    from playwright.sync_api import sync_playwright

    from modulos.notebooklm.auth import mensagem_erro_browser
    from modulos.notebooklm.browser import apply_ld_library_path, launch_chromium

    apply_ld_library_path()
    with sync_playwright() as p:
        try:
            browser = launch_chromium(p, headless=True)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(mensagem_erro_browser(exc)) from exc
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        page.locator("body").screenshot(path=str(png_path))
        browser.close()
    return png_path


def gerar_infografico(caminhos: list[Path]) -> tuple[Path, Path]:
    """Retorna (png_path, html_path)."""
    ensure_dirs()
    dados = gerar_estrutura_infografico(caminhos)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_path = OUTPUTS_DIR / f"infografico_{stamp}.html"
    png_path = OUTPUTS_DIR / f"infografico_{stamp}.png"
    html_path.write_text(montar_html_infografico(dados), encoding="utf-8")
    html_para_png(html_path, png_path)
    return png_path, html_path
