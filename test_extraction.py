import asyncio
from src.orchestrator.fast_pipeline import NativeFastPipeline
from src.extraction.llm_extractor import LLMExtractor

async def test_extraction():
    extractor = LLMExtractor()
    from scrapling import AsyncFetcher
    fetcher = AsyncFetcher()
    
    urls = [
        "https://www.bonhams.com/auction/32125/lot/1/a-late-19th-century-diamond-target-brooch/",
        "https://www.saffronart.com/auctions/PostWork.aspx?l=7208&eid=3491&lotno=1&n=1"
    ]
    
    for url in urls:
        print(f"\n--- Testing: {url} ---")
        try:
            r = await fetcher.get(url)
            body = r.body.decode('utf-8', errors='ignore') if isinstance(r.body, bytes) else str(r.body)
            # basic css extraction simulating the pipeline
            extracted_parts = []
            
            # Extract basic text content to see what LLM gets
            text = r.get_all_text(separator=' ', strip=True)[:5000]
            print(f"RAW TEXT PREVIEW: {text[:200]}")
            
            # Let's extract
            product_data = extractor.extract(f"SOURCE URL: {url}\n\nPAGE TEXT:\n{text}", url)
            print(f"EXTRACTED DATA:\n{product_data.model_dump_json(indent=2)}")
            
        except Exception as e:
            print(f"TEST FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_extraction())
