# Car Marketplace Scraper

A small scraping + storage pipeline for vehicle listings and local dealer directories. It fetches HTML with `requests` + rotating user agents, parses it with `BeautifulSoup`, cleans the extracted text into typed fields, and persists everything into a local SQLite database.

## Project structure

```
.
├── main.py                     # Entry point — runs local dealer discovery
├── requirements.txt
├── config/
│   └── user_agents.py          # Pool of user agents rotated per request
├── scrapers/
│   ├── base_scraper.py         # Shared HTTP fetching (retries, backoff, headers)
│   ├── engine_scraper.py       # Parses vehicle listing cards into structured data
│   └── local_discovery_scraper.py  # Finds nearby dealerships via YellowPages
├── pipeline/
│   ├── text_cleaner.py         # VIN / price / mileage / engine text extraction
│   └── db_pipeline.py          # Batch upserts vehicles + features into SQLite
├── database/
│   ├── connection.py           # SQLite transaction context manager
│   └── schema.sql              # Table definitions
└── settings.py                 # Paths and network tolerances
```

> Note: the folder layout above (`config/`, `scrapers/`, `pipeline/`, `database/`) is what the import statements in the code expect (e.g. `from scrapers.base_scraper import BaseScraper`). Place each file in the matching folder.

## Setup

```bash
pip install -r requirements.txt
```

Requires Python 3.9+ (uses `X | None`-style typing is avoided, but f-strings and `contextlib.contextmanager` are used throughout).

## Usage

1. Initialize the database:

   ```bash
   mkdir -p database
   sqlite3 database/car_marketplace.db < schema.sql
   ```

2. Run dealer discovery:

   ```bash
   python main.py
   ```

   This scans YellowPages for auto dealers near a target ZIP code and radius (both configurable at the top of `main.py`), and prints out each dealer found.

3. To persist scraped vehicle listings, feed `VehicleScraper.parse_listing_page()` output into `DataPipeline.batch_insert_vehicles()`.

## Local dealer discovery: OpenStreetMap instead of scraping

`local_discovery_scraper.py` no longer scrapes YellowPages. YellowPages runs active bot-detection (rate limiting, fingerprinting, CAPTCHAs) that returned a hard 403 to plain `requests` traffic regardless of user-agent rotation, and scraping around that kind of protection isn't something this project pursues.

Instead, `LocalDealerScraper` now queries **OpenStreetMap**, using two free public services that require no API key, account, or billing:

1. **Zippopotam.us** (`geocode_zip`) — converts the target ZIP code into latitude/longitude. This is tried first since it's purpose-built for ZIP lookups with no rate-limit hassle.
2. **Nominatim** — used as a ZIP fallback if Zippopotam doesn't have a given ZIP on file, and also for reverse-geocoding (see below). Nominatim's public instance is prone to 403s even for well-behaved requests (it blocks some shared/residential IP ranges outright), so it's not relied on as the primary path.
3. **Overpass API** (`discover_local_dealers`) — queries OSM's database for `shop=car` nodes/ways within the given radius, then computes distance from the ZIP's coordinates with a haversine calculation. The code tries the primary `overpass-api.de` instance first, then falls back to two mirrors (`overpass.kumi.systems`, `overpass.private.coffee`) if it's rejected — the primary has been overloaded by unthrottled scraper/AI traffic and now 406s requests that don't send a proper `User-Agent`/`Accept`/`Accept-Encoding`, which this code sets explicitly.

### Missing addresses

Not every OSM dealer node has structured `addr:*` tags — OSM's `shop=car` tagging is more complete than its address tagging in a lot of areas. By default, `discover_local_dealers()` reverse-geocodes any dealer missing an address via Nominatim's `/reverse` endpoint. This respects the same 1-request/second rate limit as ZIP geocoding, so a search radius with many untagged dealers can add real runtime (roughly 1 extra second per missing address). Pass `fill_missing_addresses=False` to skip this and get instant "Address unavailable" placeholders instead.

### Noise filtering

`shop=car` in OpenStreetMap isn't perfectly curated — parts stores, repair shops, and the occasional flatly mistagged business show up in results. `EXCLUDED_NAME_KEYWORDS` filters out common false positives by name (parts, tow, detailing, salvage, etc.). This is a heuristic, not a guarantee — a business with no dealer-ish keyword in its name that's simply mistagged in OSM (e.g. a call center incorrectly tagged as `shop=car`) can't be caught this way, since there's nothing in the name to filter on. Occasional manual review of results is still worthwhile.

A few things to know:

- **Coverage** depends on how well local businesses are mapped in OpenStreetMap. Dense/suburban US areas are usually well covered, but it won't be as exhaustive as a commercial business index.
- **Rate limits**: both services are shared public infrastructure. The code already waits ~1 second between requests to stay within Nominatim's usage policy — don't remove those delays or hammer the endpoints in a loop.
- **User-Agent**: Nominatim's usage policy asks for an honest, identifying User-Agent (app name + contact info) rather than a spoofed browser one — update the placeholder email in `NOMINATIM_HEADERS` in `local_discovery_scraper.py` to your own before running this for real.
- **Attribution**: if dealer data from this pipeline is ever shown publicly (not just used internally), OpenStreetMap's ODbL license requires crediting "© OpenStreetMap contributors."
- `main.py` no longer needs an aggregator URL — `LocalDealerScraper()` takes no constructor arguments now.

## Other bugs fixed in this pass

- **`base_scraper.py`**: `fetch_url()` only logged status codes 200 and 429; any other response (403 Forbidden, 503, a bot-check redirect, etc.) failed silently and just retried with no explanation. It now logs unexpected status codes so failures are visible instead of showing up as a mysterious "0 results."
- **`schema.sql`**: the `vehicle_features` foreign key referenced a table named `vehicle` (singular), but the actual table is `vehicles`. This would raise a "no such table" error the first time `PRAGMA foreign_keys = ON` was enforced during an insert.

## Database schema

- `vehicles` — one row per VIN, with year/make/model/price/mileage/condition.
- `vehicle_features` — many-to-many feature tags per VIN (e.g. "Sunroof", "AWD"), cascade-deleted when the parent vehicle is removed.
- Indexed on `(make, model, price)` for fast catalog-style filtering.