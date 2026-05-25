from bs4 import BeautifulSoup

from .utils import clean_block


def extract_metadata(soup: BeautifulSoup, url: str) -> dict[str, str | None]:
    title_tag = soup.find("title")
    title = title_tag.get_text().strip() if title_tag else url
    description = ""
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc:
        description = str(meta_desc.get("content", "")).strip()
    return {"title": title, "description": description}


def extract_content(
    soup: BeautifulSoup,
    min_chars: int,
    ignore_css: list[str],
) -> str:
    # Rimuovi elementi non desiderati
    for tag in soup(["script", "style", "nav", "footer", "header", "form"]):
        tag.decompose()

    # Rimuovi classi e ID ignorati
    for selector in ignore_css:
        for element in soup.select(selector):
            element.decompose()

    # Estrai blocchi di testo significativi
    blocks: list[str] = []
    for tag in soup.find_all(["p", "h1", "h2", "h3", "h4", "li", "article", "section"]):
        text = tag.get_text(separator=" ", strip=True)
        is_header = tag.name in ["h1", "h2", "h3", "h4"]
        # Per gli header usiamo una soglia minima molto bassa (es. 2 caratteri)
        threshold = 2 if is_header else min_chars
        cleaned = clean_block(text, threshold)
        if cleaned:
            blocks.append(cleaned)

    if not blocks:
        # Fallback se non abbiamo trovato nulla con i tag specifici
        text = soup.get_text(separator=" ", strip=True)
        cleaned = clean_block(text, min_chars)
        if cleaned:
            blocks.append(cleaned)

    content = "\n\n".join(blocks)
    return content


def parse_page_content(
    html: str, url: str, allowed_domain: str, min_chars: int, ignore_css: list[str]
) -> tuple[str, str, str, list[str]]:
    soup = BeautifulSoup(html, "html.parser")

    # Metadata
    title_tag = soup.find("title")
    title = title_tag.get_text().strip() if title_tag else url

    lang_tag = soup.find("html")
    lang = str(lang_tag.get("lang", "en")).strip() if lang_tag else "en"

    # Content
    content = extract_content(soup, min_chars, ignore_css)

    # Links
    # Use the already-pruned soup so we skip navigation and other non-content areas.
    links: list[str] = []
    base_url = allowed_domain
    if "://" not in base_url:
        base_url = f"https://{base_url}"

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/"):
            href = f"{base_url.rstrip('/')}{href}"
        elif not href.startswith("http"):
            continue
        if allowed_domain in href:
            links.append(href)

    return content, title, lang, links
