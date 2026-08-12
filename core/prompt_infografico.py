"""Prompt de infográfico — arco canônico de 6 casas, válido para qualquer conteúdo.

O documento-fonte pode ser de qualquer gênero (spec, relatório, plano, política,
manual). A estrutura do poster NÃO acompanha a estrutura da fonte: o conteúdo é
reancorado no arco ORIGEM → MECANISMO → RESULTADO → DESTINATÁRIO → CREDIBILIDADE
→ FICHA TÉCNICA, que é a ordem em que um leitor novo precisa receber a informação.

Casa sem matéria-prima na fonte é omitida; a ordem das demais nunca muda.

Derivação e evidência: .claude/skills/infografico/references/prompt-gerador.md
"""

from __future__ import annotations

from typing import Any

# --------------------------------------------------------------------------- #
# Arco canônico
# --------------------------------------------------------------------------- #

CASAS: tuple[str, ...] = (
    "ORIGEM",
    "MECANISMO",
    "RESULTADO",
    "DESTINATARIO",
    "CREDIBILIDADE",
    "FICHA_TECNICA",
)

PERGUNTA_DA_CASA: dict[str, str] = {
    "ORIGEM": "de onde vem a matéria-prima",
    "MECANISMO": "como ela é transformada",
    "RESULTADO": "o que sai daqui",
    "DESTINATARIO": "para quem serve, em que situação",
    "CREDIBILIDADE": "por que confiar nisto",
    "FICHA_TECNICA": "com o que é feito",
}

# Geometria estável: cada casa ocupa sempre a mesma região do poster.
REGIAO_DA_CASA: dict[str, str] = {
    "ORIGEM": "coluna à esquerda, blocos empilhados",
    "MECANISMO": "núcleo central, card escuro em destaque",
    "RESULTADO": "coluna à direita, cards claros ligados ao núcleo",
    "DESTINATARIO": "faixa horizontal sob o núcleo",
    "CREDIBILIDADE": "faixa inferior, três provas lado a lado",
    "FICHA_TECNICA": "tabela compacta no canto inferior direito",
}

METAFORAS: dict[str, str] = {
    "funil": "funil circular (seleção, classificação)",
    "cilindro": "cilindro de banco de dados empilhado (persistência)",
    "chip": "chip hexagonal com nós e esferas (processamento, IA)",
    "esteira": "esteira transportadora (pipeline, sequência)",
    "grafo": "grafo de nós conectados (rede, base de conhecimento)",
    "regua": "régua temporal com marcos (histórico, linha do tempo)",
    "documento": "folha de documento com linhas (registro, relatório)",
    "pessoa": "silhueta de pessoa em círculo (persona, papel)",
    "escudo": "escudo com cadeado (segurança, garantia)",
    "alvo": "alvo com flecha (objetivo, foco)",
    "grafico": "gráfico de barras ascendente (métrica, resultado)",
    "engrenagem": "engrenagem (operação, automação)",
    "globo": "globo com meridianos (fonte pública, web)",
    "nuvem": "nuvem (serviço externo, hospedagem)",
    "chave": "chave (credencial, acesso)",
    "balanca": "balança de dois pratos (comparação, decisão)",
}

LIMITES: dict[str, int] = {
    "titulo_marca": 24,
    "titulo_frase": 62,
    "rubrica": 34,
    "rotulo": 34,
    "texto": 150,
    "bullet": 62,
    "celula": 60,
}

PUBLICO_PADRAO = "alguém competente que nunca ouviu falar deste assunto"

# --------------------------------------------------------------------------- #
# Chamada 1 — roteiro (conteúdo)
# --------------------------------------------------------------------------- #

