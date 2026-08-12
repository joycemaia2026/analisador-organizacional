"""Levantamento estruturado de uma reunião — os 10 campos obrigatórios.

Sem LLM e sem I/O. Duas garantias que um prompt não dá sozinho:

1. **Nenhum campo some.** O esqueleto tem os 10 campos sempre. Campo sem
   conteúdo na reunião fica com `NAO_MENCIONADO` — um estado declarado, não uma
   seção que desapareceu porque o modelo se distraiu.
2. **Nada é inventado.** Números, links, e-mails e valores citados são extraídos
   do texto com a âncora onde aparecem. O modelo recebe a lista do que existe, em
   vez de reconstruir de memória.
"""

from __future__ import annotations

import re
from typing import Any

from modulos.ata_maker.normalizacao import (
    FALANTE_DESCONHECIDO,
    Turno,
    aplicar_sugestoes,
    corrigir_nomes_asr,
    formatar_ancora,
    resumo_estrutural,
    segmentar_turnos,
    sugerir_falantes,
)

NAO_MENCIONADO = "não mencionado na transcrição"

# Ordem e rótulo dos 10 campos. É esta lista que garante que nada é esquecido.
CAMPOS: list[tuple[str, str, str]] = [
    ("objetivo", "Objetivo da reunião", "por que ela aconteceu"),
    ("participantes", "Participantes", "quem estava presente e quem faltou"),
    ("decisoes", "Decisões tomadas", "tudo que foi definido"),
    ("tarefas", "Tarefas combinadas", "o que precisa ser feito depois"),
    ("responsaveis", "Responsáveis", "quem ficou com cada tarefa"),
    ("prazos", "Prazos", "datas ou períodos combinados"),
    ("pendencias", "Pendências", "assuntos que ficaram sem resposta"),
    ("proximos_passos", "Próximos passos", "o que acontece depois da reunião"),
    ("riscos", "Riscos ou problemas", "bloqueios, dúvidas, dependências"),
    (
        "informacoes",
        "Informações importantes",
        "números, links, nomes, documentos citados",
    ),
]

CHAVES = [chave for chave, _r, _d in CAMPOS]

_RE_URL = re.compile(r"\bhttps?://[^\s<>\"']+|\bwww\.[^\s<>\"']+", re.IGNORECASE)
_RE_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
_RE_DINHEIRO = re.compile(
    r"\bR\$ ?\d[\d.]*(?:,\d{2})?|\b\d[\d.]*(?:,\d{2})? ?(?:reais|mil|milh(?:ão|ões))\b",
    re.IGNORECASE,
)
_RE_PERCENTUAL = re.compile(r"\b\d{1,3}(?:,\d+)? ?%")
_RE_NUMERO = re.compile(r"(?<![\w./-])\d{2,}(?![\w./-])")
# Timestamp (mm:ss / h:mm:ss) — mascarado antes de caçar números soltos.
_RE_TIMESTAMP = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")
# Documento só com ID ou qualificador — nunca a palavra sozinha nem "ticket ontem".
_RE_DOCUMENTO = re.compile(
    r"\b(?:contrato|planilha|documento|relatório|relatorio|ata|proposta|ticket|"
    r"chamado|apresentação|apresentacao|SLA|NDA|PDF|dashboard)\b"
    r"(?:"
    r"\s+(?:n[ºo°]?\.?|#)\s*\d[\w.-]*"
    r"|\s+\d[\w.-]*"
    r"|\s+(?:de|da|do|com|para|sobre|por|prevê|preve)\s+[\wÀ-ÿ%-]+"
    r")",
    re.IGNORECASE,
)

# Pistas de quantidade/unidade perto de um número curto (2 dígitos).
_CUES_NUMERO = (
    "ticket", "tickets", "chamado", "chamados", "hora", "horas", "dia", "dias",
    "semana", "semanas", "mês", "mes", "meses", "pessoa", "pessoas", "cliente",
    "clientes", "item", "itens", "ponto", "pontos", "vez", "vezes", "porcento",
    "minuto", "minutos", "real", "reais", "mil", "milhão", "milhao", "milhões",
)


def _mascara_timestamps(texto: str) -> str:
    """Troca mm:ss por espaços do mesmo tamanho — evita virar 'número'."""
    return _RE_TIMESTAMP.sub(lambda m: " " * len(m.group(0)), texto or "")


def _numero_util(texto_turno: str, match: re.Match[str]) -> bool:
    """True só para quantidade/ID com sentido — não fragmento de relógio."""
    valor = match.group(0)
    # 00, 01…09 sozinhos quase sempre são pedaço de timestamp.
    if re.fullmatch(r"0\d", valor):
        return False
    # 1–2 dígitos: exigem pista semântica perto (tickets, horas, etc.).
    if len(valor) <= 2:
        janela = texto_turno[
            max(0, match.start() - 40) : match.end() + 40
        ].casefold()
        if not any(c in janela for c in _CUES_NUMERO):
            return False
    return True


def _documento_util(valor: str) -> bool:
    """Rejeita palavra solta ('contrato'); mantém 'contrato de SLA' / 'ticket 47'."""
    return len(valor.split()) >= 2


