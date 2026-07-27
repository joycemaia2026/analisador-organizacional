"""NLP local para análise de transcrições (sem dependências pesadas)."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

PT_STOPWORDS = {
    "a", "o", "e", "de", "da", "do", "das", "dos", "em", "no", "na", "nos", "nas",
    "um", "uma", "uns", "umas", "para", "por", "com", "sem", "sob", "sobre", "entre",
    "que", "se", "não", "nao", "mais", "menos", "muito", "muita", "como", "quando",
    "onde", "quem", "qual", "quais", "isso", "isto", "esse", "essa", "este", "esta",
    "ele", "ela", "eles", "elas", "nós", "nos", "você", "voce", "vocês", "voces",
    "meu", "minha", "seu", "sua", "dele", "dela", "já", "ja", "também", "tambem",
    "ser", "estar", "ter", "foi", "são", "sao", "está", "esta", "estão", "estao",
    "há", "ha", "tem", "tinha", "vai", "vou", "aqui", "ali", "lá", "la", "então",
    "entao", "mas", "ou", "até", "ate", "porque", "pois", "ainda", "só", "so",
    "bem", "mal", "sim", "tudo", "nada", "algo", "cada", "outro", "outra", "outros",
    "outras", "mesmo", "mesma", "próprio", "proprio", "própria", "propria", "todos",
    "todas", "todo", "toda", "gente", "coisa", "coisas", "dia", "dias", "vez", "vezes",
    "fazer", "feito", "faz", "dizer", "disse", "falar", "falou", "ver", "vê", "ve",
    "dar", "deu", "saber", "sabe", "precisa", "precisar", "pode", "podem", "poder",
    "quero", "quer", "querem", "vamos", "tipo", "assim", "né", "ne", "tá", "ta",
    "aí", "ai", "ah", "oh", "hum", "hã", "ok", "okay", "obrigado", "obrigada",
}

POSITIVE_WORDS = {
    "bom", "boa", "ótimo", "otimo", "excelente", "positivo", "sucesso", "concluído",
    "concluido", "resolvido", "aprovado", "eficiente", "rápido", "rapido", "fácil",
    "facil", "melhor", "melhoria", "avanço", "avanco", "progresso", "solução", "solucao",
    "funciona", "funcionou", "agradável", "agradavel", "feliz", "satisfeito", "útil", "util",
}

NEGATIVE_WORDS = {
    "ruim", "péssimo", "pessimo", "problema", "problemas", "erro", "erros", "falha",
    "falhas", "difícil", "dificil", "lento", "atraso", "atrasos", "crítico", "critico",
    "urgente", "bloqueio", "bloqueado", "impossível", "impossivel", "frustrante",
    "insatisfeito", "preocupante", "risco", "riscos", "gargalo", "gargalos", "manual",
    "repetitivo", "repetitiva", "demora", "demorado", "confuso", "confusão", "confusao",
}

GIRIAS = {
    "tipo", "mano", "cara", "galera", "beleza", "massa", "show", "top", "blz",
    "vlw", "flw", "tb", "tbm", "pq", "vc", "vcs", "né", "ne", "tá", "ta", "bora",
    "fechou", "valeu", "tmj", "pô", "po", "caramba", "nossa", "trampo", "rolê", "role",
}

PALAVROES = {
    "porra", "caralho", "cacete", "merda", "bosta", "puta", "puto", "fdp",
    "inferno", "droga", "babaca", "idiota", "imbecil", "pqp", "vsf", "foda",
}

ACAO_WORDS = {
    "fazer", "definir", "priorizar", "entregar", "revisar", "validar", "aprovar",
    "implementar", "corrigir", "acompanhar", "agendar", "decidir", "enviar",
    "abrir", "fechar", "resolver", "planejar", "testar", "deploy", "migrar",
}


def preprocess_transcript(text: str) -> str:
    text = re.sub(r"\[\d{1,2}:\d{2}(:\d{2})?\]", " ", text)
    text = re.sub(r"^\s*\w[\w\s]*:\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> list[str]:
    text = preprocess_transcript(text.lower())
    tokens = re.findall(r"[a-záàâãéêíóôõúüç]{3,}", text, flags=re.IGNORECASE)
    return [t for t in tokens if t not in PT_STOPWORDS]


def _normalize(word: str) -> str:
    word = word.lower().strip()
    word = unicodedata.normalize("NFKD", word)
    return "".join(c for c in word if not unicodedata.combining(c))


def _frases(text: str) -> list[str]:
    bruto = preprocess_transcript(text)
    partes = re.split(r"(?<=[.!?])\s+|\n+", bruto)
    return [p.strip() for p in partes if len(p.strip().split()) >= 3]


def _detectar_falantes(text: str) -> list[dict]:
    """Conta falas no padrão 'Nome:' no início de linha."""
    contagem: Counter[str] = Counter()
    for linha in (text or "").splitlines():
        m = re.match(r"^\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s.'-]{1,40})\s*:\s+\S", linha)
        if not m:
            continue
        nome = m.group(1).strip()
        if len(nome.split()) > 5:
            continue
        baixo = nome.lower()
        if baixo in {"http", "https", "www", "timestamp", "speaker"}:
            continue
        contagem[nome] += 1
    return [
        {"falante": nome, "falas": n}
        for nome, n in contagem.most_common(12)
    ]


def analyze_sentiment(text: str) -> dict:
    tokens = tokenize(text)
    if not tokens:
        return {
            "positive": 0.0,
            "negative": 0.0,
            "neutral": 1.0,
            "compound": 0.0,
            "label": "neutro",
            "polarized_sentences": [],
            "pos_hits": 0,
            "neg_hits": 0,
        }

    pos = sum(1 for t in tokens if t in POSITIVE_WORDS)
    neg = sum(1 for t in tokens if t in NEGATIVE_WORDS)
    total = pos + neg or 1
    positive = pos / total
    negative = neg / total
    neutral = max(0.0, 1.0 - positive - negative)
    compound = (pos - neg) / max(len(tokens), 1)

    if compound > 0.05:
        label = "positivo"
    elif compound < -0.05:
        label = "negativo"
    else:
        label = "neutro"

    polarized = []
    for sentence in _frases(text):
        stokens = tokenize(sentence)
        if not stokens:
            continue
        spos = sum(1 for t in stokens if t in POSITIVE_WORDS)
        sneg = sum(1 for t in stokens if t in NEGATIVE_WORDS)
        score = (spos - sneg) / len(stokens)
        if abs(score) >= 0.1:
            polarized.append(
                {
                    "sentence": sentence[:200],
                    "score": round(score, 3),
                    "polarity": "positivo" if score > 0 else "negativo",
                }
            )

    polarized.sort(key=lambda x: abs(x["score"]), reverse=True)
    return {
        "positive": round(positive, 3),
        "negative": round(negative, 3),
        "neutral": round(neutral, 3),
        "compound": round(compound, 3),
        "label": label,
        "polarized_sentences": polarized[:8],
        "pos_hits": pos,
        "neg_hits": neg,
    }


def _perfil_linguistico(text: str) -> dict:
    tokens_raw = re.findall(
        r"[a-záàâãéêíóôõúüç]{2,}",
        preprocess_transcript(text.lower()),
        flags=re.IGNORECASE,
    )
    if not tokens_raw:
        return {
            "nivel_formalidade": "indefinido",
            "perfil_comunicacao": "sem dados suficientes",
            "girias": [],
            "palavroes": [],
            "taxa_informalidade_pct": 0.0,
        }

    girias_norm = {_normalize(w) for w in GIRIAS}
    palavroes_norm = {_normalize(w) for w in PALAVROES}
    girias_c: Counter[str] = Counter()
    palavroes_c: Counter[str] = Counter()
    for t in tokens_raw:
        n = _normalize(t)
        if n in girias_norm:
            girias_c[t] += 1
        if n in palavroes_norm:
            palavroes_c[t] += 1

    informal = sum(girias_c.values()) + sum(palavroes_c.values())
    rate = 100.0 * informal / max(len(tokens_raw), 1)
    has_profanity = bool(palavroes_c)

    if has_profanity and rate > 8:
        formalidade = "muito informal"
    elif rate > 5 or has_profanity:
        formalidade = "informal"
    elif rate > 2:
        formalidade = "semi-formal"
    else:
        formalidade = "formal"

    if has_profanity:
        perfil = "comunicação direta e coloquial (com linguagem forte)"
    elif rate > 3:
        perfil = "comunicação coloquial / conversacional"
    else:
        perfil = "comunicação objetiva / profissional"

    return {
        "nivel_formalidade": formalidade,
        "perfil_comunicacao": perfil,
        "girias": [{"palavra": w, "ocorrencias": c} for w, c in girias_c.most_common(10)],
        "palavroes": [
            {"palavra": w, "ocorrencias": c} for w, c in palavroes_c.most_common(10)
        ],
        "taxa_informalidade_pct": round(rate, 2),
    }


def _estatisticas(text: str, tokens: list[str]) -> dict:
    chars = len(text or "")
    palavras_brutas = re.findall(r"\b\w+\b", text or "", flags=re.UNICODE)
    frases = _frases(text)
    n_palavras = len(palavras_brutas)
    n_frases = len(frases) or 1
    unicos = len(set(tokens))
    densidade = (100.0 * unicos / len(tokens)) if tokens else 0.0
    media_frase = n_palavras / n_frases
    media_tam_token = (
        sum(len(t) for t in tokens) / len(tokens) if tokens else 0.0
    )
    acoes = Counter(t for t in tokens if t in ACAO_WORDS)
    bigrams: Counter[str] = Counter()
    for i in range(len(tokens) - 1):
        bigrams[f"{tokens[i]} {tokens[i + 1]}"] += 1

    return {
        "caracteres": chars,
        "palavras_brutas": n_palavras,
        "tokens_uteis": len(tokens),
        "vocabulario_unico": unicos,
        "diversidade_lexical_pct": round(densidade, 1),
        "frases": len(frases),
        "media_palavras_por_frase": round(media_frase, 1),
        "media_tamanho_token": round(media_tam_token, 1),
        "verbos_acao_top": [
            {"palavra": w, "count": c} for w, c in acoes.most_common(8)
        ],
        "bigramas_top": [
            {"bigrama": b, "count": c} for b, c in bigrams.most_common(12)
        ],
        "falantes": _detectar_falantes(text),
    }


def run_nlp_analysis(text: str) -> dict:
    """Retorna sentimento, frequências, perfil e estatísticas."""
    tokens = tokenize(text)
    freq = Counter(tokens)
    top_words = [{"word": w, "count": c} for w, c in freq.most_common(20)]
    sentiment = analyze_sentiment(text)
    outras = _perfil_linguistico(text)
    stats = _estatisticas(text, tokens)
    return {
        "sentiment": sentiment,
        "word_frequencies": top_words,
        "tokens_analisados": len(tokens),
        "outras": outras,
        "estatisticas": stats,
    }


def nlp_para_markdown(nlp: dict) -> str:
    """Formata o resultado NLP como seção Markdown da ata."""
    sent = nlp.get("sentiment") or {}
    palavras = nlp.get("word_frequencies") or []
    outras = nlp.get("outras") or {}
    stats = nlp.get("estatisticas") or {}
    linhas = [
        "## Análise NLP",
        "",
        "### Sentimento",
        f"- Rótulo: **{sent.get('label', '—')}**",
        f"- Compound: {sent.get('compound', '—')}",
        f"- Positivo: {sent.get('positive', '—')} · Negativo: {sent.get('negative', '—')} · "
        f"Neutro: {sent.get('neutral', '—')}",
        f"- Hits léxico: +{sent.get('pos_hits', 0)} / −{sent.get('neg_hits', 0)}",
        "",
        "### Estatísticas da transcrição",
        f"- Palavras (brutas): **{stats.get('palavras_brutas', '—')}**",
        f"- Tokens úteis (sem stopwords): **{stats.get('tokens_uteis', '—')}**",
        f"- Vocabulário único: **{stats.get('vocabulario_unico', '—')}** "
        f"({stats.get('diversidade_lexical_pct', '—')}% diversidade)",
        f"- Frases: **{stats.get('frases', '—')}** · "
        f"média **{stats.get('media_palavras_por_frase', '—')}** palavras/frase",
        f"- Tamanho médio do token: {stats.get('media_tamanho_token', '—')} chars",
        "",
        "### Perfil linguístico",
        f"- Formalidade: **{outras.get('nivel_formalidade', '—')}** "
        f"(taxa informalidade {outras.get('taxa_informalidade_pct', '—')}%)",
        f"- Perfil: {outras.get('perfil_comunicacao', '—')}",
        "",
        "### Palavras mais frequentes",
    ]
    if palavras:
        for item in palavras[:15]:
            linhas.append(f"- {item['word']} ({item['count']})")
    else:
        linhas.append("- (sem palavras suficientes)")

    bigramas = stats.get("bigramas_top") or []
    if bigramas:
        linhas.extend(["", "### Bigramas mais frequentes"])
        for b in bigramas[:10]:
            linhas.append(f"- {b['bigrama']} ({b['count']})")

    acoes = stats.get("verbos_acao_top") or []
    if acoes:
        linhas.extend(["", "### Verbos de ação"])
        for a in acoes:
            linhas.append(f"- {a['palavra']} ({a['count']})")

    falantes = stats.get("falantes") or []
    if falantes:
        linhas.extend(["", "### Falantes detectados"])
        for f in falantes[:8]:
            linhas.append(f"- {f['falante']}: {f['falas']} falas")

    polarizadas = sent.get("polarized_sentences") or []
    if polarizadas:
        linhas.extend(["", "### Frases polarizadas"])
        for p in polarizadas[:5]:
            linhas.append(
                f"- [{p.get('polarity', '')} · {p.get('score', '')}] {p.get('sentence', '')}"
            )

    girias = outras.get("girias") or []
    if girias:
        linhas.extend(["", "### Gírias detectadas"])
        for g in girias[:8]:
            linhas.append(f"- {g['palavra']} ({g['ocorrencias']})")

    return "\n".join(linhas).strip()
