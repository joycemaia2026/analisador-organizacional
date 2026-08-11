"""Catálogo de modelos OpenAI/Gemini disponíveis na UI, com custo estimado em R$."""

from __future__ import annotations

import os
from dataclasses import dataclass

# Uma chamada típica nesta app: ~8k tokens de entrada + ~2k de saída.
TOKENS_ENTRADA_TIPICOS = 8_000
TOKENS_SAIDA_TIPICOS = 2_000

# Análise institucional típica = Tomador + Especialista IA (2 chamadas).
CHAMADAS_POR_ANALISE = 2

# Cotação de referência USD→BRL (override via .env USD_BRL).
_DEFAULT_USD_BRL = 5.50


def taxa_usd_brl() -> float:
    raw = (os.getenv("USD_BRL") or "").strip().replace(",", ".")
    if raw:
        try:
            valor = float(raw)
            if valor > 0:
                return valor
        except ValueError:
            pass
    return _DEFAULT_USD_BRL


@dataclass(frozen=True)
class ModeloLLM:
    id: str
    nome: str
    descricao: str
    input_por_1m: float  # USD por 1M tokens de entrada
    output_por_1m: float  # USD por 1M tokens de saída
    provider: str = "openai"  # openai | gemini


MODELOS_OPENAI: tuple[ModeloLLM, ...] = (
    ModeloLLM(
        id="gpt-4o-mini",
        nome="GPT-4o mini",
        descricao="Padrão: rápido e econômico para atas e análises do dia a dia.",
        input_por_1m=0.15,
        output_por_1m=0.60,
        provider="openai",
    ),
    ModeloLLM(
        id="gpt-4.1-mini",
        nome="GPT-4.1 mini",
        descricao="Melhor custo/qualidade — diagnósticos e planos um pouco mais densos.",
        input_por_1m=0.40,
        output_por_1m=1.60,
        provider="openai",
    ),
    ModeloLLM(
        id="gpt-4o",
        nome="GPT-4o",
        descricao="Qualidade geral alta. Use quando a nuance da análise justificar o custo.",
        input_por_1m=2.50,
        output_por_1m=10.00,
        provider="openai",
    ),
    ModeloLLM(
        id="gpt-4.1",
        nome="GPT-4.1",
        descricao="Contexto longo e produção — análises comparativas e documentos densos.",
        input_por_1m=2.00,
        output_por_1m=8.00,
        provider="openai",
    ),
)

# Preços de referência Gemini (USD / 1M tokens) — aproximados para estimativa na UI.
MODELOS_GEMINI: tuple[ModeloLLM, ...] = (
    ModeloLLM(
        id="gemini-2.0-flash",
        nome="Gemini 2.0 Flash",
        descricao="Padrão Gemini: rápido e econômico para atas e análises.",
        input_por_1m=0.10,
        output_por_1m=0.40,
        provider="gemini",
    ),
    ModeloLLM(
        id="gemini-2.5-flash",
        nome="Gemini 2.5 Flash",
        descricao="Bom equilíbrio custo/qualidade no ecossistema Google.",
        input_por_1m=0.15,
        output_por_1m=0.60,
        provider="gemini",
    ),
    ModeloLLM(
        id="gemini-2.5-pro",
        nome="Gemini 2.5 Pro",
        descricao="Maior qualidade Gemini — análises densas e contexto longo.",
        input_por_1m=1.25,
        output_por_1m=10.00,
        provider="gemini",
    ),
)

MODELOS: tuple[ModeloLLM, ...] = MODELOS_OPENAI + MODELOS_GEMINI

_POR_ID: dict[str, ModeloLLM] = {m.id: m for m in MODELOS}


def ids_validos(provider: str | None = None) -> frozenset[str]:
    if provider is None:
        return frozenset(_POR_ID)
    prov = provider.strip().lower()
    return frozenset(m.id for m in MODELOS if m.provider == prov)


def obter_modelo(modelo_id: str) -> ModeloLLM | None:
    return _POR_ID.get((modelo_id or "").strip())


