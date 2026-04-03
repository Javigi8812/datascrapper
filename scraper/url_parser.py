import re
from urllib.parse import urlparse

from config import BASE_URL, TAB_PATHS

_ID_PATTERN = re.compile(
    r"/Itinerary/\w+/([0-9a-fA-F\-]{36})"
)


def extract_itinerary_id(url: str) -> str:
    match = _ID_PATTERN.search(url)
    if not match:
        raise ValueError(f"Could not extract itinerary ID from URL: {url}")
    return match.group(1)


def build_tab_urls(itinerary_id: str) -> dict[str, str]:
    return {
        tab_name: f"{BASE_URL}{path}{itinerary_id}"
        for tab_name, path in TAB_PATHS.items()
    }
