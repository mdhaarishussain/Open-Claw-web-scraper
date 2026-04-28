import asyncio
from scrapling import AsyncFetcher

async def test_saffron():
    fetcher = AsyncFetcher()
    r = await fetcher.get("https://www.saffronart.com/auctions/PostWork.aspx?l=7209&eid=3491&lotno=2&n=2")
    text = r.get_all_text(separator='\n', strip=True)
    # Search for price indicators
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if 'Estimate' in line or 'Winning' in line or 'Rs' in line or '$' in line or 'Price' in line:
            print(f"Line {i}: {line}")

if __name__ == "__main__":
    asyncio.run(test_saffron())
