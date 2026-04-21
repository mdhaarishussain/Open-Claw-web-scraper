import asyncio
from scrapling.fetchers import AsyncStealthySession

async def main():
    async with AsyncStealthySession() as s:
        r = await s.fetch('https://www.1stdibs.com/jewelry/watches/')
        print(f"Status: {r.status}")
        print(f"Text len: {len(r.text)}")
        prices = r.css('[data-cy="price"]')
        print(f"data-cy prices found: {len(prices)}")
        html_prices = r.css('.price-amount')
        print(f"price-amount found: {len(html_prices)}")

asyncio.run(main())
