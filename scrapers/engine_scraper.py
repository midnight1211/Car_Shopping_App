from bs4 import BeautifulSoup
from typing import List, Dict, Any
from scrapers.base_scraper import BaseScraper
from pipeline.text_cleaner import TextCleaner

class VehicleScraper(BaseScraper):
    def __init__(self):
        super().__init__()

    def parse_listing_page(self, html_content: str) -> List[Dict[str, Any]]:
        """Extracts text structures out of raw DOM selector nodes safely."""
        soup = BeautifulSoup(html_content, 'html.parser')
        listings = []
        cards = soup.find_all('div', class_='vehicle-card')

        for card in cards:
            try:
                raw_vin = card.find('div', class_='vin-info')
                vin = TextCleaner.extract_vin(raw_vin.text if raw_vin else "")
                if not vin:
                    continue # Filter out anomalies lacking verifiable identifiers

                title_elem = card.find('h2', class_='vehicle-title')
                if not title_elem:
                    continue

                title_parts = title_elem.text.strip().split(' ', 2)
                year = int(title_parts[0])
                make = title_parts[1]
                model = title_parts[2] if len(title_parts) > 2 else "Unknown"

                price_elem = card.find('span', class_='primary-price')
                price = TextCleaner.extract_currency(price_elem.text if price_elem else "")

                mileage_elem = card.find('div', class_='mileage-amount')
                mileage = TextCleaner.extract_digits(mileage_elem.text if mileage_elem else "0")
                condition = 'used' if mileage > 100 else 'new'

                feature_tags = card.find_all('span', class_='feature-chip')
                features = [tag.text.strip() for tag in feature_tags]

                listings.append({
                    "vin": vin, "make": make, "model": model, "year": year,
                    "price": price, "mileage": mileage, "condition_type": condition,
                    "features": features
                })
            except (AttributeError, ValueError):
                continue

        return listings