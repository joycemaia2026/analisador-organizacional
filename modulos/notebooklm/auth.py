"""Login interativo NotebookLM (Chrome local via Playwright executable_path)."""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

from core.utils import ROOT_DIR

NOTEBOOKLM_URL = "https://notebooklm.google.com/"
GOOGLE_ACCOUNTS_URL = "https://accounts.google.com/"

_COOKIE_NAMES = frozenset(
    {
        "SID",
        "HSID",
        "SSID",
        "APISID",
        "SAPISID",
        "__Secure-1PSID",
        "__Secure-3PSID",
        "__Secure-1PSIDTS",
        "__Secure-3PSIDTS",
    }
)

_RETRYABLE_NAV = (
    "ERR_NETWORK_CHANGED",
    "ERR_CONNECTION_RESET",
    "ERR_CONNECTION_CLOSED",
    "ERR_CONNECTION_REFUSED",
    "ERR_INTERNET_DISCONNECTED",
    "ERR_NAME_NOT_RESOLVED",
    "ERR_TIMED_OUT",
    "ERR_SOCKS_CONNECTION_FAILED",
    "net::ERR_",
    "Target page, context or browser has been closed",
    "Navigation interrupted",
)
_GOTO_MAX_RETRIES = 5
_GOTO_TIMEOUT_MS = 90_000
_LOGIN_WAIT_MS = 120_000


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


def _cookies_de_sessao(state: dict) -> list[dict]:
    cookies = state.get("cookies") or []
    if not isinstance(cookies, list):
        return []
    return [c for c in cookies if isinstance(c, dict)]


def storage_tem_cookies_google(state: dict) -> bool:
    cookies = _cookies_de_sessao(state)
    if not cookies:
        return False
    dominios_ok = False
    nomes_ok = 0
    for c in cookies:
        domain = str(c.get("domain") or "").lower()
        name = str(c.get("name") or "")
        if "google.com" in domain or "notebooklm.google.com" in domain:
            dominios_ok = True
        if name in _COOKIE_NAMES:
            nomes_ok += 1
    return dominios_ok and nomes_ok >= 1


def sessao_valida() -> bool:
    p = storage_path()
    if not p.exists() or p.stat().st_size < 50:
        return False
    try:
        state = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return storage_tem_cookies_google(state)


def limpar_sessao(*, limpar_perfil: bool = False) -> None:
    p = storage_path()
    if p.exists():
        p.unlink()
    if limpar_perfil:
        profile = browser_profile_dir()
        if profile.exists():
            shutil.rmtree(profile, ignore_errors=True)


def _liberar_lock_perfil(profile: Path) -> None:
    for nome in ("SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile"):
        p = profile / nome
        try:
            if p.exists() or p.is_symlink():
                p.unlink()
        except OSError:
            pass


def login_interativo(*, fresh: bool = True, browser: str = "chrome") -> Path:
    """
    Abre nova janela do Chrome Linux (extract local) para login Google.

    `fresh=True` (padrão): limpa o perfil e abre sessão nova — fluxo simples.
    """
    del browser

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
    if not chrome.exists():
        raise RuntimeError(
            f"Binário Chrome ausente em {chrome}. "
            "Rode: ./scripts/install_chrome_wsl.sh"
        )

    destino = storage_path()
    profile = browser_profile_dir()
    if fresh and profile.exists():
        shutil.rmtree(profile, ignore_errors=True)
    profile.mkdir(parents=True, exist_ok=True)
    _liberar_lock_perfil(profile)

    try:
        from notebooklm.config import get_base_url

        base = get_base_url().rstrip("/")
    except Exception:  # noqa: BLE001
        base = NOTEBOOKLM_URL.rstrip("/")

    with sync_playwright() as p:
        try:
            context = _launch_context(p, profile=profile, chrome=chrome)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(mensagem_erro_browser(exc)) from exc

        try:
            time.sleep(1.5)
            page = context.pages[0] if context.pages else context.new_page()
            page = _goto_com_retry(context, page, f"{base}/")

            url = (page.url or "").lower()
            ja_logado = (
                "notebooklm.google" in url
                and "accounts.google" not in url
                and "signin" not in url
            )

            if not ja_logado:
                try:
                    page.wait_for_url(
                        f"{base}/**",
                        wait_until="commit",
                        timeout=_LOGIN_WAIT_MS,
                    )
                except PlaywrightTimeout as exc:
                    raise RuntimeError(
                        "Login não detectado em 2 minutos. "
                        "Na janela nova do Chrome, conclua o Google Sign-In "
                        "até o NotebookLM abrir e clique Autenticar de novo."
                    ) from exc

            for target in (GOOGLE_ACCOUNTS_URL, f"{base}/"):
                try:
                    page = _goto_com_retry(
                        context,
                        page,
                        target,
                        max_retries=3,
                        raise_on_fail=False,
                    )
                except Exception:  # noqa: BLE001
                    pass

            state = context.storage_state()
            if not storage_tem_cookies_google(state):
                raise RuntimeError(
                    "A janela do Chrome abriu, mas a sessão não ficou gravada. "
                    "Conclua o login até ver o NotebookLM e tente Autenticar de novo."
                )
            _salvar_storage(destino, state)
        finally:
            context.close()

    if not sessao_valida():
        raise RuntimeError(
            "Login terminou sem gravar storage_state. Tente Autenticar de novo."
        )
    return destino


