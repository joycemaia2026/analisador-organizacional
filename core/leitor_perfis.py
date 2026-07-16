"""Carrega e atualiza perfis analíticos a partir dos currículos."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from core.openai_client import chat_completion
from core.parser_curriculo import CurriculoBruto, ler_todos_curriculos
from core.prompts import prompt_conversao
from core.utils import (
    PERFIS_JSON,
    PESSOAS_DIR,
    capitalizar_nome,
    ensure_dirs,
    load_json,
    normalizar_lista_texto,
    save_json,
    slug_from_path,
)


SCHEMA_CAMPOS = (
    "nome",
    "cargo",
    "empresa",
    "formacao",
    "especialidades",
    "competencias",
    "certificacoes",
    "anos_experiencia",
    "areas_atuacao",
    "perfil_analitico",
    "forma_de_pensar",
    "principais_perguntas",
    "indicadores_prioritarios",
    "pontos_fortes",
    "limitacoes",
)

CAMPOS_LISTA = {
    "formacao",
    "especialidades",
    "competencias",
    "certificacoes",
    "areas_atuacao",
    "forma_de_pensar",
    "principais_perguntas",
    "indicadores_prioritarios",
    "pontos_fortes",
    "limitacoes",
}


def _perfil_vazio(curriculo: CurriculoBruto) -> dict[str, Any]:
    return {
        "id": curriculo.id,
        "nome": curriculo.nome,
        "cargo": curriculo.secoes.get("_heuristica_cargo", ""),
        "empresa": curriculo.secoes.get("_heuristica_empresa", ""),
        "formacao": [],
        "especialidades": [],
        "competencias": [],
        "certificacoes": [],
        "anos_experiencia": 0,
        "areas_atuacao": [],
        "perfil_analitico": "",
        "forma_de_pensar": [],
        "principais_perguntas": [],
        "indicadores_prioritarios": [],
        "pontos_fortes": [],
        "limitacoes": [],
        "fonte": {
            "arquivo": curriculo.caminho.name,
            "mtime": curriculo.mtime,
        },
    }


def _extrair_json(texto: str) -> dict[str, Any]:
    texto = texto.strip()
    if texto.startswith("```"):
        texto = re.sub(r"^```(?:json)?\s*", "", texto)
        texto = re.sub(r"\s*```$", "", texto)
    return json.loads(texto)


def sanitizar_perfil(perfil: dict[str, Any]) -> dict[str, Any]:
    """Garante strings legíveis nos campos de lista e nome capitalizado."""
    limpo = dict(perfil)
    limpo["nome"] = capitalizar_nome(str(limpo.get("nome") or ""))
    limpo["cargo"] = str(limpo.get("cargo") or "").strip()
    limpo["empresa"] = str(limpo.get("empresa") or "").strip()
    limpo["perfil_analitico"] = str(limpo.get("perfil_analitico") or "").strip()
    try:
        limpo["anos_experiencia"] = int(limpo.get("anos_experiencia") or 0)
    except (TypeError, ValueError):
        limpo["anos_experiencia"] = 0
    for campo in CAMPOS_LISTA:
        limpo[campo] = normalizar_lista_texto(limpo.get(campo))
    return limpo


def _normalizar_perfil(curriculo: CurriculoBruto, bruto: dict[str, Any]) -> dict[str, Any]:
    base = _perfil_vazio(curriculo)
    for campo in SCHEMA_CAMPOS:
        if campo not in bruto:
            continue
        valor = bruto[campo]
        if campo == "anos_experiencia":
            try:
                base[campo] = int(valor)
            except (TypeError, ValueError):
                base[campo] = 0
        elif campo in CAMPOS_LISTA:
            base[campo] = normalizar_lista_texto(valor)
        elif campo == "nome":
            base[campo] = capitalizar_nome(str(valor) if valor is not None else "")
        else:
            base[campo] = str(valor).strip() if valor is not None else ""
    if not base["nome"]:
        base["nome"] = curriculo.nome
    base["id"] = curriculo.id
    return sanitizar_perfil(base)


def converter_curriculo(curriculo: CurriculoBruto) -> dict[str, Any]:
    messages = prompt_conversao(curriculo.id, curriculo.texto_limpo)
    resposta = chat_completion(
        messages,
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    dados = _extrair_json(resposta)
    return _normalizar_perfil(curriculo, dados)


def _cache_por_id(perfis: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {p.get("id", ""): p for p in perfis if p.get("id")}


def _precisa_reconverter(curriculo: CurriculoBruto, cached: dict[str, Any] | None) -> bool:
    if cached is None:
        return True
    fonte = cached.get("fonte") or {}
    try:
        return float(fonte.get("mtime", 0)) < float(curriculo.mtime)
    except (TypeError, ValueError):
        return True


def carregar_ou_converter_perfis(
    *,
    forcar: bool = False,
    progresso: Any = None,
) -> list[dict[str, Any]]:
    """
    Carrega perfis/perfis.json e reconverte apenas currículos novos ou alterados.
    `progresso` pode ser um callable(msg: str) para feedback na UI.
    """
    ensure_dirs()
    curriculos = ler_todos_curriculos()
    if not curriculos:
        save_json(PERFIS_JSON, [])
        return []

    existentes: list[dict[str, Any]] = []
    if PERFIS_JSON.exists():
        try:
            dados = load_json(PERFIS_JSON)
            if isinstance(dados, list):
                existentes = dados
        except (json.JSONDecodeError, OSError):
            existentes = []

    por_id = _cache_por_id(existentes)
    atualizados: list[dict[str, Any]] = []
    alterou_cache = False

    for curriculo in curriculos:
        cached = por_id.get(curriculo.id)
        if forcar or _precisa_reconverter(curriculo, cached):
            if progresso:
                progresso(f"Convertendo perfil: {curriculo.nome}…")
            perfil = converter_curriculo(curriculo)
            atualizados.append(perfil)
            alterou_cache = True
        else:
            perfil = sanitizar_perfil(cached)
            perfil["id"] = curriculo.id
            if perfil != cached:
                alterou_cache = True
            atualizados.append(perfil)

    if alterou_cache or not PERFIS_JSON.exists():
        save_json(PERFIS_JSON, atualizados)
    return atualizados


def carregar_perfis_cached() -> list[dict[str, Any]]:
    ensure_dirs()
    if not PERFIS_JSON.exists():
        return []
    dados = load_json(PERFIS_JSON)
    if not isinstance(dados, list):
        return []
    return [sanitizar_perfil(p) for p in dados]


def _ids_em_cache() -> set[str]:
    return {p.get("id", "") for p in carregar_perfis_cached() if p.get("id")}


def listar_novos_curriculos() -> list[CurriculoBruto]:
    """Arquivos em pessoas/ que ainda não têm perfil em perfis.json."""
    ids = _ids_em_cache()
    return [c for c in ler_todos_curriculos() if c.id not in ids]


def listar_curriculos_existentes() -> list[CurriculoBruto]:
    """Arquivos em pessoas/ que já possuem perfil."""
    ids = _ids_em_cache()
    return [c for c in ler_todos_curriculos() if c.id in ids]


def adicionar_novas_personas(*, progresso: Any = None) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Lê a pasta pessoas/ e converte só os .txt novos (ainda sem perfil).
    Retorna (perfis_adicionados, nomes_arquivos).
    """
    novos = listar_novos_curriculos()
    if not novos:
        return [], []

    adicionados: list[dict[str, Any]] = []
    nomes: list[str] = []
    for curriculo in novos:
        if progresso:
            progresso(f"Adicionando: {curriculo.nome} ({curriculo.caminho.name})…")
        perfil = converter_curriculo(curriculo)
        adicionados.append(perfil)
        nomes.append(curriculo.caminho.name)

    # Mescla no cache completo.
    por_id = _cache_por_id(carregar_perfis_cached())
    for perfil in adicionados:
        por_id[perfil["id"]] = perfil

    # Mantém ordem dos arquivos atuais em pessoas/.
    ordem = [c.id for c in ler_todos_curriculos()]
    finais = [por_id[i] for i in ordem if i in por_id]
    # Inclui órfãos de cache se ainda existirem (não deveria).
    for pid, perfil in por_id.items():
        if pid not in {p["id"] for p in finais}:
            finais.append(perfil)

    save_json(PERFIS_JSON, finais)
    return adicionados, nomes


