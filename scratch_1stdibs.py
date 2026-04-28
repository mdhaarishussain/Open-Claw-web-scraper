import asyncio
from scrapling.fetchers import AsyncStealthySession

async def main():
    async with AsyncStealthySession(headless=True) as session:
        response = await session.fetch("https://www.1stdibs.com/furniture/")
        print("STATUS:", response.status)
        
        # Test finding next page links
        for a in response.css('a'):
            href = a.attrib.get('href', '')
            text = a.text_content().strip() if hasattr(a, 'text_content') else a.text
            lower_href = href.lower()
            lower_text = text.lower() if text else ''
            if 'next' in lower_href or 'next' in lower_text or 'page=' in lower_href or 'page' in a.attrib.get('class', '').lower() or 'pagination' in a.attrib.get('class', '').lower() or 'pagination' in a.attrib.get('data-tn', '').lower():
                print(f"LINK: {href} | TEXT: {text} | CLASS: {a.attrib.get('class')} | DATA-TN: {a.attrib.get('data-tn')}")

if __name__ == "__main__":
    asyncio.run(main())
