import requests
import feedparser
import json
import os
from datetime import datetime, timedelta
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import hashlib

# Configuration
NEWSAPI_KEY = os.environ.get('NEWSAPI_KEY', '')
MEDIASTACK_KEY = os.environ.get('MEDIASTACK_KEY', '')
NEWSDATA_KEY = os.environ.get('NEWSDATA_KEY', '')
MAX_ARTICLES = 200
ARTICLES_FILE = 'articles.json'
TIMEOUT = 8
MAX_RETRIES = 2

# VERIFIED & WORKING RSS FEEDS

CANADIAN_VERIFIED = [
    # CBC - Most reliable
    {'url': 'https://www.cbc.ca/cmlink/rss-topstories', 'name': 'CBC Top Stories', 'category': 'general'},
    {'url': 'https://www.cbc.ca/cmlink/rss-canada', 'name': 'CBC Canada', 'category': 'canada'},
    {'url': 'https://www.cbc.ca/cmlink/rss-politics', 'name': 'CBC Politics', 'category': 'politics'},
    {'url': 'https://www.cbc.ca/cmlink/rss-business', 'name': 'CBC Business', 'category': 'business'},
    {'url': 'https://www.cbc.ca/cmlink/rss-technology', 'name': 'CBC Tech', 'category': 'technology'},
    {'url': 'https://www.cbc.ca/cmlink/rss-health', 'name': 'CBC Health', 'category': 'health'},
    {'url': 'https://www.cbc.ca/cmlink/rss-sports', 'name': 'CBC Sports', 'category': 'sports'},
    
    # CTV News
    {'url': 'https://www.ctvnews.ca/rss/ctvnews-ca-top-stories-public-rss-1.822009', 'name': 'CTV Top Stories', 'category': 'general'},
    {'url': 'https://www.ctvnews.ca/rss/ctvnews-ca-canada-public-rss-1.822284', 'name': 'CTV Canada', 'category': 'canada'},
    {'url': 'https://www.ctvnews.ca/rss/ctvnews-ca-politics-public-rss-1.822302', 'name': 'CTV Politics', 'category': 'politics'},
    {'url': 'https://www.ctvnews.ca/rss/ctvnews-ca-world-public-rss-1.822289', 'name': 'CTV World', 'category': 'world'},
    
    # Global News
    {'url': 'https://globalnews.ca/feed/', 'name': 'Global News', 'category': 'general'},
    {'url': 'https://globalnews.ca/canada/feed/', 'name': 'Global Canada', 'category': 'canada'},
    {'url': 'https://globalnews.ca/politics/feed/', 'name': 'Global Politics', 'category': 'politics'},
    
    # National Post
    {'url': 'https://nationalpost.com/feed/', 'name': 'National Post', 'category': 'general'},
    {'url': 'https://nationalpost.com/category/news/canada/feed', 'name': 'National Post Canada', 'category': 'canada'},
    
    # The Globe and Mail (RSS)
    {'url': 'https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/national/', 'name': 'Globe & Mail', 'category': 'canada'},
]

CITY_FEEDS = {
    'Toronto': [
        {'url': 'https://www.cp24.com/feed', 'name': 'CP24', 'category': 'local'},
        {'url': 'https://toronto.citynews.ca/feed/', 'name': 'CityNews Toronto', 'category': 'local'},
        {'url': 'https://www.blogto.com/feed/', 'name': 'BlogTO', 'category': 'local'},
    ],
    'Vancouver': [
        {'url': 'https://vancouver.citynews.ca/feed/', 'name': 'CityNews Vancouver', 'category': 'local'},
        {'url': 'https://dailyhive.com/vancouver/feed', 'name': 'Daily Hive Vancouver', 'category': 'local'},
    ],
    'Montreal': [
        {'url': 'https://montreal.citynews.ca/feed/', 'name': 'CityNews Montreal', 'category': 'local'},
        {'url': 'https://www.mtlblog.com/feed', 'name': 'MTL Blog', 'category': 'local'},
    ],
    'Calgary': [
        {'url': 'https://calgary.citynews.ca/feed/', 'name': 'CityNews Calgary', 'category': 'local'},
    ],
    'Ottawa': [
        {'url': 'https://ottawa.citynews.ca/feed/', 'name': 'CityNews Ottawa', 'category': 'local'},
    ],
}

