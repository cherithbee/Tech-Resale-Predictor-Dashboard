import psycopg2
import random
from datetime import date, timedelta

# Database connection parameters (matching your docker-compose.yml)
DB_CONFIG = {
    'dbname': 'resale_predictor',
    'user': 'admin',
    'password': 'password123',
    'host': 'localhost',
    'port': '5432'
}

# Real-world condition modifiers (Poor condition drops price significantly)
CONDITIONS = ['Mint', 'Good', 'Fair', 'Poor']
CONDITION_MULTIPLIERS = {'Mint': 0.95, 'Good': 0.85, 'Fair': 0.70, 'Poor': 0.50}

# Local secondary market sources
DATA_SOURCES = ['Facebook Marketplace', 'Shopee', 'Kaidee', 'eBay']

def generate_data():
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("Connected to database successfully.")

        # Fetch our core devices
        cursor.execute("SELECT device_id, release_date, original_msrp FROM devices;")
        devices = cursor.fetchall()

        insert_query = """
            INSERT INTO historical_prices (device_id, date_recorded, condition, resale_price, data_source)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        records_to_insert = []
        today = date.today()

        # Generate 150 mock records per device
        for device in devices:
            device_id, release_date, msrp = device
            
            for _ in range(150):
                # Pick a random date between release date and today
                days_since_release = (today - release_date).days
                if days_since_release <= 0:
                    continue
                    
                random_days_passed = random.randint(1, days_since_release)
                record_date = release_date + timedelta(days=random_days_passed)
                
                # Base depreciation: tech loses roughly 2% value per month (very simplified)
                months_passed = random_days_passed / 30
                depreciation_factor = max(0.4, 1 - (months_passed * 0.02)) 
                
                # Apply condition modifier
                condition = random.choice(CONDITIONS)
                condition_mod = CONDITION_MULTIPLIERS[condition]
                
                # Add a little randomness (noise) to the price so the graph isn't too perfect
                noise = random.uniform(0.9, 1.1)
                
                # Calculate final mock price
                resale_price = round(float(msrp) * depreciation_factor * condition_mod * noise)
                data_source = random.choice(DATA_SOURCES)

                records_to_insert.append((device_id, record_date, condition, resale_price, data_source))

        # Execute the bulk insert
        cursor.executemany(insert_query, records_to_insert)
        conn.commit()
        
        print(f"Successfully inserted {len(records_to_insert)} historical price records!")

    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    generate_data()