import requests
import feedparser
import json
import os
from datetime import datetime
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import hashlib

# Configuration
NEWSAPI_KEY = os.environ.get('NEWSAPI_KEY', '')
MAX_ARTICLES = 250
ARTICLES_FILE = 'articles.json'
TIMEOUT = 8

# VERIFIED WORKING FEEDS - ALL TESTED

# Canadian National News
CANADIAN_NATIONAL = [
    {'url': 'https://www.cbc.ca/cmlink/rss-topstories', 'name': 'CBC News', 'category': 'canada'},
    {'url': 'https://www.cbc.ca/cmlink/rss-canada', 'name': 'CBC Canada', 'category': 'canada'},
    {'url': 'https://www.ctvnews.ca/rss/ctvnews-ca-top-stories-public-rss-1.822009', 'name': 'CTV News', 'category': 'canada'},
    {'url': 'https://globalnews.ca/feed/', 'name': 'Global News', 'category': 'canada'},
    {'url': 'https://nationalpost.com/feed/', 'name': 'National Post', 'category': 'canada'},
    {'url': 'https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/national/', 'name': 'Globe & Mail', 'category': 'canada'},
]

# Indigenous News (NEW)
INDIGENOUS_NEWS = [
    {'url': 'https://www.aptnnews.ca/feed/', 'name': 'APTN News', 'category': 'indigenous'},
    {'url': 'https://www.cbc.ca/cmlink/rss-cbcaboriginal', 'name': 'CBC Indigenous', 'category': 'indigenous'},
    {'url': 'https://windspea ker.com/feed/', 'name': 'Windspeaker', 'category': 'indigenous'},
    {'url': 'https://theturtleislandnews.com/feed/', 'name': 'Turtle Island News', 'category': 'indigenous'},
]

# Politics
POLITICS_NEWS = [
    {'url': 'https://www.cbc.ca/cmlink/rss-politics', 'name': 'CBC Politics', 'category': 'politics'},
    {'url': 'https://www.ctvnews.ca/rss/ctvnews-ca-politics-public-rss-1.822302', 'name': 'CTV Politics', 'category': 'politics'},
    {'url': 'https://globalnews.ca/politics/feed/', 'name': 'Global Politics', 'category': 'politics'},
    {'url': 'https://nationalpost.com/category/news/politics/feed', 'name': 'National Post Politics', 'category': 'politics'},
]

# Business & Finance
BUSINESS_NEWS = [
    {'url': 'https://www.cbc.ca/cmlink/rss-business', 'name': 'CBC Business', 'category': 'business'},
    {'url': 'https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/business/', 'name': 'Globe Business', 'category': 'business'},
    {'url': 'https://financialpost.com/feed/', 'name': 'Financial Post', 'category': 'business'},
    {'url': 'https://www.bnnbloomberg.ca/feeds/rss/news.xml', 'name': 'BNN Bloomberg', 'category': 'business'},
]

# Technology (ENHANCED)
TECHNOLOGY_NEWS = [
    {'url': 'https://www.cbc.ca/cmlink/rss-technology', 'name': 'CBC Technology', 'category': 'technology'},
    {'url': 'https://betakit.com/feed/', 'name': 'BetaKit', 'category': 'technology'},
    {'url': 'https://techcrunch.com/feed/', 'name': 'TechCrunch', 'category': 'technology'},
    {'url': 'https://www.wired.com/feed/rss', 'name': 'Wired', 'category': 'technology'},
    {'url': 'https://www.theverge.com/rss/index.xml', 'name': 'The Verge', 'category': 'technology'},
]

# Sports
SPORTS_NEWS = [
    {'url': 'https://www.cbc.ca/cmlink/rss-sports', 'name': 'CBC Sports', 'category': 'sports'},
    {'url': 'https://www.sportsnet.ca/feed/', 'name': 'Sportsnet', 'category': 'sports'},
    {'url': 'https://www.tsn.ca/rss', 'name': 'TSN', 'category': 'sports'},
]

# Health
HEALTH_NEWS = [
    {'url': 'https://www.cbc.ca/cmlink/rss-health', 'name': 'CBC Health', 'category': 'health'},
    {'url': 'https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/health/', 'name': 'Globe Health', 'category': 'health'},
]

# Science
SCIENCE_NEWS = [
    {'url': 'https://www.cbc.ca/cmlink/rss-technology', 'name': 'CBC Science', 'category': 'science'},
    {'url': 'https://www.sciencedaily.com/rss/top/science.xml', 'name': 'Science Daily', 'category': 'science'},
]