INTERNATIONAL_VERIFIED = [
    # BBC - Most reliable
    {'url': 'http://feeds.bbci.co.uk/news/world/rss.xml', 'name': 'BBC World', 'category': 'world'},
    {'url': 'http://feeds.bbci.co.uk/news/world/americas/rss.xml', 'name': 'BBC Americas', 'category': 'world'},
    {'url': 'http://feeds.bbci.co.uk/news/business/rss.xml', 'name': 'BBC Business', 'category': 'business'},
    {'url': 'http://feeds.bbci.co.uk/news/technology/rss.xml', 'name': 'BBC Technology', 'category': 'technology'},
    
    # Reuters
    {'url': 'https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best', 'name': 'Reuters Business', 'category': 'business'},
    
    # Al Jazeera
    {'url': 'https://www.aljazeera.com/xml/rss/all.xml', 'name': 'Al Jazeera', 'category': 'world'},
    
    # The Guardian
    {'url': 'https://www.theguardian.com/world/rss', 'name': 'The Guardian World', 'category': 'world'},
    {'url': 'https://www.theguardian.com/world/canada/rss', 'name': 'The Guardian Canada', 'category': 'canada'},
    
    # CNN
    {'url': 'http://rss.cnn.com/rss/cnn_world.rss', 'name': 'CNN World', 'category': 'world'},
    {'url': 'http://rss.cnn.com/rss/cnn_tech.rss', 'name': 'CNN Tech', 'category': 'technology'},
    
    # Associated Press
    {'url': 'https://apnews.com/apf-topnews', 'name': 'AP News', 'category': 'world'},
    
    # NPR
    {'url': 'https://feeds.npr.org/1001/rss.xml', 'name': 'NPR News', 'category': 'world'},
]

SOCIAL_FEEDS = [
    {'url': 'https://www.reddit.com/r/canada/.rss', 'name': 'r/canada', 'category': 'social'},
    {'url': 'https://www.reddit.com/r/CanadaPolitics/.rss', 'name': 'r/CanadaPolitics', 'category': 'social'},
    {'url': 'https://www.reddit.com/r/toronto/.rss', 'name': 'r/toronto', 'category': 'social'},
    {'url': 'https://www.reddit.com/r/vancouver/.rss', 'name': 'r/vancouver', 'category': 'social'},
]

# Google News RSS (Works without API!)
GOOGLE_NEWS_FEEDS = [
    {'url': 'https://news.google.com/rss/search?q=Canada+when:1d&hl=en-CA&gl=CA&ceid=CA:en', 'name': 'Google News Canada', 'category': 'canada'},
    {'url': 'https://news.google.com/rss/search?q=Toronto+when:1d&hl=en-CA&gl=CA&ceid=CA:en', 'name': 'Google News Toronto', 'category': 'local'},
    {'url': 'https://news.google.com/rss/search?q=Vancouver+when:1d&hl=en-CA&gl=CA&ceid=CA:en', 'name': 'Google News Vancouver', 'category': 'local'},
    {'url': 'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pEUVNnQVAB?hl=en-CA&gl=CA&ceid=CA:en', 'name': 'Google News Business', 'category': 'business'},
    {'url': 'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pEUVNnQVAB?hl=en-CA&gl=CA&ceid=CA:en', 'name': 'Google News Technology', 'category': 'technology'},
    {'url': 'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdvU0FtVnVHZ0pEUVNnQVAB?hl=en-CA&gl=CA&ceid=CA:en', 'name': 'Google News Sports', 'category': 'sports'},
]

