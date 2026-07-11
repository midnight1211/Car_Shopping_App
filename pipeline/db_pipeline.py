from typing import List, Dict, Any
from database.connection import DatabaseConnection

class DataPipeline:
    def __init__(self, db_path: str):
        self.db = DatabaseConnection(db_path)

    def save_dealers(self, dealers_data: List[Dict[str, Any]]):
        """Saves discovered dealers to the database, skipping exact duplicates
        (same name + address) that may show up across repeated searches."""
        dealer_insert = """
            INSERT OR IGNORE INTO dealers (name, address, distance, website, search_zip)
            VALUES (?, ?, ?, ?, ?);
        """

        dealer_records = [
            (d['name'], d.get('address'), d.get('distance'), d.get('website'), d.get('local_zip'))
            for d in dealers_data
        ]

        with self.db.transaction() as cursor:
            cursor.executemany(dealer_insert, dealer_records)

    def batch_insert_vehicles(self, vehicles_data: List[Dict[str, Any]]):
        """Performs atomic batch transactions to minimize disk I/O bottlenecks."""
        vehicle_upsert = """
            INSERT INTO vehicles (vin, make, model, year, price, mileage, condition_type, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(vin) DO UPDATE SET
                price = excluded.price,
                mileage = excluded.mileage,
                last_updated = CURRENT_TIMESTAMP;
        """

        feature_insert = """
            INSERT OR IGNORE INTO vehicle_features (vin, feature_name)
            VALUES (?, ?);
        """

        vehicle_records = [
            (v['vin'], v['make'], v['model'], v['year'], v['price'], v['mileage'], v['condition_type'])
            for v in vehicles_data
        ]

        feature_records = [
            (v['vin'], feature)
            for v in vehicles_data for feature in v['features']
        ]

        with self.db.transaction() as cursor:
            cursor.executemany(vehicle_upsert, vehicle_records)
            cursor.executemany(feature_insert, feature_records)