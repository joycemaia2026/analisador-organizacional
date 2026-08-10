"""Pipeline NotebookLM: notebook → fontes → slide deck e/ou infográfico → download."""

from __future__ import annotations

import asyncio
import concurrent.futures
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

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


def _status_erro(final: Any, rotulo: str) -> str | None:
    """Se o wait não terminou em completed, devolve mensagem amigável."""
    status = getattr(final, "status", None) or "?"
    if getattr(final, "is_complete", False):
        return None
    if getattr(final, "is_removed", False):
        return (
            f"{rotulo}: artefato removido pelo NotebookLM "
            "(quota diária ou rejeição). Tente mais tarde ou só um produto por vez."
        )
    if getattr(final, "is_failed", False):
        err = getattr(final, "error", None) or status
        return f"{rotulo}: geração falhou ({err})"
    if getattr(final, "is_rate_limited", False):
        return f"{rotulo}: limite diário do Google. Aguarde e tente de novo."
    err = getattr(final, "error", None)
    return f"{rotulo}: status inesperado '{status}'" + (f" — {err}" if err else "")


def _motivo_recusa(status: Any) -> str:
    """Mensagem legível quando o NotebookLM recusa iniciar a geração."""
    erro = (getattr(status, "error", None) or "").strip()
    if getattr(status, "is_rate_limited", False) or "quota" in erro.lower():
        return (
            "o NotebookLM recusou a geração (limite diário/quota da conta). "
            "Gere um produto por vez e tente novamente mais tarde."
        )
    if erro:
        return f"o NotebookLM recusou a geração — {erro}"
    return (
        "o NotebookLM não iniciou a geração e não informou o motivo. "
        "Abra o notebook e tente gerar pelo Studio."
    )


async def _iniciar_geracao(gerar_fn) -> Any:
    """Dispara a geração com retry de rate limit e valida o task_id."""
    from notebooklm.artifacts import with_rate_limit_retry
    from notebooklm.exceptions import ArtifactFeatureUnavailableError, RateLimitError

    try:
        status = await with_rate_limit_retry(gerar_fn, max_retries=2)
    except RateLimitError as exc:
        raise RuntimeError(
            f"limite diário do NotebookLM atingido ({exc}). Tente de novo mais tarde."
        ) from exc
    except ArtifactFeatureUnavailableError as exc:
        raise RuntimeError(
            f"recurso indisponível nesta conta do NotebookLM ({exc})."
        ) from exc

    if status is None or not getattr(status, "task_id", ""):
        raise RuntimeError(_motivo_recusa(status))
    return status


async def _aguardar_artefato(client: Any, notebook_id: str, task_id: str) -> Any:
    return await client.artifacts.wait_for_completion(
        notebook_id,
        task_id,
        timeout=600.0,
        max_not_found=12,
        min_not_found_window=20.0,
    )


async def _baixar_slides(
    client: Any,
    notebook_id: str,
    artifact_id: str,
    destino_pptx: Path,
    destino_pdf: Path,
) -> Path:
    """Tenta PPTX; se URL/PPTX falhar, cai para PDF. Retry se ainda não listado."""
    from notebooklm.exceptions import ArtifactNotReadyError

    ultimo: BaseException | None = None
    for tentativa in range(1, 7):
        try:
            await client.artifacts.download_slide_deck(
                notebook_id,
                str(destino_pptx),
                artifact_id=artifact_id,
                output_format="pptx",
            )
            if destino_pptx.exists() and destino_pptx.stat().st_size > 0:
                return destino_pptx
        except Exception as exc:  # noqa: BLE001
            ultimo = exc
            # PPTX pode não existir ainda — tenta PDF.
            try:
                await client.artifacts.download_slide_deck(
                    notebook_id,
                    str(destino_pdf),
                    artifact_id=artifact_id,
                    output_format="pdf",
                )
                if destino_pdf.exists() and destino_pdf.stat().st_size > 0:
                    return destino_pdf
            except Exception as exc2:  # noqa: BLE001
                ultimo = exc2
                if not isinstance(exc2, ArtifactNotReadyError) and tentativa >= 3:
                    raise
        await asyncio.sleep(min(2 * tentativa, 10))
    assert ultimo is not None
    raise ultimo


async def _baixar_infografico(
    client: Any,
    notebook_id: str,
    artifact_id: str,
    destino: Path,
) -> Path:
    from notebooklm.exceptions import ArtifactNotReadyError

    ultimo: BaseException | None = None
    for tentativa in range(1, 7):
        try:
            await client.artifacts.download_infographic(
                notebook_id,
                str(destino),
                artifact_id=artifact_id,
            )
            if destino.exists() and destino.stat().st_size > 0:
                return destino
        except Exception as exc:  # noqa: BLE001
            ultimo = exc
            if not isinstance(exc, ArtifactNotReadyError) and tentativa >= 3:
                raise
        await asyncio.sleep(min(2 * tentativa, 10))
    assert ultimo is not None
    raise ultimo


