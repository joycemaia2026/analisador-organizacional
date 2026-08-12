"""Motor local do Ata Maker (clonado/adaptado do projeto ata_maker)."""

from __future__ import annotations

from dataclasses import dataclass, field

from core.especificacoes_llm import anexar_especificacoes
from core.manual_voz import anexar_manual_voz_ao_sistema
from core.openai_client import chat_completion, get_api_key
from modulos.ata_maker.nlp import nlp_para_markdown, nomes_do_cadastro, run_nlp_analysis
from modulos.ata_maker.normalizacao import bloco_fatos_reuniao, corrigir_nomes_asr
from modulos.ata_maker.prompts_catalog import (
    PERSONA_OPCOES,
    PERSONA_TITLES,
    build_consolidation_prompt,
    build_executive_summary_prompt,
    fill_prompt,
    get_persona_prompt,
    load_default_prompt,
)

PERSONA_ORDER = [key for key, _ in PERSONA_OPCOES]

SYSTEM_ATA = (
    "Você é um assistente especializado em análise de reuniões, "
    "produto e automação com IA. Responda em português do Brasil."
)


@dataclass
class AtaGerada:
    texto: str
    fonte: str
    erros: list[str] = field(default_factory=list)
    saved_report: str | None = None
    nlp: dict | None = None


def _enviar(
    prompt: str,
    *,
    temperature: float = 0.3,
    incluir_manual_voz: bool = False,
) -> str:
    if not get_api_key():
        raise RuntimeError("Chave de API do provedor LLM não configurada no .env.")
    system = anexar_manual_voz_ao_sistema(SYSTEM_ATA, incluir_manual_voz)
    return chat_completion(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt[:120000]},
        ],
        temperature=temperature,
    )


def _normalizar_personas(personas: list[str] | None) -> list[str]:
    """None = todos (compat); lista explícita (mesmo vazia) = só o que veio."""
    if personas is None:
        return list(PERSONA_ORDER)
    validas = {key for key, _ in PERSONA_OPCOES}
    selecionadas = [p for p in PERSONA_ORDER if p in personas and p in validas]
    extras = [p for p in personas if p in validas and p not in selecionadas]
    return selecionadas + extras


def gerar_ata_prompt(
    transcricao: str,
    prompt_custom: str | None = None,
    *,
    incluir_nlp: bool = False,
    especificacoes: str = "",
    incluir_manual_voz: bool = False,
) -> AtaGerada:
    """Modo rápido: prompt principal (+ NLP opcional ao final)."""
    if not transcricao.strip():
        raise ValueError("Transcrição vazia.")

    erros: list[str] = []
    partes: list[str] = []
    nlp_result: dict | None = None
    nlp_md = ""

    if incluir_nlp:
        try:
            nlp_result = run_nlp_analysis(transcricao)
            nlp_md = nlp_para_markdown(nlp_result)
        except Exception as exc:  # noqa: BLE001
            erros.append(f"NLP: {exc}")

    template = prompt_custom or load_default_prompt()
    extras: dict[str, str] = {}
    corpo = transcricao
    if "{{CABECALHO_FATOS}}" in template:
        # O modelo não precisa adivinhar duração, data nem participantes: recebe medido.
        try:
            nomes = nomes_do_cadastro()
            extras["CABECALHO_FATOS"] = bloco_fatos_reuniao(transcricao, nomes)
            # A transcrição vai corrigida junto: o cabeçalho diz "Lindia" e o corpo
            # precisa dizer o mesmo, senão o modelo trata como duas pessoas.
            corpo = corrigir_nomes_asr(transcricao, nomes).texto
        except Exception as exc:  # noqa: BLE001
            erros.append(f"Cabeçalho factual: {exc}")
            extras["CABECALHO_FATOS"] = "(não foi possível apurar os fatos da gravação)"

    filled = anexar_especificacoes(fill_prompt(template, corpo, **extras), especificacoes)
    partes.append(_enviar(filled, incluir_manual_voz=incluir_manual_voz))

    if nlp_md:
        partes.append(nlp_md)

    texto = "\n\n".join(partes).strip()
    fonte = f"modulos.ata_maker:prompt(nlp={incluir_nlp};voz={incluir_manual_voz})"
    return AtaGerada(texto=texto, fonte=fonte, erros=erros, nlp=nlp_result)


