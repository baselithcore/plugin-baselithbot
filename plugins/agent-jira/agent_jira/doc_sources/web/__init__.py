import asyncio
import logging
from typing import Any, Dict, List, Optional

from .crawler import crawl_url
from .utils import normalize_url, should_skip_url

logger = logging.getLogger(__name__)


class WebDocumentSource:
    """
    Sorgente documenti che recupera contenuti da URL web.
    Usa Playwright per il rendering JavaScript se necessario.
    """

    def __init__(
        self,
        urls: List[str],
        render_timeout: float = 30.0,
        min_chars: int = 20,
        ignore_css: Optional[List[str]] = None,
        user_agent: Optional[str] = None,
        wait_selector: Optional[str] = None,
    ) -> None:
        self.urls = list(dict.fromkeys([normalize_url(u) for u in urls if u]))
        self.render_timeout = render_timeout
        self.min_chars = min_chars
        self.ignore_css = ignore_css or []
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        self.wait_selector = wait_selector

    async def fetch_documents(self) -> List[Dict[str, Any]]:
        """
        Recupera i documenti dagli URL specificati.
        """
        valid_urls = [u for u in self.urls if u and not should_skip_url(u)]
        if not valid_urls:
            return []

        logger.info(f"[web-source] Crawling {len(valid_urls)} URLs...")

        tasks = [
            crawl_url(
                url=url,
                user_agent=self.user_agent,
                render_timeout=self.render_timeout,
                min_chars=self.min_chars,
                ignore_css=self.ignore_css,
                wait_selector=self.wait_selector,
            )
            for url in valid_urls
        ]

        results = await asyncio.gather(*tasks)
        documents = [res for res in results if res]

        logger.info(f"[web-source] Successfully fetched {len(documents)} documents.")
        return documents

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "WebDocumentSource":
        return cls(
            urls=config.get("urls", []),
            render_timeout=config.get("render_timeout", 30.0),
            min_chars=config.get("min_chars", 200),
            ignore_css=config.get("ignore_css", []),
            user_agent=config.get("user_agent"),
            wait_selector=config.get("wait_selector"),
        )

    def _normalize_url(self, url: str) -> str:
        return normalize_url(url)

    def _should_skip_url(self, url: str) -> bool:
        return should_skip_url(url)

    def _normalize_domain(self, domain: str) -> str:
        from .utils import normalize_domain

        return normalize_domain(domain)

    def _parse_page(self, html: str, url: str, allowed_domain: str) -> tuple:
        from .parser import parse_page_content

        return parse_page_content(
            html, url, allowed_domain, self.min_chars, self.ignore_css
        )

    def close(self):
        pass
