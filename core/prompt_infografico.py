"""Prompt de infográfico corporativo (estilo diagrama de arquitetura de produto de IA)."""

from __future__ import annotations

PROMPT_INFOGRAFICO_BASE = """\
Crie um infográfico horizontal (proporção 16:9, alta resolução) em português brasileiro, \
com estética corporativa moderna e limpa, estilo "diagrama de arquitetura de produto de IA".

Título no topo (fonte sans-serif bold, escura):
"{titulo}"

Estrutura de fluxo da esquerda para a direita:

Coluna esquerda — "Fontes de Dados" (rótulo vertical na lateral): três blocos empilhados, \
cada um com um ícone ilustrado colorido e legenda em negrito com subtítulo entre parênteses:
1) {fonte_1_nome} ({fonte_1_sub})
2) {fonte_2_nome} ({fonte_2_sub})
3) {fonte_3_nome} ({fonte_3_sub})

Centro — núcleo de processamento: um card escuro (azul-marinho/roxo) com título acima em negrito: \
"{nucleo_titulo}". Dentro, à esquerda, um ícone hexagonal abstrato com nós e esferas coloridas \
(laranja, verde-água, roxo) representando IA. À direita, um painel interno rotulado \
"Análise sob Lentes:" com três linhas, cada uma com ícone de funil circular colorido, \
título em negrito e subtítulo entre parênteses:
1) {lente_1_titulo} ({lente_1_sub})
2) {lente_2_titulo} ({lente_2_sub})
3) {lente_3_titulo} ({lente_3_sub})

Coluna direita — saídas principais: dois ramos que saem do núcleo por curvas suaves e grossas \
(gradiente verde-água e roxo), cada um com um ícone grande (alvo/escudo) e um card branco com \
borda arredondada e sombra leve:
1) {saida_1_titulo} — {saida_1_desc}
2) {saida_2_titulo} — {saida_2_desc}

Faixa inferior — módulos de entrega: quatro cards brancos lado a lado, conectados ao núcleo por \
linhas curvas laranja e azul que descem e se ramificam:
1) {mod_1_titulo}: {mod_1_det}
2) {mod_2_titulo}: {mod_2_det}
3) {mod_3_titulo}: {mod_3_det}
4) {mod_4_titulo}: {mod_4_det}

Rodapé — barra horizontal arredondada: metade esquerda em azul-escuro com ícone de engrenagem e \
texto: "{rodape_esq}"; metade direita em laranja com ícones de documentos (JSON, Excel, Word) e \
ícone de download: "{rodape_dir}".

Diretrizes visuais:

Fundo branco levemente azulado (#F4F9FB)
Paleta: azul-marinho, verde-água, roxo suave, laranja como acento
Conectores: curvas grossas e suaves com gradiente, nunca linhas retas
Cards brancos com cantos arredondados e sombra sutil
Ícones ilustrativos coloridos em estilo flat moderno, não fotorrealistas
Todo o texto legível, sem palavras inventadas ou distorcidas
Espaçamento generoso, hierarquia tipográfica clara
"""

SYSTEM_EXTRAIR_CONTEUDO = """\
Você monta o conteúdo textual de um infográfico de arquitetura a partir das fontes.
Responda SOMENTE JSON válido no formato:
{
  "titulo": "string curta",
  "fontes": [
    {"nome": "...", "subtitulo": "..."},
    {"nome": "...", "subtitulo": "..."},
    {"nome": "...", "subtitulo": "..."}
  ],
  "nucleo_titulo": "...",
  "lentes": [
    {"titulo": "...", "subtitulo": "..."},
    {"titulo": "...", "subtitulo": "..."},
    {"titulo": "...", "subtitulo": "..."}
  ],
  "saidas": [
    {"titulo": "...", "descricao": "..."},
    {"titulo": "...", "descricao": "..."}
  ],
  "modulos": [
    {"titulo": "...", "detalhes": "..."},
    {"titulo": "...", "detalhes": "..."},
    {"titulo": "...", "detalhes": "..."},
    {"titulo": "...", "detalhes": "..."}
  ],
  "rodape_esquerda": "duas linhas curtas sobre eficiência técnica",
  "rodape_direita": "texto curto sobre exportação / download"
}
Regras: português do Brasil; não invente fatos fora das fontes; textos curtos e legíveis.
"""


def _item(lista: list, idx: int, *keys: str, default: str = "—") -> str:
    if idx >= len(lista) or not isinstance(lista[idx], dict):
        return default
    d = lista[idx]
    for k in keys:
        v = d.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return default


def montar_prompt_infografico(dados: dict) -> str:
    """Preenche o prompt visual com o conteúdo extraído das fontes."""
    fontes = list(dados.get("fontes") or [])
    lentes = list(dados.get("lentes") or [])
    saidas = list(dados.get("saidas") or [])
    modulos = list(dados.get("modulos") or [])
    return PROMPT_INFOGRAFICO_BASE.format(
        titulo=str(dados.get("titulo") or "Análise Organizacional").strip(),
        fonte_1_nome=_item(fontes, 0, "nome"),
        fonte_1_sub=_item(fontes, 0, "subtitulo"),
        fonte_2_nome=_item(fontes, 1, "nome"),
        fonte_2_sub=_item(fontes, 1, "subtitulo"),
        fonte_3_nome=_item(fontes, 2, "nome"),
        fonte_3_sub=_item(fontes, 2, "subtitulo"),
        nucleo_titulo=str(dados.get("nucleo_titulo") or "Processamento com IA").strip(),
        lente_1_titulo=_item(lentes, 0, "titulo"),
        lente_1_sub=_item(lentes, 0, "subtitulo"),
        lente_2_titulo=_item(lentes, 1, "titulo"),
        lente_2_sub=_item(lentes, 1, "subtitulo"),
        lente_3_titulo=_item(lentes, 2, "titulo"),
        lente_3_sub=_item(lentes, 2, "subtitulo"),
        saida_1_titulo=_item(saidas, 0, "titulo"),
        saida_1_desc=_item(saidas, 0, "descricao"),
        saida_2_titulo=_item(saidas, 1, "titulo"),
        saida_2_desc=_item(saidas, 1, "descricao"),
        mod_1_titulo=_item(modulos, 0, "titulo"),
        mod_1_det=_item(modulos, 0, "detalhes"),
        mod_2_titulo=_item(modulos, 1, "titulo"),
        mod_2_det=_item(modulos, 1, "detalhes"),
        mod_3_titulo=_item(modulos, 2, "titulo"),
        mod_3_det=_item(modulos, 2, "detalhes"),
        mod_4_titulo=_item(modulos, 3, "titulo"),
        mod_4_det=_item(modulos, 3, "detalhes"),
        rodape_esq=str(dados.get("rodape_esquerda") or "Eficiência técnica e rastreabilidade").strip(),
        rodape_dir=str(dados.get("rodape_direita") or "Exportação JSON, Excel e Word").strip(),
    )
