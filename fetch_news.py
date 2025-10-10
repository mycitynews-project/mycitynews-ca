import requests
import feedparser
import json
import os
from datetime import datetime, timedelta
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
NEWSAPI_KEY = os.environ.get('NEWSAPI_KEY', '')
MAX_ARTICLES = 100
ARTICLES_FILE = 'articles.json'
TIMEOUT = 5  # Faster timeout

# Comprehensive Canadian RSS Feeds (optimized list)
RSS_FEEDS = {
    'National': [
        'https://www.cbc.ca/cmlink/rss-topstories',
        'https://www.cbc.ca/cmlink/rss-canada',
        'https://globalnews.ca/feed/',
        'https://nationalpost.com/feed/',
    ],
    'Toronto': [
        'https://www.cp24.com/feed',
        'https://www.thestar.com/feed/',
        'https://toronto.ctvnews.ca/rss/ctv-news-toronto-1.822066',
    ],
    'Vancouver': [
        'https://bc.ctvnews.ca/rss/ctv-news-vancouver-1.822075',
        'https://vancouversun.com/category/news/feed',
    ],
    'Montreal': [
        'https://montreal.ctvnews.ca/rss/ctv-news-montreal-1.822245',
        'https://montrealgazette.com/category/news/feed',
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

# Social Media RSS Feeds (top communities only)
SOCIAL_FEEDS = [
    'https://www.reddit.com/r/canada/.rss',
    'https://www.reddit.com/r/toronto/.rss',
    'https://www.reddit.com/r/vancouver/.rss',
    'https://www.reddit.com/r/CanadaPolitics/.rss',
]

# City/Location mapping
CITY_KEYWORDS = {
    'Toronto': ['toronto', 'gta', 'scarborough', 'mississauga', 'brampton'],
    'Vancouver': ['vancouver', 'burnaby', 'surrey', 'richmond', 'bc'],
    'Montreal': ['montreal', 'laval', 'quebec'],
    'Calgary': ['calgary', 'alberta'],
    'Edmonton': ['edmonton'],
    'Ottawa': ['ottawa'],
    'Winnipeg': ['winnipeg', 'manitoba'],
    'Halifax': ['halifax', 'nova scotia', 'atlantic'],
    'Saskatchewan': ['regina', 'saskatoon', 'saskatchewan'],
}

def fetch_single_feed(feed_url, source_region='Unknown'):
    """Fetch a single RSS feed with timeout"""
    articles = []
    try:
        feed = feedparser.parse(feed_url, timeout=TIMEOUT)
        
        if not feed.entries:
            return articles
        
        source_name = feed.feed.get('title', source_region)
        
        for entry in feed.entries[:10]:  # Limit to 10 per feed
            if not entry.get('link'):
                continue
            
            # Extract image
            image_url = ''
            try:
                if hasattr(entry, 'media_content') and len(entry.media_content) > 0:
                    image_url = entry.media_content[0].get('url', '')
                elif hasattr(entry, 'media_thumbnail') and len(entry.media_thumbnail) > 0:
                    image_url = entry.media_thumbnail[0].get('url', '')
            except:
                pass
            
            # Clean description
            description = entry.get('summary', '')
            if description:
                description = re.sub('<[^<]+?>', '', description)
                description = ' '.join(description.split()).strip()
            
            # Detect location and category
            content = entry.get('title', '') + ' ' + description
            location = detect_location(content) or source_region
            
            articles.append({
                'title': entry.get('title', '').strip(),
                'description': description[:200],
                'url': entry.get('link', ''),
                'source': source_name,
                'image': image_url,
                'published': entry.get('published', datetime.now().isoformat()),
                'location': location,
                'category': categorize_content(content),
                'fetched_at': datetime.now().isoformat()
            })
        
        return articles
    except Exception as e:
        print(f"⚠️  Error fetching {feed_url}: {str(e)[:50]}")
        return articles

def fetch_newsapi_articles():
    """Fetch from NewsAPI - optimized"""
    articles = []
    
    if not NEWSAPI_KEY:
        print("⚠️  No NewsAPI key")
        return articles
    
    try:
        url = 'https://newsapi.org/v2/everything'
        params = {
            'q': 'Canada OR Toronto OR Vancouver',
            'language': 'en',
            'sortBy': 'publishedAt',
            'pageSize': 20,
            'apiKey': NEWSAPI_KEY
        }
        
        response = requests.get(url, params=params, timeout=TIMEOUT)
        data = response.json()
        
        if data.get('status') == 'ok':
            for article in data.get('articles', []):
                if article.get('title') and article.get('url'):
                    content = article.get('title', '') + ' ' + article.get('description', '')
                    location = detect_location(content)
                    
                    articles.append({
                        'title': article.get('title', '').strip(),
                        'description': (article.get('description', '') or '').strip()[:200],
                        'url': article.get('url', ''),
                        'source': article.get('source', {}).get('name', 'Unknown'),
                        'image': article.get('urlToImage', ''),
                        'published': article.get('publishedAt', ''),
                        'location': location,
                        'category': categorize_content(content),
                        'fetched_at': datetime.now().isoformat()
                    })
        
        print(f"✓ NewsAPI: {len(articles)} articles")
    except Exception as e:
        print(f"⚠️  NewsAPI error: {str(e)[:50]}")
    
    return articles

def fetch_all_rss_feeds_parallel():
    """Fetch all RSS feeds in parallel for speed"""
    all_articles = []
    
    # Prepare feed list with regions
    feed_list = []
    for region, feeds in RSS_FEEDS.items():
        for feed_url in feeds:
            feed_list.append((feed_url, region))
    
    # Fetch in parallel (much faster!)
    print(f"\n📡 Fetching {len(feed_list)} RSS feeds in parallel...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_single_feed, url, region): (url, region) 
                   for url, region in feed_list}
        
        completed = 0
        for future in as_completed(futures):
            completed += 1
            articles = future.result()
            all_articles.extend(articles)
            if completed % 5 == 0:
                print(f"  Progress: {completed}/{len(feed_list)} feeds")
    
    print(f"✓ RSS Feeds: {len(all_articles)} articles")
    return all_articles

def fetch_social_feeds_parallel():
    """Fetch social media feeds in parallel"""
    all_articles = []
    
    print(f"\n💬 Fetching {len(SOCIAL_FEEDS)} social feeds...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_single_feed, url, 'Social'): url 
                   for url in SOCIAL_FEEDS}
        
        for future in as_completed(futures):
            articles = future.result()
            # Tag as social and clean up
            for article in articles:
                if 'reddit.com' in article['url']:
                    subreddit = article['url'].split('/r/')[1].split('/')[0] if '/r/' in article['url'] else 'reddit'
                    article['source'] = f'r/{subreddit}'
                    article['category'] = 'social'
            all_articles.extend(articles)
    
    print(f"✓ Social Media: {len(all_articles)} articles")
    return all_articles

def detect_location(text):
    """Detect Canadian city/region from text"""
    text_lower = text.lower()
    
    for city, keywords in CITY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return city
    
    return 'Canada'

def categorize_content(text):
    """Categorize article by content"""
    text_lower = text.lower()
    
    if any(w in text_lower for w in ['politic', 'election', 'parliament', 'trudeau', 'minister']):
        return 'politics'
    elif any(w in text_lower for w in ['business', 'economy', 'stock', 'market', 'finance']):
        return 'business'
    elif any(w in text_lower for w in ['sport', 'hockey', 'nhl', 'basketball', 'soccer', 'football']):
        return 'sports'
    elif any(w in text_lower for w in ['tech', 'ai', 'software', 'digital', 'cyber']):
        return 'tech'
    elif any(w in text_lower for w in ['weather', 'temperature', 'storm', 'snow']):
        return 'weather'
    else:
        return 'general'

def remove_duplicates(articles):
    """Remove duplicates by URL and title"""
    seen_urls = set()
    seen_titles = set()
    unique = []
    
    for article in articles:
        url = article.get('url', '')
        title = article.get('title', '').lower()[:50]
        
        if url in seen_urls or title in seen_titles:
            continue
        
        if url:
            seen_urls.add(url)
        if title:
            seen_titles.add(title)
        
        unique.append(article)
    
    return unique

def main():
    print("=" * 70)
    print("🍁 MYCITYNEWS.CA - Fast Parallel Fetch")
    print("=" * 70)
    
    start_time = datetime.now()
    all_articles = []
    
    # Fetch all sources in parallel
    print("\n📰 Fetching NewsAPI...")
    all_articles.extend(fetch_newsapi_articles())
    
    # RSS feeds in parallel (FAST!)
    all_articles.extend(fetch_all_rss_feeds_parallel())
    
    # Social media in parallel
    all_articles.extend(fetch_social_feeds_parallel())
    
    print(f"\n📊 Total fetched: {len(all_articles)} articles")
    
    if len(all_articles) == 0:
        print("⚠️  No articles fetched!")
        output = {
            'last_updated': datetime.now().isoformat(),
            'total_articles': 0,
            'articles': []
        }
        with open(ARTICLES_FILE, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        return
    
    # Remove duplicates
    all_articles = remove_duplicates(all_articles)
    print(f"📊 After deduplication: {len(all_articles)} articles")
    
    # Sort by date
    all_articles.sort(key=lambda x: x.get('published', ''), reverse=True)
    
    # Limit
    all_articles = all_articles[:MAX_ARTICLES]
    
    # Statistics
    locations = {}
    for article in all_articles:
        loc = article.get('location', 'Canada')
        locations[loc] = locations.get(loc, 0) + 1
    
    print(f"\n📍 Top locations:")
    for loc, count in sorted(locations.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"   {loc}: {count}")
    
    # Save
    output = {
        'last_updated': datetime.now().isoformat(),
        'total_articles': len(all_articles),
        'articles': all_articles,
        'locations': list(locations.keys()),
        'stats': {
            'by_location': locations,
            'total_sources': len(set(a.get('source', '') for a in all_articles))
        }
    }
    
    with open(ARTICLES_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n✅ Saved {len(all_articles)} articles in {elapsed:.1f} seconds")
    print("=" * 70)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
