"""Catálogo de lentes de continuidade para enriquecer a análise do Tomador."""

from __future__ import annotations

from typing import Any


LENTES: dict[str, dict[str, Any]] = {
    "planejador": {
        "id": "planejador",
        "nome": "Planejador",
        "foco": "sequência, donos, prazos, dependências",
        "pergunta_guia": "O que precisa acontecer em que ordem?",
        "caracteristicas": [
            "Sequenciamento de ações e dependências",
            "Ownership claro (dono + prazo)",
            "RACI leve e comunicação a quem não esteve na sala",
            "Backlog priorizado (P0/P1/P2)",
            "Cadência de revisão e escalation path",
        ],
        "perguntas_tipicas": [
            "Qual é a ordem mínima viável das ações?",
            "Quem é o dono único de cada frente?",
            "O que bloqueia o próximo passo nas próximas 48–72h?",
            "Quem precisa ser informado do resultado da reunião?",
        ],
    },
    "analitico": {
        "id": "analitico",
        "nome": "Analítico",
        "foco": "hipóteses, evidências, métricas, causa-raiz",
        "pergunta_guia": "O que sabemos vs. o que estamos assumindo?",
        "caracteristicas": [
            "Separar fato, opinião, decisão e pendência",
            "Hipóteses falsificáveis",
            "Evidências e dados mínimos",
            "Métricas leading e lagging",
            "Framing sintoma vs. causa",
        ],
        "perguntas_tipicas": [
            "Quais afirmações são fato e quais são hipótese?",
            "Que evidência invalidaria esta conclusão?",
            "Qual métrica mostra progresso em 7 e 30 dias?",
            "Estamos tratando sintoma ou causa-raiz?",
        ],
    },
    "tecnico": {
        "id": "tecnico",
        "nome": "Técnico",
        "foco": "viabilidade, arquitetura, integração, risco operacional",
        "pergunta_guia": "Dá para fazer com o que temos?",
        "caracteristicas": [
            "Viabilidade com stack e capacidade atuais",
            "Integrações, dados e restrições técnicas",
            "Riscos operacionais e de segurança",
            "Complexidade e esforço técnico",
            "Piloto / menor passo válido (MVP técnico)",
        ],
        "perguntas_tipicas": [
            "Quais dependências técnicas estão implícitas?",
            "O que quebra se fizermos o caminho rápido?",
            "Qual o menor experimento técnico válido?",
            "Há gaps de dados, integração ou operação?",
        ],
    },
    "financista": {
        "id": "financista",
        "nome": "Financista",
        "foco": "custo, ROI, cash, trade-off de investimento",
        "pergunta_guia": "Vale o esforço e o risco financeiro?",
        "caracteristicas": [
            "Custo de oportunidade e trade-offs",
            "ROI / payback estimado",
            "Impacto em cash e capacidade",
            "Critérios go/no-go financeiros",
            "Priorização por valor vs. esforço",
        ],
        "perguntas_tipicas": [
            "Qual o custo de não decidir agora?",
            "O retorno justifica o esforço nas próximas 4–12 semanas?",
            "Há opção mais barata com 80% do valor?",
            "Quais custos ocultos (retrabalho, risco, atraso)?",
        ],
    },
}

DEFAULT_LENTES = ["planejador", "analitico"]

CHECKLIST_MINIMO_CONTINUIDADE = [
    "Decisões tomadas",
    "Pendências com dono e prazo",
    "O que ficou ambíguo",
    "Riscos abertos",
    "Próximos 3 passos (48–72h)",
    "Dependências externas",
    "Métrica de progresso",
    "Quem precisa ser informado",
]

CARACTERISTICAS_PRE = [
    "Objetivo único da reunião",
    "Agenda com decisões esperadas",
    "Pré-leitura / materiais",
    "Critério de sucesso da conversa",
    "Riscos e restrições já conhecidos",
    "Papéis: quem decide / informa / executa",
]

CARACTERISTICAS_DURANTE = [
    "Separar fato / opinião / decisão / pendência",
    "Registrar dono + prazo na hora",
    "Explicitar não-decisões e motivos",
    "Detectar ambiguidade e forçar definição",
    "Mapear bloqueios e dependências",
    "Priorizar crítico vs. nice-to-have",
]

CARACTERISTICAS_POS = [
    "Ata acionável (decisões, pendências, próximos passos)",
    "RACI leve",
    "Backlog priorizado com esforço e impacto",
    "SLA de follow-up (24h / 7 dias / 30 dias)",
    "Definição de pronto por item",
    "Riscos residuais e mitigação",
    "Métricas de progresso",
    "Escalation path",
    "Comunicação para quem não esteve",
    "Aprendizado (repetir / evitar)",
]


def ids_validos() -> list[str]:
    return list(LENTES.keys())


def rotulo_lente(lente_id: str) -> str:
    lente = LENTES.get(lente_id)
    if not lente:
        return lente_id
    return f"{lente['nome']} — {lente['foco']}"


def normalizar_lentes(selecionadas: list[str] | None) -> list[str]:
    if not selecionadas:
        return list(DEFAULT_LENTES)
    validas = [x for x in selecionadas if x in LENTES]
    return validas or list(DEFAULT_LENTES)


def montar_bloco_lentes(selecionadas: list[str] | None) -> str:
    """Texto estruturado para injetar no prompt."""
    ids = normalizar_lentes(selecionadas)
    partes: list[str] = []
    for lid in ids:
        lente = LENTES[lid]
        chars = "\n".join(f"  - {c}" for c in lente["caracteristicas"])
        perguntas = "\n".join(f"  - {p}" for p in lente["perguntas_tipicas"])
        partes.append(
            f"### Lente: {lente['nome']}\n"
            f"Pergunta-guia: {lente['pergunta_guia']}\n"
            f"Características:\n{chars}\n"
            f"Perguntas típicas:\n{perguntas}"
        )

    checklist = "\n".join(f"- {item}" for item in CHECKLIST_MINIMO_CONTINUIDADE)
    pre = "\n".join(f"- {item}" for item in CARACTERISTICAS_PRE)
    durante = "\n".join(f"- {item}" for item in CARACTERISTICAS_DURANTE)
    pos = "\n".join(f"- {item}" for item in CARACTERISTICAS_POS)

    return (
        "LENTES ATIVAS (ampliam o roteiro; NÃO substituem o perfil do Tomador):\n\n"
        + "\n\n".join(partes)
        + "\n\n### Checklist mínimo de continuidade (obrigatório cobrir no pós)\n"
        + checklist
        + "\n\n### Características — Antes da reunião\n"
        + pre
        + "\n\n### Características — Durante a reunião\n"
        + durante
        + "\n\n### Características — Depois da reunião\n"
        + pos
    )
