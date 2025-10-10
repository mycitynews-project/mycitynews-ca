import requests
import feedparser
import json
import os
from datetime import datetime, timedelta
import re

# Configuration
NEWSAPI_KEY = os.environ.get('NEWSAPI_KEY', '')
MAX_ARTICLES = 100
ARTICLES_FILE = 'articles.json'

# Comprehensive Canadian RSS Feeds by Province/City
RSS_FEEDS = {
    'National': [
        'https://www.cbc.ca/cmlink/rss-topstories',
        'https://www.cbc.ca/cmlink/rss-canada',
        'https://globalnews.ca/feed/',
        'https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/national/',
        'https://nationalpost.com/feed/',
        'https://www.huffpost.com/news/canada/feed',
    ],
    'Toronto': [
        'https://www.cp24.com/feed',
        'https://www.citynews.ca/feed/',
        'https://www.thestar.com/feed/',
        'https://toronto.ctvnews.ca/rss/ctv-news-toronto-1.822066',
        'https://www.blogto.com/feed/',
        'https://torontosun.com/category/news/feed',
    ],
    'Vancouver': [
        'https://bc.ctvnews.ca/rss/ctv-news-vancouver-1.822075',
        'https://www.vancouverisawesome.com/feed',
        'https://vancouversun.com/category/news/feed',
        'https://dailyhive.com/vancouver/feed',
    ],
    'Montreal': [
        'https://montreal.ctvnews.ca/rss/ctv-news-montreal-1.822245',
        'https://montrealgazette.com/category/news/feed',
        'https://www.mtlblog.com/feed',
    ],
    'Calgary': [
        'https://calgary.ctvnews.ca/rss/ctv-news-calgary-1.822097',
        'https://www.660citynews.com/feed/',
        'https://calgarysun.com/category/news/feed',
    ],
    'Edmonton': [
        'https://edmonton.ctvnews.ca/rss/ctv-news-edmonton-1.822112',
        'https://edmontonjournal.com/category/news/feed',
        'https://edmontonsun.com/category/news/feed',
    ],
    'Ottawa': [
        'https://ottawa.ctvnews.ca/rss/ctv-news-ottawa-1.822113',
        'https://ottawacitizen.com/category/news/feed',
        'https://ottawasun.com/category/news/feed',
    ],
    'Winnipeg': [
        'https://winnipeg.ctvnews.ca/rss/ctv-news-winnipeg-1.822009',
        'https://www.winnipegfreepress.com/rss/?path=/breakingnews',
        'https://winnipegsun.com/category/news/feed',
    ],
    'Halifax': [
        'https://atlantic.ctvnews.ca/rss/ctv-news-atlantic-1.822009',
        'https://www.saltwire.com/feeds/rss/',
    ],
    'Quebec': [
        'https://montreal.ctvnews.ca/rss/ctv-news-montreal-1.822245',
        'https://www.cbc.ca/cmlink/rss-canada-montreal',
    ],
}

# Social Media RSS Feeds (Reddit Canadian communities)
SOCIAL_FEEDS = [
    'https://www.reddit.com/r/canada/.rss',
    'https://www.reddit.com/r/toronto/.rss',
    'https://www.reddit.com/r/vancouver/.rss',
    'https://www.reddit.com/r/montreal/.rss',
    'https://www.reddit.com/r/calgary/.rss',
    'https://www.reddit.com/r/ottawa/.rss',
    'https://www.reddit.com/r/Edmonton/.rss',
    'https://www.reddit.com/r/winnipeg/.rss',
    'https://www.reddit.com/r/halifax/.rss',
    'https://www.reddit.com/r/CanadaPolitics/.rss',
    'https://www.reddit.com/r/onguardforthee/.rss',
]

# City/Location mapping for geo-targeting
CITY_KEYWORDS = {
    'Toronto': ['toronto', 'gta', 'scarborough', 'mississauga', 'brampton', 'markham', 'vaughan', 'oakville'],
    'Vancouver': ['vancouver', 'burnaby', 'surrey', 'richmond', 'coquitlam', 'langley', 'delta', 'bc lower mainland'],
    'Montreal': ['montreal', 'laval', 'longueuil', 'quebec city', 'gatineau'],
    'Calgary': ['calgary', 'airdrie', 'cochrane', 'okotoks'],
    'Edmonton': ['edmonton', 'st albert', 'sherwood park', 'spruce grove'],
    'Ottawa': ['ottawa', 'kanata', 'nepean', 'orleans'],
    'Winnipeg': ['winnipeg', 'brandon'],
    'Halifax': ['halifax', 'dartmouth', 'bedford'],
    'Quebec': ['quebec', 'sherbrooke', 'trois-rivières'],
    'Saskatchewan': ['regina', 'saskatoon'],
    'Manitoba': ['winnipeg', 'brandon'],
    'Atlantic': ['newfoundland', 'new brunswick', 'prince edward island', 'pei', 'nova scotia'],
}

