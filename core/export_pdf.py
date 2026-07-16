"""Exportação de Markdown para PDF (fpdf2)."""

from __future__ import annotations

import io
import re
from pathlib import Path

from fpdf import FPDF

_RE_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_RE_UL = re.compile(r"^[-*]\s+(.*)$")
_RE_OL = re.compile(r"^(\d+)[.)]\s+(.*)$")
_RE_BOLD = re.compile(r"\*\*(.+?)\*\*")


def _limpar_md_inline(texto: str) -> str:
    return _RE_BOLD.sub(r"\1", texto or "")


def _safe_latin(texto: str) -> str:
    """Converte para latin-1 com substituição (Helvetica)."""
    # Troca tipográficos comuns por ASCII seguro.
    mapa = {
        "•": "-",
        "–": "-",
        "—": "-",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "…": "...",
    }
    out = texto or ""
    for a, b in mapa.items():
        out = out.replace(a, b)
    return out.encode("latin-1", errors="replace").decode("latin-1")


class _PdfAta(FPDF):
    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", size=8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, str(self.page_no()), align="C")


def markdown_para_pdf_bytes(titulo: str, markdown: str) -> bytes:
    """Converte Markdown básico em PDF (bytes)."""
    pdf = _PdfAta(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_left_margin(18)
    pdf.set_right_margin(18)
    usable = pdf.epw

    def _write(txt: str, *, size: int = 11, bold: bool = False, color=None) -> None:
        style = "B" if bold else ""
        pdf.set_font("Helvetica", style, size)
        if color:
            pdf.set_text_color(*color)
        else:
            pdf.set_text_color(0, 0, 0)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(usable, 6, _safe_latin(txt))

    _write(titulo, size=16, bold=True, color=(0, 16, 96))
    pdf.ln(3)

    for linha in (markdown or "").replace("\r\n", "\n").split("\n"):
        strip = linha.strip()
        if not strip:
            pdf.ln(2)
            continue

        m_h = _RE_HEADING.match(strip)
        if m_h:
            nivel = len(m_h.group(1))
            sizes = {1: 14, 2: 13, 3: 12}
            _write(
                _limpar_md_inline(m_h.group(2)),
                size=sizes.get(nivel, 11),
                bold=True,
                color=(0, 16, 96),
            )
            pdf.ln(1)
            continue

        m_ul = _RE_UL.match(strip)
        if m_ul:
            _write(f"- {_limpar_md_inline(m_ul.group(1))}")
            continue

        m_ol = _RE_OL.match(strip)
        if m_ol:
            _write(f"{m_ol.group(1)}. {_limpar_md_inline(m_ol.group(2))}")
            continue

        _write(_limpar_md_inline(strip))

    out = io.BytesIO()
    pdf.output(out)
    return out.getvalue()


def salvar_markdown_como_pdf(caminho: Path, titulo: str, markdown: str) -> Path:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(markdown_para_pdf_bytes(titulo, markdown))
    return caminho
