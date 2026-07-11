import sqlite3
from contextlib import contextmanager

class DatabaseConnection:
    def __init__(self, dp_path: str):
        self.db_path = dp_path

    @contextmanager
    def transaction(self):
        """Context manager to auto-commit modifications or rollback on failure."""
        conn = sqlite3.connect(self.db_path)
        # Enable foreign key validation checks
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()