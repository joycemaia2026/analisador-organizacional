"""Leitura e limpeza heurística de currículos .txt."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from core.utils import (
    PESSOAS_DIR,
    extrair_nome_bruto,
    limpar_ruido_linkedin,
    slug_from_path,
)


SECOES = (
    "experiência",
    "experiencia",
    "formação acadêmica",
    "formacao academica",
    "formação",
    "formacao",
    "competências",
    "competencias",
    "certificações",
    "certificacoes",
    "idiomas",
    "sobre",
)


@dataclass
class CurriculoBruto:
    id: str
    caminho: Path
    nome: str
    texto_limpo: str
    secoes: dict[str, str] = field(default_factory=dict)
    mtime: float = 0.0


def listar_arquivos_curriculo(diretorio: Path | None = None) -> list[Path]:
    base = diretorio or PESSOAS_DIR
    if not base.exists():
        return []
    return sorted(base.glob("*.txt"))


def _normalizar_titulo_secao(linha: str) -> str | None:
    baixa = linha.strip().lower()
    for secao in SECOES:
        if baixa == secao or baixa.startswith(secao + " "):
            if "experi" in baixa:
                return "experiencia"
            if "forma" in baixa:
                return "formacao"
            if "compet" in baixa:
                return "competencias"
            if "certif" in baixa:
                return "certificacoes"
            if "idioma" in baixa:
                return "idiomas"
            if baixa.startswith("sobre"):
                return "sobre"
    return None


def _fatiar_secoes(texto: str) -> dict[str, str]:
    secoes: dict[str, list[str]] = {}
    atual: str | None = None
    for linha in texto.splitlines():
        titulo = _normalizar_titulo_secao(linha)
        if titulo:
            atual = titulo
            secoes.setdefault(atual, [])
            continue
        if atual is not None:
            secoes[atual].append(linha)
    return {k: "\n".join(v).strip() for k, v in secoes.items() if "".join(v).strip()}


def _estimar_cargo_empresa(texto: str) -> tuple[str, str]:
    """Heurística leve: primeiros cargos/empresas após Experiência."""
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    cargo = ""
    empresa = ""
    for i, linha in enumerate(linhas):
        baixa = linha.lower()
        if baixa in {"experiência", "experiencia"}:
            # Próximas linhas úteis
            for j in range(i + 1, min(i + 8, len(linhas))):
                cand = linhas[j]
                if re.search(r"\b(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez|\d{4})\b", cand.lower()):
                    continue
                if "·" in cand and not empresa:
                    empresa = cand.split("·")[0].strip()
                    continue
                if not cargo and len(cand) < 80:
                    cargo = cand
                elif not empresa and len(cand) < 80:
                    empresa = cand.split("·")[0].strip()
                if cargo and empresa:
                    break
            break
    return cargo, empresa


def ler_curriculo(path: Path) -> CurriculoBruto:
    bruto = path.read_text(encoding="utf-8", errors="ignore")
    limpo = limpar_ruido_linkedin(bruto)
    nome = extrair_nome_bruto(limpo)
    secoes = _fatiar_secoes(limpo)
    cargo, empresa = _estimar_cargo_empresa(limpo)
    if cargo or empresa:
        secoes["_heuristica_cargo"] = cargo
        secoes["_heuristica_empresa"] = empresa
    return CurriculoBruto(
        id=slug_from_path(path),
        caminho=path,
        nome=nome,
        texto_limpo=limpo,
        secoes=secoes,
        mtime=path.stat().st_mtime,
    )


def ler_todos_curriculos(diretorio: Path | None = None) -> list[CurriculoBruto]:
    return [ler_curriculo(p) for p in listar_arquivos_curriculo(diretorio)]
