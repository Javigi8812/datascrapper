from __future__ import annotations

import re
from bs4 import BeautifulSoup

from models.itinerary import DailyInfo


def _text(el) -> str:
    return el.get_text(strip=True) if el else ""


def parse_daily_info(html: str) -> list[DailyInfo]:
    soup = BeautifulSoup(html, "lxml")
    days: list[DailyInfo] = []
    day_pattern = re.compile(r"[Dd]ía\s+(\d+)")

    for block in soup.select("div.content-block"):
        title_bar = block.select_one("div.custom_title-bar")
        if not title_bar:
            continue

        h2 = title_bar.select_one("h2")
        title = _text(h2) if h2 else title_bar.get_text(strip=True)
        match = day_pattern.search(title)
        if not match:
            continue

        day = DailyInfo()
        day.day_number = match.group(1)
        day.title = title

        # City from "Día N:City" or "Día N: City"
        city_part = re.split(r":\s*", title, maxsplit=1)
        day.city = city_part[1].strip() if len(city_part) > 1 else ""

        container = block.select_one("div.block-container")
        if not container:
            continue

        # Description paragraphs
        paragraphs = []
        for p in container.select("p"):
            txt = _text(p)
            if txt and txt.lower() not in ("alojamiento", "alojamiento."):
                paragraphs.append(txt)
        day.description = "\n".join(paragraphs)

        # Images
        for img in container.select("img"):
            src = img.get("src") or img.get("data-src", "")
            if src and src not in day.image_urls:
                day.image_urls.append(src)

        days.append(day)

    return days
