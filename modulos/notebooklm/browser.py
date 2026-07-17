"""Chrome real + libs locais para login NotebookLM no WSL."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from core.utils import ROOT_DIR

SYSLIBS_ROOT = ROOT_DIR / ".notebooklm" / "syslibs"
SYSLIBS_LIBDIR = SYSLIBS_ROOT / "usr" / "lib" / "x86_64-linux-gnu"
CHROME_DIR = ROOT_DIR / ".notebooklm" / "chrome" / "opt" / "google" / "chrome"
CHROME_WRAPPER = CHROME_DIR / "google-chrome"
CHROME_BINARY = CHROME_DIR / "chrome"
CHROME_BIN_DIR = ROOT_DIR / ".notebooklm" / "bin"

_PACKAGES = (
    "libnspr4",
    "libnss3",
    "libasound2t64",
    "libasound2-data",
)

_WIN_CHROME_CANDIDATES = (
    "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
    "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe",
)

_LINUX_CHROME_CANDIDATES = (
    str(CHROME_WRAPPER),
    str(CHROME_BIN_DIR / "google-chrome"),
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
)


def syslibs_ok() -> bool:
    return (SYSLIBS_LIBDIR / "libnspr4.so").exists()


def ensure_syslibs() -> Path | None:
    if _sistema_tem_libnspr4():
        return None
    if syslibs_ok():
        return SYSLIBS_LIBDIR
    _baixar_e_extrair()
    if not syslibs_ok():
        raise RuntimeError(
            "Não foi possível preparar libs locais do Chromium/Chrome. "
            "Rode: ./scripts/install_playwright_deps.sh"
        )
    return SYSLIBS_LIBDIR


def apply_ld_library_path() -> None:
    libdir = ensure_syslibs()
    if libdir is None:
        return
    atual = os.environ.get("LD_LIBRARY_PATH", "")
    prefixo = str(libdir)
    if atual.startswith(prefixo) or f":{prefixo}" in f":{atual}":
        return
    os.environ["LD_LIBRARY_PATH"] = f"{prefixo}:{atual}" if atual else prefixo


def ensure_chrome_bin_on_path() -> Path | None:
    chrome = chrome_real_path()
    if chrome is None:
        return None
    CHROME_BIN_DIR.mkdir(parents=True, exist_ok=True)
    link = CHROME_BIN_DIR / "google-chrome"
    if chrome.resolve() != link.resolve() or not link.exists():
        try:
            if link.is_symlink() or link.exists():
                link.unlink()
            link.symlink_to(chrome.resolve())
        except OSError:
            pass
    bin_dir = str(CHROME_BIN_DIR)
    path = os.environ.get("PATH", "")
    if not path.startswith(bin_dir):
        os.environ["PATH"] = f"{bin_dir}:{path}"
    return chrome


def prepare_browser_env() -> Path | None:
    apply_ld_library_path()
    return ensure_chrome_bin_on_path()


def chrome_binary_path() -> Path | None:
    """ELF `chrome` para Playwright executable_path (não o wrapper bash)."""
    prepare_browser_env()
    if CHROME_BINARY.exists():
        return CHROME_BINARY.resolve()
    wrapper = chrome_real_path()
    if wrapper is None:
        return None
    sibling = wrapper.parent / "chrome"
    if sibling.exists():
        return sibling.resolve()
    return None


def chrome_real_path() -> Path | None:
    env = os.getenv("NOTEBOOKLM_CHROME_PATH", "").strip()
    if env:
        p = Path(env)
        if p.exists():
            return p
    for raw in (*_LINUX_CHROME_CANDIDATES, *_WIN_CHROME_CANDIDATES):
        p = Path(raw)
        if p.exists():
            return p
    return None


def chrome_instalado() -> bool:
    """True se há Chrome Linux usável (binário ELF local ou sistema)."""
    return chrome_binary_path() is not None


def launch_chromium(playwright, *, headless: bool = True, **kwargs):
    apply_ld_library_path()
    args = list(kwargs.pop("args", []) or [])
    for a in (
        "--disable-blink-features=AutomationControlled",
        "--no-first-run",
        "--no-default-browser-check",
    ):
        if a not in args:
            args.append(a)
    ignore = list(kwargs.pop("ignore_default_args", []) or [])
    if "--enable-automation" not in ignore:
        ignore.append("--enable-automation")
    return playwright.chromium.launch(
        headless=headless,
        args=args,
        ignore_default_args=ignore,
        **kwargs,
    )


def _sistema_tem_libnspr4() -> bool:
    try:
        import ctypes

        ctypes.CDLL("libnspr4.so")
        return True
    except OSError:
        return False


def _baixar_e_extrair() -> None:
    SYSLIBS_ROOT.mkdir(parents=True, exist_ok=True)
    work = ROOT_DIR / ".notebooklm" / "_debs"
    work.mkdir(parents=True, exist_ok=True)
    for old in work.glob("*.deb"):
        old.unlink()
    subprocess.run(
        ["apt-get", "download", *_PACKAGES],
        cwd=str(work),
        check=True,
        capture_output=True,
    )
    for deb in work.glob("*.deb"):
        subprocess.run(
            ["dpkg-deb", "-x", str(deb), str(SYSLIBS_ROOT)],
            check=True,
            capture_output=True,
        )
