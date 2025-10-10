import requests
import feedparser
import json
import os
from datetime import datetime, timedelta
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
NEWSAPI_KEY = os.environ.get('NEWSAPI_KEY', '')
MAX_ARTICLES = 150
ARTICLES_FILE = 'articles.json'
TIMEOUT = 5

# COMPREHENSIVE NEWS SOURCES

# Canadian National News
CANADIAN_NATIONAL = [
    'https://www.cbc.ca/cmlink/rss-topstories',
    'https://www.cbc.ca/cmlink/rss-canada',
    'https://globalnews.ca/feed/',
    'https://nationalpost.com/feed/',
    'https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/national/',
    'https://www.huffpost.com/news/canada/feed',
    'https://www.thestar.com/feed/',
]

# Canadian Local/Regional
CANADIAN_LOCAL = {
    'Toronto': [
        'https://www.cp24.com/feed',
        'https://toronto.ctvnews.ca/rss/ctv-news-toronto-1.822066',
        'https://www.blogto.com/feed/',
        'https://torontosun.com/category/news/feed',
    ],
    'Vancouver': [
        'https://bc.ctvnews.ca/rss/ctv-news-vancouver-1.822075',
        'https://vancouversun.com/category/news/feed',
        'https://dailyhive.com/vancouver/feed',
        'https://www.vancouverisawesome.com/feed',
    ],
    'Montreal': [
        'https://montreal.ctvnews.ca/rss/ctv-news-montreal-1.822245',
        'https://montrealgazette.com/category/news/feed',
        'https://www.mtlblog.com/feed',
    ],
    'Calgary': [
        'https://calgary.ctvnews.ca/rss/ctv-news-calgary-1.822097',
        'https://calgarysun.com/category/news/feed',
    ],
    'Edmonton': [
        'https://edmonton.ctvnews.ca/rss/ctv-news-edmonton-1.822112',
        'https://edmontonjournal.com/category/news/feed',
    ],
    'Ottawa': [
        'https://ottawa.ctvnews.ca/rss/ctv-news-ottawa-1.822113',
        'https://ottawacitizen.com/category/news/feed',
    ],
    'Winnipeg': [
        'https://winnipeg.ctvnews.ca/rss/ctv-news-winnipeg-1.822009',
    ],
    'Halifax': [
        'https://atlantic.ctvnews.ca/rss/ctv-news-atlantic-1.822009',
    ],
}

# International News (covering Canada)
INTERNATIONAL_SOURCES = [
    # BBC
    'http://feeds.bbci.co.uk/news/world/americas/rss.xml',
    'http://feeds.bbci.co.uk/news/world/rss.xml',
    
    # Reuters
    'https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best',
    
    # Al Jazeera
    'https://www.aljazeera.com/xml/rss/all.xml',
    
    # The Guardian
    'https://www.theguardian.com/world/canada/rss',
    'https://www.theguardian.com/world/americas/rss',
    
    # CNN
    'http://rss.cnn.com/rss/cnn_world.rss',
    
    # Associated Press
    'https://feeds.apnews.com/rss/apf-topnews',
    
    # NPR
    'https://feeds.npr.org/1004/rss.xml',
]

# Category-Specific Feeds
CATEGORY_FEEDS = {
    'politics': [
        'https://www.cbc.ca/cmlink/rss-politics',
        'https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/politics/',
        'https://nationalpost.com/category/news/politics/feed',
    ],
    'business': [
        'https://www.cbc.ca/cmlink/rss-business',
        'https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/business/',
        'https://financialpost.com/feed/',
        'https://www.bnnbloomberg.ca/feeds/rss/news.xml',
    ],
    'technology': [
        'https://www.cbc.ca/cmlink/rss-technology',
        'https://betakit.com/feed/',
        'https://techcrunch.com/feed/',
    ],
    'sports': [
        'https://www.cbc.ca/cmlink/rss-sports',
        'https://www.sportsnet.ca/feed/',
        'https://www.tsn.ca/rss',
    ],
    'entertainment': [
        'https://www.cbc.ca/cmlink/rss-arts',
        'https://www.blogto.com/eat_drink/feed/',
    ],
    'health': [
        'https://www.cbc.ca/cmlink/rss-health',
    ],
    'science': [
        'https://www.cbc.ca/cmlink/rss-technology',
    ],
}

# Social Media (Reddit)
SOCIAL_FEEDS = [
    'https://www.reddit.com/r/canada/.rss',
    'https://www.reddit.com/r/toronto/.rss',
    'https://www.reddit.com/r/vancouver/.rss',
    'https://www.reddit.com/r/CanadaPolitics/.rss',
    'https://www.reddit.com/r/onguardforthee/.rss',
]

