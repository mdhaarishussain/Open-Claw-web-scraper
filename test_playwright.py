import asyncio
from scrapling import StealthyFetcher

async def test():
    fetcher = StealthyFetcher()
    response = await fetcher.fetch('https://www.novica.com/p/wood-figurine-depicting-a-grey-elephant-with/477519/', network_idle=True)
    nodes = response.css('.displayprice')
    print('ALL .displayprice:')
    for i in range(min(10, len(nodes))):
        print(f'{i}: "{nodes[i].text.strip() if nodes[i].text else ""}"')
        
    print('H1:', response.css('h1')[0].text if response.css('h1') else 'none')

asyncio.run(test())
