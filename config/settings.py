import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'car_marketplace.db')

# Network connection tolerances
REQUEST_TIMEOUT = 10
MAX_RETRIES = 3