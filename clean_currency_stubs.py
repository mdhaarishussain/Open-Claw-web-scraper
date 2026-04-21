import pandas as pd
import sqlite3
import os

def clean_currency_data():
    csv_path = 'data/heartisans.csv'
    db_path = 'data/heartisans.db'
    
    us_domains = [
        'therealreal.com', '1stdibs.com', 'rebag.com', 'grailed.com',
        'novica.com', 'pamono.com', 'catawiki.com', 'chrono24.com'
    ]
    
    # Domains with known bad historic data that need re-scraping
    bad_price_domains = ['itokri.com']
    
    print("[1] Loading CSV...")
    df = pd.read_csv(csv_path)
    
    # Identify polluted rows: USD/EUR domains OR itokri rows with suspicious 10000 price
    mask_usd = df['source_url'].astype(str).apply(lambda x: any(d in x for d in us_domains))
    mask_itokri_bad = (
        df['source_url'].astype(str).apply(lambda x: any(d in x for d in bad_price_domains)) &
        (df['current_market_price_inr'] == 10000.0)
    )
    mask = mask_usd | mask_itokri_bad
    dirty_count = mask.sum()
    print(f"Found {dirty_count} heavily polluted rows from US luxury domains.")
    
    if dirty_count == 0:
        print("No dirty rows found. Exiting.")
        return

    # Keep only the rows that are clean
    clean_df = df[~mask]
    
    # Drop from SQLite DB 
    print(f"[2] Deleting '{dirty_count}' corrupted items from SQLite Database (so they can be rescraped)...")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get the actual URLs to delete
        urls_to_delete = df[mask]['source_url'].tolist()
        
        # Batch delete
        cursor.executemany(
            "DELETE FROM products WHERE source_url = ?", 
            [(url,) for url in urls_to_delete]
        )
        conn.commit()
        conn.close()
        print("Successfully purged database states.")
    else:
        print("No database found, skipped.")

    # Overwrite CSV
    print("[3] Overwriting CSV with clean items...")
    clean_df.to_csv(csv_path, index=False)
    
    print(f"Success! Deleted {dirty_count} corrupted items. Your orchestrator will seamlessly refetch and perfectly scale these the next time you run it.")

if __name__ == "__main__":
    clean_currency_data()