def atualizar_personas_da_pasta(
    *,
    forcar: bool = True,
    progresso: Any = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Relê pessoas/ e atualiza perfis já existentes (reconverte via IA).
    Retorna (perfis_atualizados, nomes_arquivos).
    """
    existentes = listar_curriculos_existentes()
    if not existentes:
        return [], []

    atualizados: list[dict[str, Any]] = []
    nomes: list[str] = []
    por_id = _cache_por_id(carregar_perfis_cached())

    for curriculo in existentes:
        cached = por_id.get(curriculo.id)
        if forcar or _precisa_reconverter(curriculo, cached):
            if progresso:
                progresso(f"Atualizando: {curriculo.nome} ({curriculo.caminho.name})…")
            perfil = converter_curriculo(curriculo)
            por_id[curriculo.id] = perfil
            atualizados.append(perfil)
            nomes.append(curriculo.caminho.name)

    ordem = [c.id for c in ler_todos_curriculos()]
    finais = [por_id[i] for i in ordem if i in por_id]
    for pid, perfil in por_id.items():
        if pid not in {p["id"] for p in finais}:
            finais.append(perfil)

    if atualizados:
        save_json(PERFIS_JSON, finais)
    return atualizados, nomes


def obter_perfil_por_id(perfis: list[dict[str, Any]], perfil_id: str) -> dict[str, Any] | None:
    for p in perfis:
        if p.get("id") == perfil_id:
            return p
    return None


def _slug_arquivo_seguro(nome: str) -> str:
    base = Path(nome).stem if nome else "persona"
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", base).strip("_").lower()
    return slug or "persona"


def _proximo_nome_persona() -> str:
    """Gera personaN.txt livre em pessoas/."""
    ensure_dirs()
    existentes = {p.stem.lower() for p in PESSOAS_DIR.glob("*.txt")}
    n = 1
    while f"persona{n}" in existentes:
        n += 1
    return f"persona{n}.txt"


def caminho_curriculo_por_id(perfil_id: str) -> Path | None:
    """Resolve o .txt em pessoas/ a partir do id do perfil."""
    ensure_dirs()
    candidato = PESSOAS_DIR / f"{perfil_id}.txt"
    if candidato.exists():
        return candidato
    for path in PESSOAS_DIR.glob("*.txt"):
        if slug_from_path(path) == perfil_id:
            return path
    return None


def salvar_curriculo_texto(
    texto: str,
    *,
    perfil_id: str | None = None,
    nome_arquivo: str | None = None,
) -> Path:
    """
    Grava currículo em pessoas/.
    - Com perfil_id: sobrescreve a persona existente.
    - Sem perfil_id: cria nova (usa nome_arquivo ou personaN.txt).
    """
    ensure_dirs()
    conteudo = (texto or "").strip()
    if not conteudo:
        raise ValueError("Currículo vazio.")

    if perfil_id:
        destino = caminho_curriculo_por_id(perfil_id)
        if destino is None:
            destino = PESSOAS_DIR / f"{_slug_arquivo_seguro(perfil_id)}.txt"
    else:
        if nome_arquivo:
            slug = _slug_arquivo_seguro(nome_arquivo)
            destino = PESSOAS_DIR / f"{slug}.txt"
            if destino.exists():
                # Evita sobrescrever sem intenção: gera nome livre.
                destino = PESSOAS_DIR / _proximo_nome_persona()
        else:
            destino = PESSOAS_DIR / _proximo_nome_persona()

    destino.write_text(conteudo + "\n", encoding="utf-8")
    return destino


def atualizar_perfis_apos_mudanca(
    *,
    forcar_todos: bool = False,
    progresso: Any = None,
) -> list[dict[str, Any]]:
    """Reconverte perfis após inclusão/alteração de arquivos em pessoas/."""
    return carregar_ou_converter_perfis(forcar=forcar_todos, progresso=progresso)