def esqueleto_levantamento() -> dict[str, Any]:
    """Os 10 campos, todos presentes, todos declarados como não mencionados.

    É o ponto de partida obrigatório: preencher o que a reunião trouxe e deixar o
    resto como está. Nunca montar o dicionário do zero.
    """
    return {chave: NAO_MENCIONADO for chave in CHAVES}


def campo_vazio(valor: Any) -> bool:
    """True quando o campo não tem conteúdo real — inclusive lista vazia."""
    if valor is None:
        return True
    if isinstance(valor, str):
        return not valor.strip() or valor.strip() == NAO_MENCIONADO
    if isinstance(valor, (list, tuple, dict)):
        return len(valor) == 0
    return False


def normalizar_levantamento(dados: dict[str, Any] | None) -> dict[str, Any]:
    """Completa campos faltantes e converte vazio em `NAO_MENCIONADO`.

    Aceita o dicionário parcial que o modelo devolveu e devolve um completo. Campo
    que veio como `[]`, `""` ou `None` vira o texto declarado — nunca some.
    """
    base = esqueleto_levantamento()
    for chave, valor in (dados or {}).items():
        if chave not in base:
            continue
        base[chave] = NAO_MENCIONADO if campo_vazio(valor) else valor
    return base


def validar_levantamento(dados: dict[str, Any] | None) -> list[str]:
    """Problemas estruturais. Lista vazia significa levantamento bem formado."""
    problemas: list[str] = []
    d = dados or {}

    faltando = [c for c in CHAVES if c not in d]
    if faltando:
        problemas.append(f"campos ausentes: {', '.join(faltando)}")

    extras = [c for c in d if c not in CHAVES]
    if extras:
        problemas.append(f"campos fora do schema: {', '.join(extras)}")

    for chave in CHAVES:
        valor = d.get(chave)
        if chave in d and campo_vazio(valor) and valor != NAO_MENCIONADO:
            problemas.append(
                f"'{chave}' está vazio mas não foi declarado como "
                f"'{NAO_MENCIONADO}'"
            )
    return problemas


# --------------------------------------------------------------------------- #
# Extração determinística
# --------------------------------------------------------------------------- #


def _achados_do_turno(turno: Turno) -> list[dict[str, str]]:
    achados: list[dict[str, str]] = []
    ancora = formatar_ancora(turno.inicio_seg)
    texto = turno.texto or ""
    texto_numeros = _mascara_timestamps(texto)
    tipos = (
        ("link", _RE_URL, texto),
        ("e-mail", _RE_EMAIL, texto),
        ("valor", _RE_DINHEIRO, texto),
        ("percentual", _RE_PERCENTUAL, texto),
        ("documento", _RE_DOCUMENTO, texto),
        ("número", _RE_NUMERO, texto_numeros),
    )
    ja_visto: set[tuple[str, str]] = set()
    for rotulo, padrao, corpus in tipos:
        for m in padrao.finditer(corpus):
            valor = m.group(0).strip()
            if not valor or (rotulo, valor.lower()) in ja_visto:
                continue
            if rotulo == "número" and not _numero_util(texto, m):
                continue
            if rotulo == "documento" and not _documento_util(valor):
                continue
            ja_visto.add((rotulo, valor.lower()))
            inicio = max(0, m.start() - 45)
            achados.append(
                {
                    "tipo": rotulo,
                    "valor": valor,
                    "ancora": ancora,
                    "contexto": texto[inicio : m.end() + 45].strip(),
                }
            )
    return achados


def extrair_mencoes_objetivas(turnos: list[Turno], *, limite: int = 15) -> list[dict]:
    """Números, links, e-mails, valores e documentos citados — só o útil.

    Guardrails:
    - timestamps (mm:ss) não viram "número";
    - número curto (1–2 dígitos) só com pista de quantidade perto;
    - documento exige qualificador ("contrato de SLA"), não a palavra sozinha;
    - teto baixo (15) para não inundar o levantamento.
    """
    unicos: dict[tuple[str, str], dict] = {}
    for turno in turnos:
        for achado in _achados_do_turno(turno):
            chave = (achado["tipo"], achado["valor"].lower())
            if chave in unicos:
                unicos[chave]["ocorrencias"] += 1
                continue
            unicos[chave] = {**achado, "ocorrencias": 1}
            if len(unicos) >= limite:
                return list(unicos.values())
    return list(unicos.values())


def turnos_do_artefato(turnos_dict: list[dict]) -> list[Turno]:
    """Reconstrói os `Turno` a partir do JSON da transcrição processada.

    Existe para o levantamento **não** re-segmentar nada: o artefato do
    processamento já resolveu falante e âncora, e reparsear o markdown dele
    perderia exatamente essa informação.
    """
    from modulos.ata_maker.normalizacao import ts_para_segundos

    turnos: list[Turno] = []
    for i, d in enumerate(turnos_dict or []):
        falante = d.get("falante")
        if falante == FALANTE_DESCONHECIDO:
            falante = None
        inicio = d.get("inicio_seg")
        if inicio is None and d.get("ancora"):
            inicio = ts_para_segundos(str(d["ancora"]))
        turnos.append(
            Turno(
                indice=d.get("indice", i),
                texto=d.get("texto", ""),
                inicio_seg=inicio,
                falante=falante,
                origem_falante=d.get("origem_falante", "desconhecido"),
                confianca=float(d.get("confianca") or 0.0),
            )
        )
    return turnos


