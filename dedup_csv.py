import csv
from pathlib import Path
import re

def dedup_csv():
    csv_path = Path('data/heartisans.csv')
    if not csv_path.exists():
        return

    # Read all rows
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # Dedup logic
    seen_ids = set()
    cleaned_rows = []
    
    for row in rows:
        url = row.get('source_url', '')
        
        # Determine the unique identifier for this row
        match = re.search(r'(/item/\d+)', url)
        if match:
            uid = match.group(1) # Base LiveAuctioneers ID
        else:
            uid = url # Exact URL for Bonhams/others
            
        if uid in seen_ids:
            continue
        seen_ids.add(uid)
        
        cleaned_rows.append(row)

    # Write back
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned_rows)
        
    print(f"Removed {len(rows) - len(cleaned_rows)} duplicate rows from CSV.")

if __name__ == "__main__":
    dedup_csv()
