from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ItinerarySummaryRow:
    day: str = ""
    hotel: str = ""
    hotel_type: str = ""
    destination: str = ""
    duration: str = ""
    basis: str = ""


@dataclass
class Supplement:
    category: str = ""
    destination: str = ""
    name: str = ""
    price: str = ""


@dataclass
class Destination:
    name: str = ""
    day_range: str = ""
    description: str = ""
    accommodation: str = ""
    alternatives: list[str] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)


@dataclass
class Accommodation:
    name: str = ""
    city: str = ""
    description: str = ""
    property_type: str = ""
    nights: str = ""
    meal_plan: str = ""
    image_urls: list[str] = field(default_factory=list)
    is_alternative: bool = False
    alternative_for: str = ""


@dataclass
class DailyInfo:
    day_number: str = ""
    city: str = ""
    title: str = ""
    description: str = ""
    image_urls: list[str] = field(default_factory=list)


@dataclass
class Flight:
    airline: str = ""
    flight_number: str = ""
    departure_airport: str = ""
    departure_time: str = ""
    arrival_airport: str = ""
    arrival_time: str = ""
    notes: str = ""


@dataclass
class TransportInfo:
    flights: list[Flight] = field(default_factory=list)
    car_rental: str = ""


@dataclass
class TravelInfo:
    country: str = ""
    country_description: str = ""
    currency: str = ""
    currency_code: str = ""
    currency_symbol: str = ""
    bills: str = ""
    coins: str = ""
    accepted_cards: str = ""
    banking_hours: str = ""
    airlines: str = ""
    international_airports: str = ""
    national_airports: str = ""
    driving_license_required: str = ""
    car_rental: str = ""
    taxis: str = ""
    buses: str = ""
    trains: str = ""
    tap_water_safe: str = ""
    local_cuisine: str = ""
    tipping: str = ""
    avg_rainfall: str = ""
    avg_temperature: str = ""
    summer_temps: str = ""
    winter_temps: str = ""
    best_time_to_visit: str = ""
    clothing_summer: str = ""
    clothing_winter: str = ""
    internet_availability: str = ""
    plug_type: str = ""
    voltage: str = ""
    frequency: str = ""


@dataclass
class Document:
    name: str = ""
    url: str = ""


@dataclass
class Itinerary:
    itinerary_id: str = ""
    title: str = ""
    duration: str = ""
    reference: str = ""
    price: str = ""
    introduction: str = ""
    includes: str = ""
    excludes: str = ""
    client_responsibility: str = ""
    agent_name: str = ""
    agent_phone: str = ""
    agent_email: str = ""
    agent_web: str = ""

    summary_rows: list[ItinerarySummaryRow] = field(default_factory=list)
    supplements: list[Supplement] = field(default_factory=list)
    destinations: list[Destination] = field(default_factory=list)
    accommodations: list[Accommodation] = field(default_factory=list)
    daily_info: list[DailyInfo] = field(default_factory=list)
    transport: TransportInfo = field(default_factory=TransportInfo)
    travel_info: TravelInfo = field(default_factory=TravelInfo)
    documents: list[Document] = field(default_factory=list)
