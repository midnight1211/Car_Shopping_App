from scrapers.local_discovery_scraper import LocalDealerScraper
from pipeline.db_pipeline import DataPipeline

def run_local_discovery():
    db_path = "database/car_marketplace.db"

    # Enter your target geographic center
    target_zip = "44514"
    search_radius = 25

    discovery_engine = LocalDealerScraper()
    pipeline = DataPipeline(db_path)

    print(f"Scanning for auto retailers within {search_radius} miles of {target_zip}...")

    local_dealers = discovery_engine.discover_local_dealers(target_zip, search_radius)

    print(f"Found {len(local_dealers)} local retailers.")

    for dealer in local_dealers:
        print(f"Discovered: {dealer['name']} ({dealer['distance']}) - {dealer['address']}")

    if local_dealers:
        pipeline.save_dealers(local_dealers)
        print(f"Saved {len(local_dealers)} dealers to {db_path}")

if __name__ == "__main__":
    run_local_discovery()