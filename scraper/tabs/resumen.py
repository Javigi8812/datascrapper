from __future__ import annotations

import re
from bs4 import BeautifulSoup

from models.itinerary import ItinerarySummaryRow, Supplement


def _text(el) -> str:
    return el.get_text(strip=True) if el else ""


def parse_overview(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    data: dict = {}

    # Title (from the page h1)
    h1 = soup.select_one("h1")
    data["title"] = _text(h1)

    # Introduction: div.content-body.paragraphs after the Introducción heading
    intro_bar = soup.find(
        "h2", string=lambda s: s and "Introducción" in s
    )
    data["introduction"] = ""
    if intro_bar:
        title_bar = intro_bar.find_parent("div", class_="custom_title-bar")
        if title_bar:
            content_div = title_bar.find_next_sibling("div", class_="content-body")
            if not content_div:
                content_div = title_bar.find_next_sibling("div")
            if content_div:
                data["introduction"] = content_div.get_text("\n", strip=True)

    # Summary table (first table with itinerary rows)
    rows: list[ItinerarySummaryRow] = []
    table = soup.select_one("table")
    if table:
        for tr in table.select("tr")[1:]:  # skip header
            cells = tr.select("td")
            if len(cells) >= 6:
                row = ItinerarySummaryRow(
                    day=_text(cells[0]),
                    hotel=_text(cells[1]),
                    hotel_type=_text(cells[2]),
                    destination=_text(cells[3]),
                    duration=_text(cells[4]),
                    basis=_text(cells[5]),
                )
                rows.append(row)
    data["summary_rows"] = rows

    # Duration & Reference: from "Datos Básicos" h3 section
    full_text = soup.get_text("\n")
    dur_match = re.search(r"(\d+\s*[Dd]ías?\s*/\s*\d+\s*noches?)", full_text)
    data["duration"] = dur_match.group(1) if dur_match else ""
    ref_match = re.search(r"Número de Referencia:\s*(\S+)", full_text)
    data["reference"] = ref_match.group(1).strip() if ref_match else ""

    # Price: text after h3 "Precio" title bar
    price_bar = soup.find("h3", string=lambda s: s and "Precio" in s)
    data["price"] = ""
    if price_bar:
        title_div = price_bar.find_parent("div", class_="custom_title-bar")
        if title_div:
            price_p = title_div.find_next_sibling("p")
            if price_p:
                price_m = re.search(r"Precio desde\s+(.+)", _text(price_p))
                data["price"] = price_m.group(1).strip() if price_m else _text(price_p)

    # Supplements: UL items after "Suplementos opcionales:" paragraph
    supplements: list[Supplement] = []
    supp_p = soup.find("p", string=lambda s: s and "Suplementos opcionales" in s)
    if supp_p:
        # The UL immediately following the supplements paragraph
        supp_ul = supp_p.find_next_sibling("ul")
        if supp_ul:
            current_category = ""
            for li in supp_ul.find_all("li", recursive=False):
                # Check if this LI has nested ULs (category header)
                nested_ul = li.find("ul")
                if nested_ul:
                    # This is a category (Hoteles, Excursiones)
                    li_text = ""
                    for child in li.children:
                        if child.name == "ul":
                            break
                        if hasattr(child, "get_text"):
                            li_text += child.get_text(strip=True)
                        elif isinstance(child, str):
                            li_text += child.strip()
                    current_category = li_text.rstrip(":")
                    for sub_li in nested_ul.find_all("li", recursive=False):
                        sub_nested = sub_li.find("ul")
                        if sub_nested:
                            dest_name = ""
                            for ch in sub_li.children:
                                if ch.name == "ul":
                                    break
                                if hasattr(ch, "get_text"):
                                    dest_name += ch.get_text(strip=True)
                                elif isinstance(ch, str):
                                    dest_name += ch.strip()
                            dest_name = dest_name.rstrip(":")
                            for item_li in sub_nested.select("li"):
                                if item_li.find("ul"):
                                    continue
                                txt = _text(item_li)
                                s = Supplement(category=current_category, destination=dest_name)
                                price_m = re.search(r"Suplemento\s*([+\-]?\s*[\d.,]+\s*€[^€]*)", txt)
                                if price_m:
                                    s.price = price_m.group(1).strip()
                                    s.name = txt[:txt.index("Suplemento")].strip().rstrip("-").strip()
                                else:
                                    s.name = txt
                                supplements.append(s)
                        else:
                            txt = _text(sub_li)
                            s = Supplement(category=current_category)
                            price_m = re.search(r"Suplemento\s*([+\-]?\s*[\d.,]+\s*€[^€]*)", txt)
                            if price_m:
                                s.price = price_m.group(1).strip()
                                s.name = txt[:txt.index("Suplemento")].strip().rstrip("-").strip()
                            else:
                                s.name = txt
                            parts = s.name.split(" - ", 1)
                            if len(parts) > 1:
                                s.destination = parts[0].strip()
                                s.name = parts[1].strip()
                            supplements.append(s)
                else:
                    txt = _text(li)
                    s = Supplement(category=current_category)
                    price_m = re.search(r"Suplemento\s*([+\-]?\s*[\d.,]+\s*€[^€]*)", txt)
                    if price_m:
                        s.price = price_m.group(1).strip()
                        s.name = txt[:txt.index("Suplemento")].strip().rstrip("-").strip()
                    else:
                        s.name = txt
                    parts = s.name.split(" - ", 1)
                    if len(parts) > 1:
                        s.destination = parts[0].strip()
                        s.name = parts[1].strip()
                    supplements.append(s)
    data["supplements"] = supplements

    # Includes / Excludes / Client Responsibility
    def _extract_section(keyword: str) -> str:
        heading = soup.find("p", class_="sectionheading", string=lambda s: s and keyword in s)
        if not heading:
            heading = soup.find(lambda t: t.name in ("p", "strong", "b") and t.get_text(strip=True).startswith(keyword))
        if not heading:
            return ""
        parts = []
        for sib in heading.find_next_siblings():
            if sib.name == "p" and "sectionheading" in (sib.get("class") or []):
                break
            if sib.name in ("h2", "h3", "h4"):
                break
            txt = sib.get_text("\n", strip=True)
            if txt:
                parts.append(txt)
        return "\n".join(parts).strip()

    data["includes"] = _extract_section("Incluye")
    data["excludes"] = _extract_section("Excluye")
    data["client_responsibility"] = _extract_section("Por cuenta del cliente")

    # Agent info: follows h3 "Detalles del Agente" title bar
    agent_heading = soup.find("h3", string=lambda s: s and "Detalles del Agente" in s)
    data["agent_name"] = ""
    data["agent_phone"] = ""
    data["agent_email"] = ""
    data["agent_web"] = ""
    if agent_heading:
        title_div = agent_heading.find_parent("div", class_="custom_title-bar")
        if title_div:
            agent_div = title_div.find_next_sibling("div")
            if agent_div:
                text = agent_div.get_text("\n", strip=True)
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                if lines:
                    data["agent_name"] = lines[0]
                phone_m = re.search(r"(\+34[\d\s/]+)", text)
                if phone_m:
                    data["agent_phone"] = phone_m.group(1).strip()
                email_a = agent_div.select_one("a[href^='mailto:']")
                if email_a:
                    data["agent_email"] = _text(email_a)
                for a in agent_div.select("a[href]"):
                    href = a.get("href", "")
                    if href.startswith("http") and "mailto:" not in href:
                        data["agent_web"] = href
                        break

    return data