SYSTEM_ROTEIRO = """\
Você monta o conteúdo textual de um infográfico de página única a partir de um documento.

Não resuma o documento. Reorganize-o no arco abaixo, que é a ordem em que um leitor
que nunca ouviu falar do assunto precisa receber a informação:

1. ORIGEM        — de onde vem a matéria-prima
2. MECANISMO     — como ela é transformada
3. RESULTADO     — o que sai
4. DESTINATARIO  — para quem serve, em que situação
5. CREDIBILIDADE — por que confiar
6. FICHA_TECNICA — com o que é feito

O documento provavelmente está organizado por outra lógica (arquitetura, capítulos,
cronologia). Ignore essa ordem. Se uma casa não tiver matéria-prima no documento,
omita a casa — nunca a preencha por conta própria e nunca altere a ordem das demais.

SELEÇÃO
- Mantenha o que um comprador ou usuário perguntaria.
- Descarte o que só um mantenedor perguntaria: modelo de dados, inventário de rotas,
  estrutura de pastas, requisitos numerados, critérios de aceite, backlog, histórico
  de versões, glossário, referências.
- Prefira todo trecho com número ou nome próprio. Quantidade e nome próprio são o que
  distingue informação de folheto.
- Nada pode aparecer duas vezes, nem parafraseado.
- Proibido: "etc.", "entre outros", "diversos", "vários", "robusto", "eficiente".

FIDELIDADE
- Não afirme nada que não esteja no documento. O que faltar vai em "lacunas".
- Preserve a grafia exata de toda sigla e nome próprio e liste todos em "glossario";
  eles não podem variar de grafia em nenhum outro campo.
- Escreva em {idioma}.

FORMA
- titulo_marca: o nome do sujeito exatamente como o documento o escreve (máx. 24 car.)
- titulo_frase: a promessa em uma linha, em Title Case (máx. 62 car.); quando o
  documento descrever uma transformação, use a fórmula "Da <origem> à <destino>"
- rubrica: máx. 34 caracteres · rotulo: máx. 34 · texto: 1 a 2 frases, máx. 150
- bullets: até 3 por bloco, máx. 62 caracteres cada
- 4 a 6 casas · 2 a 5 blocos por casa · 18 a 24 blocos no total
- exatamente uma tabela, na casa FICHA_TECNICA, até 5 linhas x 3 colunas
- a casa CREDIBILIDADE traz exatamente 3 provas
- metafora de cada bloco, escolhida entre: {metaforas}

Responda SOMENTE JSON válido:

{{
  "titulo_marca": "...",
  "titulo_frase": "...",
  "eixo": "a pergunta que o poster responde, em uma linha",
  "genero_fonte": "spec de produto | relatorio | plano | politica | manual | outro",
  "idioma": "...",
  "glossario": ["sigla ou nome próprio, grafia canônica"],
  "casas": [
    {{
      "casa": "ORIGEM",
      "rubrica": "...",
      "papel": "o início",
      "blocos": [
        {{"rotulo": "...", "texto": "...", "bullets": ["..."], "metafora": "cilindro"}}
      ]
    }}
  ],
  "tabela": {{
    "rubrica": "...",
    "colunas": ["...", "...", "..."],
    "linhas": [["...", "...", "..."]]
  }},
  "credibilidade": [{{"rotulo": "...", "texto": "..."}}],
  "lacunas": ["o que o documento não responde e por isso não virou bloco"]
}}
"""


def montar_system_roteiro(idioma: str = "pt-BR") -> str:
    """System prompt da extração, com idioma e vocabulário de metáforas resolvidos."""
    return SYSTEM_ROTEIRO.format(
        idioma=idioma,
        metaforas=", ".join(METAFORAS),
    )


def montar_user_roteiro(fontes: str, publico: str = PUBLICO_PADRAO) -> str:
    """Mensagem de usuário da extração."""
    return f"PÚBLICO: {publico.strip() or PUBLICO_PADRAO}\n\nDOCUMENTO:\n{fontes}"


# Compatibilidade com chamadores anteriores.
SYSTEM_EXTRAIR_CONTEUDO = montar_system_roteiro()

# --------------------------------------------------------------------------- #
# Leitura do roteiro
# --------------------------------------------------------------------------- #


def _txt(valor: Any, default: str = "") -> str:
    return str(valor).strip() if valor is not None and str(valor).strip() else default


def titulo_completo(roteiro: dict) -> str:
    """`Marca: Frase`, tolerante a roteiros no formato antigo (campo `titulo`)."""
    marca = _txt(roteiro.get("titulo_marca"))
    frase = _txt(roteiro.get("titulo_frase"))
    if marca and frase:
        return f"{marca}: {frase}"
    return marca or frase or _txt(roteiro.get("titulo"), "Infográfico")


def casas_presentes(roteiro: dict) -> list[dict]:
    """Casas do roteiro, na ordem canônica, ignorando nomes desconhecidos."""
    por_nome = {
        _normalizar_casa(c.get("casa")): c
        for c in roteiro.get("casas") or []
        if isinstance(c, dict)
    }
    return [por_nome[nome] for nome in CASAS if nome in por_nome]


def _normalizar_casa(valor: Any) -> str:
    """`Ficha Técnica`, `FICHA TECNICA` e `ficha_tecnica` são a mesma casa."""
    texto = _txt(valor).upper().replace(" ", "_").replace("-", "_")
    for acentuada, plana in (("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U")):
        texto = texto.replace(acentuada, plana)
    return texto


