import random
import time
import requests
from config.user_agents import USER_AGENTS
from typing import Optional

class BaseScraper:
    def __init__(self):
        self.session = requests.Session()

    def get_headers(self) -> dict:
        """Generates dynamic headers per request to avoid deterministic patterns."""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }

    def fetch_url(self, url: str, retries: int = 3) -> Optional[str]:
        """Executes requests with exponential backoff and randomized intervals."""
        for attempt in range(retries):
            try:
                # Add a polite delay (1 to 3.5 seconds) to avoid trigger-happy rate limits
                time.sleep(random.uniform(1, 3.5))

                response = self.session.get(url, headers=self.get_headers(), timeout=10)
                if response.status_code == 200:
                    return response.text
                elif response.status_code == 429:
                    print(f"Rate limited (429). Backing off. Attempt {attempt + 1}/{retries}")
                    time.sleep(5 * (attempt + 1))
                else:
                    # BUG FIX: previously any non-200/429 status (403 Forbidden,
                    # 503, bot-check redirects, etc.) was silently swallowed,
                    # so a blocked request just quietly returned None with no
                    # indication of why. Sites like YellowPages commonly return
                    # 403 to non-browser clients.
                    print(f"Unexpected status {response.status_code} on {url}. Attempt {attempt + 1}/{retries}")
            except requests.RequestException as e:
                print(f"Network error on {url}: {e}. Retrying...")
                time.sleep(2)
        return None