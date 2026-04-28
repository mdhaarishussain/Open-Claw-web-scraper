import asyncio
from scrapling.fetchers import AsyncFetcher

async def test_liveauctioneers():
    url = "https://www.liveauctioneers.com/c/art/1/"
    fetcher = AsyncFetcher()
    response = await fetcher.get(url)
    print(f"Status Code: {response.status}")
    if response.status != 200:
        print("Blocked or error. Might need stealth.")
        return
        
    title = response.css('title')[0].text if response.css('title') else 'No title'
    print(f"Title: {title}")
    
    # Try generic link finding
    print("\nSample Links:")
    all_links = response.css('a')
    product_links = set()
    next_links = set()
    
    for a in all_links:
        href = a.attrib.get('href', '')
        if '/item/' in href or '/lot/' in href:
            product_links.add(href)
        if 'page=' in href or 'next' in href.lower() or 'next' in (a.text or '').lower():
            next_links.add(href)
            
    print(f"\nFound {len(product_links)} potential product links")
    for link in list(product_links)[:5]:
        print(link)
        
    print(f"\nFound potential next page links:")
    for a in all_links:
        href = a.attrib.get('href', '')
        if 'page=' in href or 'next' in href.lower() or 'next' in (a.text or '').lower():
            print(f"HREF: {href} | TEXT: {a.text} | CLASS: {a.attrib.get('class')} | REL: {a.attrib.get('rel')}")

if __name__ == "__main__":
    asyncio.run(test_liveauctioneers())
