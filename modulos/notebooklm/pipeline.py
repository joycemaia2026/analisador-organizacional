"""Pipeline NotebookLM: notebook → fontes → slide deck + infográfico → download."""

from __future__ import annotations

import asyncio
import concurrent.futures
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from core.utils import OUTPUTS_DIR, ensure_dirs


@dataclass
class ProdutosResultado:
    ok: bool
    notebook_id: str | None = None
    notebook_url: str | None = None
    slides: Path | None = None
    infografico: Path | None = None
    fontes: list[str] = field(default_factory=list)
    falhas: list[str] = field(default_factory=list)
    mensagem: str = ""


def _run_async(coro):
    """Roda coroutine mesmo se já houver event loop (Streamlit)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


async def _gerar_async(
    caminhos: list[Path],
    *,
    storage: Path,
    language: str = "pt",
    limpar_ao_fim: bool = True,
) -> ProdutosResultado:
    from notebooklm import NotebookLMClient

    from modulos.notebooklm.auth import limpar_sessao

    ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    resultado = ProdutosResultado(ok=False)

    async with NotebookLMClient.from_storage(str(storage)) as client:
        titulo = f"Analisador Organizacional {stamp}"
        nb = await client.notebooks.create(titulo)
        resultado.notebook_id = nb.id
        try:
            resultado.notebook_url = client.notebooks.get_share_url(nb.id)
        except Exception:  # noqa: BLE001
            resultado.notebook_url = f"https://notebooklm.google.com/notebook/{nb.id}"

        for caminho in caminhos:
            try:
                await client.sources.add_file(
                    nb.id,
                    caminho,
                    wait=True,
                    wait_timeout=180.0,
                    title=caminho.stem,
                )
                resultado.fontes.append(caminho.name)
            except Exception as exc:  # noqa: BLE001
                resultado.falhas.append(f"{caminho.name}: {exc}")

        if not resultado.fontes:
            resultado.mensagem = "Nenhuma fonte enviada com sucesso."
            if limpar_ao_fim:
                limpar_sessao()
            return resultado

        instrucoes = (
            "Com base nas atas e análises anexadas, destaque decisões, "
            "riscos, próximos passos e insights executivos."
        )

        # Slide deck
        try:
            status = await client.artifacts.generate_slide_deck(
                nb.id,
                language=language,
                instructions=instrucoes,
            )
            await client.artifacts.wait_for_completion(
                nb.id,
                status.task_id,
                timeout=600.0,
            )
            slides_path = OUTPUTS_DIR / f"nlm_slides_{stamp}.pptx"
            await client.artifacts.download_slide_deck(
                nb.id,
                str(slides_path),
                output_format="pptx",
            )
            if slides_path.exists():
                resultado.slides = slides_path
            else:
                # fallback PDF
                pdf_path = OUTPUTS_DIR / f"nlm_slides_{stamp}.pdf"
                await client.artifacts.download_slide_deck(
                    nb.id,
                    str(pdf_path),
                    output_format="pdf",
                )
                if pdf_path.exists():
                    resultado.slides = pdf_path
        except Exception as exc:  # noqa: BLE001
            resultado.falhas.append(f"slide-deck: {exc}")

        # Infográfico
        try:
            from notebooklm import InfographicOrientation

            status = await client.artifacts.generate_infographic(
                nb.id,
                language=language,
                instructions=instrucoes,
                orientation=InfographicOrientation.LANDSCAPE,
            )
            await client.artifacts.wait_for_completion(
                nb.id,
                status.task_id,
                timeout=600.0,
            )
            info_path = OUTPUTS_DIR / f"nlm_infografico_{stamp}.png"
            await client.artifacts.download_infographic(nb.id, str(info_path))
            if info_path.exists():
                resultado.infografico = info_path
        except Exception as exc:  # noqa: BLE001
            resultado.falhas.append(f"infographic: {exc}")

    if limpar_ao_fim:
        limpar_sessao()

    resultado.ok = bool(resultado.slides or resultado.infografico)
    if resultado.ok:
        partes = []
        if resultado.slides:
            partes.append(resultado.slides.name)
        if resultado.infografico:
            partes.append(resultado.infografico.name)
        resultado.mensagem = "Produtos gerados: " + ", ".join(partes)
    else:
        resultado.mensagem = "Falha ao gerar produtos no NotebookLM."
    return resultado


def gerar_produtos(
    caminhos: list[Path],
    *,
    storage: Path | None = None,
    language: str = "pt",
    limpar_ao_fim: bool = True,
) -> ProdutosResultado:
    """Síncrono: create → upload → generate → download."""
    from modulos.notebooklm.auth import storage_path

    paths = [Path(c) for c in caminhos]
    if not paths:
        return ProdutosResultado(ok=False, mensagem="Nenhum arquivo selecionado.")
    for p in paths:
        if not p.exists():
            return ProdutosResultado(ok=False, mensagem=f"Arquivo ausente: {p}")

    return _run_async(
        _gerar_async(
            paths,
            storage=storage or storage_path(),
            language=language,
            limpar_ao_fim=limpar_ao_fim,
        )
    )


def login_e_gerar_produtos(
    caminhos: list[Path],
    *,
    language: str = "pt",
) -> ProdutosResultado:
    """Login interativo (Chrome) + pipeline completo."""
    from modulos.notebooklm.auth import login_interativo

    try:
        storage = login_interativo(fresh=True, browser="chrome")
    except Exception as exc:  # noqa: BLE001
        return ProdutosResultado(ok=False, mensagem=f"Login: {exc}")

    return gerar_produtos(
        caminhos,
        storage=storage,
        language=language,
        limpar_ao_fim=True,
    )