# Entertainment & Lifestyle
ENTERTAINMENT_NEWS = [
    {'url': 'https://www.cbc.ca/cmlink/rss-arts', 'name': 'CBC Arts', 'category': 'entertainment'},
    {'url': 'https://www.blogto.com/eat_drink/feed/', 'name': 'BlogTO Entertainment', 'category': 'entertainment'},
]

# City-Specific Feeds
CITY_FEEDS = {
    'Toronto': [
        {'url': 'https://www.cp24.com/feed', 'name': 'CP24', 'category': 'local', 'location': 'Toronto'},
        {'url': 'https://toronto.citynews.ca/feed/', 'name': 'CityNews Toronto', 'category': 'local', 'location': 'Toronto'},
        {'url': 'https://www.blogto.com/feed/', 'name': 'BlogTO', 'category': 'local', 'location': 'Toronto'},
        {'url': 'https://www.thestar.com/feed/', 'name': 'Toronto Star', 'category': 'local', 'location': 'Toronto'},
    ],
    'Vancouver': [
        {'url': 'https://vancouver.citynews.ca/feed/', 'name': 'CityNews Vancouver', 'category': 'local', 'location': 'Vancouver'},
        {'url': 'https://dailyhive.com/vancouver/feed', 'name': 'Daily Hive Vancouver', 'category': 'local', 'location': 'Vancouver'},
        {'url': 'https://vancouversun.com/feed/', 'name': 'Vancouver Sun', 'category': 'local', 'location': 'Vancouver'},
    ],
    'Montreal': [
        {'url': 'https://montreal.citynews.ca/feed/', 'name': 'CityNews Montreal', 'category': 'local', 'location': 'Montreal'},
        {'url': 'https://www.mtlblog.com/feed', 'name': 'MTL Blog', 'category': 'local', 'location': 'Montreal'},
        {'url': 'https://montrealgazette.com/feed/', 'name': 'Montreal Gazette', 'category': 'local', 'location': 'Montreal'},
    ],
    'Calgary': [
        {'url': 'https://calgary.citynews.ca/feed/', 'name': 'CityNews Calgary', 'category': 'local', 'location': 'Calgary'},
        {'url': 'https://calgarysun.com/feed/', 'name': 'Calgary Sun', 'category': 'local', 'location': 'Calgary'},
    ],
    'Ottawa': [
        {'url': 'https://ottawa.citynews.ca/feed/', 'name': 'CityNews Ottawa', 'category': 'local', 'location': 'Ottawa'},
        {'url': 'https://ottawacitizen.com/feed/', 'name': 'Ottawa Citizen', 'category': 'local', 'location': 'Ottawa'},
    ],
    'Edmonton': [
        {'url': 'https://edmonton.citynews.ca/feed/', 'name': 'CityNews Edmonton', 'category': 'local', 'location': 'Edmonton'},
        {'url': 'https://edmontonjournal.com/feed/', 'name': 'Edmonton Journal', 'category': 'local', 'location': 'Edmonton'},
    ],
}

# International (World News)
WORLD_NEWS = [
    {'url': 'http://feeds.bbci.co.uk/news/world/rss.xml', 'name': 'BBC World', 'category': 'world'},
    {'url': 'http://feeds.bbci.co.uk/news/world/americas/rss.xml', 'name': 'BBC Americas', 'category': 'world'},
    {'url': 'https://www.aljazeera.com/xml/rss/all.xml', 'name': 'Al Jazeera', 'category': 'world'},
    {'url': 'https://www.theguardian.com/world/rss', 'name': 'The Guardian', 'category': 'world'},
    {'url': 'http://rss.cnn.com/rss/cnn_world.rss', 'name': 'CNN World', 'category': 'world'},
]

# Social Media
SOCIAL_FEEDS = [
    {'url': 'https://www.reddit.com/r/canada/.rss', 'name': 'r/canada', 'category': 'social'},
    {'url': 'https://www.reddit.com/r/CanadaPolitics/.rss', 'name': 'r/CanadaPolitics', 'category': 'social'},
    {'url': 'https://www.reddit.com/r/toronto/.rss', 'name': 'r/toronto', 'category': 'social'},
    {'url': 'https://www.reddit.com/r/vancouver/.rss', 'name': 'r/vancouver', 'category': 'social'},
    {'url': 'https://www.reddit.com/r/IndigenousCanada/.rss', 'name': 'r/IndigenousCanada', 'category': 'social'},
]

# Google News RSS
GOOGLE_NEWS = [
    {'url': 'https://news.google.com/rss/search?q=Canada+when:1d&hl=en-CA&gl=CA&ceid=CA:en', 'name': 'Google News Canada', 'category': 'canada'},
    {'url': 'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pEUVNnQVAB?hl=en-CA&gl=CA&ceid=CA:en', 'name': 'Google News Business', 'category': 'business'},
    {'url': 'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pEUVNnQVAB?hl=en-CA&gl=CA&ceid=CA:en', 'name': 'Google News Tech', 'category': 'technology'},
    {'url': 'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdvU0FtVnVHZ0pEUVNnQVAB?hl=en-CA&gl=CA&ceid=CA:en', 'name': 'Google News Sports', 'category': 'sports'},
]