def fetch_with_retry(url, headers=None, timeout=TIMEOUT):
    """Fetch URL with retry logic"""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise e
            time.sleep(1)
    return None

def fetch_single_feed(feed_info):
    """Fetch a single RSS feed with validation"""
    articles = []
    url = feed_info['url']
    source_name = feed_info['name']
    category = feed_info['category']
    
    try:
        # Parse RSS feed
        feed = feedparser.parse(url)
        
        if not feed.entries:
            print(f"⚠️  Empty feed: {source_name}")
            return articles
        
        for entry in feed.entries[:12]:
            try:
                # Validate required fields
                if not entry.get('link') or not entry.get('title'):
                    continue
                
                # Extract data
                title = entry.get('title', '').strip()
                link = entry.get('link', '').strip()
                
                # Skip if no valid URL
                if not link.startswith('http'):
                    continue
                
                # Get description
                description = ''
                if entry.get('summary'):
                    description = clean_html(entry.summary)
                elif entry.get('description'):
                    description = clean_html(entry.description)
                
                # Get image
                image_url = extract_image(entry)
                
                # Get published date
                published = entry.get('published', '')
                if not published:
                    published = datetime.now().isoformat()
                
                # Detect location and enhance category
                content = title + ' ' + description
                location = detect_location(content)
                enhanced_category = enhance_category(content, category)
                
                # Create article object
                article = {
                    'id': hashlib.md5(link.encode()).hexdigest()[:12],
                    'title': title[:200],
                    'description': description[:300],
                    'url': link,
                    'source': source_name,
                    'image': image_url,
                    'published': published,
                    'location': location,
                    'category': enhanced_category,
                    'fetched_at': datetime.now().isoformat()
                }
                
                articles.append(article)
                
            except Exception as e:
                continue
        
        if articles:
            print(f"✓ {source_name}: {len(articles)} articles")
        
        return articles
        
    except Exception as e:
        print(f"✗ {source_name}: {str(e)[:40]}")
        return articles

def fetch_newsapi():
    """Fetch from NewsAPI (if key available)"""
    articles = []
    
    if not NEWSAPI_KEY:
        return articles
    
    try:
        url = 'https://newsapi.org/v2/top-headlines'
        params = {
            'country': 'ca',
            'pageSize': 20,
            'apiKey': NEWSAPI_KEY
        }
        
        response = fetch_with_retry(url, timeout=10)
        if not response:
            return articles
        
        data = response.json()
        
        if data.get('status') == 'ok':
            for item in data.get('articles', []):
                if item.get('title') and item.get('url'):
                    articles.append({
                        'id': hashlib.md5(item['url'].encode()).hexdigest()[:12],
                        'title': item['title'][:200],
                        'description': (item.get('description') or '')[:300],
                        'url': item['url'],
                        'source': item.get('source', {}).get('name', 'NewsAPI'),
                        'image': item.get('urlToImage', ''),
                        'published': item.get('publishedAt', ''),
                        'location': detect_location(item['title']),
                        'category': 'general',
                        'fetched_at': datetime.now().isoformat()
                    })
            
            print(f"✓ NewsAPI: {len(articles)} articles")
    
    except Exception as e:
        print(f"✗ NewsAPI: {str(e)[:40]}")
    
    return articles

def fetch_mediastack():
    """Fetch from MediaStack API (Free tier: 500 req/month)"""
    articles = []
    
    if not MEDIASTACK_KEY:
        return articles
    
    try:
        url = 'http://api.mediastack.com/v1/news'
        params = {
            'access_key': MEDIASTACK_KEY,
            'countries': 'ca',
            'languages': 'en',
            'limit': 25
        }
        
        response = fetch_with_retry(url)
        if not response:
            return articles
        
        data = response.json()
        
        for item in data.get('data', []):
            if item.get('title') and item.get('url'):
                articles.append({
                    'id': hashlib.md5(item['url'].encode()).hexdigest()[:12],
                    'title': item['title'][:200],
                    'description': (item.get('description') or '')[:300],
                    'url': item['url'],
                    'source': item.get('source', 'MediaStack'),
                    'image': item.get('image', ''),
                    'published': item.get('published_at', ''),
                    'location': 'Canada',
                    'category': item.get('category', 'general'),
                    'fetched_at': datetime.now().isoformat()
                })
        
        print(f"✓ MediaStack: {len(articles)} articles")
    
    except Exception as e:
        print(f"✗ MediaStack: {str(e)[:40]}")
    
    return articles

