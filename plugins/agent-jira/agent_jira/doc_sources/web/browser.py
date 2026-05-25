import contextlib
import sys
from typing import Optional, Tuple

from agent_jira.doc_sources.utils import warn_missing_dependency

_PLAYWRIGHT_FACTORY = None
_PLAYWRIGHT_TIMEOUT = None
_PLAYWRIGHT_LOADED = False


def _load_playwright():
    global _PLAYWRIGHT_FACTORY, _PLAYWRIGHT_TIMEOUT, _PLAYWRIGHT_LOADED
    if _PLAYWRIGHT_LOADED:
        return _PLAYWRIGHT_FACTORY, _PLAYWRIGHT_TIMEOUT
    try:  # pragma: no cover
        from playwright.async_api import TimeoutError as PWTimeoutError
        from playwright.async_api import async_playwright as async_runner

        _PLAYWRIGHT_FACTORY = async_runner
        _PLAYWRIGHT_TIMEOUT = PWTimeoutError
    except Exception:
        _PLAYWRIGHT_FACTORY = None
        _PLAYWRIGHT_TIMEOUT = None
    _PLAYWRIGHT_LOADED = True
    return _PLAYWRIGHT_FACTORY, _PLAYWRIGHT_TIMEOUT


@contextlib.asynccontextmanager
async def playwright_page(user_agent: str, render_timeout: float):
    runner_factory, timeout_exc = _load_playwright()
    if runner_factory is None:
        warn_missing_dependency("playwright", "sorgente web dinamica")
        yield None, None
        return
    playwright = await runner_factory().start()
    browser = None
    context = None
    try:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=user_agent)
        page = await context.new_page()
        yield page, timeout_exc
    except Exception as exc:  # pragma: no cover
        print(f"[web-source] ⚠️ Playwright non disponibile: {exc}", file=sys.stderr)
        yield None, None
    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        await playwright.stop()


async def render_with_playwright(
    page,
    url: str,
    render_timeout: float,
    timeout_exc,
    wait_selector: str | None = None,
) -> Optional[Tuple[str, str]]:
    if not page:
        return None
    try:
        await page.goto(
            url,
            wait_until="networkidle",
            timeout=int(render_timeout * 1000),
        )
        if wait_selector:
            await page.wait_for_selector(
                wait_selector,
                timeout=int(render_timeout * 1000),
            )
        else:
            await page.wait_for_load_state(
                state="networkidle",
                timeout=int(render_timeout * 1000),
            )
        return await page.content(), page.url
    except Exception as exc:  # pragma: no cover
        if timeout_exc and isinstance(exc, timeout_exc):
            print(f"[web-source] ⚠️ Timeout Playwright su {url}", file=sys.stderr)
        else:
            print(f"[web-source] ⚠️ Errore Playwright su {url}: {exc}", file=sys.stderr)
    return None