def fetch_newsapi_articles():
    """Fetch articles from NewsAPI - Canadian sources"""
    articles = []
    
    if not NEWSAPI_KEY:
        print("⚠️  No NewsAPI key found, skipping NewsAPI")
        return articles
    
    # Fetch from Canadian sources
    canadian_sources = [
        'the-globe-and-mail',
        'cbc-news',
    ]
    
    # General Canadian news
    queries = [
        'Canada',
        'Toronto',
        'Vancouver', 
        'Montreal',
        'Canadian politics',
        'Canadian business',
    ]
    
    for query in queries:
        try:
            url = 'https://newsapi.org/v2/everything'
            params = {
                'q': query,
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': 10,
                'apiKey': NEWSAPI_KEY
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('status') == 'ok':
                for article in data.get('articles', []):
                    if article.get('title') and article.get('url'):
                        # Detect location from content
                        location = detect_location(article.get('title', '') + ' ' + article.get('description', ''))
                        
                        articles.append({
                            'title': article.get('title', '').strip(),
                            'description': article.get('description', '').strip() if article.get('description') else '',
                            'url': article.get('url', ''),
                            'source': article.get('source', {}).get('name', 'Unknown'),
                            'image': article.get('urlToImage', ''),
                            'published': article.get('publishedAt', ''),
                            'location': location,
                            'category': categorize_content(article.get('title', '') + ' ' + article.get('description', '')),
                            'fetched_at': datetime.now().isoformat()
                        })
        except Exception as e:
            print(f"⚠️  NewsAPI query error ({query}): {e}")
            continue
    
    print(f"✓ Fetched {len(articles)} articles from NewsAPI")
    return articles

def fetch_rss_feeds():
    """Fetch articles from all RSS feeds"""
    articles = []
    
    # Fetch from news RSS feeds
    for region, feeds in RSS_FEEDS.items():
        for feed_url in feeds:
            try:
                print(f"Fetching from: {feed_url}")
                feed = feedparser.parse(feed_url)
                
                if not feed.entries:
                    continue
                
                source_name = feed.feed.get('title', 'Unknown Source')
                
                for entry in feed.entries[:15]:
                    if not entry.get('link'):
                        continue
                    
                    # Extract image
                    image_url = extract_image(entry)
                    
                    # Clean description
                    description = clean_description(entry.get('summary', ''))
                    
                    # Detect location
                    content = entry.get('title', '') + ' ' + description
                    location = detect_location(content) or region
                    
                    articles.append({
                        'title': entry.get('title', '').strip(),
                        'description': description,
                        'url': entry.get('link', ''),
                        'source': source_name,
                        'image': image_url,
                        'published': entry.get('published', datetime.now().isoformat()),
                        'location': location,
                        'category': categorize_content(content),
                        'fetched_at': datetime.now().isoformat()
                    })
                
                print(f"✓ Fetched articles from {source_name}")
            except Exception as e:
                print(f"⚠️  RSS feed error ({feed_url}): {e}")
                continue
    
    return articles

def fetch_social_feeds():
    """Fetch from social media RSS feeds (Reddit)"""
    articles = []
    
    for feed_url in SOCIAL_FEEDS:
        try:
            print(f"Fetching social: {feed_url}")
            feed = feedparser.parse(feed_url)
            
            if not feed.entries:
                continue
            
            subreddit = feed_url.split('/r/')[1].split('/')[0] if '/r/' in feed_url else 'reddit'
            
            for entry in feed.entries[:10]:
                if not entry.get('link'):
                    continue
                
                # Skip if it's a comment or low engagement
                title = entry.get('title', '')
                if not title or len(title) < 10:
                    continue
                
                # Extract image from Reddit post
                image_url = extract_image(entry)
                
                description = clean_description(entry.get('summary', ''))
                content = title + ' ' + description
                
                # Detect location
                location = detect_location(content) or subreddit.title()
                
                articles.append({
                    'title': title.strip(),
                    'description': description[:200] if description else '',
                    'url': entry.get('link', ''),
                    'source': f'r/{subreddit}',
                    'image': image_url,
                    'published': entry.get('published', datetime.now().isoformat()),
                    'location': location,
                    'category': 'social',
                    'fetched_at': datetime.now().isoformat()
                })
            
            print(f"✓ Fetched from r/{subreddit}")
        except Exception as e:
            print(f"⚠️  Social feed error: {e}")
            continue
    
    return articles

def extract_image(entry):
    """Extract image from feed entry"""
    image_url = ''
    try:
        if hasattr(entry, 'media_content') and len(entry.media_content) > 0:
            image_url = entry.media_content[0].get('url', '')
        elif hasattr(entry, 'media_thumbnail') and len(entry.media_thumbnail) > 0:
            image_url = entry.media_thumbnail[0].get('url', '')
        elif hasattr(entry, 'enclosures') and len(entry.enclosures) > 0:
            if 'image' in entry.enclosures[0].get('type', ''):
                image_url = entry.enclosures[0].get('href', '')
        
        # Reddit specific - extract from content
        if 'reddit.com' in entry.get('link', '') and not image_url:
            content = entry.get('content', [{}])[0].get('value', '')
            img_match = re.search(r'<img[^>]+src="([^"]+)"', content)
            if img_match:
                image_url = img_match.group(1)
    except:
        pass
    
    return image_url

def clean_description(text):
    """Remove HTML tags and clean text"""
    if not text:
        return ''
    
    # Remove HTML tags
    text = re.sub('<[^<]+?>', '', text)
    # Remove extra whitespace
    text = ' '.join(text.split())
    # Remove Reddit formatting
    text = re.sub(r'\[link\].*?\[comments\]', '', text)
    text = re.sub(r'submitted by.*?to r/\w+', '', text)
    
    return text.strip()

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
    
    if any(word in text_lower for word in ['politic', 'election', 'parliament', 'government', 'minister', 'trudeau', 'liberal', 'conservative', 'ndp']):
        return 'politics'
    elif any(word in text_lower for word in ['business', 'economy', 'stock', 'market', 'finance', 'company', 'bank', 'dollar', 'trade']):
        return 'business'
    elif any(word in text_lower for word in ['sport', 'hockey', 'nhl', 'basketball', 'soccer', 'football', 'baseball', 'nba', 'mlb', 'raptors', 'leafs', 'canadiens']):
        return 'sports'
    elif any(word in text_lower for word in ['tech', 'technology', 'ai', 'software', 'digital', 'internet', 'cyber', 'data', 'computer', 'app']):
        return 'tech'
    elif any(word in text_lower for word in ['weather', 'temperature', 'forecast', 'storm', 'snow', 'rain', 'climate']):
        return 'weather'
    else:
        return 'general'

def remove_duplicates(articles):
    """Remove duplicate articles based on URL and title similarity"""
    seen_urls = set()
    seen_titles = set()
    unique_articles = []
    
    for article in articles:
        url = article.get('url', '')
        title = article.get('title', '').lower()
        
        # Check URL
        if url and url in seen_urls:
            continue
        
        # Check title similarity (first 50 chars)
        title_key = title[:50]
        if title_key in seen_titles:
            continue
        
        if url:
            seen_urls.add(url)
        if title:
            seen_titles.add(title_key)
        
        unique_articles.append(article)
    
    return unique_articles

def main():
    print("=" * 70)
    print("🍁 MYCITYNEWS.CA - Enhanced Canadian News Aggregator")
    print("=" * 70)
    
    # Fetch from all sources
    all_articles = []
    
    print("\n📰 Fetching from NewsAPI...")
    all_articles.extend(fetch_newsapi_articles())
    
    print("\n📡 Fetching from RSS feeds...")
    all_articles.extend(fetch_rss_feeds())
    
    print("\n💬 Fetching from social media...")
    all_articles.extend(fetch_social_feeds())
    
    print(f"\n📊 Total articles fetched: {len(all_articles)}")
    
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
    
    # Process articles
    all_articles = remove_duplicates(all_articles)
    print(f"📊 After removing duplicates: {len(all_articles)}")
    
    # Sort by published date (newest first)
    all_articles.sort(
        key=lambda x: x.get('published', ''), 
        reverse=True
    )
    
    # Limit total articles
    all_articles = all_articles[:MAX_ARTICLES]
    
    # Group by location for statistics
    locations = {}
    for article in all_articles:
        loc = article.get('location', 'Canada')
        locations[loc] = locations.get(loc, 0) + 1
    
    print(f"\n📍 Articles by location:")
    for loc, count in sorted(locations.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   {loc}: {count}")
    
    # Save to JSON
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
    
    print(f"\n✅ Successfully saved {len(all_articles)} articles to {ARTICLES_FILE}")
    print("=" * 70)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
