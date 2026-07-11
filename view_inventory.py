"""Quick utility to print out everything currently saved in the database.
Run from the project root: python view_inventory.py
"""
import sqlite3

DB_PATH = "database/car_marketplace.db"


def print_table(cursor, table_name: str):
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    col_names = [description[0] for description in cursor.description]

    print(f"\n=== {table_name} ({len(rows)} rows) ===")
    if not rows:
        print("(empty)")
        return

    print(" | ".join(col_names))
    for row in rows:
        print(" | ".join(str(value) for value in row))


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print_table(cursor, "dealers")
    print_table(cursor, "vehicles")
    print_table(cursor, "vehicle_features")

    conn.close()