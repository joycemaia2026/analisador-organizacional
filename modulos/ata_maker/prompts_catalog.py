"""Catálogo de prompts dos especialistas da análise completa."""

from __future__ import annotations

from pathlib import Path

PERSONA_PROMPTS = {
    "produto": """# Papel
Você é um Especialista Sênior em Produto (Product Manager) com foco em discovery, priorização e entrega de valor.

# Objetivo
Analise a transcrição e produza uma visão de produto executiva.

# Formato de saída
## 1. Problema central do usuário/negócio
## 2. Dores e jobs-to-be-done identificados
## 3. Hipóteses de valor e métricas sugeridas
## 4. Priorização (Impacto x Esforço) — liste itens em ordem
## 5. MVP / quick wins de produto (implementáveis em semanas)
## 6. Riscos de produto e dependências
## 7. Recomendações para próxima sprint

# Critérios
- Não invente fatos; sinalize inferências.
- Linguagem executiva e objetiva.

# Transcrição
{{TRANSCRICAO}}""",
    "marketing": """# Papel
Você é um Especialista Sênior em Marketing com foco em posicionamento, aquisição, retenção e comunicação de valor.

# Objetivo
Analise a transcrição sob a ótica de marketing e go-to-market.

# Formato de saída
## 1. Mensagem e proposta de valor inferidas
## 2. Público-alvo / personas de comunicação
## 3. Oportunidades de campanha, conteúdo ou posicionamento
## 4. Canais e táticas de curto prazo (quick wins)
## 5. Métricas de marketing sugeridas (leading/lagging)
## 6. Riscos de comunicação e reputação
## 7. Recomendações acionáveis para as próximas 2 semanas

# Critérios
- Não invente fatos; sinalize inferências.
- Priorize ações de baixo custo e alto impacto.

# Transcrição
{{TRANSCRICAO}}""",
    "financas": """# Papel
Você é um Especialista Sênior em Finanças corporativas com foco em ROI, custo, cashflow e priorização econômica.

# Objetivo
Analise a transcrição sob a ótica financeira e de retorno.

# Formato de saída
## 1. Impactos financeiros identificados (custo, receita, risco)
## 2. Oportunidades de redução de custo ou geração de valor
## 3. Estimativa qualitativa de esforço × retorno
## 4. Quick wins financeiros (implementáveis em semanas)
## 5. Indicadores financeiros a acompanhar
## 6. Riscos financeiros e pressupostos
## 7. Recomendações de decisão com critério econômico

# Critérios
- Não invente números; use faixas ou ordens de magnitude quando necessário e declare incerteza.
- Linguagem executiva e objetiva.

# Transcrição
{{TRANSCRICAO}}""",
    "ia": """# Papel
Você é um Especialista Sênior em Inteligência Artificial, Automação e transformação digital aplicada.

# Objetivo
Analise a transcrição e proponha oportunidades reais de IA/automação com foco em quick wins.

# Formato de saída
## 1. Problemas e processos passíveis de IA/automação
## 2. Oportunidades de Quick Wins (IA generativa, agentes, RPA, OCR, APIs)
## 3. Dados disponíveis vs. dados faltantes
## 4. Stack e ferramentas recomendadas (baixo acoplamento)
## 5. Sequência de implementação (1-2-4 semanas)
## 6. Riscos (qualidade, segurança, custo, dependência de modelo)
## 7. Critérios de sucesso mensuráveis

# Critérios
- Priorize soluções simples e de alto ROI operacional.
- Não proponha reescrita completa de sistemas.

# Transcrição
{{TRANSCRICAO}}""",
    "ti": """# Papel
Você é um Especialista Sênior em TI (infraestrutura, sistemas, integrações, segurança e operação).

# Objetivo
Analise a transcrição sob a ótica técnica de TI e viabilidade operacional.

# Formato de saída
## 1. Landscape técnico inferido (sistemas, integrações, gaps)
## 2. Dependências técnicas e débitos mencionados
## 3. Viabilidade das soluções discutidas
## 4. Quick wins de TI (scripts, integrações, automação operacional)
## 5. Riscos de segurança, disponibilidade e suporte
## 6. Estimativa de esforço técnico relativo
## 7. Próximos passos técnicos recomendados

# Critérios
- Seja pragmático: estabilidade, manutenção e ownership importam.
- Não invente fatos; sinalize inferências.

# Transcrição
{{TRANSCRICAO}}""",
    "consolidador": """# Papel
Você é um facilitador executivo que consolida análises de especialistas.

# Objetivo
Com base nas análises abaixo e na transcrição original, produza um plano único de ação.

# Entradas
{{ANALISES_ESPECIALISTAS}}

## Transcrição original (resumo permitido)
{{TRANSCRICAO}}

# Formato de saída
## 1. Top 5 problemas consolidados
## 2. Top 5 soluções factíveis e rápidas (com ferramenta, prazo e responsável sugerido)
## 3. Matriz impacto x esforço final
## 4. Plano de 7 dias (ações diárias)
## 5. Conflitos entre especialistas e como resolver
## 6. Decisões que precisam ser tomadas na próxima reunião

Priorize quick wins de alto ROI.""",
}

