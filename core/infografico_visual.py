"""Infográfico visual HTML — skill `infografico-visual`.

Síntese colorida e escaneável (estilo NotebookLM), saída em HTML/CSS responsivo
com Lucide Icons. Diferente de `export_infografico.py` (PNG via Images API).
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from core.documentos import extrair_texto_arquivo
from core.openai_client import chat_completion, get_api_key
from core.skills_locais import corpo_skill
from core.utils import OUTPUTS_DIR, ensure_dirs

PUBLICO_PADRAO = "alguém competente que precisa entender o tema em 30 segundos"

SYSTEM_INFOGRAFICO_VISUAL = """\
Você é um designer visual e especialista em síntese de conteúdo. Sua tarefa é \
transformar o material fornecido em um infográfico altamente visual, claro, \
colorido e informativo, no estilo de um resumo visual moderno semelhante ao NotebookLM.

Objetivo:
Criar um infográfico eficiente, visualmente organizado e fácil de entender, \
mantendo apenas as informações mais relevantes para o usuário. O resultado deve \
sintetizar o conteúdo de forma estratégica, evitando excesso de texto e \
priorizando clareza, hierarquia visual e impacto.

Estilo visual obrigatório:
- Visual moderno, limpo, colorido e dinâmico.
- Layout editorial com blocos bem definidos.
- Uso de cores vivas, mas harmoniosas.
- Fundo claro ou levemente colorido.
- Seções organizadas em cards, linhas, colunas ou módulos visuais.
- Ícones relevantes em cada seção (Lucide Icons via CDN unpkg).
- Elementos visuais leves: setas, conectores, etiquetas, badges, destaques e divisores.
- Aparência profissional, informativa e agradável — pronta para apresentação ou compartilhamento.

Regras de conteúdo:
- Sintetize o material ao máximo.
- Mantenha apenas as informações mais importantes, úteis e acionáveis.
- Elimine repetições, exemplos longos, frases genéricas e detalhes secundários.
- Transforme parágrafos extensos em frases curtas, tópicos visuais e destaques.
- Use linguagem simples, direta e precisa.
- Nunca invente fatos, números, nomes ou conclusões ausentes no material.
- Sempre que possível, converta explicações em esquemas, listas, fluxos ou comparações.

Estrutura fixa do infográfico:
1. Título principal curto e forte.
2. Subtítulo explicativo em uma frase.
3. Bloco "Ideia central", resumindo o tema em até 3 linhas.
4. De 4 a 6 seções principais, cada uma com: ícone; título curto; 2 a 4 bullets; \
destaque visual de uma informação-chave.
5. Um bloco de "Resumo rápido" com os pontos essenciais.
6. Um bloco final de "Aplicação prática" / "O que fazer com isso".
7. Rodapé discreto com uma frase-síntese memorável.

Direção de design:
- Paleta consistente com 4 a 6 cores (CSS variables).
- Cada seção com cor de apoio própria, em harmonia.
- Tipografia com hierarquia clara (título grande, subtítulos, bullets, destaques).
- Evite blocos grandes de texto; espaçamento visual generoso.
- Ícones Lucide simples e coerentes (data-lucide="nome-do-icone").

Consistência:
Sempre a mesma estrutura, hierarquia, linguagem, quantidade aproximada de informação \
e aparência geral de infográfico visual, colorido e didático.

Formato de saída (obrigatório):
- Responda SOMENTE com um documento HTML completo e válido (começa com <!DOCTYPE html>).
- CSS no próprio arquivo (<style>); JavaScript mínimo se precisar (init Lucide).
- Inclua: <script src="https://unpkg.com/lucide@latest"></script> e \
<script>lucide.createIcons();</script> no final do body.
- Responsivo (desktop e mobile). Sem React/Vite/build.
- Idioma: {idioma}.

Importante:
O resultado NÃO deve parecer artigo, relatório ou slide comum. Deve parecer um \
infográfico visual, sintético, colorido, modular e altamente escaneável.
"""


def _texto_fontes(caminhos: list[Path], *, max_chars: int = 50000) -> str:
    partes: list[str] = []
    total = 0
    for path in caminhos:
        try:
            doc = extrair_texto_arquivo(path.name, path.read_bytes())
            bloco = f"--- {path.name} ---\n{doc.texto}"
        except Exception as exc:  # noqa: BLE001
            bloco = f"--- {path.name} (erro: {exc}) ---"
        if total + len(bloco) > max_chars:
            resto = max_chars - total
            if resto > 500:
                partes.append(bloco[:resto] + "\n…")
            break
        partes.append(bloco)
        total += len(bloco)
    return "\n\n".join(partes)


def _extrair_html(texto: str) -> str:
    bruto = (texto or "").strip()
    cerca = re.search(r"```(?:html)?\s*([\s\S]*?)```", bruto, re.IGNORECASE)
    if cerca:
        bruto = cerca.group(1).strip()
    if "<html" not in bruto.lower() and "<!doctype" not in bruto.lower():
        raise ValueError("O modelo não devolveu HTML completo.")
    if not bruto.lower().lstrip().startswith("<!doctype"):
        if bruto.lower().lstrip().startswith("<html"):
            bruto = "<!DOCTYPE html>\n" + bruto
    return bruto


def montar_user_infografico(
    material: str,
    *,
    publico: str = PUBLICO_PADRAO,
) -> str:
    return (
        "Antes de gerar o infográfico:\n"
        "1. Leia todo o material.\n"
        "2. Identifique os conceitos principais.\n"
        "3. Remova informações redundantes ou pouco úteis.\n"
        "4. Organize o conteúdo na estrutura fixa da skill.\n"
        "5. Escolha ícones Lucide, cores e blocos adequados ao tema.\n"
        "6. Só então gere o HTML final (somente o HTML, sem markdown).\n\n"
        f"Público-alvo: {publico}\n\n"
        "### Material de entrada\n\n"
        f"{material.strip()}"
    )


def gerar_html_infografico_visual(
    caminhos: list[Path],
    especificacoes: str = "",
    *,
    publico: str = PUBLICO_PADRAO,
    idioma: str = "pt-BR",
) -> Path:
    """Lê as fontes, pede ao LLM o HTML da skill e grava em outputs/."""
    if not get_api_key():
        raise RuntimeError("Chave de API do provedor LLM não configurada.")
    if not caminhos:
        raise ValueError("Nenhuma fonte selecionada.")

    from core.especificacoes_llm import anexar_especificacoes

    material = _texto_fontes(caminhos)
    if not material.strip():
        raise ValueError("Fontes vazias.")

    user = anexar_especificacoes(
        montar_user_infografico(material, publico=publico), especificacoes
    )
    skill_body = corpo_skill("infografico-visual")
    system = SYSTEM_INFOGRAFICO_VISUAL.format(idioma=idioma)
    if skill_body:
        system = f"{system}\n\n### Skill `infografico-visual`\n{skill_body}"

    raw = chat_completion(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user[:120000]},
        ],
        temperature=0.35,
    )
    html = _extrair_html(raw)

    ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = OUTPUTS_DIR / f"infografico_visual_{stamp}.html"
    destino.write_text(html, encoding="utf-8")
    return destino
