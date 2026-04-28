import yaml

def update_seeds():
    with open('config/seed_urls.yaml', 'r') as f:
        data = yaml.safe_load(f)
        
    for source in data['sources']:
        source['enabled'] = False
        
    urls = [
        'https://www.liveauctioneers.com/c/art/1/',
        'https://www.liveauctioneers.com/c/fashion/3/',
        'https://www.liveauctioneers.com/c/home-and-decor/5/',
        'https://www.liveauctioneers.com/c/coins-currency-and-stamps/24/',
        'https://www.liveauctioneers.com/c/collectibles/2/',
        'https://www.liveauctioneers.com/c/furniture/4/',
        'https://www.liveauctioneers.com/c/asian/158/',
        'https://www.liveauctioneers.com/c/jewelry/6/'
    ]
    
    new_sources = []
    for url in urls:
        category_name = url.split('/')[-2]
        new_sources.append({
            'name': f'liveauctioneers_{category_name}',
            'base_url': url,
            'category': category_name,
            'product_selector': 'a[href*="/item/"]',
            'next_page_selector': 'a[rel="next"]',
            'priority': 1,
            'enabled': True
        })
        
    data['sources'].extend(new_sources)
    
    with open('config/seed_urls.yaml', 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

if __name__ == "__main__":
    update_seeds()
