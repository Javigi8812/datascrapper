from __future__ import annotations

from bs4 import BeautifulSoup

from models.itinerary import Document


def _text(el) -> str:
    return el.get_text(strip=True) if el else ""


def parse_documents(html: str) -> list[Document]:
    soup = BeautifulSoup(html, "lxml")
    documents: list[Document] = []

    # Find the "Documentos" heading
    doc_heading = soup.find(
        lambda t: t.name in ("h2", "h3") and "Documentos" in (t.string or t.get_text())
    )

    if doc_heading:
        search_area = doc_heading.parent if doc_heading.parent else soup
    else:
        search_area = soup

    skip_hrefs = {"mailto:", "#", "javascript:"}

    for ul in search_area.select("ul"):
        for li in ul.select("li"):
            a = li.select_one("a[href]")
            if a:
                href = a.get("href", "")
                if any(href.startswith(s) for s in skip_hrefs):
                    continue
                name = _text(a)
                if name and ("blob" in href or ".pdf" in href.lower() or href.startswith("http")):
                    documents.append(Document(name=name, url=href))

    # Fallback: search all links with PDF extensions
    if not documents:
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if ".pdf" in href.lower():
                documents.append(Document(name=_text(a), url=href))

    return documents
