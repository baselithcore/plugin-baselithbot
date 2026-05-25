from bs4 import BeautifulSoup

from .browser import playwright_page, render_with_playwright
from .parser import extract_content, extract_metadata
from .utils import get_document_id, normalize_url, should_skip_url


async def crawl_url(
    url: str,
    user_agent: str,
    render_timeout: float,
    min_chars: int,
    ignore_css: list[str],
    wait_selector: str | None = None,
) -> dict | None:
    norm_url = normalize_url(url)
    if not norm_url or should_skip_url(norm_url):
        return None

    async with playwright_page(user_agent, render_timeout) as (page, timeout_exc):
        if not page:
            return None
        render_res = await render_with_playwright(
            page, norm_url, render_timeout, timeout_exc, wait_selector
        )
        if not render_res:
            return None

        html_content, final_url = render_res
        soup = BeautifulSoup(html_content, "html.parser")
        metadata = extract_metadata(soup, final_url)
        content = extract_content(soup, min_chars, ignore_css)

        if not content:
            return None

        return {
            "document_id": get_document_id(final_url),
            "content": content,
            "title": metadata["title"],
            "description": metadata["description"],
            "url": final_url,
            "metadata": {
                "source_type": "web",
                "original_url": norm_url,
                "final_url": final_url,
                "title": metadata["title"],
                "description": metadata["description"],
            },
        }