def fetch_newsdata():
    """Fetch from NewsData.io (Free tier: 200 req/day)"""
    articles = []
    
    if not NEWSDATA_KEY:
        return articles
    
    try:
        url = 'https://newsdata.io/api/1/news'
        params = {
            'apikey': NEWSDATA_KEY,
            'country': 'ca',
            'language': 'en',
            'size': 10
        }
        
        response = fetch_with_retry(url)
        if not response:
            return articles
        
        data = response.json()
        
        for item in data.get('results', []):
            if item.get('title') and item.get('link'):
                articles.append({
                    'id': hashlib.md5(item['link'].encode()).hexdigest()[:12],
                    'title': item['title'][:200],
                    'description': (item.get('description') or '')[:300],
                    'url': item['link'],
                    'source': item.get('source_id', 'NewsData'),
                    'image': item.get('image_url', ''),
                    'published': item.get('pubDate', ''),
                    'location': 'Canada',
                    'category': (item.get('category') or ['general'])[0],
                    'fetched_at': datetime.now().isoformat()
                })
        
        print(f"✓ NewsData.io: {len(articles)} articles")
    
    except Exception as e:
        print(f"✗ NewsData.io: {str(e)[:40]}")
    
    return articles

def extract_image(entry):
    """Extract image from feed entry"""
    try:
        # Media content
        if hasattr(entry, 'media_content') and entry.media_content:
            return entry.media_content[0].get('url', '')
        
        # Media thumbnail
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            return entry.media_thumbnail[0].get('url', '')
        
        # Enclosures
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enc in entry.enclosures:
                if 'image' in enc.get('type', ''):
                    return enc.get('href', '')
        
        # Search in content
        content = entry.get('content', [{}])[0].get('value', '')
        if not content:
            content = entry.get('summary', '')
        
        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content)
        if img_match:
            return img_match.group(1)
    
    except:
        pass
    
    return ''

def clean_html(text):
    """Remove HTML tags and clean text"""
    if not text:
        return ''
    text = re.sub('<[^<]+?>', '', text)
    text = re.sub(r'\[.*?\]', '', text)
    text = ' '.join(text.split())
    return text.strip()

def detect_location(text):
    """Detect location from text"""
    text_lower = text.lower()
    
    cities = {
        'Toronto': ['toronto', 'gta', 'scarborough', 'mississauga'],
        'Vancouver': ['vancouver', 'burnaby', 'surrey', 'richmond', 'bc'],
        'Montreal': ['montreal', 'laval', 'quebec city'],
        'Calgary': ['calgary'],
        'Edmonton': ['edmonton'],
        'Ottawa': ['ottawa'],
        'Winnipeg': ['winnipeg'],
        'Halifax': ['halifax'],
    }
    
    for city, keywords in cities.items():
        if any(kw in text_lower for kw in keywords):
            return city
    
    if 'canad' in text_lower:
        return 'Canada'
    
    return 'World'

def enhance_category(text, base_category):
    """Enhance category detection"""
    text_lower = text.lower()
    
    keywords = {
        'politics': ['politic', 'election', 'parliament', 'trudeau', 'government'],
        'business': ['business', 'economy', 'stock', 'market', 'finance'],
        'sports': ['sport', 'hockey', 'nhl', 'soccer', 'football', 'baseball'],
        'technology': ['tech', 'ai', 'software', 'cyber', 'digital'],
        'entertainment': ['entertainment', 'movie', 'music', 'celebrity'],
        'health': ['health', 'medical', 'hospital', 'covid', 'vaccine'],
        'science': ['science', 'research', 'study', 'space'],
    }
    
    for category, words in keywords.items():
        if any(word in text_lower for word in words):
            return category
    
    return base_category