def lista_ids_ordenados(provider: str | None = "openai") -> list[str]:
    if provider is None:
        return [m.id for m in MODELOS]
    prov = provider.strip().lower()
    return [m.id for m in MODELOS if m.provider == prov]


def default_modelo_id(provider: str) -> str:
    ids = lista_ids_ordenados(provider)
    return ids[0] if ids else "gpt-4o-mini"


def custo_geracao_usd(modelo: ModeloLLM) -> float:
    """USD estimado para 1 chamada (~8k in + ~2k out)."""
    return (
        modelo.input_por_1m * TOKENS_ENTRADA_TIPICOS / 1_000_000
        + modelo.output_por_1m * TOKENS_SAIDA_TIPICOS / 1_000_000
    )


def custo_analise_usd(modelo: ModeloLLM) -> float:
    """USD estimado para 1 análise (Tomador + Especialista = 2 chamadas)."""
    return custo_geracao_usd(modelo) * CHAMADAS_POR_ANALISE


def custo_analise_brl(modelo: ModeloLLM) -> float:
    """R$ estimado para 1 análise típica."""
    return custo_analise_usd(modelo) * taxa_usd_brl()


def custo_analise_centavos_brl(modelo: ModeloLLM) -> float:
    """Centavos de real (R$ 0,01) por análise típica."""
    return custo_analise_brl(modelo) * 100


def formatar_reais(valor_brl: float) -> str:
    """Ex.: R$ 0,026  |  R$ 1,25"""
    if valor_brl < 0.01:
        return "R$ " + f"{valor_brl:.4f}".replace(".", ",")
    if valor_brl < 1:
        return "R$ " + f"{valor_brl:.3f}".replace(".", ",")
    return "R$ " + f"{valor_brl:.2f}".replace(".", ",")


def formatar_centavos_brl(centavos: float) -> str:
    """Ex.: 2,6 centavos  |  44 centavos"""
    if centavos < 10:
        return f"{centavos:.1f}".replace(".", ",") + " centavos"
    return f"{centavos:.0f} centavos"


def multiplicador_vs_mini(modelo: ModeloLLM) -> float:
    base = custo_analise_usd(_POR_ID["gpt-4o-mini"])
    if base <= 0:
        return 1.0
    return custo_analise_usd(modelo) / base


def _texto_multiplicador(mult: float) -> str:
    if 0.95 <= mult <= 1.05:
        return "~1×"
    if mult < 1:
        return f"~{mult:.1f}×"
    if mult < 1.5:
        return f"~{mult:.1f}×"
    return f"~{mult:.0f}×"


def rotulo_selectbox(modelo_id: str) -> str:
    m = obter_modelo(modelo_id)
    if not m:
        return modelo_id
    return f"{m.nome}  ·  ≈ {formatar_reais(custo_analise_brl(m))} / análise"


def rotulo_radio(modelo_id: str) -> str:
    return rotulo_selectbox(modelo_id)


def texto_custo(modelo_id: str) -> str:
    m = obter_modelo(modelo_id)
    if not m:
        return "Modelo sem tabela de custo nesta app."
    brl = formatar_reais(custo_analise_brl(m))
    return (
        f"{m.descricao}  \n"
        f"≈ **{brl}** / análise · US$ {m.input_por_1m:.2f}/"
        f"{m.output_por_1m:.2f} por 1M tokens "
        f"(cotação US$ 1 = R$ {taxa_usd_brl():.2f})"
    )


# Compatibilidade
def custo_geracao_tipica(modelo: ModeloLLM) -> float:
    return custo_geracao_usd(modelo)


def custo_analise_centavos(modelo: ModeloLLM) -> float:
    """Deprecated alias: agora retorna centavos de real."""
    return custo_analise_centavos_brl(modelo)


def formatar_centavos(centavos: float) -> str:
    """Deprecated alias: formata centavos de real."""
    return formatar_centavos_brl(centavos)