# Location Keywords
CITY_KEYWORDS = {
    'Toronto': ['toronto', 'gta', 'scarborough', 'mississauga', 'brampton'],
    'Vancouver': ['vancouver', 'burnaby', 'surrey', 'richmond', 'bc'],
    'Montreal': ['montreal', 'laval', 'quebec'],
    'Calgary': ['calgary', 'alberta'],
    'Edmonton': ['edmonton'],
    'Ottawa': ['ottawa'],
    'Winnipeg': ['winnipeg', 'manitoba'],
    'Halifax': ['halifax', 'nova scotia'],
}

def fetch_single_feed(feed_url, source_info):
    """Fetch a single RSS feed"""
    articles = []
    try:
        feed = feedparser.parse(feed_url)
        
        if not feed.entries:
            return articles
        
        source_name = source_info.get('name', feed.feed.get('title', 'Unknown'))
        category = source_info.get('category', 'general')
        location = source_info.get('location', 'Canada')
        
        for entry in feed.entries[:10]:
            if not entry.get('link'):
                continue
            
            # Extract image
            image_url = extract_image(entry)
            
            # Clean description
            description = clean_text(entry.get('summary', ''))
            title = entry.get('title', '').strip()
            
            # Detect location and category from content
            content = title + ' ' + description
            detected_location = detect_location(content) or location
            detected_category = categorize_content(content) or category
            
            articles.append({
                'title': title,
                'description': description[:250],
                'url': entry.get('link', ''),
                'source': source_name,
                'image': image_url,
                'published': entry.get('published', datetime.now().isoformat()),
                'location': detected_location,
                'category': detected_category,
                'fetched_at': datetime.now().isoformat()
            })
        
        return articles
        
    except Exception as e:
        print(f"⚠️  Error: {feed_url[:50]}... - {str(e)[:30]}")
        return articles

def extract_image(entry):
    """Extract image from feed entry"""
    try:
        if hasattr(entry, 'media_content') and len(entry.media_content) > 0:
            return entry.media_content[0].get('url', '')
        elif hasattr(entry, 'media_thumbnail') and len(entry.media_thumbnail) > 0:
            return entry.media_thumbnail[0].get('url', '')
        elif hasattr(entry, 'enclosures') and len(entry.enclosures) > 0:
            enc = entry.enclosures[0]
            if 'image' in enc.get('type', ''):
                return enc.get('href', '')
        
        # Extract from content
        content = entry.get('content', [{}])[0].get('value', '')
        img_match = re.search(r'<img[^>]+src="([^"]+)"', content)
        if img_match:
            return img_match.group(1)
    except:
        pass
    return ''

def clean_text(text):
    """Remove HTML and clean text"""
    if not text:
        return ''
    text = re.sub('<[^<]+?>', '', text)
    text = re.sub(r'\[link\].*?\[comments\]', '', text)
    text = re.sub(r'submitted by.*?to r/\w+', '', text)
    text = ' '.join(text.split())
    return text.strip()

def detect_location(text):
    """Detect Canadian city from text"""
    text_lower = text.lower()
    for city, keywords in CITY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return city
    return 'Canada'

def categorize_content(text):
    """Categorize article"""
    text_lower = text.lower()
    
    keywords = {
        'politics': ['politic', 'election', 'parliament', 'trudeau', 'minister', 'government', 'liberal', 'conservative'],
        'business': ['business', 'economy', 'stock', 'market', 'finance', 'bank', 'dollar', 'trade', 'company'],
        'sports': ['sport', 'hockey', 'nhl', 'basketball', 'soccer', 'football', 'baseball', 'nba', 'mlb'],
        'technology': ['tech', 'ai', 'software', 'digital', 'cyber', 'app', 'startup', 'innovation'],
        'entertainment': ['entertainment', 'movie', 'music', 'celebrity', 'film', 'concert', 'festival'],
        'health': ['health', 'medical', 'hospital', 'doctor', 'disease', 'vaccine', 'wellness'],
        'science': ['science', 'research', 'study', 'scientist', 'discovery', 'space'],
        'world': ['international', 'global', 'world', 'foreign', 'overseas'],
    }
    
    for category, words in keywords.items():
        if any(word in text_lower for word in words):
            return category
    
    return 'general'

def fetch_newsapi_articles():
    """Fetch from NewsAPI with multiple queries"""
    articles = []
    
    if not NEWSAPI_KEY:
        print("⚠️  No NewsAPI key")
        return articles
    
    queries = [
        ('Canada', 'general'),
        ('Toronto', 'general'),
        ('Vancouver', 'general'),
        ('Canadian politics', 'politics'),
        ('Canadian business', 'business'),
    ]
    
    for query, category in queries:
        try:
            url = 'https://newsapi.org/v2/everything'
            params = {
                'q': query,
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': 15,
                'apiKey': NEWSAPI_KEY
            }
            
            response = requests.get(url, params=params, timeout=TIMEOUT)
            data = response.json()
            
            if data.get('status') == 'ok':
                for article in data.get('articles', []):
                    if article.get('title') and article.get('url'):
                        content = article.get('title', '') + ' ' + article.get('description', '')
                        
                        articles.append({
                            'title': article.get('title', '').strip(),
                            'description': (article.get('description', '') or '').strip()[:250],
                            'url': article.get('url', ''),
                            'source': article.get('source', {}).get('name', 'Unknown'),
                            'image': article.get('urlToImage', ''),
                            'published': article.get('publishedAt', ''),
                            'location': detect_location(content),
                            'category': categorize_content(content) or category,
                            'fetched_at': datetime.now().isoformat()
                        })
        except Exception as e:
            print(f"⚠️  NewsAPI {query}: {str(e)[:30]}")
            continue
    
    print(f"✓ NewsAPI: {len(articles)} articles")
    return articles

