"""Descobre e descreve as skills do BriefBoard em `skills/*/SKILL.md`."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.utils import ROOT_DIR

SKILLS_DIR = ROOT_DIR / "skills"

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)


@dataclass(frozen=True)
class SkillMeta:
    name: str
    description: str
    ordem: int
    obrigatoria: bool
    entrada: str
    saida: str
    version: str
    path: Path
    body: str

    @property
    def rotulo(self) -> str:
        return f"{self.ordem}. {self.name}"


def _parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    m = _FRONTMATTER_RE.match(raw.strip())
    if not m:
        return {}, raw
    meta: dict[str, Any] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        chave, _, valor = line.partition(":")
        chave = chave.strip()
        valor = valor.strip().strip('"').strip("'")
        if chave == "ordem":
            try:
                meta[chave] = int(valor)
            except ValueError:
                meta[chave] = 99
        elif chave == "obrigatoria":
            meta[chave] = valor.lower() in {"true", "1", "yes", "sim"}
        elif chave == "metadata":
            continue
        else:
            meta[chave] = valor
    # nested metadata.ordem already handled as top-level in our SKILL files
    return meta, m.group(2).strip()


def _parse_skill_file(caminho: Path) -> SkillMeta | None:
    try:
        raw = caminho.read_text(encoding="utf-8")
    except OSError:
        return None
    meta, body = _parse_frontmatter(raw)
    name = str(meta.get("name") or caminho.parent.name).strip()
    if not name:
        return None

    # metadata block may put ordem under nested yaml; our files put it under metadata:
    # We also accept ordem at top level after a second pass for "  ordem: N" lines.
    if "ordem" not in meta:
        m_ord = re.search(r"(?m)^\s*ordem:\s*(\d+)\s*$", raw)
        if m_ord:
            meta["ordem"] = int(m_ord.group(1))
    if "obrigatoria" not in meta:
        m_ob = re.search(r"(?m)^\s*obrigatoria:\s*(true|false)\s*$", raw, re.I)
        if m_ob:
            meta["obrigatoria"] = m_ob.group(1).lower() == "true"

    return SkillMeta(
        name=name,
        description=str(meta.get("description") or "").strip(),
        ordem=int(meta.get("ordem", 99)),
        obrigatoria=bool(meta.get("obrigatoria", False)),
        entrada=str(meta.get("entrada") or "").strip(),
        saida=str(meta.get("saida") or "").strip(),
        version=str(meta.get("version") or "").strip(),
        path=caminho,
        body=body,
    )


# Skills ocultas na UI do BriefBoard (infra ou fundidas em outra etapa).
_SKILLS_OCULTAS = frozenset({"ata-reuniao", "processamento"})


def listar_skills(*, apenas_framework: bool = True) -> list[SkillMeta]:
    """Skills selecionáveis em `skills/`, ordenadas por `ordem`.

    Ocultas na UI:
    - ``ata-reuniao`` — fundida em **Gerar Ata**
    - ``processamento`` — pré-requisito interno (código), sempre automático
    """
    _ = apenas_framework
    if not SKILLS_DIR.is_dir():
        return []
    encontradas: list[SkillMeta] = []
    for pasta in sorted(SKILLS_DIR.iterdir()):
        if not pasta.is_dir():
            continue
        skill_md = pasta / "SKILL.md"
        if not skill_md.is_file():
            continue
        meta = _parse_skill_file(skill_md)
        if meta is None:
            continue
        if meta.name in _SKILLS_OCULTAS:
            continue
        encontradas.append(meta)
    encontradas.sort(key=lambda s: (s.ordem, s.name))
    return encontradas


def obter_skill(name: str, *, incluir_fundidas: bool = False) -> SkillMeta | None:
    alvo = (name or "").strip()
    if incluir_fundidas and alvo in _SKILLS_OCULTAS:
        caminho = SKILLS_DIR / alvo / "SKILL.md"
        if caminho.is_file():
            return _parse_skill_file(caminho)
    for s in listar_skills():
        if s.name == alvo:
            return s
    return None


def ids_skills() -> list[str]:
    return [s.name for s in listar_skills()]


# Skills que consomem o levantamento (incluem a dep. automaticamente).
_PRECISA_LEVANTAMENTO = frozenset(
    {"resumo-decisoes", "pontos-de-acao", "proxima-reuniao"}
)


def garantir_dependencias(selecionadas: list[str]) -> list[str]:
    """Ordena skills para execução e inclui levantamento quando necessário.

    ``processamento`` não entra na lista: o runner garante como pré-requisito.
    Exibição na UI: 1 resumo · 2 levantamento · 3 pontos · 4 próxima reunião.
    Execução: levantamento sempre antes das skills que o consomem.
    """
    catalogo = {s.name: s for s in listar_skills()}
    pedidas = {n for n in selecionadas if n in catalogo}
    if not pedidas:
        return []

    if pedidas & _PRECISA_LEVANTAMENTO:
        pedidas.add("levantamento-reuniao")

    resto = sorted(
        (n for n in pedidas if n != "levantamento-reuniao"),
        key=lambda n: (catalogo[n].ordem, n),
    )
    if "levantamento-reuniao" in pedidas:
        return ["levantamento-reuniao", *resto]
    return resto