def preencher_do_processamento(
    dados_processamento: dict[str, Any], nomes_conhecidos: list[str] | None = None
) -> dict[str, Any]:
    """Caminho normal: preenche a partir do artefato da skill `processamento`.

    Aceita o dict de `processamento.processar` (ou o `.dados` de um
    `Processamento` carregado do disco).
    """
    turnos = turnos_do_artefato(dados_processamento.get("turnos") or [])
    return _preencher_de_turnos(turnos, list(nomes_conhecidos or []))


def preencher_deterministico(
    texto: str, nomes_conhecidos: list[str] | None = None
) -> dict[str, Any]:
    """Mesma coisa, partindo do texto bruto — para quem ainda não processou.

    Prefira `preencher_do_processamento`: aqui a segmentação é refeita, e refazer
    pode divergir do que a skill `processamento` decidiu sobre os falantes.
    """
    nomes = list(nomes_conhecidos or [])
    corrigido = corrigir_nomes_asr(texto, nomes).texto
    turnos = segmentar_turnos(corrigido)
    aplicar_sugestoes(turnos, sugerir_falantes(turnos, nomes))
    return _preencher_de_turnos(turnos, nomes)


def _preencher_de_turnos(turnos: list[Turno], nomes: list[str]) -> dict[str, Any]:
    """Os dois campos que se apuram sem interpretar a conversa.

    `participantes` (quem falou e quem foi citado sem falar) e as menções
    objetivas de `informacoes`. Os outros oito exigem ler a reunião.
    """
    resumo = resumo_estrutural(turnos, nomes)

    base = esqueleto_levantamento()

    presentes = resumo["participantes"]
    ausentes = resumo["citados_sem_falar"]
    if presentes or ausentes:
        base["participantes"] = {
            "presentes": presentes or NAO_MENCIONADO,
            "citados_sem_falar": ausentes or NAO_MENCIONADO,
            "turnos_sem_falante": resumo["turnos_sem_falante"],
        }

    mencoes = extrair_mencoes_objetivas(turnos)
    if mencoes:
        base["informacoes"] = mencoes

    return base


# --------------------------------------------------------------------------- #
# Saída
# --------------------------------------------------------------------------- #


def _formatar_mencao(item: dict) -> str:
    """Linha legível: valor útil + tipo + âncora; sem lixo de contagem."""
    valor = str(item.get("valor") or "").strip()
    tipo = str(item.get("tipo") or "").strip()
    ancora = str(item.get("ancora") or "").strip()
    ctx = str(item.get("contexto") or "").strip()
    partes = [valor]
    if tipo:
        partes.append(f"({tipo})")
    if ancora and ancora != "??:??":
        partes.append(f"[t={ancora}]")
    linha = " ".join(partes)
    if ctx and ctx.casefold() != valor.casefold():
        # Trecho curto para o leitor validar — sem despejar a fala inteira.
        trecho = ctx if len(ctx) <= 90 else ctx[:87] + "…"
        linha = f"{linha} — {trecho}"
    return f"- {linha}"


def _formatar_valor(valor: Any) -> list[str]:
    if isinstance(valor, str):
        return [valor]
    if isinstance(valor, dict):
        linhas = []
        for chave, item in valor.items():
            rotulo = chave.replace("_", " ").capitalize()
            if isinstance(item, list):
                conteudo = ", ".join(str(x) for x in item) if item else NAO_MENCIONADO
            else:
                conteudo = str(item)
            linhas.append(f"- {rotulo}: {conteudo}")
        return linhas
    if isinstance(valor, (list, tuple)):
        linhas = []
        for item in valor:
            if isinstance(item, dict) and ("valor" in item or "tipo" in item):
                linhas.append(_formatar_mencao(item))
            elif isinstance(item, dict):
                partes = [
                    str(v)
                    for k, v in item.items()
                    if k not in {"contexto", "ocorrencias"} and v
                ]
                linhas.append(f"- {' · '.join(partes)}")
            else:
                linhas.append(f"- {item}")
        return linhas
    return [str(valor)]


def levantamento_para_markdown(dados: dict[str, Any] | None) -> str:
    """Os 10 campos em Markdown, na ordem, sempre todos — vazios inclusive."""
    completo = normalizar_levantamento(dados)
    linhas: list[str] = ["## Levantamento da reunião", ""]
    for chave, rotulo, ajuda in CAMPOS:
        valor = completo[chave]
        linhas.append(f"### {rotulo}")
        if campo_vazio(valor) or valor == NAO_MENCIONADO:
            linhas.append(f"_{NAO_MENCIONADO}_ ({ajuda})")
        else:
            linhas.extend(_formatar_valor(valor))
        linhas.append("")
    return "\n".join(linhas).strip()