def fetch_all_feeds_parallel():
    """Fetch all feeds in parallel"""
    all_articles = []
    feed_list = []
    
    # Canadian National
    for feed in CANADIAN_NATIONAL:
        feed_list.append((feed, {'name': None, 'category': 'general', 'location': 'Canada'}))
    
    # Canadian Local
    for city, feeds in CANADIAN_LOCAL.items():
        for feed in feeds:
            feed_list.append((feed, {'name': None, 'category': 'general', 'location': city}))
    
    # International
    for feed in INTERNATIONAL_SOURCES:
        feed_list.append((feed, {'name': None, 'category': 'world', 'location': 'World'}))
    
    # Categories
    for category, feeds in CATEGORY_FEEDS.items():
        for feed in feeds:
            feed_list.append((feed, {'name': None, 'category': category, 'location': 'Canada'}))
    
    # Social
    for feed in SOCIAL_FEEDS:
        feed_list.append((feed, {'name': None, 'category': 'social', 'location': 'Social'}))
    
    print(f"\n📡 Fetching {len(feed_list)} feeds in parallel...")
    
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(fetch_single_feed, url, info): url for url, info in feed_list}
        
        completed = 0
        for future in as_completed(futures):
            completed += 1
            articles = future.result()
            all_articles.extend(articles)
            
            if completed % 10 == 0:
                print(f"  Progress: {completed}/{len(feed_list)}")
    
    print(f"✓ RSS: {len(all_articles)} articles")
    return all_articles

def remove_duplicates(articles):
    """Remove duplicates"""
    seen_urls = set()
    seen_titles = set()
    unique = []
    
    for article in articles:
        url = article.get('url', '')
        title = article.get('title', '').lower()[:60]
        
        if url in seen_urls or title in seen_titles:
            continue
        
        if url:
            seen_urls.add(url)
        if title:
            seen_titles.add(title)
        
        unique.append(article)
    
    return unique

def main():
    print("=" * 80)
    print("🍁 MYCITYNEWS.CA - Comprehensive News Aggregator")
    print("=" * 80)
    
    start_time = datetime.now()
    all_articles = []
    
    # Fetch from all sources
    print("\n📰 Fetching NewsAPI...")
    all_articles.extend(fetch_newsapi_articles())
    
    print("\n📡 Fetching all RSS feeds...")
    all_articles.extend(fetch_all_feeds_parallel())
    
    print(f"\n📊 Total fetched: {len(all_articles)}")
    
    if len(all_articles) == 0:
        print("⚠️  No articles!")
        output = {
            'last_updated': datetime.now().isoformat(),
            'total_articles': 0,
            'articles': [],
            'sources': [],
            'categories': []
        }
        with open(ARTICLES_FILE, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        return
    
    # Remove duplicates
    all_articles = remove_duplicates(all_articles)
    print(f"📊 After deduplication: {len(all_articles)}")
    
    # Sort by date
    all_articles.sort(key=lambda x: x.get('published', ''), reverse=True)
    
    # Limit
    all_articles = all_articles[:MAX_ARTICLES]
    
    # Statistics
    locations = {}
    categories = {}
    sources = set()
    
    for article in all_articles:
        loc = article.get('location', 'Canada')
        cat = article.get('category', 'general')
        src = article.get('source', 'Unknown')
        
        locations[loc] = locations.get(loc, 0) + 1
        categories[cat] = categories.get(cat, 0) + 1
        sources.add(src)
    
    print(f"\n📍 Top locations:")
    for loc, count in sorted(locations.items(), key=lambda x: x[1], reverse=True)[:8]:
        print(f"   {loc}: {count}")
    
    print(f"\n📂 Categories:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"   {cat}: {count}")
    
    print(f"\n📰 Unique sources: {len(sources)}")
    
    # Save
    output = {
        'last_updated': datetime.now().isoformat(),
        'total_articles': len(all_articles),
        'articles': all_articles,
        'sources': list(sources),
        'categories': list(categories.keys()),
        'stats': {
            'by_location': locations,
            'by_category': categories,
            'total_sources': len(sources)
        }
    }
    
    with open(ARTICLES_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n✅ Saved {len(all_articles)} articles in {elapsed:.1f}s")
    print("=" * 80)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
