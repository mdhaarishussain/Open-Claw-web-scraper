import asyncio, re, json
from scrapling import AsyncFetcher

async def test():
    fetcher = AsyncFetcher()
    
    # Full Bonhams auction list (not just upcoming - past results too)
    print("=== BONHAMS PAST RESULTS ===")
    for url in [
        "https://www.bonhams.com/auctions/jewelry/",
        "https://www.bonhams.com/auctions/watches/", 
        "https://www.bonhams.com/auctions/art/",
        "https://www.bonhams.com/auctions/furniture/",
        "https://www.bonhams.com/department/jewelry/",
        "https://www.bonhams.com/department/fine-art/",
    ]:
        r = await fetcher.get(url)
        links = r.css('a[href]')
        lot_links = [l.attrib.get('href','') for l in links if '/lot/' in l.attrib.get('href','')]
        print(f"  {url.split('/')[-2]}: status=ok, lot_links={len(lot_links)}")
    
    # Test more accessible Bonhams auction pages
    print("\n=== BONHAMS SPECIFIC AUCTIONS ===")
    test_auctions = [
        "/auction/32125/weekly-jewelry/",
        "/auction/32417/old-master-and-19th-century-paintings/",
        "/auction/32166/hermes-from-the-vault-ii/",
        "/auction/31874/new-york-watches/",
        "/auction/32188/the-marine-sale/",
    ]
    for path in test_auctions:
        r = await fetcher.get("https://www.bonhams.com" + path)
        links = r.css('a[href]')
        lot_links = [l.attrib.get('href','') for l in links if '/lot/' in l.attrib.get('href','')]
        print(f"  {path.split('/')[-2]}: {len(lot_links)} lot links")
    
    # Test Saffronart - can we reach lot detail pages?
    print("\n=== SAFFRONART postwork pages ===")
    r2 = await fetcher.get("https://www.saffronart.com/auctions/PostCatalog.aspx?eid=3491")
    # Find actual lot/item links
    links2 = r2.css('a[href]')
    item_links = [l.attrib.get('href','') for l in links2 if 'postwork' in l.attrib.get('href','').lower() or 'item' in l.attrib.get('href','').lower()]
    print(f"Item links: {len(item_links)}")
    print(f"Sample: {item_links[:5]}")
    # Try broader search
    all_hrefs = [l.attrib.get('href','') for l in links2]
    art_links = [h for h in all_hrefs if h and not h.startswith('javascript') and not h.startswith('#') and 'saffronart' in h.lower()]
    print(f"Full saffronart links: {art_links[:10]}")

asyncio.run(test())
