import asyncio
from scrapling.fetchers import AsyncFetcher

async def test_bonhams_calendar():
    fetcher = AsyncFetcher()
    url = "https://www.bonhams.com/auctions/"
    try:
        response = await fetcher.get(url)
        print(f"Status Code: {response.status}")
        
        # Test basic title block and look for auction links
        title = response.css('title')[0].text if response.css('title') else 'No title'
        print(f"Title: {title}")
        
        links = response.css('a[href*="/auction/"]')
        auction_links = set([link.attrib.get('href', '') for link in links if '/lot/' not in link.attrib.get('href', '')])
        
        print("\nFound Auction Links:")
        for link in list(auction_links)[:10]:
            print(link)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_bonhams_calendar())
