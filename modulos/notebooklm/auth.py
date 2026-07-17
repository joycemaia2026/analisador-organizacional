"""Login interativo NotebookLM (Chrome local via Playwright executable_path)."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from core.utils import ROOT_DIR

NOTEBOOKLM_URL = "https://notebooklm.google.com/"
GOOGLE_ACCOUNTS_URL = "https://accounts.google.com/"


def storage_path() -> Path:
    raw = os.getenv(
        "NOTEBOOKLM_STATE_PATH",
        ".notebooklm/storage_state.json",
    ).strip()
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT_DIR / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def state_path() -> Path:
    return storage_path()


def browser_profile_dir() -> Path:
    return ROOT_DIR / ".notebooklm" / "browser_profile"


def sessao_valida() -> bool:
    p = storage_path()
    return p.exists() and p.stat().st_size > 50


def limpar_sessao() -> None:
    p = storage_path()
    if p.exists():
        p.unlink()


def login_interativo(*, fresh: bool = True, browser: str = "chrome") -> Path:
    """
    Abre o Chrome Linux de `.notebooklm/chrome` via executable_path.

    O CLI `notebooklm login --browser chrome` exige `/opt/google/chrome`
    (channel Playwright). No WSL usamos o extract local.
    """
    del browser  # sempre Chrome local / executable_path

    from playwright.sync_api import TimeoutError as PlaywrightTimeout
    from playwright.sync_api import sync_playwright

    from modulos.notebooklm.browser import chrome_binary_path, chrome_instalado, prepare_browser_env

    prepare_browser_env()
    if not chrome_instalado():
        raise RuntimeError(
            "Google Chrome Linux não encontrado. Rode: ./scripts/install_chrome_wsl.sh"
        )

    chrome = chrome_binary_path()
    assert chrome is not None

    destino = storage_path()
    profile = browser_profile_dir()
    if fresh and profile.exists():
        shutil.rmtree(profile, ignore_errors=True)
    profile.mkdir(parents=True, exist_ok=True)

    try:
        from notebooklm.config import get_base_url

        base = get_base_url().rstrip("/")
    except Exception:  # noqa: BLE001
        base = NOTEBOOKLM_URL.rstrip("/")

    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(profile),
                executable_path=str(chrome),
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--password-store=basic",
                    "--no-sandbox",
                ],
                ignore_default_args=["--enable-automation"],
            )
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(mensagem_erro_browser(exc)) from exc

        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(f"{base}/", wait_until="commit", timeout=60_000)

            url = page.url or ""
            ja_logado = "notebooklm.google.com" in url and "accounts.google" not in url

            if not ja_logado:
                try:
                    page.wait_for_url(
                        f"{base}/**",
                        wait_until="commit",
                        timeout=300_000,
                    )
                except PlaywrightTimeout as exc:
                    raise RuntimeError(
                        "Login não detectado em 5 minutos. "
                        "Conclua o Google Sign-In na janela do Chrome e tente de novo."
                    ) from exc

            for target in (GOOGLE_ACCOUNTS_URL, f"{base}/"):
                try:
                    page.goto(target, wait_until="commit", timeout=60_000)
                except Exception:  # noqa: BLE001
                    pass

            state = context.storage_state()
            _salvar_storage(destino, state)
        finally:
            context.close()

    if not sessao_valida():
        raise RuntimeError(
            "Login terminou sem gravar storage_state. "
            "Conclua o login Google na janela do Chrome e tente novamente."
        )
    return destino


def _salvar_storage(destino: Path, state: dict) -> None:
    try:
        from notebooklm.cli.services.playwright_login import (
            filter_storage_state_cookies_by_domain_policy,
        )
        from notebooklm.io import atomic_write_json

        filtered = filter_storage_state_cookies_by_domain_policy(
            dict(state),
            include_domains=frozenset(),
        )
        atomic_write_json(destino, filtered)
        return
    except Exception:  # noqa: BLE001
        pass

    destino.write_text(json.dumps(state, indent=2), encoding="utf-8")
    try:
        os.chmod(destino, 0o600)
    except OSError:
        pass


def mensagem_erro_browser(exc: BaseException) -> str:
    texto = str(exc)
    if "libnspr4" in texto or "shared libraries" in texto.lower():
        return (
            "Chrome/Chromium sem libs de sistema. "
            "Rode ./scripts/install_playwright_deps.sh e "
            "./scripts/install_chrome_wsl.sh"
        )
    if "chrome' is not found" in texto or "/opt/google/chrome" in texto:
        return (
            "Chrome do sistema não está em /opt/google/chrome. "
            "O app usa o extract em .notebooklm/chrome — "
            "rode ./scripts/install_chrome_wsl.sh e tente Gerar de novo."
        )
    return texto