def _launch_context(playwright, *, profile: Path, chrome: Path):
    kwargs = dict(
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
    try:
        return playwright.chromium.launch_persistent_context(**kwargs)
    except Exception as exc:  # noqa: BLE001
        texto = str(exc).lower()
        if "singleton" in texto or "profile" in texto or "lock" in texto:
            _liberar_lock_perfil(profile)
            time.sleep(0.5)
            return playwright.chromium.launch_persistent_context(**kwargs)
        raise


def _eh_erro_rede_transitorio(exc: BaseException) -> bool:
    texto = str(exc)
    return any(m in texto for m in _RETRYABLE_NAV)


def _goto_com_retry(
    context,
    page,
    url: str,
    *,
    max_retries: int = _GOTO_MAX_RETRIES,
    raise_on_fail: bool = True,
):
    from playwright.sync_api import Error as PlaywrightError

    ultimo: BaseException | None = None
    for tentativa in range(1, max_retries + 1):
        try:
            page.goto(url, wait_until="commit", timeout=_GOTO_TIMEOUT_MS)
            return page
        except Exception as exc:  # noqa: BLE001
            ultimo = exc
            if not _eh_erro_rede_transitorio(exc) or tentativa >= max_retries:
                break
            try:
                if page.is_closed():
                    page = context.new_page()
            except Exception:  # noqa: BLE001
                try:
                    page = context.new_page()
                except Exception as inner:  # noqa: BLE001
                    ultimo = inner
                    break
            time.sleep(min(2 * tentativa, 8))

    if not raise_on_fail:
        return page
    assert ultimo is not None
    if isinstance(ultimo, PlaywrightError) or _eh_erro_rede_transitorio(ultimo):
        raise RuntimeError(mensagem_erro_browser(ultimo)) from ultimo
    raise RuntimeError(str(ultimo)) from ultimo


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
    baixo = texto.lower()
    if "libnspr4" in texto or "shared libraries" in baixo:
        return (
            "Chrome/Chromium sem libs de sistema. "
            "Rode ./scripts/install_playwright_deps.sh e "
            "./scripts/install_chrome_wsl.sh"
        )
    if (
        "chromium distribution 'chrome' is not found" in baixo
        or "browser type chrome is not found" in baixo
        or (
            "executable doesn't exist" in baixo
            and "/opt/google/chrome" in texto
            and ".notebooklm" not in texto
        )
    ):
        return (
            "Playwright não achou o Chrome do sistema. "
            "Este app usa o extract em `.notebooklm/chrome`. "
            "Rode ./scripts/install_chrome_wsl.sh e tente Autenticar de novo."
        )
    if "singleton" in baixo or ("profile" in baixo and "lock" in baixo):
        return (
            "Há outra janela Chrome usando o perfil do NotebookLM. "
            "Feche essas janelas e clique Autenticar de novo."
        )
    if any(
        m in texto
        for m in (
            "ERR_NETWORK_CHANGED",
            "ERR_CONNECTION_",
            "ERR_INTERNET_",
            "ERR_NAME_NOT_RESOLVED",
            "ERR_TIMED_OUT",
            "ERR_SOCKS_",
            "net::ERR_",
        )
    ):
        return (
            "Falha de rede ao abrir o NotebookLM. "
            "Aguarde 2–3 s e clique Autenticar de novo.\n"
            f"Detalhe: {texto[:400]}"
        )
    return texto
