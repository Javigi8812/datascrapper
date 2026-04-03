#!/usr/bin/env python3
"""Honimunn Travel Itinerary Scraper - CLI entry point + reusable engine."""
from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Callable, Optional

from tqdm import tqdm

from config import DEFAULT_CONCURRENCY
from models.itinerary import Itinerary
from scraper.url_parser import extract_itinerary_id, build_tab_urls
from scraper.browser import BrowserManager
from scraper.tabs.resumen import parse_overview
from scraper.tabs.destinos import parse_destinations
from scraper.tabs.alojamiento import parse_accommodation
from scraper.tabs.info_diaria import parse_daily_info
from scraper.tabs.transporte import parse_transport
from scraper.tabs.informacion import parse_travel_info
from scraper.tabs.documentos import parse_documents
from exporters.excel_exporter import export_itinerary, export_consolidated

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scraper.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")

ProgressCallback = Optional[Callable[[str, int, int], None]]

TAB_LABELS = [
    "Resumen", "Destinos", "Alojamiento",
    "Info Diaria", "Transporte", "Info Viaje", "Documentos",
]


def read_urls_from_csv(csv_path: str) -> list[str]:
    urls: list[str] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("url", "").strip()
            if url:
                urls.append(url)
    return urls


async def scrape_itinerary(
    browser: BrowserManager,
    url: str,
    on_progress: ProgressCallback = None,
    url_index: int = 0,
    url_total: int = 1,
) -> Itinerary:
    itinerary_id = extract_itinerary_id(url)
    tab_urls = build_tab_urls(itinerary_id)
    itinerary = Itinerary(itinerary_id=itinerary_id)
    total_tabs = len(TAB_LABELS)

    def _report(tab_idx: int, label: str):
        msg = f"[{url_index+1}/{url_total}] {label} ({tab_idx+1}/{total_tabs})"
        logger.info("Scraping %s for %s", label, itinerary_id)
        if on_progress:
            on_progress(msg, tab_idx + 1, total_tabs)

    # 1. Overview / Resumen
    _report(0, "Resumen")
    try:
        html = await browser.fetch_html(tab_urls["overview"])
        data = parse_overview(html)
        itinerary.title = data.get("title", "")
        itinerary.duration = data.get("duration", "")
        itinerary.reference = data.get("reference", "")
        itinerary.price = data.get("price", "")
        itinerary.introduction = data.get("introduction", "")
        itinerary.summary_rows = data.get("summary_rows", [])
        itinerary.supplements = data.get("supplements", [])
        itinerary.includes = data.get("includes", "")
        itinerary.excludes = data.get("excludes", "")
        itinerary.client_responsibility = data.get("client_responsibility", "")
        itinerary.agent_name = data.get("agent_name", "")
        itinerary.agent_phone = data.get("agent_phone", "")
        itinerary.agent_email = data.get("agent_email", "")
        itinerary.agent_web = data.get("agent_web", "")
    except Exception as e:
        logger.error("Failed to scrape Overview: %s", e)

    # 2. Destinations
    _report(1, "Destinos")
    try:
        html = await browser.fetch_html(tab_urls["destinations"])
        itinerary.destinations = parse_destinations(html)
    except Exception as e:
        logger.error("Failed to scrape Destinations: %s", e)

    # 3. Accommodation
    _report(2, "Alojamiento")
    try:
        html = await browser.fetch_html(tab_urls["accommodation"])
        itinerary.accommodations = parse_accommodation(html)
    except Exception as e:
        logger.error("Failed to scrape Accommodation: %s", e)

    # 4. Daily Info
    _report(3, "Info Diaria")
    try:
        html = await browser.fetch_html(tab_urls["daily_info"])
        itinerary.daily_info = parse_daily_info(html)
    except Exception as e:
        logger.error("Failed to scrape Daily Info: %s", e)

    # 5. Transport
    _report(4, "Transporte")
    try:
        html = await browser.fetch_html(tab_urls["transport"])
        itinerary.transport = parse_transport(html)
    except Exception as e:
        logger.error("Failed to scrape Transport: %s", e)

    # 6. Travel Info
    _report(5, "Info Viaje")
    try:
        html = await browser.fetch_html(tab_urls["travel_info"])
        itinerary.travel_info = parse_travel_info(html)
    except Exception as e:
        logger.error("Failed to scrape Travel Info: %s", e)

    # 7. Documents
    _report(6, "Documentos")
    try:
        html = await browser.fetch_html(tab_urls["documents"])
        itinerary.documents = parse_documents(html)
    except Exception as e:
        logger.error("Failed to scrape Documents: %s", e)

    return itinerary