# --------------------------------------------------------------------------- #
# Validação — o linter do roteiro
# --------------------------------------------------------------------------- #


def validar_roteiro(roteiro: dict) -> list[str]:
    """Devolve a lista de problemas. Vazia = roteiro aprovado.

    Checa o que só aparece quando se olha a página como conjunto: texto repetido,
    grafia divergente de termo do glossário, campo estourado, casa fora de ordem.
    """
    problemas: list[str] = []
    casas = casas_presentes(roteiro)

    if not 4 <= len(casas) <= 6:
        problemas.append(f"casas: {len(casas)} (esperado 4 a 6)")

    for campo in ("titulo_marca", "titulo_frase"):
        valor = _txt(roteiro.get(campo))
        if len(valor) > LIMITES[campo]:
            problemas.append(f"{campo}: {len(valor)} caracteres (máx. {LIMITES[campo]})")

    vistos: dict[str, str] = {}
    total_blocos = 0
    for casa in casas:
        nome = _txt(casa.get("casa"))
        if len(_txt(casa.get("rubrica"))) > LIMITES["rubrica"]:
            problemas.append(f"{nome}: rubrica acima de {LIMITES['rubrica']} caracteres")
        blocos = [b for b in casa.get("blocos") or [] if isinstance(b, dict)]
        if not 2 <= len(blocos) <= 5:
            problemas.append(f"{nome}: {len(blocos)} blocos (esperado 2 a 5)")
        total_blocos += len(blocos)
        for bloco in blocos:
            for campo in ("rotulo", "texto"):
                valor = _txt(bloco.get(campo))
                if len(valor) > LIMITES[campo]:
                    problemas.append(
                        f"{nome}/{_txt(bloco.get('rotulo'), '?')}: {campo} com "
                        f"{len(valor)} caracteres (máx. {LIMITES[campo]})"
                    )
            texto = _txt(bloco.get("texto"))
            onde = f"{nome}/{_txt(bloco.get('rotulo'), '?')}"
            chave = " ".join(texto.lower().split())
            if chave and chave in vistos:
                problemas.append(
                    f"texto repetido em {vistos[chave]} e {onde}: {texto[:60]}…"
                )
            elif chave:
                vistos[chave] = onde
            bullets = [b for b in bloco.get("bullets") or [] if _txt(b)]
            if len(bullets) > 3:
                problemas.append(f"{nome}: {len(bullets)} bullets (máx. 3)")
            for bullet in bullets:
                if len(_txt(bullet)) > LIMITES["bullet"]:
                    problemas.append(f"{nome}: bullet acima de {LIMITES['bullet']} car.")
            metafora = _txt(bloco.get("metafora"))
            if metafora and metafora not in METAFORAS:
                problemas.append(f"{nome}: metáfora fora do vocabulário: {metafora}")

    if total_blocos and not 18 <= total_blocos <= 24:
        problemas.append(f"total de blocos: {total_blocos} (esperado 18 a 24)")

    provas = [p for p in roteiro.get("credibilidade") or [] if isinstance(p, dict)]
    if provas and len(provas) != 3:
        problemas.append(f"credibilidade: {len(provas)} provas (esperado 3)")

    tabela = roteiro.get("tabela") or {}
    linhas = [ln for ln in tabela.get("linhas") or [] if isinstance(ln, (list, tuple))]
    if len(linhas) > 5:
        problemas.append(f"tabela: {len(linhas)} linhas (máx. 5)")
    for linha in linhas:
        for celula in linha:
            if len(_txt(celula)) > LIMITES["celula"]:
                problemas.append(f"tabela: célula acima de {LIMITES['celula']} car.")

    problemas.extend(_conferir_glossario(roteiro, casas))
    return problemas


def _conferir_glossario(roteiro: dict, casas: list[dict]) -> list[str]:
    """Termo do glossário escrito com outra caixa em algum campo é grafia divergente."""
    termos = [_txt(t) for t in roteiro.get("glossario") or [] if _txt(t)]
    if not termos:
        return []
    corpo: list[str] = []
    for casa in casas:
        for bloco in casa.get("blocos") or []:
            if isinstance(bloco, dict):
                corpo.append(_txt(bloco.get("rotulo")))
                corpo.append(_txt(bloco.get("texto")))
                corpo.extend(_txt(b) for b in bloco.get("bullets") or [])
    for linha in (roteiro.get("tabela") or {}).get("linhas") or []:
        if isinstance(linha, (list, tuple)):
            corpo.extend(_txt(c) for c in linha)
    texto = " ".join(corpo)
    baixo = texto.lower()
    problemas: list[str] = []
    for termo in termos:
        if termo.lower() in baixo and termo not in texto:
            problemas.append(f"glossário: '{termo}' aparece com outra grafia no corpo")
    return problemas


