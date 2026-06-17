"""CVE Discovery Agent — online source scanning helpers.

Separated from discovery.py to keep that module under 500 LOC.
Contains: ONLINE_SOURCES constant, scan_online_sources async generator,
and the XML/JSON item-extraction helpers it depends on.
"""

from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List

from core.observability.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Source catalogue
# ---------------------------------------------------------------------------

ONLINE_SOURCES: List[Dict[str, str]] = [
    {
        "name": "Hacker News",
        "url": "https://feeds.feedburner.com/TheHackersNews",
        "type": "rss",
    },
    {
        "name": "Exploit-DB",
        "url": "https://www.exploit-db.com/rss.xml",
        "type": "rss",
    },
    {
        "name": "Reddit NetSec",
        "url": "https://www.reddit.com/r/netsec/.json",
        "type": "json",
    },
    {
        "name": "Full Disclosure",
        "url": "http://seclists.org/rss/fulldisclosure.rss",
        "type": "rss",
    },
]


def _extract_rss_items(content: str) -> List[str]:
    """Parse RSS XML and return title + description texts."""
    import defusedxml.ElementTree as ET

    items: List[str] = []
    try:
        root = ET.fromstring(content)
        for item in root.findall(".//item")[:5]:
            title = item.find("title")
            desc = item.find("description")
            if title is not None and title.text:
                items.append(title.text)
            if desc is not None and desc.text:
                items.append(desc.text)
    except Exception:
        pass  # nosec B110
    return items


def _extract_json_items(response_json: Any) -> List[str]:
    """Extract post titles + selftexts from Reddit-style JSON."""
    items: List[str] = []
    data = response_json.get("data", {})
    for child in data.get("children", [])[:5]:
        child_data = child.get("data", {})
        title = child_data.get("title", "")
        selftext = child_data.get("selftext", "")
        if title:
            items.append(title)
        if selftext:
            items.append(selftext)
    return items


async def scan_online_sources(
    analyze_fn: Any,
) -> AsyncIterator[Dict[str, Any]]:
    """Scan online security news sources for potential zero-days.

    Args:
        analyze_fn: Async callable(text, source) → List[finding dicts].
                    Typically CVEDiscoveryAgent.analyze_text_for_vulnerabilities.

    Yields:
        Dicts with keys "type" ∈ {"log", "finding", "error"}.
    """
    import asyncio
    import httpx

    async with httpx.AsyncClient(timeout=10.0) as client:
        for source in ONLINE_SOURCES:
            yield {
                "type": "log",
                "message": f"DISCOVERY: Connecting to {source['name']}...",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            try:
                await asyncio.sleep(1.0)

                response = await client.get(source["url"])
                content = response.text

                yield {
                    "type": "log",
                    "message": (
                        f"DISCOVERY: Processing {len(content)} bytes "
                        f"from {source['name']}..."
                    ),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                if source["type"] == "json":
                    items = _extract_json_items(response.json())
                else:
                    items = _extract_rss_items(content)

                for item_text in items:
                    if not item_text:
                        continue

                    yield {
                        "type": "log",
                        "message": (
                            f"DISCOVERY: Inspecting item '{item_text[:30]}...'..."
                        ),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                    findings = await analyze_fn(item_text, source["name"])

                    for finding in findings:
                        yield {
                            "type": "finding",
                            "data": finding,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }

            except Exception as e:
                yield {
                    "type": "error",
                    "message": (
                        f"DISCOVERY: Failed to scan {source['name']}: {str(e)}"
                    ),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
