from __future__ import annotations

import re
from bs4 import BeautifulSoup

from models.itinerary import Destination


def _text(el) -> str:
    return el.get_text(strip=True) if el else ""


def parse_destinations(html: str) -> list[Destination]:
    soup = BeautifulSoup(html, "lxml")
    destinations: list[Destination] = []

    for block in soup.select("div.content-block"):
        title_bar = block.select_one("div.custom_title-bar")
        if not title_bar:
            continue

        h2 = title_bar.select_one("h2")
        name = _text(h2)
        if not name:
            continue

        full_title = title_bar.get_text(strip=True)
        day_match = re.search(r"Días?\s+([\d\s\-–]+)", full_title)
        day_range = day_match.group(0).strip() if day_match else ""

        container = block.select_one("div.block-container")
        if not container:
            continue

        dest = Destination(name=name, day_range=day_range)

        # Description from paragraphs in the body/block-container
        paragraphs = []
        for p in container.select("p"):
            txt = _text(p)
            if txt and len(txt) > 20:
                paragraphs.append(txt)
        dest.description = "\n".join(paragraphs)

        # Accommodation and alternatives: found via title-bar h3 headings inside block-container
        for inner_bar in container.select("div.custom_title-bar"):
            h3 = inner_bar.select_one("h3")
            if not h3:
                continue
            heading = _text(h3)

            if heading == "Alojamiento":
                # The link is in a sibling element after this title bar
                for sib in inner_bar.find_next_siblings():
                    if sib.name == "div" and "custom_title-bar" in " ".join(sib.get("class", [])):
                        break
                    a = sib.select_one("a") if hasattr(sib, "select_one") else None
                    if not a and sib.name == "a":
                        a = sib
                    if a:
                        dest.accommodation = _text(a)
                        break

            elif "Alojamiento Alternativo" in heading:
                for sib in inner_bar.find_next_siblings():
                    if sib.name == "div" and "custom_title-bar" in " ".join(sib.get("class", [])):
                        break
                    for a in (sib.select("a") if hasattr(sib, "select") else []):
                        alt_name = _text(a)
                        if alt_name and alt_name not in dest.alternatives:
                            dest.alternatives.append(alt_name)
                    if sib.name == "a":
                        alt_name = _text(sib)
                        if alt_name and alt_name not in dest.alternatives:
                            dest.alternatives.append(alt_name)

        # Images
        for img in container.select("img"):
            src = img.get("src") or img.get("data-src", "")
            if src and src not in dest.image_urls:
                dest.image_urls.append(src)

        destinations.append(dest)

    return destinations
