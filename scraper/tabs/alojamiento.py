from __future__ import annotations

import re
from bs4 import BeautifulSoup

from models.itinerary import Accommodation
from config import BASE_URL


def _text(el) -> str:
    return el.get_text(strip=True) if el else ""


def parse_accommodation(html: str) -> list[Accommodation]:
    soup = BeautifulSoup(html, "lxml")
    accommodations: list[Accommodation] = []

    for block in soup.select("div.content-block"):
        title_bar = block.select_one("div.custom_title-bar")
        if not title_bar:
            continue
        h2 = title_bar.select_one("h2")
        raw_title = _text(h2)
        if not raw_title:
            continue

        # Parse "Hotel Name| City" format
        parts = raw_title.split("|")
        name = parts[0].strip()
        city = parts[1].strip() if len(parts) > 1 else ""

        acc = Accommodation(name=name, city=city)

        # Description from div.body paragraphs
        body = block.select_one("div.body")
        if body:
            paragraphs = []
            for p in body.select("p"):
                txt = _text(p)
                if txt and len(txt) > 10:
                    paragraphs.append(txt)
            acc.description = "\n".join(paragraphs)

            for img in body.select("img"):
                src = img.get("src") or img.get("data-src", "")
                if src:
                    if src.startswith("/"):
                        src = BASE_URL + src
                    if src not in acc.image_urls:
                        acc.image_urls.append(src)

        # Side blocks for Su Estancia, Datos Básicos, Alternativas
        for side_block in block.select("div.side-block"):
            h3 = side_block.select_one("h3")
            heading = _text(h3)

            if "Su Estancia" in heading:
                for p in side_block.select("p"):
                    txt = _text(p)
                    nights_m = re.search(r"(\d+\s*noches?)", txt)
                    if nights_m:
                        acc.nights = nights_m.group(1)
                    elif txt and not acc.meal_plan:
                        acc.meal_plan = txt

            elif "Datos Básicos" in heading:
                p = side_block.select_one("p")
                if p:
                    acc.property_type = _text(p)

            elif "Alojamiento Alternativo" in heading:
                for a in side_block.select("a"):
                    alt_name = _text(a)
                    if alt_name:
                        alt = Accommodation(
                            name=alt_name,
                            city=acc.city,
                            is_alternative=True,
                            alternative_for=acc.name,
                        )
                        accommodations.append(alt)

        accommodations.append(acc)

    return accommodations
