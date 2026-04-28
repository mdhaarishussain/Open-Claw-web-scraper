import logging
from typing import List, Dict
from scrapling.fetchers import AsyncFetcher

logger = logging.getLogger(__name__)

async def discover_bonhams_auctions() -> List[Dict]:
    """
    Crawls the Bonhams upcoming auctions page and returns dynamic seed configs
    to be injected into the scraper's initialization payload.
    """
    logger.info("Initializing Bonhams Auto-Discovery Worker...")
    
    url = "https://www.bonhams.com/auctions/upcoming/"
    new_seeds = []
    
    try:
        fetcher = AsyncFetcher()
        response = await fetcher.get(url)
        
        # Extract all upcoming auction paths
        links = response.css('a[href*="/auction/"]')
        auction_paths = set()
        
        for link in links:
            href = link.attrib.get('href', '')
            if href.startswith('/auction/') and '/lot/' not in href:
                auction_paths.add(href)
                
        for path in auction_paths:
            # path is typically: /auction/32371/space-movement-and-light-a-british-constructivist-collection/
            parts = path.strip('/').split('/')
            if len(parts) >= 2:
                auction_id = parts[1]
                
                # Create the dynamic dictionary corresponding to our yaml config schema
                seed_blob = {
                    "name": f"bonhams_auto_{auction_id}",
                    "base_url": f"https://www.bonhams.com{path}",
                    "category": "auction_auto_discovered",
                    "product_selector": "a[href*='/lot/']",
                    "next_page_selector": "a[rel='next']",
                    "priority": 6,
                    "enabled": True
                }
                new_seeds.append(seed_blob)
                
        logger.info(f"Bonhams Worker found {len(new_seeds)} active auctions!")
        return new_seeds
        
    except Exception as e:
        logger.error(f"Failed to auto-discover Bonhams auctions: {str(e)}")
        return []
