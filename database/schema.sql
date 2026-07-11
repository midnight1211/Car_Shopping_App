--- Core vehicle specifications table
CREATE TABLE vehicles (
    vin VARCHAR(17) PRIMARY KEY,
    year INT NOT NULL,
    make VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    mileage INT DEFAULT 0,
    condition_type VARCHAR(4) CHECK (condition_type IN ('new', 'used')),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

--- Variable child records for arbitrary features/packages
CREATE TABLE IF NOT EXISTS vehicle_features (
    feature_id INTEGER PRIMARY KEY AUTOINCREMENT,
    vin VARCHAR(17),
    feature_name VARCHAR(100) NOT NULL,
    FOREIGN KEY (vin) REFERENCES vehicles(vin) ON DELETE CASCADE,
    UNIQUE(vin, feature_name)
);

--- Local dealerships discovered via OpenStreetMap
CREATE TABLE IF NOT EXISTS dealers (
    dealer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    address VARCHAR(300),
    distance VARCHAR(20),
    website VARCHAR(300),
    search_zip VARCHAR(10),
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, address)
);

--- Heavy read optimization indexes
CREATE INDEX IF NOT EXISTS idx_vehicle_search ON vehicles (make, model, price);
CREATE INDEX IF NOT EXISTS idx_dealer_zip ON dealers (search_zip);