-- Table to store the core tech devices
CREATE TABLE devices (
    device_id SERIAL PRIMARY KEY,
    brand VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    release_date DATE,
    original_msrp DECIMAL(10, 2) NOT NULL
);

-- Table to track market value over time
CREATE TABLE historical_prices (
    record_id SERIAL PRIMARY KEY,
    device_id INT REFERENCES devices(device_id),
    date_recorded DATE NOT NULL DEFAULT CURRENT_DATE,
    condition VARCHAR(20) CHECK (condition IN ('Mint', 'Good', 'Fair', 'Poor')),
    resale_price DECIMAL(10, 2) NOT NULL,
    data_source VARCHAR(50) -- e.g., 'Facebook Marketplace', 'eBay'
);

-- Seed data for our initial tracking
INSERT INTO devices (brand, model, category, release_date, original_msrp) VALUES
('Samsung', 'Galaxy Tab S8 Ultra', 'Tablet', '2022-02-25', 38900),
('GoPro', 'Hero 12 Black', 'Action Camera', '2023-09-13', 14900),
('DJI', 'Osmo Action 6', 'Action Camera', '2025-08-01', 15500);

-- Insert a few mock historical records to test
INSERT INTO historical_prices (device_id, date_recorded, condition, resale_price, data_source) VALUES
(1, '2025-10-01', 'Good', 650.00, 'Facebook Marketplace'),
(2, '2025-10-15', 'Mint', 280.00, 'eBay'),
(3, '2025-11-01', 'Mint', 400.00, 'eBay');