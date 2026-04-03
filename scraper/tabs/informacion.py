from __future__ import annotations

import re
from bs4 import BeautifulSoup

from models.itinerary import TravelInfo


def _text(el) -> str:
    return el.get_text(strip=True) if el else ""


def _between(text: str, start: str, ends: list[str]) -> str:
    """Extract text between 'start' label and the first occurring 'end' label."""
    pattern = re.compile(re.escape(start) + r"\s*:?\s*", re.IGNORECASE)
    m = pattern.search(text)
    if not m:
        return ""
    rest = text[m.end():]
    earliest = len(rest)
    for end_label in ends:
        pos = rest.lower().find(end_label.lower())
        if pos != -1 and pos < earliest:
            earliest = pos
    return rest[:earliest].strip()


def _yes_no(text: str, label: str) -> str:
    m = re.search(rf"{re.escape(label)}[?¿]*\s*:?\s*(Sí|No)", text, re.IGNORECASE)
    return m.group(1) if m else ""


def parse_travel_info(html: str) -> TravelInfo:
    soup = BeautifulSoup(html, "lxml")
    info = TravelInfo()

    # Country name & description
    block = soup.select_one("div.content-block")
    if block:
        title_bar = block.select_one("div.custom_title-bar")
        h2 = title_bar.select_one("h2") if title_bar else None
        info.country = _text(h2)

        body = block.select_one("div.body")
        if body:
            desc_parts = []
            for child in body.children:
                if hasattr(child, "name"):
                    if child.name == "h3":
                        break
                    if child.name in ("hr",):
                        continue
                    txt = child.get_text(strip=True) if hasattr(child, "get_text") else ""
                    if txt and len(txt) > 30:
                        desc_parts.append(txt)
            info.country_description = "\n".join(desc_parts)

    # Extract section texts by h3
    def _section_text(keyword: str) -> str:
        if not body:
            return ""
        h3 = body.find("h3", string=lambda s: s and keyword in (s or ""))
        if not h3:
            return ""
        next_div = h3.find_next_sibling("div")
        if next_div:
            next_h3 = h3.find_next_sibling("h3")
            if not next_h3:
                return next_div.get_text(" ", strip=True)
            div_line = getattr(next_div, "sourceline", None) or 0
            h3_line = getattr(next_h3, "sourceline", None) or float("inf")
            if div_line <= h3_line:
                return next_div.get_text(" ", strip=True)
        parts = []
        for sib in h3.find_next_siblings():
            if sib.name in ("h3", "hr"):
                break
            parts.append(sib.get_text(" ", strip=True))
        return " ".join(parts).strip()

    body = block.select_one("div.body") if block else None

    # Currency section
    currency_text = _section_text("Bancos")
    info.currency = _between(currency_text, "Moneda local", ["Símbolo"])
    info.currency_symbol = _between(currency_text, "Símbolo", ["Código ISO"])
    info.currency_code = _between(currency_text, "Código ISO", ["Subunidad"])
    info.bills = _between(currency_text, "Billetes", ["Monedas"])
    info.coins = _between(currency_text, "Monedas", ["Transacciones", "bancaria", "Cajeros"])
    cards = []
    for card in ("Mastercard", "Visa", "American Express", "Diner"):
        if _yes_no(currency_text, card) == "Sí":
            cards.append(card)
    info.accepted_cards = ", ".join(cards)
    info.banking_hours = _between(currency_text, "Horario bancario", ["Fines de semana", "servicios", "cambio"])

    # Transport section
    transport_text = _section_text("Transportes")
    info.airlines = _between(transport_text, "Aerolíneas principales", ["Aeropuertos internacionales"])
    info.international_airports = _between(transport_text, "Aeropuertos internacionales", ["Aeropuertos nacionales"])
    info.national_airports = _between(transport_text, "Aeropuertos nacionales", ["Carretera", "Conducir"])
    dl_match = re.search(r"carné de conducir internacional[^:]*:\s*(Sí|No)", transport_text, re.IGNORECASE)
    if not dl_match:
        dl_match = re.search(r"conducir internacional[^:]*:\s*(Sí|No)", transport_text, re.IGNORECASE)
    info.driving_license_required = dl_match.group(1) if dl_match else ""
    info.car_rental = _yes_no(transport_text, "Alquiler de coches")
    info.taxis = _yes_no(transport_text, "Taxis")
    info.buses = f"Interurbanos: {_yes_no(transport_text, 'interurbanos')}, Urbanos: {_yes_no(transport_text, 'urbanos')}"
    info.trains = f"Ferrocarril: {_yes_no(transport_text, 'ferroviario')}, Metro: {_yes_no(transport_text, 'metro')}"

    # Gastronomy section
    gastro_text = _section_text("Gastronomía")
    info.tap_water_safe = _yes_no(gastro_text, "agua del grifo")
    info.local_cuisine = _between(gastro_text, "Cocina local", ["Propina", "César", "vino"])
    if not info.local_cuisine:
        m = re.search(r"Cocina local\s*:?\s*(.+?)(?:Propina|$)", gastro_text, re.IGNORECASE)
        if m:
            info.local_cuisine = m.group(1).strip()
    info.tipping = _between(gastro_text, "Propina", ["Climatología", "Vestimenta", "Seguridad"])
    if not info.tipping:
        m = re.search(r"Propina\s*:?\s*(.+?)$", gastro_text, re.IGNORECASE)
        if m:
            info.tipping = m.group(1).strip()

    # Climate section
    climate_text = _section_text("Climatología")
    info.avg_rainfall = _between(climate_text, "Lluvia anual", ["Temperatura promedio", "Verano"])
    info.avg_temperature = _between(climate_text, "Temperatura promedio", ["Verano", "máximos"])
    summer_m = re.search(r"Verano\s*:?\s*máximos?\s*promedio\s*:?\s*([\d\-–]+\s*°?C[^I]*?)(?:Mínimos|Invierno)", climate_text, re.IGNORECASE)
    if summer_m:
        info.summer_temps = summer_m.group(1).strip()
    else:
        info.summer_temps = _between(climate_text, "Verano", ["Invierno", "Mejor"])
    winter_m = re.search(r"Invierno\s*:?\s*máximos?\s*promedio\s*:?\s*([\d\-–]+[^M]*?)(?:Mínimos|Mejor|$)", climate_text, re.IGNORECASE)
    if winter_m:
        info.winter_temps = winter_m.group(1).strip()
    else:
        info.winter_temps = _between(climate_text, "Invierno", ["Mejor", "Vestimenta"])
    info.best_time_to_visit = _between(climate_text, "Mejor época", ["Vestimenta", "Primavera", "Internet"])
    if not info.best_time_to_visit:
        m = re.search(r"Mejor época[^:]*:?\s*(.+?)$", climate_text, re.IGNORECASE)
        if m:
            info.best_time_to_visit = m.group(1).strip()

    # Clothing section
    clothing_text = _section_text("Vestimenta")
    info.clothing_summer = _between(clothing_text, "Primavera y verano", ["Otoño", "Invierno", "Paraguas", "General"])
    info.clothing_winter = _between(clothing_text, "Otoño", ["Paraguas", "General", "Internet", "Disponibilidad"])
    if not info.clothing_winter:
        info.clothing_winter = _between(clothing_text, "Invierno", ["Paraguas", "General", "Internet"])

    # Internet section
    internet_text = _section_text("Internet")
    internet_parts = []
    for place in ("Cibercafés", "alojamiento", "Restaurantes", "Cafeterías", "Centros comerciales", "Parques públicos", "Bibliotecas"):
        val = _yes_no(internet_text, place)
        if val:
            internet_parts.append(f"{place}: {val}")
    info.internet_availability = ", ".join(internet_parts)

    # Electricity section
    electricity_text = _section_text("Electricidad")
    info.plug_type = _between(electricity_text, "Tipo de enchufe", ["Voltaje", "frecuencia"])
    voltage_m = re.search(r"(\d+)\s*V", electricity_text)
    info.voltage = f"{voltage_m.group(1)} V" if voltage_m else ""
    freq_m = re.search(r"(\d+)\s*Hz", electricity_text)
    info.frequency = f"{freq_m.group(1)} Hz" if freq_m else ""

    return info
