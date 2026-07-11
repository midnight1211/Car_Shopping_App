import math
import time
import requests
from typing import List, Dict, Any, Optional
from scrapers.base_scraper import BaseScraper


class LocalDealerScraper(BaseScraper):
    """Finds local car dealers using OpenStreetMap data (Nominatim + Overpass API).

    No API key, account, or billing required. Two public OSM services are used:
      1. Nominatim - converts a ZIP code into latitude/longitude
      2. Overpass  - queries OSM's database for shop=car within a radius

    Both are shared public infrastructure, so this deliberately rate-limits
    itself and identifies the app honestly rather than spoofing a browser.
    """

    ZIPPOPOTAM_URL = "https://api.zippopotam.us/us"
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"

    # Names containing these (case-insensitive) are filtered out of results.
    # OpenStreetMap's shop=car tag isn't perfectly curated - parts stores,
    # repair shops, and the occasional flatly mistagged business (a call
    # center, a towing service) show up under it. This catches the common
    # patterns but isn't exhaustive; a business with no dealer-ish keyword
    # in its name that's simply mistagged in OSM (e.g. "Alorica") can't be
    # filtered this way since there's nothing to key off of.
    EXCLUDED_NAME_KEYWORDS = [
        "parts", "auto parts", "autoparts", "clinic", "tow", "towing",
        "accessories", "upholstery", "detailing", "car wash", "carwash",
        "junkyard", "junk yard", "salvage", "scrap"
    ]

    # overpass-api.de is the primary instance but is heavily loaded and now
    # 406-gates requests that don't look like a normal, identified client.
    # These mirrors are tried in order if the primary rejects the request.
    OVERPASS_ENDPOINTS = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    ]

    # A descriptive, honest User-Agent (with contact info) plus standard
    # Accept/Accept-Encoding headers - overpass-api.de started rejecting
    # requests with generic/missing versions of these with a 406 in 2026.
    OVERPASS_HEADERS = {
        "User-Agent": "car-shopping-app/1.0 (personal project; contact: your_email@example.com)",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
    }

    # Nominatim's usage policy requires a descriptive User-Agent that
    # identifies the application - NOT a spoofed browser UA like base_scraper
    # uses for regular scraping. See:
    # https://operations.osmfoundation.org/policies/nominatim/
    NOMINATIM_HEADERS = {
        "User-Agent": "car-shopping-app/1.0 (personal project; contact: your_email@example.com)"
    }

    def __init__(self):
        super().__init__()

    def geocode_zip(self, zip_code: str, country: str = "US") -> Optional[Dict[str, float]]:
        """Converts a ZIP/postal code into latitude/longitude.

        Tries Zippopotam.us first - a free, keyless, no-rate-limit-hassle
        service purpose-built for postal-code lookups. Falls back to
        Nominatim if that fails (e.g. non-US postal code, or a ZIP it
        doesn't have on file). Nominatim's public instance is prone to
        blocking requests with 403s even when the usage policy is followed
        correctly (shared/residential IPs sometimes get flagged from prior
        unrelated traffic), so it's kept as a fallback rather than primary.
        """
        zippopotam_result = self._geocode_via_zippopotam(zip_code)
        if zippopotam_result:
            return zippopotam_result

        print(f"Zippopotam lookup failed for ZIP {zip_code}, falling back to Nominatim...")
        return self._geocode_via_nominatim(zip_code, country)

    def _geocode_via_zippopotam(self, zip_code: str) -> Optional[Dict[str, float]]:
        try:
            response = self.session.get(f"{self.ZIPPOPOTAM_URL}/{zip_code}", timeout=10)
            if response.status_code != 200:
                return None

            data = response.json()
            places = data.get("places", [])
            if not places:
                return None

            return {"lat": float(places[0]["latitude"]), "lon": float(places[0]["longitude"])}
        except (requests.RequestException, ValueError, KeyError, IndexError):
            return None

    def _geocode_via_nominatim(self, zip_code: str, country: str) -> Optional[Dict[str, float]]:
        params = {
            "postalcode": zip_code,
            "country": country,
            "format": "json",
            "limit": 1
        }
        try:
            time.sleep(1)  # Nominatim's policy caps usage at ~1 request/second
            response = self.session.get(
                self.NOMINATIM_URL, params=params, headers=self.NOMINATIM_HEADERS, timeout=10
            )
            if response.status_code != 200:
                print(f"Nominatim geocoding failed with status {response.status_code} for ZIP {zip_code}")
                return None

            results = response.json()
            if not results:
                print(f"No geocoding results found for ZIP {zip_code}")
                return None

            return {"lat": float(results[0]["lat"]), "lon": float(results[0]["lon"])}
        except (requests.RequestException, ValueError, KeyError, IndexError) as e:
            print(f"Geocoding error for ZIP {zip_code}: {e}")
            return None

    def _reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """Looks up a human-readable address for a lat/lon via Nominatim's
        reverse endpoint, used as a fallback when an OSM node has no addr:*
        tags of its own."""
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "zoom": 18,
            "addressdetails": 1
        }
        try:
            time.sleep(1)  # Nominatim's policy caps usage at ~1 request/second
            response = self.session.get(
                self.NOMINATIM_REVERSE_URL, params=params, headers=self.NOMINATIM_HEADERS, timeout=10
            )
            if response.status_code != 200:
                return None

            result = response.json()
            display_name = result.get("display_name")
            return display_name if display_name else None
        except (requests.RequestException, ValueError, KeyError):
            return None

    @staticmethod
    def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Great-circle distance between two lat/lon points, in miles."""
        r = 3958.8  # Earth's radius in miles
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return 2 * r * math.asin(math.sqrt(a))

    @staticmethod
    def _build_overpass_query(lat: float, lon: float, radius_miles: float) -> str:
        radius_meters = int(radius_miles * 1609.34)
        return f"""
        [out:json][timeout:25];
        (
          node["shop"="car"](around:{radius_meters},{lat},{lon});
          way["shop"="car"](around:{radius_meters},{lat},{lon});
        );
        out center tags;
        """

    def _query_overpass(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Tries each Overpass endpoint in order, using proper headers to
        avoid the primary server's bot-filter (see OVERPASS_HEADERS comment).
        Returns the parsed 'elements' list, or None if every endpoint fails.
        """
        for endpoint in self.OVERPASS_ENDPOINTS:
            try:
                time.sleep(1)  # be polite to shared public infrastructure
                response = self.session.post(
                    endpoint, data={"data": query}, headers=self.OVERPASS_HEADERS, timeout=30
                )
            except requests.RequestException as e:
                print(f"Overpass request to {endpoint} failed: {e}")
                continue

            if response.status_code != 200:
                print(f"Overpass endpoint {endpoint} returned status {response.status_code}, trying next mirror...")
                continue

            try:
                return response.json().get("elements", [])
            except ValueError:
                print(f"Failed to parse Overpass JSON response from {endpoint}, trying next mirror...")
                continue

        print("All Overpass endpoints failed.")
        return None

    def discover_local_dealers(
        self, zip_code: str, radius_miles: int = 25, fill_missing_addresses: bool = True
    ) -> List[Dict[str, Any]]:
        """Finds car dealers within radius_miles of zip_code using OpenStreetMap data.

        fill_missing_addresses: when True (default), nodes lacking addr:*
        tags get a reverse-geocoding lookup instead of "Address unavailable".
        This adds ~1 second per missing address (Nominatim's rate limit), so
        for a large radius with lots of results this can add real runtime -
        set to False to skip it and get instant "Address unavailable" instead.
        """
        origin = self.geocode_zip(zip_code)
        if not origin:
            return []

        query = self._build_overpass_query(origin["lat"], origin["lon"], radius_miles)
        elements = self._query_overpass(query)
        if elements is None:
            return []

        dealers = []
        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name")
            if not name:
                continue

            if any(keyword in name.lower() for keyword in self.EXCLUDED_NAME_KEYWORDS):
                continue

            # Nodes carry lat/lon directly; ways return a computed "center" instead
            if "lat" in el and "lon" in el:
                el_lat, el_lon = el["lat"], el["lon"]
            elif "center" in el:
                el_lat, el_lon = el["center"]["lat"], el["center"]["lon"]
            else:
                continue

            distance = round(self._haversine_miles(origin["lat"], origin["lon"], el_lat, el_lon), 1)

            address_parts = [
                tags.get("addr:housenumber", ""),
                tags.get("addr:street", ""),
                tags.get("addr:city", ""),
                tags.get("addr:state", ""),
                tags.get("addr:postcode", "")
            ]
            address = " ".join(p for p in address_parts if p).strip()

            if not address and fill_missing_addresses:
                reverse_address = self._reverse_geocode(el_lat, el_lon)
                address = reverse_address or ""

            dealers.append({
                "name": name,
                "distance": f"{distance} mi",
                "website": tags.get("website") or tags.get("contact:website"),
                "local_zip": zip_code,
                "address": address or "Address unavailable"
            })

        dealers.sort(key=lambda d: float(d["distance"].split()[0]))
        return dealers