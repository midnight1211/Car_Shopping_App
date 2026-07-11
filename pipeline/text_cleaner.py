import re
from typing import Optional

class TextCleaner:
    @staticmethod
    def extract_vin(text: str) -> Optional[str]:
        """Validates and extracts a standard 17-character alphanumeric VIN."""
        match = re.search(r'\b[A-HJ-NPR-Z0-9]{17}\b', text.upper())
        return match.group(0) if match else None

    @staticmethod
    def extract_digits(text: str) -> int:
        """Removes non-numeric characters to isolate integers (e.g., mileage)."""
        cleaned = re.sub(r'[^\d]', '', text)
        return int(cleaned) if cleaned else 0

    @staticmethod
    def extract_currency(text: str) -> float:
        """Parses price strings into floating-point decimals."""
        cleaned = re.sub(r'[^\d.]', '', text)
        return float(cleaned) if cleaned else 0.0

    @staticmethod
    def parse_engine_displacement(text: str) -> Optional[str]:
        """Extracts engine displacement notations (e.g., '2.0L', '3.5 Liters')."""
        match = re.search(r'\b(\d\.\d)\s*(?:L|Liter|Liters)\b', text, re.IGNORECASE)
        return f"{match.group(1)}L" if match else None