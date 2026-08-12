"""Carrega o corpo das skills locais do BriefBoard (SKILL.md)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from core.utils import ROOT_DIR

_SKILL_DIRS = (
    ROOT_DIR / ".claude" / "skills",
    ROOT_DIR / ".agents" / "skills",
    ROOT_DIR / "skills",
)


@lru_cache(maxsize=32)
def corpo_skill(nome: str, *, max_chars: int = 12000) -> str:
    """Texto após o frontmatter YAML — vazio se a skill não existir."""
    for base in _SKILL_DIRS:
        caminho = base / nome / "SKILL.md"
        if not caminho.is_file():
            continue
        raw = caminho.read_text(encoding="utf-8")
        if raw.startswith("---"):
            partes = raw.split("---", 2)
            if len(partes) >= 3:
                return partes[2].strip()[:max_chars]
        return raw.strip()[:max_chars]
    return ""