# --------------------------------------------------------------------------- #
# Chamada 2 — prompt visual (só quando o destino é imagem)
# --------------------------------------------------------------------------- #

_CABECALHO = """\
Crie um infográfico horizontal (proporção 16:9, alta resolução) em {idioma}, \
com estética corporativa moderna e limpa, estilo "diagrama de arquitetura".

Título no topo (sans-serif bold, escura):
"{titulo}"

O poster tem {n_casas} faixas de conteúdo, nesta ordem de leitura:
"""

_DIRETRIZES = """\

Diretrizes visuais:

Fundo branco levemente azulado (#F4F9FB)
Paleta: azul-marinho, verde-água, roxo suave, laranja como acento
Conectores: curvas grossas e suaves com gradiente, nunca linhas retas
Cards brancos com cantos arredondados e sombra sutil
Ícones ilustrativos coloridos em estilo flat moderno, não fotorrealistas
Espaçamento generoso, hierarquia tipográfica clara
Todo o texto legível, transcrito exatamente como escrito acima, \
sem palavras inventadas, abreviadas ou distorcidas
"""


def montar_prompt_visual(roteiro: dict) -> str:
    """Monta o prompt de imagem a partir do roteiro, iterando as casas presentes.

    Cada casa ocupa sempre a mesma região do poster (ver REGIAO_DA_CASA), então a
    geometria é estável mesmo quando o documento não sustenta todas as casas.
    """
    casas = casas_presentes(roteiro)
    partes = [
        _CABECALHO.format(
            idioma=_txt(roteiro.get("idioma"), "português brasileiro"),
            titulo=titulo_completo(roteiro),
            n_casas=len(casas) + (1 if roteiro.get("tabela") else 0),
        )
    ]

    for indice, casa in enumerate(casas, start=1):
        nome = _txt(casa.get("casa")).upper()
        rubrica = _txt(casa.get("rubrica"), nome.title())
        papel = _txt(casa.get("papel"))
        cabecalho = f'{indice}) "{rubrica}"'
        if papel:
            cabecalho += f' — subtítulo entre parênteses: "({papel})"'
        regiao = REGIAO_DA_CASA.get(nome, "faixa horizontal")
        partes.append(f"\n{cabecalho}\n   Posição: {regiao}.")

        for bloco in casa.get("blocos") or []:
            if not isinstance(bloco, dict):
                continue
            rotulo = _txt(bloco.get("rotulo"), "—")
            texto = _txt(bloco.get("texto"))
            icone = METAFORAS.get(_txt(bloco.get("metafora")), "")
            linha = f"   • {rotulo}"
            if texto:
                linha += f": {texto}"
            if icone:
                linha += f"  [ícone: {icone}]"
            partes.append(linha)
            for bullet in bloco.get("bullets") or []:
                if _txt(bullet):
                    partes.append(f"      – {_txt(bullet)}")

    provas = [p for p in roteiro.get("credibilidade") or [] if isinstance(p, dict)]
    if provas:
        partes.append("\nFaixa de fechamento — três provas lado a lado:")
        for prova in provas:
            partes.append(
                f"   • {_txt(prova.get('rotulo'), '—')}: {_txt(prova.get('texto'))}"
            )

    tabela = roteiro.get("tabela") or {}
    linhas = [ln for ln in tabela.get("linhas") or [] if isinstance(ln, (list, tuple))]
    if linhas:
        colunas = [_txt(c) for c in tabela.get("colunas") or []]
        partes.append(
            f"\nTabela compacta no canto inferior direito — "
            f'"{_txt(tabela.get("rubrica"), "Ficha técnica")}", '
            f"cabeçalho azul-marinho com texto branco:"
        )
        if colunas:
            partes.append("   | " + " | ".join(colunas) + " |")
        for linha in linhas:
            partes.append("   | " + " | ".join(_txt(c) for c in linha) + " |")

    partes.append(_DIRETRIZES)
    return "\n".join(partes)


# Compatibilidade com chamadores anteriores.
montar_prompt_infografico = montar_prompt_visual