def remove_duplicates(articles):
    """Remove duplicates by URL and title similarity"""
    seen_ids = set()
    seen_urls = set()
    unique = []
    
    for article in articles:
        article_id = article.get('id', '')
        url = article.get('url', '')
        
        if article_id in seen_ids or url in seen_urls:
            continue
        
        seen_ids.add(article_id)
        seen_urls.add(url)
        unique.append(article)
    
    return unique

def main():
    print("=" * 90)
    print("🍁 MYCITYNEWS.CA - Professional News Aggregator v2.0")
    print("=" * 90)
    
    start_time = datetime.now()
    all_articles = []
    
    # Compile all feeds
    all_feeds = []
    all_feeds.extend(CANADIAN_VERIFIED)
    all_feeds.extend(INTERNATIONAL_VERIFIED)
    all_feeds.extend(GOOGLE_NEWS_FEEDS)
    all_feeds.extend(SOCIAL_FEEDS)
    
    for city_feeds in CITY_FEEDS.values():
        all_feeds.extend(city_feeds)
    
    print(f"\n📡 Fetching from {len(all_feeds)} RSS feeds...")
    
    # Fetch RSS feeds in parallel
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_single_feed, feed): feed for feed in all_feeds}
        
        completed = 0
        for future in as_completed(futures):
            completed += 1
            articles = future.result()
            all_articles.extend(articles)
            
            if completed % 15 == 0:
                print(f"  Progress: {completed}/{len(all_feeds)}")
    
    # Fetch from APIs
    print(f"\n🔌 Fetching from APIs...")
    all_articles.extend(fetch_newsapi())
    all_articles.extend(fetch_mediastack())
    all_articles.extend(fetch_newsdata())
    
    print(f"\n📊 Total fetched: {len(all_articles)}")
    
    if len(all_articles) == 0:
        print("⚠️  No articles fetched!")
        return
    
    # Remove duplicates
    all_articles = remove_duplicates(all_articles)
    print(f"📊 After deduplication: {len(all_articles)}")
    
    # Sort by date
    all_articles.sort(key=lambda x: x.get('published', ''), reverse=True)
    
    # Limit
    all_articles = all_articles[:MAX_ARTICLES]
    
    # Statistics
    stats = {
        'locations': {},
        'categories': {},
        'sources': set()
    }
    
    for article in all_articles:
        loc = article.get('location', 'Unknown')
        cat = article.get('category', 'general')
        src = article.get('source', 'Unknown')
        
        stats['locations'][loc] = stats['locations'].get(loc, 0) + 1
        stats['categories'][cat] = stats['categories'].get(cat, 0) + 1
        stats['sources'].add(src)
    
    # Print statistics
    print(f"\n📍 Articles by location:")
    for loc, count in sorted(stats['locations'].items(), key=lambda x: x[1], reverse=True)[:8]:
        print(f"   {loc}: {count}")
    
    print(f"\n📂 Articles by category:")
    for cat, count in sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True):
        print(f"   {cat}: {count}")
    
    print(f"\n📰 Unique sources: {len(stats['sources'])}")
    
    # Save output
    output = {
        'last_updated': datetime.now().isoformat(),
        'total_articles': len(all_articles),
        'articles': all_articles,
        'sources': list(stats['sources']),
        'stats': {
            'by_location': stats['locations'],
            'by_category': stats['categories'],
            'source_count': len(stats['sources'])
        }
    }
    
    with open(ARTICLES_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n✅ Successfully saved {len(all_articles)} articles in {elapsed:.1f}s")
    print("=" * 90)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