EXECUTIVE_SUMMARY_PROMPT = """# Papel
Você escreve briefings executivos para líderes com pouco tempo.

# Objetivo
Com base na análise completa desta reunião, responda: "O que eu preciso saber desta reunião?"

# Entradas
## Highlights NLP
{{NLP_HIGHLIGHTS}}

{{ANALISES_ESPECIALISTAS}}

## Consolidador
{{CONSOLIDACAO}}

## Transcrição (trecho)
{{TRANSCRICAO}}

# Formato de saída
## Em uma frase
## O que você precisa saber (5 bullets)
## Decisões ou pendências críticas
## Próximo passo recomendado

# Critérios
- Direto, sem jargão, linguagem executiva.
- Não invente fatos; sinalize inferências.
- Priorize o que é acionável."""


def load_default_prompt() -> str:
    path = Path(__file__).resolve().parent / "prompts" / "default_prompt.txt"
    return path.read_text(encoding="utf-8")


PERSONA_TITLES = {
    "produto": "Especialista em Produto",
    "marketing": "Especialista em Marketing",
    "financas": "Especialista em Finanças",
    "ia": "Especialista em Inteligência Artificial",
    "ti": "Especialista em TI",
    "consolidador": "Consolidador de Soluções",
}

# Ordem e rótulos para a UI (multiselect).
PERSONA_OPCOES: list[tuple[str, str]] = [
    ("produto", PERSONA_TITLES["produto"]),
    ("marketing", PERSONA_TITLES["marketing"]),
    ("financas", PERSONA_TITLES["financas"]),
    ("ia", PERSONA_TITLES["ia"]),
    ("ti", PERSONA_TITLES["ti"]),
]


def get_persona_prompt(persona_key: str, custom_prompt: str | None = None) -> tuple[str, str]:
    """Retorna (título, template). `custom_prompt` sobrescreve o especialista em IA."""
    if persona_key not in PERSONA_TITLES or persona_key == "consolidador":
        if persona_key not in PERSONA_PROMPTS:
            raise KeyError(f"Persona desconhecida: {persona_key}")
    if persona_key == "ia" and custom_prompt:
        template = custom_prompt
    else:
        template = PERSONA_PROMPTS[persona_key]
    return PERSONA_TITLES[persona_key], template


def fill_prompt(template: str, transcription: str, **extra: str) -> str:
    result = template.replace("{{TRANSCRICAO}}", transcription)
    for key, value in extra.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


def _bloco_analises(outputs: dict[str, str]) -> str:
    if not outputs:
        return "(Nenhuma análise de especialista disponível.)"
    partes: list[str] = []
    for key, _label in PERSONA_OPCOES:
        if key not in outputs or not outputs[key].strip():
            continue
        titulo = PERSONA_TITLES.get(key, key)
        partes.append(f"## Análise — {titulo}\n{outputs[key].strip()}")
    return "\n\n".join(partes) if partes else "(Nenhuma análise de especialista disponível.)"


def build_consolidation_prompt(transcription: str, outputs: dict[str, str]) -> str:
    template = PERSONA_PROMPTS["consolidador"]
    return fill_prompt(
        template,
        transcription[:4000],
        ANALISES_ESPECIALISTAS=_bloco_analises(outputs),
    )


def _format_nlp_highlights(nlp: dict | None, outras: dict | None) -> str:
    lines: list[str] = []
    if nlp:
        sentiment = nlp.get("sentiment", {})
        lines.append(
            f"Sentimento: {sentiment.get('label', '—')} "
            f"(compound {sentiment.get('compound', '—')})"
        )
        words = nlp.get("word_frequencies", [])[:10]
        if words:
            lines.append(
                "Palavras frequentes: "
                + ", ".join(f"{w['word']} ({w['count']})" for w in words)
            )
    outras_eff = outras or (nlp.get("outras") if nlp else None)
    if outras_eff:
        lines.append(f"Formalidade: {outras_eff.get('nivel_formalidade', '—')}")
        lines.append(f"Perfil: {outras_eff.get('perfil_comunicacao', '—')}")
    return "\n".join(lines) if lines else "Não disponível."


def build_executive_summary_prompt(
    transcription: str,
    outputs: dict[str, str],
    consolidacao: str,
    *,
    nlp: dict | None = None,
    outras: dict | None = None,
) -> str:
    outras_eff = outras
    if outras_eff is None and nlp:
        outras_eff = nlp.get("outras")
    return fill_prompt(
        EXECUTIVE_SUMMARY_PROMPT,
        transcription[:4000],
        NLP_HIGHLIGHTS=_format_nlp_highlights(nlp, outras_eff),
        ANALISES_ESPECIALISTAS=_bloco_analises(outputs),
        CONSOLIDACAO=consolidacao or "Não disponível.",
    )
