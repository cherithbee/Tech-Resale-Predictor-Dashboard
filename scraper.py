"""
Web Scraper for Tech Resale Prices using Playwright

INSTALLATION INSTRUCTIONS:
1. Install Playwright: pip install playwright
2. Install browser binaries: playwright install
3. Ensure psycopg2 is installed: pip install psycopg2-binary
4. Run this script: python scraper.py

This script scrapes eBay for secondhand listings of our tracked devices
and inserts the data into the PostgreSQL database.
"""

from playwright.sync_api import sync_playwright
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date
import re
import time

# Database connection parameters (matching docker-compose.yml and main.py)
DB_CONFIG = {
    'dbname': 'resale_predictor',
    'user': 'admin',
    'password': 'password123',
    'host': 'localhost',
    'port': '5432'
}

# Device search mappings: device name -> device_id
DEVICE_MAPPING = {
    'Galaxy Tab S8 Ultra': 1,
    'Hero 12 Black': 2,
    'Osmo Action 6': 3,
}

# Search queries for each device
SEARCH_QUERIES = [
    'Galaxy Tab S8 Ultra',
    'GoPro Hero 12',
    'DJI Osmo Action 6',
]

# USD to Thai Baht conversion rate
USD_TO_THB = 36.0


def get_db_connection():
    """Establish and return a database connection."""
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)


def clean_price(price_str):
    """
    Extract numeric price from string and convert USD to THB.
    Example: '$299.99' -> 10796.64
    """
    if not price_str:
        return None
    
    # Remove currency symbols and commas
    price_clean = re.sub(r'[$,]', '', price_str.strip())
    
    try:
        # Extract first numeric value (handles cases like "$299.99 or best offer")
        match = re.search(r'(\d+\.?\d*)', price_clean)
        if match:
            usd_price = float(match.group(1))
            # Convert to Thai Baht
            thb_price = usd_price * USD_TO_THB
            return round(thb_price, 2)
    except (ValueError, AttributeError):
        pass
    
    return None


def extract_condition(title_and_listing):
    """
    Infer product condition from listing text.
    Returns one of: 'Mint', 'Good', 'Fair', 'Poor'
    """
    text_lower = (title_and_listing or '').lower()
    
    # Check for condition keywords in order of preference
    if any(word in text_lower for word in ['mint', 'like new', 'unopened', 'sealed']):
        return 'Mint'
    elif any(word in text_lower for word in ['very good', 'excellent', 'perfect', 'no scratches']):
        return 'Good'
    elif any(word in text_lower for word in ['good', 'normal wear', 'light wear', 'used']):
        return 'Good'
    elif any(word in text_lower for word in ['fair', 'some damage', 'worn', 'cosmetic damage']):
        return 'Fair'
    elif any(word in text_lower for word in ['poor', 'parts', 'not working', 'broken']):
        return 'Poor'
    
    # Default to 'Good' if uncertain
    return 'Good'


def get_device_id_from_listing(title, device_query):
    """
    Determine which device_id this listing belongs to based on the search query.
    Returns device_id or None if no match found.
    """
    # Try to match the search query keywords to our device mapping
    for device_name, device_id in DEVICE_MAPPING.items():
        if device_name.lower() in title.lower():
            return device_id
    
    # If exact match fails, use the search query to infer
    query_lower = device_query.lower()
    if 'galaxy tab s8 ultra' in query_lower:
        return 1
    elif 'hero 12' in query_lower:
        return 2
    elif 'osmo action 6' in query_lower:
        return 3
    
    return None


def scrape_ebay_search(search_query):
    """
    Scrape eBay search results for a given query.
    Returns list of dicts with: title, condition, price_thb, device_id
    """
    results = []
    
    with sync_playwright() as p:
        # Launch browser (headless=False for debugging, set to True for production)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Navigate to eBay search
            search_url = f"https://www.ebay.com/sch/i.html?_nkw={search_query.replace(' ', '+')}&_sacat=0"
            print(f"Navigating to: {search_url}")
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait a moment for JavaScript to render
            time.sleep(2)
            
            # Extract listings
            # Note: eBay's structure may vary; adjust selectors if needed
            listing_elements = page.locator('div[data-component-type="s-search-result"]').all()
            
            print(f"Found {len(listing_elements)} listings for '{search_query}'")
            
            for listing in listing_elements[:10]:  # Limit to first 10 results per search
                try:
                    # Extract title
                    title_elem = listing.locator('span[role="heading"]')
                    title = title_elem.inner_text() if title_elem.count() > 0 else None
                    
                    if not title:
                        continue
                    
                    # Extract price
                    price_elem = listing.locator('span.s-price')
                    price_str = price_elem.inner_text() if price_elem.count() > 0 else None
                    
                    if not price_str:
                        continue
                    
                    # Clean price and convert to THB
                    price_thb = clean_price(price_str)
                    if not price_thb:
                        continue
                    
                    # Extract condition from title/listing text
                    condition = extract_condition(title)
                    
                    # Determine device_id
                    device_id = get_device_id_from_listing(title, search_query)
                    if not device_id:
                        print(f"  Skipping '{title}' - could not match to device")
                        continue
                    
                    results.append({
                        'title': title,
                        'condition': condition,
                        'price_thb': price_thb,
                        'price_usd': price_thb / USD_TO_THB,
                        'device_id': device_id,
                        'data_source': 'eBay'
                    })
                    
                    print(f"  ✓ {title[:60]}... | Condition: {condition} | Price: ฿{price_thb}")
                
                except Exception as e:
                    print(f"  Error extracting listing: {e}")
                    continue
        
        finally:
            browser.close()
    
    return results


def insert_into_database(records):
    """
    Insert scraped records into the historical_prices table.
    """
    if not records:
        print("No records to insert.")
        return 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    inserted_count = 0
    
    try:
        for record in records:
            cursor.execute(
                """
                INSERT INTO historical_prices 
                (device_id, date_recorded, condition, resale_price, data_source)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    record['device_id'],
                    date.today(),
                    record['condition'],
                    record['price_thb'],
                    record['data_source']
                )
            )
            inserted_count += 1
        
        conn.commit()
        print(f"\n✓ Successfully inserted {inserted_count} records into historical_prices table")
    
    except Exception as e:
        conn.rollback()
        print(f"Error inserting records: {e}")
    
    finally:
        cursor.close()
        conn.close()
    
    return inserted_count


def main():
    """Main execution flow."""
    print("=" * 70)
    print("Tech Resale Price Scraper - eBay Edition")
    print("=" * 70)
    print(f"Conversion rate: 1 USD = {USD_TO_THB} THB\n")
    
    all_results = []
    
    # Scrape each device
    for query in SEARCH_QUERIES:
        print(f"\nScraping: '{query}'")
        print("-" * 70)
        try:
            results = scrape_ebay_search(query)
            all_results.extend(results)
            time.sleep(2)  # Be respectful to the server
        except Exception as e:
            print(f"Error scraping '{query}': {e}")
    
    # Insert into database
    print("\n" + "=" * 70)
    print("Inserting into Database")
    print("=" * 70)
    
    if all_results:
        inserted = insert_into_database(all_results)
        print(f"\nTotal records processed: {len(all_results)}")
        print(f"Total records inserted: {inserted}")
    else:
        print("No results were scraped. Check the selectors and eBay page structure.")
    
    print("\n" + "=" * 70)
    print("Scraping complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
