from typing import Optional, Type
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


CITY_IDS = {
    "peshawar": 17,
    "islamabad": 3,
    "lahore": 1,
    "karachi": 2,
    "rawalpindi": 41,
    "faisalabad": 16,
    "multan": 18,
    "quetta": 76,
}

PURPOSE_PATH = {
    "buy": "Homes",
    "rent": "Homes_Rentals",
}

TYPE_PATH = {
    "homes": "Homes",
    "plots": "Plots",
    "commercial": "Commercial",
}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


class ZameenSearchInput(BaseModel):
    city: str = Field(..., description="Pakistani city, e.g. 'peshawar', 'lahore', 'karachi'")
    purpose: str = Field("buy", description="'buy' or 'rent'")
    property_type: str = Field("homes", description="'homes', 'plots', or 'commercial'")
    area: Optional[str] = Field(None, description="Optional sub-area or neighborhood, e.g. 'Hayatabad'")
    min_price: Optional[int] = Field(None, description="Minimum price in PKR")
    max_price: Optional[int] = Field(None, description="Maximum price in PKR")
    limit: int = Field(10, description="Maximum number of listings to return")


def _build_url(city: str, purpose: str, property_type: str,
               min_price: Optional[int], max_price: Optional[int]) -> str:
    city_key = city.strip().lower()
    if city_key not in CITY_IDS:
        return ""

    if purpose.lower() == "rent":
        section = TYPE_PATH.get(property_type.lower(), "Homes") + "_Rentals"
    else:
        section = TYPE_PATH.get(property_type.lower(), "Homes")

    base = f"https://www.zameen.com/{section}/{city_key.capitalize()}-{CITY_IDS[city_key]}-1.html"
    params = {}
    if min_price:
        params["price_min"] = min_price
    if max_price:
        params["price_max"] = max_price
    if params:
        base += "?" + urlencode(params)
    return base


def _parse_listings(html: str, area_filter: Optional[str], limit: int):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select('[aria-label="Listing"]')
    listings = []

    for card in cards:
        title_el = card.select_one('[aria-label="Title"]')
        price_el = card.select_one('[aria-label="Price"]')
        currency_el = card.select_one('[aria-label="Currency"]')
        loc_el = card.select_one('[aria-label="Location"]')
        area_el = card.select_one('[aria-label="Area"]')
        beds_el = card.select_one('[aria-label="Beds"]')
        baths_el = card.select_one('[aria-label="Baths"]')
        link_el = card.select_one('a[aria-label="Listing link"]') or card.find("a", href=True)

        title = title_el.get_text(strip=True) if title_el else ""
        price_num = price_el.get_text(strip=True) if price_el else ""
        currency = currency_el.get_text(strip=True) if currency_el else ""
        price = (currency + " " + price_num).strip() if price_num else ""
        location = loc_el.get_text(strip=True) if loc_el else ""
        area_size = area_el.get_text(strip=True) if area_el else ""
        beds = beds_el.get_text(strip=True) if beds_el else ""
        baths = baths_el.get_text(strip=True) if baths_el else ""
        href = link_el["href"] if link_el else ""
        if href and href.startswith("/"):
            href = "https://www.zameen.com" + href

        if area_filter and area_filter.lower() not in (location + " " + title).lower():
            continue

        if not (title or price or location):
            continue

        listings.append({
            "title": title,
            "price": price,
            "location": location,
            "area": area_size,
            "beds": beds,
            "baths": baths,
            "url": href,
        })

        if len(listings) >= limit:
            break

    return listings


def _format_markdown(listings, search_url: str) -> str:
    if not listings:
        return f"No listings found. Verify on Zameen directly: {search_url}"

    lines = ["| # | Title | Price | Location | Beds | Baths | Area | Link |",
             "|---|---|---|---|---|---|---|---|"]
    for i, lst in enumerate(listings, 1):
        lines.append(
            f"| {i} | {lst['title']} | {lst['price']} | {lst['location']} | "
            f"{lst['beds']} | {lst['baths']} | {lst['area']} | {lst['url']} |"
        )
    lines.append(f"\nSource: {search_url}")
    return "\n".join(lines)


class ZameenSearchTool(BaseTool):
    name: str = "zameen_property_search"
    description: str = (
        "Search live property listings on Zameen.com (Pakistan's largest real estate portal). "
        "Use this whenever the user asks for current properties for sale or rent in a Pakistani city. "
        "Required: city (e.g. 'peshawar'). Optional: purpose ('buy'/'rent'), property_type "
        "('homes'/'plots'/'commercial'), area (neighborhood substring filter), min_price, max_price (PKR), limit."
    )
    args_schema: Type[BaseModel] = ZameenSearchInput

    def _run(self, city: str, purpose: str = "buy", property_type: str = "homes",
             area: Optional[str] = None, min_price: Optional[int] = None,
             max_price: Optional[int] = None, limit: int = 10) -> str:
        url = _build_url(city, purpose, property_type, min_price, max_price)
        if not url:
            supported = ", ".join(sorted(CITY_IDS))
            return f"City '{city}' is not supported yet. Supported cities: {supported}."

        try:
            resp = requests.get(
                url,
                headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
                timeout=20,
            )
        except requests.RequestException as e:
            return f"Failed to reach Zameen.com ({e}). Try again or visit: {url}"

        if resp.status_code != 200:
            return f"Zameen returned HTTP {resp.status_code}. Visit: {url}"

        listings = _parse_listings(resp.text, area, limit)
        return _format_markdown(listings, url)


zameen_tool = ZameenSearchTool()
