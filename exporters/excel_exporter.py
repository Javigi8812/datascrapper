from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from models.itinerary import Itinerary


def _safe_sheet_name(name: str) -> str:
    return name[:31]


def export_itinerary(itinerary: Itinerary, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in itinerary.title)[:80]
    filename = f"{safe_title}_{itinerary.itinerary_id[:8]}.xlsx"
    filepath = os.path.join(output_dir, filename)

    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        # Sheet 1: Resumen
        summary_data = {
            "Título": [itinerary.title],
            "Duración": [itinerary.duration],
            "Referencia": [itinerary.reference],
            "Precio": [itinerary.price],
            "Introducción": [itinerary.introduction],
            "Agente": [itinerary.agent_name],
            "Teléfono Agente": [itinerary.agent_phone],
            "Email Agente": [itinerary.agent_email],
            "Web Agente": [itinerary.agent_web],
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Resumen", index=False)

        # Sheet 2: Itinerario (summary rows)
        if itinerary.summary_rows:
            rows = [
                {
                    "Día": r.day,
                    "Hotel": r.hotel,
                    "Tipo": r.hotel_type,
                    "Destino": r.destination,
                    "Duración": r.duration,
                    "Régimen": r.basis,
                }
                for r in itinerary.summary_rows
            ]
            pd.DataFrame(rows).to_excel(writer, sheet_name="Itinerario", index=False)

        # Sheet 3: Destinos
        if itinerary.destinations:
            rows = [
                {
                    "Nombre": d.name,
                    "Días": d.day_range,
                    "Descripción": d.description,
                    "Alojamiento": d.accommodation,
                    "Alternativas": ", ".join(d.alternatives),
                    "Imágenes": ", ".join(d.image_urls),
                }
                for d in itinerary.destinations
            ]
            pd.DataFrame(rows).to_excel(writer, sheet_name="Destinos", index=False)

        # Sheet 4: Alojamiento
        if itinerary.accommodations:
            rows = [
                {
                    "Nombre": a.name,
                    "Ciudad": a.city,
                    "Descripción": a.description,
                    "Tipo Propiedad": a.property_type,
                    "Noches": a.nights,
                    "Régimen": a.meal_plan,
                    "Es Alternativo": "Sí" if a.is_alternative else "No",
                    "Alternativo Para": a.alternative_for,
                    "Imágenes": ", ".join(a.image_urls),
                }
                for a in itinerary.accommodations
            ]
            pd.DataFrame(rows).to_excel(writer, sheet_name="Alojamiento", index=False)

        # Sheet 5: Info Diaria
        if itinerary.daily_info:
            rows = [
                {
                    "Día": d.day_number,
                    "Ciudad": d.city,
                    "Título": d.title,
                    "Descripción": d.description,
                    "Imágenes": ", ".join(d.image_urls),
                }
                for d in itinerary.daily_info
            ]
            pd.DataFrame(rows).to_excel(writer, sheet_name="Info Diaria", index=False)

        # Sheet 6: Vuelos
        if itinerary.transport.flights:
            rows = [
                {
                    "Aerolínea": f.airline,
                    "Nº Vuelo": f.flight_number,
                    "Aeropuerto Salida": f.departure_airport,
                    "Hora Salida": f.departure_time,
                    "Aeropuerto Llegada": f.arrival_airport,
                    "Hora Llegada": f.arrival_time,
                    "Notas": f.notes,
                }
                for f in itinerary.transport.flights
            ]
            pd.DataFrame(rows).to_excel(writer, sheet_name="Vuelos", index=False)

        if itinerary.transport.car_rental:
            pd.DataFrame([{"Alquiler de Coche": itinerary.transport.car_rental}]).to_excel(
                writer, sheet_name="Alquiler Coche", index=False
            )

        # Sheet 7: Suplementos
        if itinerary.supplements:
            rows = [
                {
                    "Categoría": s.category,
                    "Destino": s.destination,
                    "Nombre": s.name,
                    "Precio": s.price,
                }
                for s in itinerary.supplements
            ]
            pd.DataFrame(rows).to_excel(writer, sheet_name="Suplementos", index=False)

        # Sheet 8: Info País
        ti = itinerary.travel_info
        travel_data = {
            "País": [ti.country],
            "Descripción": [ti.country_description],
            "Moneda": [ti.currency],
            "Código ISO": [ti.currency_code],
            "Símbolo": [ti.currency_symbol],
            "Billetes": [ti.bills],
            "Monedas": [ti.coins],
            "Tarjetas Aceptadas": [ti.accepted_cards],
            "Horario Bancario": [ti.banking_hours],
            "Aerolíneas": [ti.airlines],
            "Aeropuertos Internacionales": [ti.international_airports],
            "Aeropuertos Nacionales": [ti.national_airports],
            "Carnet Conducir Internacional": [ti.driving_license_required],
            "Alquiler Coches": [ti.car_rental],
            "Taxis": [ti.taxis],
            "Autobuses": [ti.buses],
            "Trenes": [ti.trains],
            "Agua Potable": [ti.tap_water_safe],
            "Cocina Local": [ti.local_cuisine],
            "Propinas": [ti.tipping],
            "Precipitación Anual": [ti.avg_rainfall],
            "Temperatura Media": [ti.avg_temperature],
            "Temperaturas Verano": [ti.summer_temps],
            "Temperaturas Invierno": [ti.winter_temps],
            "Mejor Época": [ti.best_time_to_visit],
            "Ropa Verano": [ti.clothing_summer],
            "Ropa Invierno": [ti.clothing_winter],
            "Internet": [ti.internet_availability],
            "Tipo Enchufe": [ti.plug_type],
            "Voltaje": [ti.voltage],
            "Frecuencia": [ti.frequency],
        }
        pd.DataFrame(travel_data).to_excel(writer, sheet_name="Info País", index=False)

        # Sheet 9: Documentos
        if itinerary.documents:
            rows = [{"Nombre": d.name, "URL": d.url} for d in itinerary.documents]
            pd.DataFrame(rows).to_excel(writer, sheet_name="Documentos", index=False)

        # Sheet 10: Incluye / Excluye
        ie_data = {
            "Incluye": [itinerary.includes],
            "Excluye": [itinerary.excludes],
            "Por Cuenta del Cliente": [itinerary.client_responsibility],
        }
        pd.DataFrame(ie_data).to_excel(writer, sheet_name="Incluye-Excluye", index=False)

    return filepath


def export_consolidated(itineraries: list[Itinerary], output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, "resumen_consolidado.xlsx")

    rows = [
        {
            "ID": it.itinerary_id,
            "Título": it.title,
            "Duración": it.duration,
            "Referencia": it.reference,
            "Precio": it.price,
            "Nº Destinos": len(it.destinations),
            "Nº Hoteles": len([a for a in it.accommodations if not a.is_alternative]),
            "Nº Vuelos": len(it.transport.flights),
            "Nº Días Detallados": len(it.daily_info),
            "Nº Documentos": len(it.documents),
        }
        for it in itineraries
    ]

    pd.DataFrame(rows).to_excel(filepath, index=False, engine="openpyxl")
    return filepath
