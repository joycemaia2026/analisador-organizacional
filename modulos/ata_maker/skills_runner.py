"""Executa o pipeline de skills do BriefBoard (skills/ + helpers + LLM)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from core.especificacoes_llm import anexar_especificacoes
from core.manual_voz import anexar_manual_voz_ao_sistema
from core.openai_client import chat_completion, get_api_key
from modulos.ata_maker import acoes as mod_acoes
from modulos.ata_maker import cobertura as mod_cob
from modulos.ata_maker import decisoes as mod_decisoes
from modulos.ata_maker import levantamento as mod_lev
from modulos.ata_maker import processamento as mod_proc
from modulos.ata_maker import proxima_reuniao as mod_pauta
from modulos.ata_maker.engine import AtaGerada
from modulos.ata_maker.nlp import nlp_para_markdown, nomes_do_cadastro, run_nlp_analysis
from modulos.ata_maker.normalizacao import bloco_fatos_reuniao
from modulos.ata_maker.prompts_catalog import fill_prompt, load_prompt_ata
from modulos.ata_maker.skills_registry import (
    SkillMeta,
    garantir_dependencias,
    listar_skills,
    obter_skill,
)

SYSTEM_SKILLS = (
    "Você executa skills do BriefBoard sobre reuniões de startup. "
    "Responda em português do Brasil. Nunca invente fatos, nomes, números "
    "ou prazos que não estejam na transcrição processada. "
    "Quando um campo não existir na reunião, declare isso explicitamente."
)

ProgressCb = Callable[[str], None] | None


@dataclass
class SkillResultado:
    name: str
    ok: bool
    caminhos: dict[str, str] = field(default_factory=dict)
    markdown: str = ""
    erro: str | None = None
    avisos: list[str] = field(default_factory=list)


@dataclass
class PipelineResultado:
    stem: str
    pasta: str
    skills: list[SkillResultado] = field(default_factory=list)
    ata_markdown: str | None = None
    erros: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.skills) and all(s.ok for s in self.skills)


def _progresso(cb: ProgressCb, msg: str) -> None:
    if cb:
        cb(msg)


def _extrair_json(texto: str) -> Any:
    bruto = (texto or "").strip()
    if not bruto:
        raise ValueError("Resposta vazia do modelo.")
    cerca = re.search(r"```(?:json)?\s*([\s\S]*?)```", bruto)
    if cerca:
        bruto = cerca.group(1).strip()
    try:
        return json.loads(bruto)
    except json.JSONDecodeError:
        ini = bruto.find("{")
        fim = bruto.rfind("}")
        if ini >= 0 and fim > ini:
            return json.loads(bruto[ini : fim + 1])
        ini = bruto.find("[")
        fim = bruto.rfind("]")
        if ini >= 0 and fim > ini:
            return json.loads(bruto[ini : fim + 1])
        raise


def _data_reuniao(proc: mod_proc.Processamento) -> date | None:
    raw = (proc.metadados or {}).get("data_reuniao") or ""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "")).date()
    except ValueError:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", str(raw))
        if m:
            return date.fromisoformat(m.group(1))
    return None


def _gravar(stem: str, nome: str, conteudo: str) -> Path:
    pasta = mod_proc.pasta_do_stem(stem)
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / nome
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho


def _llm(
    skill: SkillMeta,
    user: str,
    *,
    incluir_manual_voz: bool,
    temperature: float = 0.2,
    json_mode: bool = False,
) -> str:
    if not get_api_key():
        raise RuntimeError("Chave de API do provedor LLM não configurada.")
    system = (
        f"{SYSTEM_SKILLS}\n\n"
        f"### Skill `{skill.name}` (v{skill.version or '?'})\n"
        f"{skill.description}\n\n"
        f"{skill.body[:14000]}"
    )
    system = anexar_manual_voz_ao_sistema(system, incluir_manual_voz)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user[:120000]},
    ]
    if json_mode:
        try:
            return chat_completion(
                messages,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
        except Exception:  # noqa: BLE001 — Gemini nem sempre aceita response_format
            messages = [
                messages[0],
                {
                    "role": "user",
                    "content": messages[1]["content"]
                    + "\n\nResponda somente com JSON válido, sem markdown.",
                },
            ]
    return chat_completion(messages, temperature=temperature)


def _run_processamento(
    texto: str,
    stem: str,
    *,
    origem: str,
    nomes: list[str],
) -> SkillResultado:
    """Pré-requisito interno. Reaproveita artefato se o hash da origem bater."""
    st = mod_proc.status(stem, texto)
    if st.get("existe") and st.get("atualizado"):
        proc = mod_proc.carregar(stem)
        assert proc is not None
        caminho_md = mod_proc.pasta_do_stem(stem) / mod_proc.NOME_MD
        caminho_json = mod_proc.pasta_do_stem(stem) / mod_proc.NOME_JSON
        md = (
            caminho_md.read_text(encoding="utf-8")
            if caminho_md.is_file()
            else (proc.texto_ancorado or "")[:4000]
        )
        return SkillResultado(
            name="processamento",
            ok=True,
            caminhos={
                "json": str(caminho_json),
                "markdown": str(caminho_md),
            },
            markdown=md[:4000],
            avisos=[],
        )

    dados = mod_proc.processar(texto, nomes, origem=origem or stem)
    caminhos = mod_proc.salvar(stem, dados)
    md = (caminhos["markdown"]).read_text(encoding="utf-8")
    avisos: list[str] = []
    sem = int(dados.get("turnos_sem_falante") or 0)
    if sem:
        avisos.append(f"{sem} turno(s) sem falante identificado.")
    return SkillResultado(
        name="processamento",
        ok=True,
        caminhos={k: str(v) for k, v in caminhos.items()},
        markdown=md[:4000],
        avisos=avisos,
    )


def _run_levantamento(
    texto: str,
    stem: str,
    skill: SkillMeta,
    *,
    nomes: list[str],
    incluir_manual_voz: bool,
) -> SkillResultado:
    proc = mod_proc.exigir(stem, texto)
    base = mod_lev.preencher_do_processamento(proc.dados, nomes)
    user = (
        "Preencha os campos interpretativos do levantamento a partir da "
        "transcrição processada. Devolva APENAS um JSON com as chaves:\n"
        "objetivo, decisoes, tarefas, responsaveis, prazos, pendencias, "
        "proximos_passos, riscos.\n"
        "Use listas de strings com âncora [t=mm:ss] quando couber. "
        f"Se o campo não existir na reunião, use exatamente: "
        f"\"{mod_lev.NAO_MENCIONADO}\".\n"
        "Não invente. Não reescreva participantes nem informacoes "
        "(já estão preenchidos deterministicamente).\n\n"
        f"### Metadados\n{json.dumps(proc.metadados, ensure_ascii=False)}\n\n"
        f"### Base já preenchida\n"
        f"{json.dumps({k: base[k] for k in ('participantes', 'informacoes')}, ensure_ascii=False, indent=2)}\n\n"
        f"### Transcrição processada\n{proc.texto_ancorado}"
    )
    try:
        raw = _llm(skill, user, incluir_manual_voz=incluir_manual_voz, json_mode=True)
        parcial = _extrair_json(raw)
        if not isinstance(parcial, dict):
            raise ValueError("JSON do levantamento não é um objeto.")
    except Exception as exc:  # noqa: BLE001
        # Sem LLM interpretativo, mantém o que o determinístico já entregou.
        parcial = {}
        avisos_llm = [f"LLM do levantamento falhou ({exc}); mantendo campos determinísticos."]
    else:
        avisos_llm = []

    mesclado = dict(base)
    for chave in (
        "objetivo",
        "decisoes",
        "tarefas",
        "responsaveis",
        "prazos",
        "pendencias",
        "proximos_passos",
        "riscos",
    ):
        if chave in parcial:
            mesclado[chave] = parcial[chave]

    dados = mod_lev.normalizar_levantamento(mesclado)
    problemas = mod_lev.validar_levantamento(dados)
    md = mod_lev.levantamento_para_markdown(dados)
    preenc, total = mod_cob.cobertura_levantamento(dados)
    avisos, md = mod_cob.aplicar_cobertura(avisos_llm + problemas, md, preenc, total)
    caminho_json = _gravar(
        stem, "levantamento.json", json.dumps(dados, ensure_ascii=False, indent=2)
    )
    caminho_md = _gravar(stem, "levantamento.md", md)
    return SkillResultado(
        name="levantamento-reuniao",
        ok=not problemas,
        caminhos={"json": str(caminho_json), "markdown": str(caminho_md)},
        markdown=md,
        erro="; ".join(problemas) if problemas else None,
        avisos=avisos,
    )


def _ler_levantamento(stem: str) -> dict[str, Any]:
    caminho = mod_proc.pasta_do_stem(stem) / "levantamento.json"
    if not caminho.is_file():
        raise FileNotFoundError(
            f"levantamento.json ausente em {caminho.parent}. "
            "Rode a skill levantamento-reuniao antes."
        )
    return json.loads(caminho.read_text(encoding="utf-8"))


def _run_ata(
    texto: str,
    stem: str,
    skill: SkillMeta | None,
    *,
    incluir_manual_voz: bool,
    especificacoes: str = "",
) -> SkillResultado:
    """Gera ata assertiva (ex-skill ata-reuniao), fundida em Gerar Ata."""
    _ = skill
    proc = mod_proc.exigir(stem, texto)
    lev = _ler_levantamento(stem)
    lev_md = mod_lev.levantamento_para_markdown(lev)
    nomes = nomes_do_cadastro()
    try:
        cabecalho = bloco_fatos_reuniao(texto, nomes)
    except Exception:  # noqa: BLE001
        cabecalho = "(não foi possível apurar os fatos da gravação)"

    template = load_prompt_ata("reuniao")
    filled = fill_prompt(
        template,
        proc.texto_ancorado[:100000],
        CABECALHO_FATOS=cabecalho,
        LEVANTAMENTO=lev_md,
    )
    filled = anexar_especificacoes(filled, especificacoes)

    system = (
        "Você escreve atas assertivas para quem não esteve na reunião. "
        "Priorize decisões, donos e prazos. Português do Brasil. "
        "Nunca invente fatos."
    )
    system = anexar_manual_voz_ao_sistema(system, incluir_manual_voz)
    if not get_api_key():
        raise RuntimeError("Chave de API do provedor LLM não configurada.")
    ata_md = chat_completion(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": filled[:120000]},
        ],
        temperature=0.25,
    ).strip()
    caminho = _gravar(stem, "ata.md", ata_md)
    return SkillResultado(
        name="ata-reuniao",
        ok=True,
        caminhos={"markdown": str(caminho)},
        markdown=ata_md,
    )


def gerar_ata_fundida(
    texto: str,
    *,
    stem: str,
    origem: str = "",
    incluir_nlp: bool = False,
    incluir_manual_voz: bool = True,
    especificacoes: str = "",
    progress: ProgressCb = None,
) -> AtaGerada:
    """Gerar Ata = processamento + levantamento + ata assertiva (ex-skill 2)."""
    if not (texto or "").strip():
        raise ValueError("Transcrição vazia.")
    stem = Path(stem).stem or "transcricao"
    nomes = nomes_do_cadastro()
    erros: list[str] = []

    _progresso(progress, "Preparando transcrição…")
    r_proc = _run_processamento(texto, stem, origem=origem, nomes=nomes)
    if not r_proc.ok:
        raise RuntimeError(r_proc.erro or "Falha ao preparar a transcrição.")
    erros.extend(r_proc.avisos)

    skill_lev = obter_skill("levantamento-reuniao")
    if skill_lev is None:
        raise RuntimeError("Skill levantamento-reuniao não encontrada em skills/.")
    _progresso(progress, "Levantando os 10 campos da reunião…")
    r_lev = _run_levantamento(
        texto,
        stem,
        skill_lev,
        nomes=nomes,
        incluir_manual_voz=incluir_manual_voz,
    )
    erros.extend(r_lev.avisos)
    if r_lev.erro:
        erros.append(r_lev.erro)

    _progresso(progress, "Escrevendo ata assertiva…")
    r_ata = _run_ata(
        texto,
        stem,
        obter_skill("ata-reuniao", incluir_fundidas=True),
        incluir_manual_voz=incluir_manual_voz,
        especificacoes=especificacoes,
    )
    if not r_ata.ok:
        raise RuntimeError(r_ata.erro or "Falha ao gerar a ata.")

    partes = [r_ata.markdown]
    nlp_result = None
    if incluir_nlp:
        try:
            _progresso(progress, "Análise NLP…")
            nlp_result = run_nlp_analysis(texto)
            partes.append(nlp_para_markdown(nlp_result))
        except Exception as exc:  # noqa: BLE001
            erros.append(f"NLP: {exc}")

    return AtaGerada(
        texto="\n\n".join(partes).strip(),
        fonte=(
            f"modulos.ata_maker:ata_fundida(nlp={incluir_nlp};"
            f"voz={incluir_manual_voz};stem={stem})"
        ),
        erros=erros,
        nlp=nlp_result,
        saved_report=str(mod_proc.pasta_do_stem(stem) / "ata.md"),
    )


def _montar_acoes(
    itens: list[dict[str, Any]], data_ref: date | None
) -> list[mod_acoes.Acao]:
    lista: list[mod_acoes.Acao] = []
    for i, item in enumerate(itens, start=1):
        if not isinstance(item, dict):
            continue
        expr = str(item.get("prazo_expressao") or item.get("prazo") or "").strip()
        prazo = None
        if data_ref and expr:
            prazo = mod_acoes.resolver_prazo(expr, data_ref).data
        elif isinstance(item.get("prazo"), str) and re.match(
            r"\d{4}-\d{2}-\d{2}", item["prazo"]
        ):
            try:
                prazo = date.fromisoformat(item["prazo"][:10])
            except ValueError:
                prazo = None
        dono = item.get("dono")
        if dono in (None, "", "[dono não definido]"):
            dono = None
        lista.append(
            mod_acoes.Acao(
                id=str(item.get("id") or f"a{i}"),
                descricao=str(item.get("descricao") or "").strip(),
                dono=dono,
                origem=str(item.get("origem") or mod_acoes.ORIGEM_EXPLICITA),
                prazo=prazo,
                prazo_expressao=expr,
                esforco_horas=float(item.get("esforco_horas") or 0),
                depende_de=list(item.get("depende_de") or []),
                ancora=str(item.get("ancora") or ""),
            )
        )
    return [a for a in lista if a.descricao]


def _md_acoes(acoes: list[mod_acoes.Acao], data_ref: date | None) -> str:
    por_dono: dict[str, list[mod_acoes.Acao]] = {}
    sem_dep = []
    com_dep = []
    orfas = []
    for a in acoes:
        if not a.dono:
            orfas.append(a)
        if a.depende_de:
            com_dep.append(a)
        else:
            sem_dep.append(a)
        chave = a.dono or "[dono não definido]"
        por_dono.setdefault(chave, []).append(a)

    linhas = ["## Pode começar hoje", ""]
    if sem_dep:
        for a in sem_dep:
            linhas.append(
                f"- {a.descricao} — {a.dono or '[dono não definido]'} · "
                f"{a.prazo.isoformat() if a.prazo else '[prazo não definido]'} · "
                f"{a.ancora or '[sem âncora]'}"
            )
    else:
        linhas.append("_Nenhuma ação sem dependência._")
    linhas.extend(["", "## Plano por pessoa", ""])
    for dono, itens in por_dono.items():
        linhas.append(f"### {dono}")
        linhas.append("| Ação | Prazo | Esforço | Âncora |")
        linhas.append("|---|---|---|---|")
        for a in itens:
            linhas.append(
                f"| {a.descricao} | "
                f"{a.prazo.isoformat() if a.prazo else '[prazo não definido]'} | "
                f"{a.esforco_horas:g}h | {a.ancora or '[sem âncora]'} |"
            )
        linhas.append("")
    linhas.extend(["## Depende de outra coisa", ""])
    if com_dep:
        for a in com_dep:
            linhas.append(
                f"- {a.descricao} depende de: {', '.join(a.depende_de)}"
            )
    else:
        linhas.append("_Nenhuma._")
    linhas.extend(["", "## Ninguém assumiu", ""])
    if orfas:
        for a in orfas:
            linhas.append(f"- {a.descricao} ({a.origem}) — {a.ancora or '[sem âncora]'}")
    else:
        linhas.append("_Nenhuma._")
    linhas.extend(
        [
            "",
            "## Onde o plano aperta",
            "",
            mod_acoes.relatorio_realismo(acoes, data_ref),
            "",
            "## Fora de escopo por agora",
            "",
            "_Nenhum item marcado como projeto nesta passagem._",
        ]
    )
    return "\n".join(linhas)


def _run_pontos_acao(
    texto: str,
    stem: str,
    skill: SkillMeta,
    *,
    incluir_manual_voz: bool,
) -> SkillResultado:
    proc = mod_proc.exigir(stem, texto)
    lev = _ler_levantamento(stem)
    data_ref = _data_reuniao(proc)
    user = (
        "Extraia o plano de ação. Devolva JSON no formato:\n"
        '{"acoes":[{"id":"a1","descricao":"...","dono":"...","origem":"explicita|inferida",'
        '"prazo_expressao":"até sexta","esforco_horas":2,"depende_de":[],"ancora":"[t=mm:ss]"}],'
        f'"capacidade_h":{mod_acoes.CAPACIDADE_SEMANAL_H}}}\n'
        "Ação explícita sem âncora não entra. Não invente donos.\n\n"
        f"### Data da reunião\n{data_ref.isoformat() if data_ref else 'não informada'}\n\n"
        f"### Levantamento\n{mod_lev.levantamento_para_markdown(lev)}\n\n"
        f"### Transcrição processada\n{proc.texto_ancorado[:80000]}"
    )
    raw = _llm(skill, user, incluir_manual_voz=incluir_manual_voz, json_mode=True)
    payload = _extrair_json(raw)
    if isinstance(payload, list):
        itens = payload
        capacidade = mod_acoes.CAPACIDADE_SEMANAL_H
    else:
        itens = list(payload.get("acoes") or [])
        capacidade = float(payload.get("capacidade_h") or mod_acoes.CAPACIDADE_SEMANAL_H)
    acoes = _montar_acoes(itens, data_ref)
    avisos = [
        f"{a.tipo}: {a.mensagem}"
        for a in mod_acoes.validar_acoes(acoes, data_ref, capacidade_h=capacidade)
    ]
    md = _md_acoes(acoes, data_ref)
    preenc, total = mod_cob.cobertura_pontos_acao(acoes, lev)
    avisos, md = mod_cob.aplicar_cobertura(avisos, md, preenc, total)
    payload_out = {
        "acoes": [a.para_dict() for a in acoes],
        "avisos": avisos,
        "capacidade_h": capacidade,
        "cobertura": {"preenchidos": preenc, "total": total},
    }
    caminho_json = _gravar(
        stem, "pontos_de_acao.json", json.dumps(payload_out, ensure_ascii=False, indent=2)
    )
    caminho_md = _gravar(stem, "pontos_de_acao.md", md)
    return SkillResultado(
        name="pontos-de-acao",
        ok=True,
        caminhos={"json": str(caminho_json), "markdown": str(caminho_md)},
        markdown=md,
        avisos=avisos,
    )


def _normalizar_contexto_resumo(valor: Any) -> str:
    """Contexto é obrigatório: texto real ou declaração explícita de ausência."""
    txt = str(valor or "").strip()
    if not txt or txt.lower() in {"não informado", "nao informado", "n/a", "-"}:
        return mod_lev.NAO_MENCIONADO
    return txt


def _normalizar_temas_resumo(valor: Any) -> list[dict[str, str]]:
    """Temas são obrigatórios na estrutura; cada um com faixa de tempo quando houver."""
    temas: list[dict[str, str]] = []
    if not isinstance(valor, list):
        return temas
    for item in valor:
        if isinstance(item, str):
            nome = item.strip()
            if not nome:
                continue
            temas.append(
                {
                    "tema": nome,
                    "inicio": "",
                    "fim": "",
                    "onde_parou": "",
                }
            )
            continue
        if not isinstance(item, dict):
            continue
        nome = str(item.get("tema") or item.get("titulo") or "").strip()
        if not nome:
            continue
        temas.append(
            {
                "tema": nome,
                "inicio": str(item.get("inicio") or "").strip(),
                "fim": str(item.get("fim") or "").strip(),
                "onde_parou": str(item.get("onde_parou") or item.get("parada") or "").strip(),
            }
        )
    return temas


def _temas_para_markdown(temas: list[dict[str, str]]) -> str:
    if not temas:
        return f"_{mod_lev.NAO_MENCIONADO}_"
    linhas: list[str] = []
    for t in temas:
        faixa = ""
        if t.get("inicio") and t.get("fim"):
            faixa = f" ({t['inicio']}–{t['fim']})"
        elif t.get("inicio"):
            faixa = f" (a partir de {t['inicio']})"
        linha = f"- **{t['tema']}**{faixa}"
        if t.get("onde_parou"):
            linha += f" — onde parou: {t['onde_parou']}"
        linhas.append(linha)
    return "\n".join(linhas)


def _run_resumo_decisoes(
    texto: str,
    stem: str,
    skill: SkillMeta,
    *,
    incluir_manual_voz: bool,
) -> SkillResultado:
    from modulos.ata_maker.normalizacao import blocos_de_tempo

    proc = mod_proc.exigir(stem, texto)
    lev = _ler_levantamento(stem)
    turnos = mod_lev.turnos_do_artefato(proc.dados.get("turnos") or [])
    blocos = blocos_de_tempo(turnos, minutos=10)
    janelas_txt = (
        "\n".join(
            f"- {b['inicio']}–{b['fim']}: {b['total_turnos']} turnos"
            + (f"; falantes: {', '.join(b['falantes'])}" if b.get("falantes") else "")
            for b in blocos
        )
        or "(sem janelas de tempo — temas ainda são obrigatórios; declare se não houver)"
    )
    user = (
        "Produza o resumo das decisões. "
        "OBRIGATÓRIO: preencha sempre `contexto` e `temas` "
        "(mesmo se `decisoes` estiver vazio).\n\n"
        "JSON:\n"
        "{\n"
        '  "contexto": "1 a 3 frases: o que motivou a reunião e o estado do assunto ao começar. '
        f'Se ninguém disse, use exatamente: {mod_lev.NAO_MENCIONADO}",\n'
        '  "temas": [\n'
        '    {"tema": "assunto da janela", "inicio": "0:00", "fim": "10:00", '
        '"onde_parou": "em que ponto ficou"}\n'
        "  ],\n"
        '  "decisoes": [\n'
        '    {"id": "d1", "enunciado": "...", '
        '"criterio": "...|critério não declarado na reunião", '
        '"alternativas_descartadas": [], "sustentada_por": "...", '
        '"ancora": "[t=mm:ss]", "tipo": "reversivel|irreversivel|indefinido"}\n'
        "  ],\n"
        '  "criterios_gerais": []\n'
        "}\n\n"
        "Regras:\n"
        "- `contexto` e `temas` NÃO podem ficar vazios nem omitidos.\n"
        "- Nomeie um tema por janela relevante (use as janelas abaixo). "
        "Tema de passagem: mencione sem o mesmo peso.\n"
        "- Se a reunião não discutiu tema nomeável, `temas` fica com um item "
        f'{{"tema": "{mod_lev.NAO_MENCIONADO}", "inicio": "", "fim": "", "onde_parou": ""}}.\n'
        "- Se não houve decisão, `decisoes` = [].\n"
        "- Não invente critério, alternativa, nome ou prazo.\n\n"
        f"### Janelas de tempo (âncora dos temas)\n{janelas_txt}\n\n"
        f"### Levantamento\n{mod_lev.levantamento_para_markdown(lev)}\n\n"
        f"### Transcrição processada\n{proc.texto_ancorado[:80000]}"
    )
    raw = _llm(skill, user, incluir_manual_voz=incluir_manual_voz, json_mode=True)
    try:
        parsed = _extrair_json(raw)
    except Exception:  # noqa: BLE001
        parsed = {}
    payload = parsed if isinstance(parsed, dict) else {}

    itens = list(payload.get("decisoes") or [])
    decisoes: list[mod_decisoes.Decisao] = []
    for i, item in enumerate(itens, start=1):
        if not isinstance(item, dict) or not str(item.get("enunciado") or "").strip():
            continue
        decisoes.append(
            mod_decisoes.Decisao(
                id=str(item.get("id") or f"d{i}"),
                enunciado=str(item["enunciado"]).strip(),
                criterio=str(item.get("criterio") or mod_decisoes.SEM_CRITERIO),
                alternativas_descartadas=list(item.get("alternativas_descartadas") or []),
                sustentada_por=item.get("sustentada_por"),
                ancora=str(item.get("ancora") or ""),
                tipo=str(item.get("tipo") or mod_decisoes.INDEFINIDO),
            )
        )

    contexto = _normalizar_contexto_resumo(payload.get("contexto"))
    temas = _normalizar_temas_resumo(payload.get("temas"))
    avisos_extra: list[str] = []
    if not str(payload.get("contexto") or "").strip():
        avisos_extra.append("modelo omitiu o contexto — seção preenchida com declaração explícita")
    if not temas:
        temas = [
            {
                "tema": mod_lev.NAO_MENCIONADO,
                "inicio": "",
                "fim": "",
                "onde_parou": "",
            }
        ]
        avisos_extra.append("modelo omitiu os temas — seção preenchida com declaração explícita")

    criterios_gerais = []
    for c in payload.get("criterios_gerais") or []:
        if isinstance(c, str) and c.strip():
            criterios_gerais.append(c.strip())
        elif isinstance(c, dict) and str(c.get("texto") or c.get("criterio") or "").strip():
            criterios_gerais.append(
                str(c.get("texto") or c.get("criterio")).strip()
            )

    bloco = mod_decisoes.decisoes_para_markdown(decisoes)
    avisos_dec = mod_decisoes.validar_decisoes(decisoes)
    avisos_txt = mod_decisoes.relatorio_decisoes(decisoes)
    if avisos_extra:
        avisos_txt = avisos_txt + ("\n" if avisos_txt else "") + "\n".join(
            f"- {a}" for a in avisos_extra
        )

    criterios_md = (
        "\n".join(f"- {c}" for c in criterios_gerais)
        if criterios_gerais
        else f"_{mod_lev.NAO_MENCIONADO}_"
    )
    md = (
        "# Resumo das decisões\n\n"
        f"## Contexto principal\n\n{contexto}\n\n"
        f"## Temas discutidos\n\n{_temas_para_markdown(temas)}\n\n"
        f"## Decisões tomadas\n\n{bloco}\n\n"
        "## Critérios e justificativas que valem além desta reunião\n\n"
        f"{criterios_md}\n\n"
        f"## O que não ficou registrado\n\n{avisos_txt}"
    )
    avisos_finais = [a.mensagem for a in avisos_dec] + avisos_extra
    preenc, total = mod_cob.cobertura_resumo_decisoes(contexto, temas, decisoes)
    avisos_finais, md = mod_cob.aplicar_cobertura(avisos_finais, md, preenc, total)
    out = {
        "contexto": contexto,
        "temas": temas,
        "decisoes": [d.para_dict() for d in decisoes],
        "criterios_gerais": criterios_gerais,
        "cobertura": {"preenchidos": preenc, "total": total},
        "avisos": [
            {"tipo": a.tipo, "mensagem": a.mensagem, "gravidade": a.gravidade}
            for a in avisos_dec
        ]
        + [{"tipo": "estrutura", "mensagem": a, "gravidade": "alta"} for a in avisos_extra]
        + [
            {
                "tipo": "cobertura",
                "mensagem": m,
                "gravidade": "alta" if mod_cob.AVISO_ESTRUTURA_INADEQUADA in m else "baixa",
            }
            for m in avisos_finais
            if m.startswith("Cobertura") or m.startswith(mod_cob.AVISO_ESTRUTURA_INADEQUADA)
        ],
    }
    caminho_json = _gravar(
        stem, "resumo_decisoes.json", json.dumps(out, ensure_ascii=False, indent=2)
    )
    caminho_md = _gravar(stem, "resumo_decisoes.md", md)
    return SkillResultado(
        name="resumo-decisoes",
        ok=True,
        caminhos={"json": str(caminho_json), "markdown": str(caminho_md)},
        markdown=md,
        avisos=avisos_finais,
    )


def _run_proxima_reuniao(
    texto: str,
    stem: str,
    skill: SkillMeta,
    *,
    incluir_manual_voz: bool,
) -> SkillResultado:
    proc = mod_proc.exigir(stem, texto)
    lev = _ler_levantamento(stem)
    data_ref = _data_reuniao(proc) or date.today()
    extras = []
    for nome in ("pontos_de_acao.md", "resumo_decisoes.md"):
        p = mod_proc.pasta_do_stem(stem) / nome
        if p.is_file():
            extras.append(f"### {nome}\n{p.read_text(encoding='utf-8')[:12000]}")
    user = (
        "Monte a pauta da próxima reunião. JSON:\n"
        '{"data_expressao":"semana que vem","duracao_min":30,'
        '"itens":[{"id":"i1","assunto":"...","objetivo":"...","dono":"...",'
        '"minutos":5,"origem":"pergunta|adiado|pendencia|sem_criterio","material":"nenhum"}],'
        '"presentes":["..."],"citados_ausentes":["..."]}\n\n'
        f"### Data da reunião atual\n{data_ref.isoformat()}\n\n"
        f"### Levantamento\n{mod_lev.levantamento_para_markdown(lev)}\n\n"
        + ("\n\n".join(extras) + "\n\n" if extras else "")
        + f"### Transcrição processada\n{proc.texto_ancorado[:60000]}"
    )
    raw = _llm(skill, user, incluir_manual_voz=incluir_manual_voz, json_mode=True)
    payload = _extrair_json(raw)
    if not isinstance(payload, dict):
        raise ValueError("JSON da pauta inválido.")
    duracao = int(payload.get("duracao_min") or mod_pauta.DURACAO_PADRAO_MIN)
    itens: list[mod_pauta.ItemPauta] = []
    for item in payload.get("itens") or []:
        if not isinstance(item, dict):
            continue
        assunto = str(item.get("assunto") or "").strip()
        if not assunto:
            continue
        origem_raw = str(item.get("origem") or mod_pauta.ORIGEM_PENDENCIA).strip()
        # Aceita aliases curtos vindos do LLM.
        alias = {
            "pergunta": mod_pauta.ORIGEM_PERGUNTA,
            "adiado": mod_pauta.ORIGEM_ADIADO,
            "pendencia": mod_pauta.ORIGEM_PENDENCIA,
            "sem_criterio": mod_pauta.ORIGEM_SEM_CRITERIO,
        }
        origem = alias.get(origem_raw, origem_raw)
        if origem not in mod_pauta.ORIGENS:
            origem = mod_pauta.ORIGEM_PENDENCIA
        itens.append(
            mod_pauta.ItemPauta(
                assunto=assunto,
                objetivo=str(item.get("objetivo") or "").strip(),
                dono=item.get("dono"),
                minutos=int(item.get("minutos") or 0),
                origem=origem,
                material=str(item.get("material") or "nenhum"),
                ancora=str(item.get("ancora") or ""),
            )
        )
    data_info = mod_pauta.resolver_data(
        str(payload.get("data_expressao") or ""), data_ref
    )
    participantes = mod_pauta.sugerir_participantes(
        donos_de_itens=[i.dono for i in itens if i.dono],
        citados_ausentes=list(payload.get("citados_ausentes") or []),
        presentes=list(payload.get("presentes") or []),
    )
    md_pauta = mod_pauta.pauta_para_markdown(
        itens,
        participantes,
        data_texto=str(data_info.get("texto") or "[data não combinada]"),
        duracao_min=duracao,
    )
    conferencia = mod_pauta.relatorio_pauta(itens, duracao_min=duracao)
    md = (
        "# Próxima reunião\n\n"
        + md_pauta
        + "\n\n## Conferência da pauta\n\n"
        + conferencia
    )
    avisos_lista = [
        a.mensagem for a in mod_pauta.validar_pauta(itens, duracao_min=duracao)
    ]
    data_ok = bool(data_info.get("data"))
    preenc, total = mod_cob.cobertura_proxima_reuniao(itens, data_ok=data_ok)
    avisos_lista, md = mod_cob.aplicar_cobertura(avisos_lista, md, preenc, total)
    out = {
        "data": data_info,
        "duracao_min": duracao,
        "itens": [i.para_dict() for i in itens],
        "participantes": [
            {
                "nome": p.nome,
                "motivo": p.motivo,
                "obrigatorio": p.obrigatorio,
            }
            for p in participantes
        ],
        "cobertura": {"preenchidos": preenc, "total": total},
        "avisos": [
            {"tipo": a.tipo, "mensagem": a.mensagem}
            for a in mod_pauta.validar_pauta(itens, duracao_min=duracao)
        ],
    }
    caminho_json = _gravar(
        stem, "proxima_reuniao.json", json.dumps(out, ensure_ascii=False, indent=2)
    )
    caminho_md = _gravar(stem, "proxima_reuniao.md", md)
    return SkillResultado(
        name="proxima-reuniao",
        ok=True,
        caminhos={"json": str(caminho_json), "markdown": str(caminho_md)},
        markdown=md,
        avisos=avisos_lista,
    )


_HANDLERS = {
    "levantamento-reuniao": "levantamento",
    "pontos-de-acao": "pontos",
    "resumo-decisoes": "decisoes",
    "proxima-reuniao": "pauta",
}


def rodar_pipeline(
    texto: str,
    *,
    stem: str,
    skills: list[str] | None = None,
    origem: str = "",
    incluir_manual_voz: bool = True,
    progress: ProgressCb = None,
) -> PipelineResultado:
    """Roda as skills selecionadas (com deps) e grava em outputs/analise_texto/<stem>/.

    O processamento da transcrição é pré-requisito interno (sempre roda, não
    aparece como skill na UI nem no painel de resultados).
    """
    if not (texto or "").strip():
        raise ValueError("Transcrição vazia.")
    stem = Path(stem).stem or "transcricao"
    pedidas = skills if skills is not None else [s.name for s in listar_skills()]
    # Infraestrutura / fundidas nunca entram na lista selecionável.
    pedidas = [n for n in pedidas if n not in {"processamento", "ata-reuniao"}]
    ordem = garantir_dependencias(pedidas)
    if not ordem:
        raise ValueError("Nenhuma skill válida selecionada.")

    nomes = nomes_do_cadastro()
    resultado = PipelineResultado(
        stem=stem,
        pasta=str(mod_proc.pasta_do_stem(stem)),
    )

    _progresso(progress, "Preparando transcrição…")
    try:
        r_proc = _run_processamento(texto, stem, origem=origem, nomes=nomes)
    except Exception as exc:  # noqa: BLE001
        resultado.erros.append(f"preparação: {exc}")
        return resultado
    if not r_proc.ok:
        resultado.erros.append(r_proc.erro or "Falha ao preparar a transcrição.")
        return resultado
    # Avisos internos (ex.: turnos sem falante) sobem sem expor a skill.
    resultado.erros.extend(r_proc.avisos)

    for name in ordem:
        skill = obter_skill(name)
        if skill is None:
            resultado.skills.append(
                SkillResultado(name=name, ok=False, erro="Skill não encontrada em skills/")
            )
            resultado.erros.append(f"{name}: não encontrada")
            continue
        _progresso(progress, f"Executando skill `{name}`…")
        try:
            if name == "levantamento-reuniao":
                item = _run_levantamento(
                    texto,
                    stem,
                    skill,
                    nomes=nomes,
                    incluir_manual_voz=incluir_manual_voz,
                )
            elif name == "pontos-de-acao":
                item = _run_pontos_acao(
                    texto, stem, skill, incluir_manual_voz=incluir_manual_voz
                )
            elif name == "resumo-decisoes":
                item = _run_resumo_decisoes(
                    texto, stem, skill, incluir_manual_voz=incluir_manual_voz
                )
            elif name == "proxima-reuniao":
                item = _run_proxima_reuniao(
                    texto, stem, skill, incluir_manual_voz=incluir_manual_voz
                )
            else:
                item = SkillResultado(
                    name=name,
                    ok=False,
                    erro="Handler não implementado no runner.",
                )
        except Exception as exc:  # noqa: BLE001
            item = SkillResultado(name=name, ok=False, erro=str(exc))
            resultado.erros.append(f"{name}: {exc}")

        resultado.skills.append(item)
        # Propaga aviso de estrutura inadequada para o topo do pipeline.
        for aviso in item.avisos:
            if aviso.startswith(mod_cob.AVISO_ESTRUTURA_INADEQUADA):
                resultado.erros.append(f"{name}: {aviso}")
                break
        if not item.ok and name == "levantamento-reuniao":
            # Sem levantamento, as próximas falhariam em cascata.
            break

    return resultado
