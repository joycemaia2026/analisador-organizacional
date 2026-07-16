"""Utilitários compartilhados."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
PESSOAS_DIR = ROOT_DIR / "pessoas"
PERFIS_DIR = ROOT_DIR / "perfis"
PERFIS_JSON = PERFIS_DIR / "perfis.json"
OUTPUTS_DIR = ROOT_DIR / "outputs"
ASSETS_DIR = ROOT_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "Gedanken.png"
# Fallback legado
if not LOGO_PATH.exists():
    LOGO_PATH = ASSETS_DIR / "logo.png"


def ensure_dirs() -> None:
    PESSOAS_DIR.mkdir(parents=True, exist_ok=True)
    PERFIS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def slug_from_path(path: Path) -> str:
    return path.stem.lower().strip()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def limpar_ruido_linkedin(texto: str) -> str:
    """Remove artefatos típicos de export LinkedIn."""
    linhas = []
    for linha in texto.splitlines():
        limpa = linha.strip()
        if limpa.startswith("Logo da empresa"):
            # Mantém só o nome da empresa depois do prefixo, se houver.
            resto = limpa.replace("Logo da empresa", "", 1).strip()
            if resto:
                linhas.append(resto)
            continue
        linhas.append(linha.rstrip())
    texto = "\n".join(linhas)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def extrair_nome_bruto(texto: str) -> str:
    """Usa a primeira linha não vazia como nome candidato."""
    for linha in texto.splitlines():
        nome = linha.strip()
        if nome and not nome.lower().startswith("experiência"):
            return capitalizar_nome(nome)
    return "Profissional sem nome"


def capitalizar_nome(nome: str) -> str:
    nome = (nome or "").strip()
    if not nome:
        return nome
    if nome.isupper() or nome.islower() or nome == nome.lower():
        return nome.title()
    return nome


def _formatar_dict_formacao(dados: dict[str, Any]) -> str:
    curso = str(dados.get("curso") or dados.get("degree") or "").strip()
    area = str(dados.get("area") or dados.get("campo") or "").strip()
    instituicao = str(
        dados.get("instituicao") or dados.get("institution") or dados.get("escola") or ""
    ).strip()
    inicio = dados.get("ano_inicio") or dados.get("inicio")
    fim = dados.get("ano_fim") or dados.get("fim") or dados.get("ano")

    partes: list[str] = []
    if curso and area:
        partes.append(f"{curso} em {area}")
    elif curso:
        partes.append(curso)
    elif area:
        partes.append(area)

    if instituicao:
        partes.append(f"— {instituicao}" if partes else instituicao)

    if inicio and fim:
        partes.append(f"({inicio}–{fim})")
    elif fim:
        partes.append(f"({fim})")
    elif inicio:
        partes.append(f"(desde {inicio})")

    texto = " ".join(partes).strip()
    return texto or json.dumps(dados, ensure_ascii=False)


def formatar_item_lista(item: Any) -> str:
    """Converte item de lista (str/dict/repr) em texto legível."""
    if item is None:
        return ""
    if isinstance(item, dict):
        return _formatar_dict_formacao(item)
    if isinstance(item, (list, tuple)):
        return "; ".join(formatar_item_lista(x) for x in item if x)

    texto = str(item).strip()
    if not texto:
        return ""

    # Corrige resíduos do modelo: "{'curso': ...}"
    if (texto.startswith("{") and texto.endswith("}")) or (
        texto.startswith("[") and texto.endswith("]")
    ):
        try:
            parsed = ast.literal_eval(texto)
            return formatar_item_lista(parsed)
        except (SyntaxError, ValueError):
            try:
                parsed = json.loads(texto.replace("'", '"'))
                return formatar_item_lista(parsed)
            except (json.JSONDecodeError, TypeError):
                return texto
    return texto


def normalizar_lista_texto(valores: Any) -> list[str]:
    if valores is None:
        return []
    if isinstance(valores, str):
        valores = [valores]
    if not isinstance(valores, list):
        item = formatar_item_lista(valores)
        return [item] if item else []
    saida: list[str] = []
    for v in valores:
        texto = formatar_item_lista(v)
        if texto:
            saida.append(texto)
    return saida