async def _gerar_async(
    caminhos: list[Path],
    *,
    storage: Path,
    language: str = "pt",
    limpar_ao_fim: bool = False,
    gerar_slides: bool = True,
    gerar_infografico: bool = True,
) -> ProdutosResultado:
    from notebooklm import NotebookLMClient

    from modulos.notebooklm.auth import limpar_sessao

    if not gerar_slides and not gerar_infografico:
        return ProdutosResultado(
            ok=False,
            mensagem="Selecione pelo menos um produto: apresentação (PPTX) ou infográfico.",
        )

    ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    resultado = ProdutosResultado(ok=False)

    async with NotebookLMClient.from_storage(str(storage)) as client:
        titulo = f"BriefBoard Gedanken {stamp}"
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

        # Pequena folga após indexação das fontes.
        await asyncio.sleep(3.0)

        instrucoes = (
            "Com base nas atas e análises anexadas, destaque decisões, "
            "riscos, próximos passos e insights executivos."
        )

        if gerar_slides:
            try:
                status = await _iniciar_geracao(
                    lambda: client.artifacts.generate_slide_deck(
                        nb.id,
                        language=language,
                        instructions=instrucoes,
                    )
                )
                final = await _aguardar_artefato(client, nb.id, status.task_id)
                err = _status_erro(final, "slide-deck")
                if err:
                    resultado.falhas.append(err)
                else:
                    slides_path = OUTPUTS_DIR / f"nlm_slides_{stamp}.pptx"
                    pdf_path = OUTPUTS_DIR / f"nlm_slides_{stamp}.pdf"
                    resultado.slides = await _baixar_slides(
                        client,
                        nb.id,
                        final.task_id or status.task_id,
                        slides_path,
                        pdf_path,
                    )
            except Exception as exc:  # noqa: BLE001
                resultado.falhas.append(f"slide-deck: {exc}")

        if gerar_infografico:
            try:
                from notebooklm import InfographicOrientation

                if gerar_slides:
                    # Duas gerações seguidas no mesmo notebook costumam ser recusadas.
                    await asyncio.sleep(10.0)

                status = await _iniciar_geracao(
                    lambda: client.artifacts.generate_infographic(
                        nb.id,
                        language=language,
                        instructions=instrucoes,
                        orientation=InfographicOrientation.LANDSCAPE,
                    )
                )
                final = await _aguardar_artefato(client, nb.id, status.task_id)
                err = _status_erro(final, "infográfico")
                if err:
                    resultado.falhas.append(err)
                else:
                    info_path = OUTPUTS_DIR / f"nlm_infografico_{stamp}.png"
                    resultado.infografico = await _baixar_infografico(
                        client,
                        nb.id,
                        final.task_id or status.task_id,
                        info_path,
                    )
            except Exception as exc:  # noqa: BLE001
                resultado.falhas.append(f"infográfico: {exc}")

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
        if resultado.notebook_url:
            resultado.mensagem += (
                f" Abra o notebook e confira no Studio: {resultado.notebook_url}"
            )
    return resultado


def _mensagem_sessao_expirada(exc: BaseException) -> str | None:
    """Se o erro parecer auth expirada, sugere autenticar de novo."""
    texto = str(exc).lower()
    marcadores = (
        "unauthorized",
        "401",
        "403",
        "forbidden",
        "unauthenticated",
        "not authenticated",
        "login required",
        "cookie",
        "csrf",
        "session",
        "storage_state",
        "auth",
    )
    if any(m in texto for m in marcadores):
        return (
            "Sessão Google inválida ou expirada. "
            "Clique em Autenticar (nova janela) e depois Gerar no NotebookLM."
        )
    return None


def gerar_produtos(
    caminhos: list[Path],
    *,
    storage: Path | None = None,
    language: str = "pt",
    limpar_ao_fim: bool = False,
    gerar_slides: bool = True,
    gerar_infografico: bool = True,
) -> ProdutosResultado:
    """Síncrono: create → upload → generate → download (após Autenticar)."""
    from modulos.notebooklm.auth import sessao_valida, storage_path

    paths = [Path(c) for c in caminhos]
    if not paths:
        return ProdutosResultado(ok=False, mensagem="Nenhum arquivo selecionado.")
    for p in paths:
        if not p.exists():
            return ProdutosResultado(ok=False, mensagem=f"Arquivo ausente: {p}")

    store = storage or storage_path()
    if not sessao_valida():
        return ProdutosResultado(
            ok=False,
            mensagem=(
                "Sem autenticação Google. Clique em Autenticar (nova janela), "
                "conclua o login no Chrome e depois Gerar no NotebookLM."
            ),
        )

    try:
        return _run_async(
            _gerar_async(
                paths,
                storage=store,
                language=language,
                limpar_ao_fim=limpar_ao_fim,
                gerar_slides=gerar_slides,
                gerar_infografico=gerar_infografico,
            )
        )
    except Exception as exc:  # noqa: BLE001
        hint = _mensagem_sessao_expirada(exc)
        return ProdutosResultado(
            ok=False,
            mensagem=hint or f"Falha NotebookLM: {exc}",
            falhas=[str(exc)],
        )


def login_e_gerar_produtos(
    caminhos: list[Path],
    *,
    language: str = "pt",
    gerar_slides: bool = True,
    gerar_infografico: bool = True,
) -> ProdutosResultado:
    """Compat: autentica em nova janela (fresh) e gera."""
    from modulos.notebooklm.auth import login_interativo

    try:
        storage = login_interativo(fresh=True, browser="chrome")
    except Exception as exc:  # noqa: BLE001
        return ProdutosResultado(ok=False, mensagem=f"Login: {exc}")

    return gerar_produtos(
        caminhos,
        storage=storage,
        language=language,
        limpar_ao_fim=False,
        gerar_slides=gerar_slides,
        gerar_infografico=gerar_infografico,
    )