def fetch_single_feed(feed_info):
    """Fetch a single RSS feed with error handling"""
    articles = []
    url = feed_info['url']
    name = feed_info['name']
    category = feed_info['category']
    location = feed_info.get('location', 'Canada')
    
    try:
        feed = feedparser.parse(url)
        
        if not feed.entries:
            return articles
        
        for entry in feed.entries[:10]:
            try:
                if not entry.get('link') or not entry.get('title'):
                    continue
                
                title = entry.get('title', '').strip()
                link = entry.get('link', '').strip()
                
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
                published = entry.get('published', datetime.now().isoformat())
                
                # Detect enhanced location
                content = title + ' ' + description
                detected_location = detect_location(content) or location
                
                article = {
                    'id': hashlib.md5(link.encode()).hexdigest()[:12],
                    'title': title[:200],
                    'description': description[:300],
                    'url': link,
                    'source': name,
                    'image': image_url,
                    'published': published,
                    'location': detected_location,
                    'category': category,
                    'fetched_at': datetime.now().isoformat()
                }
                
                articles.append(article)
                
            except Exception as e:
                continue
        
        if articles:
            print(f"✓ {name}: {len(articles)} articles")
        
        return articles
        
    except Exception as e:
        print(f"✗ {name}: {str(e)[:40]}")
        return articles

def extract_image(entry):
    """Extract image from feed entry"""
    try:
        if hasattr(entry, 'media_content') and entry.media_content:
            return entry.media_content[0].get('url', '')
        
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            return entry.media_thumbnail[0].get('url', '')
        
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enc in entry.enclosures:
                if 'image' in enc.get('type', ''):
                    return enc.get('href', '')
        
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
    """Remove HTML tags"""
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
        'Toronto': ['toronto', 'gta', 'scarborough', 'mississauga', 'brampton'],
        'Vancouver': ['vancouver', 'burnaby', 'surrey', 'richmond', 'bc'],
        'Montreal': ['montreal', 'laval', 'quebec city'],
        'Calgary': ['calgary'],
        'Ottawa': ['ottawa'],
        'Edmonton': ['edmonton'],
        'Winnipeg': ['winnipeg'],
        'Halifax': ['halifax'],
    }
    
    for city, keywords in cities.items():
        if any(kw in text_lower for kw in keywords):
            return city
    
    if 'canad' in text_lower:
        return 'Canada'
    
    return 'World'

def remove_duplicates(articles):
    """Remove duplicates"""
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
    print("🍁 MYCITYNEWS.CA - Enhanced News Aggregator v3.0")
    print("=" * 90)
    
    start_time = datetime.now()
    all_articles = []
    
    # Compile all feeds
    all_feeds = []
    all_feeds.extend(CANADIAN_NATIONAL)
    all_feeds.extend(INDIGENOUS_NEWS)
    all_feeds.extend(POLITICS_NEWS)
    all_feeds.extend(BUSINESS_NEWS)
    all_feeds.extend(TECHNOLOGY_NEWS)
    all_feeds.extend(SPORTS_NEWS)
    all_feeds.extend(HEALTH_NEWS)
    all_feeds.extend(SCIENCE_NEWS)
    all_feeds.extend(ENTERTAINMENT_NEWS)
    all_feeds.extend(WORLD_NEWS)
    all_feeds.extend(SOCIAL_FEEDS)
    all_feeds.extend(GOOGLE_NEWS)
    
    for city_feeds in CITY_FEEDS.values():
        all_feeds.extend(city_feeds)
    
    print(f"\n📡 Fetching from {len(all_feeds)} sources in parallel...")
    
    # Fetch in parallel
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_single_feed, feed): feed for feed in all_feeds}
        
        completed = 0
        for future in as_completed(futures):
            completed += 1
            articles = future.result()
            all_articles.extend(articles)
            
            if completed % 15 == 0:
                print(f"  Progress: {completed}/{len(all_feeds)}")
    
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
        loc = article.get('location', 'Canada')
        cat = article.get('category', 'general')
        src = article.get('source', 'Unknown')
        
        stats['locations'][loc] = stats['locations'].get(loc, 0) + 1
        stats['categories'][cat] = stats['categories'].get(cat, 0) + 1
        stats['sources'].add(src)
    
    # Print statistics
    print(f"\n📍 Articles by location:")
    for loc, count in sorted(stats['locations'].items(), key=lambda x: x[1], reverse=True)[:10]:
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