def gerar_ata_completa(
    transcricao: str,
    prompt_custom: str | None = None,
    *,
    personas: list[str] | None = None,
    incluir_nlp: bool = True,
    especificacoes: str = "",
    incluir_manual_voz: bool = False,
) -> AtaGerada:
    """
    Análise completa modular:
    1) especialistas selecionados (1+)
    2) consolidação / resumo quando houver especialistas
    3) análise NLP (opcional) — sempre por último no documento
    """
    if not transcricao.strip():
        raise ValueError("Transcrição vazia.")

    selecionadas = _normalizar_personas(personas)
    if not selecionadas and not incluir_nlp:
        raise ValueError("Selecione ao menos um especialista ou ative a análise NLP.")

    erros: list[str] = []
    outputs: dict[str, str] = {}
    partes: list[str] = []
    nlp_result: dict | None = None
    nlp_md = ""

    if incluir_nlp:
        try:
            nlp_result = run_nlp_analysis(transcricao)
            nlp_md = nlp_para_markdown(nlp_result)
        except Exception as exc:  # noqa: BLE001
            erros.append(f"NLP: {exc}")

    custom = prompt_custom or load_default_prompt()
    for key in selecionadas:
        title, template = get_persona_prompt(key, custom)
        filled = anexar_especificacoes(fill_prompt(template, transcricao), especificacoes)
        try:
            content = _enviar(filled, incluir_manual_voz=incluir_manual_voz)
            outputs[key] = content
            partes.append(f"## {title}\n\n{content}")
        except Exception as exc:  # noqa: BLE001
            erros.append(f"{title}: {exc}")

    consolidacao = ""
    if len(outputs) >= 2:
        try:
            cons_prompt = anexar_especificacoes(
                build_consolidation_prompt(transcricao, outputs),
                especificacoes,
            )
            consolidacao = _enviar(cons_prompt, incluir_manual_voz=incluir_manual_voz)
            partes.insert(0, f"## Consolidação\n\n{consolidacao}")
        except Exception as exc:  # noqa: BLE001
            erros.append(f"Consolidador: {exc}")

    if outputs:
        try:
            summary_prompt = anexar_especificacoes(
                build_executive_summary_prompt(
                    transcricao,
                    outputs,
                    consolidacao,
                    nlp=nlp_result,
                ),
                especificacoes,
            )
            executive = _enviar(summary_prompt, incluir_manual_voz=incluir_manual_voz)
            partes.insert(0, f"## Resumo executivo\n\n{executive}")
        except Exception as exc:  # noqa: BLE001
            erros.append(f"Resumo executivo: {exc}")

    # NLP sempre por último no documento gerado.
    if nlp_md:
        partes.append(nlp_md)

    texto = "\n\n".join(partes).strip()
    if not texto:
        raise RuntimeError("Falha ao gerar ata: nenhuma seção produzida.")

    nomes = ", ".join(PERSONA_TITLES.get(k, k) for k in selecionadas) or "nenhum"
    fonte = (
        f"modulos.ata_maker:full(nlp={incluir_nlp};voz={incluir_manual_voz};"
        f"especialistas={nomes})"
    )
    return AtaGerada(texto=texto, fonte=fonte, erros=erros, nlp=nlp_result)


def gerar_ata(
    transcricao: str,
    *,
    modo: str = "prompt",
    prompt_custom: str | None = None,
    personas: list[str] | None = None,
    incluir_nlp: bool = True,
    especificacoes: str = "",
    incluir_manual_voz: bool = False,
) -> AtaGerada:
    if modo == "full":
        return gerar_ata_completa(
            transcricao,
            prompt_custom,
            personas=personas,
            incluir_nlp=incluir_nlp,
            especificacoes=especificacoes,
            incluir_manual_voz=incluir_manual_voz,
        )
    return gerar_ata_prompt(
        transcricao,
        prompt_custom,
        incluir_nlp=incluir_nlp,
        especificacoes=especificacoes,
        incluir_manual_voz=incluir_manual_voz,
    )
