from __future__ import annotations

import re
from bs4 import BeautifulSoup

from models.itinerary import Flight, TransportInfo


def _text(el) -> str:
    return el.get_text(strip=True) if el else ""


def parse_transport(html: str) -> TransportInfo:
    soup = BeautifulSoup(html, "lxml")
    info = TransportInfo()

    table = soup.select_one("table")
    if table:
        for tr in table.select("tr"):
            cells = tr.select("td")
            if len(cells) < 5:
                continue
            airline = _text(cells[0])
            if not airline or "Compañía" in airline:
                continue

            flight = Flight(
                airline=airline,
                flight_number=_text(cells[1]),
                departure_airport=_text(cells[2]),
                departure_time=_text(cells[3]),
                arrival_airport=_text(cells[4]),
                arrival_time=_text(cells[5]) if len(cells) > 5 else "",
            )

            # Notes (e.g. "+1" for next-day arrival)
            if len(cells) > 6:
                notes = _text(cells[6])
                if notes:
                    flight.notes = notes
            if "+1" in flight.arrival_time:
                flight.notes = "+1 día"
                flight.arrival_time = flight.arrival_time.replace("+1", "").strip()

            info.flights.append(flight)

    # Car rental from page text
    full_text = soup.get_text()
    car_match = re.search(
        r"(Coche de alquiler[^\n.]{5,80})", full_text, re.IGNORECASE
    )
    if car_match:
        info.car_rental = car_match.group(1).strip()

    return info