async def run_with_progress(
    urls: list[str],
    output_dir: str,
    concurrency: int = DEFAULT_CONCURRENCY,
    on_progress: ProgressCallback = None,
    pause_event: threading.Event | None = None,
) -> list[dict]:
    """Run scraping with progress callback. Returns list of result dicts."""
    os.makedirs(output_dir, exist_ok=True)
    all_itineraries: list[Itinerary] = []
    results: list[dict] = []

    if on_progress:
        on_progress("Iniciando navegador...", 0, len(urls))

    async with BrowserManager() as browser:
        for i, url in enumerate(urls):
            if pause_event and not pause_event.is_set():
                if on_progress:
                    on_progress("Pausado — esperando reanudar...", i, len(urls))
                while not pause_event.is_set():
                    await asyncio.sleep(0.3)
                if on_progress:
                    on_progress("Reanudado", i, len(urls))

            if on_progress:
                on_progress(
                    f"Itinerario {i+1}/{len(urls)}: iniciando...",
                    i, len(urls),
                )
            try:
                itinerary = await scrape_itinerary(
                    browser, url,
                    on_progress=on_progress,
                    url_index=i,
                    url_total=len(urls),
                )
                all_itineraries.append(itinerary)
                filepath = export_itinerary(itinerary, output_dir)
                filename = os.path.basename(filepath)
                results.append({
                    "url": url,
                    "title": itinerary.title,
                    "filename": filename,
                    "status": "ok",
                })
                if on_progress:
                    on_progress(
                        f"Exportado: {itinerary.title}",
                        i + 1, len(urls),
                    )
            except Exception as e:
                logger.error("Failed to scrape %s: %s", url, e)
                results.append({
                    "url": url,
                    "title": "",
                    "filename": "",
                    "status": f"error: {e}",
                })

    consolidated_filename = ""
    if all_itineraries:
        consolidated_path = export_consolidated(all_itineraries, output_dir)
        consolidated_filename = os.path.basename(consolidated_path)

    if on_progress:
        on_progress("Completado", len(urls), len(urls))

    return results, consolidated_filename


async def run(urls: list[str], output_dir: str, concurrency: int) -> None:
    """CLI-compatible run (uses tqdm for progress)."""
    all_itineraries: list[Itinerary] = []

    async with BrowserManager() as browser:
        semaphore = asyncio.Semaphore(concurrency)

        async def _scrape_one(url: str) -> Itinerary | None:
            async with semaphore:
                try:
                    return await scrape_itinerary(browser, url)
                except Exception as e:
                    logger.error("Failed to scrape %s: %s", url, e)
                    return None

        tasks = [_scrape_one(url) for url in urls]

        with tqdm(total=len(urls), desc="Scraping itineraries", unit="itinerary") as pbar:
            for coro in asyncio.as_completed(tasks):
                result = await coro
                if result:
                    all_itineraries.append(result)
                    filepath = export_itinerary(result, output_dir)
                    logger.info("Exported: %s", filepath)
                pbar.update(1)

    if all_itineraries:
        consolidated = export_consolidated(all_itineraries, output_dir)
        logger.info("Consolidated report: %s", consolidated)

    print(f"\nDone! {len(all_itineraries)} itineraries exported to {output_dir}/")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape Honimunn travel itineraries and export to Excel"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", "-i", help="CSV file with 'url' column")
    group.add_argument("--url", "-u", help="Single itinerary URL to scrape")
    parser.add_argument("--output", "-o", default="./output", help="Output directory (default: ./output)")
    parser.add_argument("--concurrency", "-c", type=int, default=DEFAULT_CONCURRENCY, help="Max concurrent scrapes")

    args = parser.parse_args()

    if args.url:
        urls = [args.url]
    else:
        urls = read_urls_from_csv(args.input)
        if not urls:
            print("No URLs found in the CSV file.", file=sys.stderr)
            sys.exit(1)

    print(f"Found {len(urls)} URL(s) to scrape.")
    asyncio.run(run(urls, args.output, args.concurrency))


if __name__ == "__main__":
    main()
