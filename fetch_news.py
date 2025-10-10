import requests
import feedparser
import json
import os
from datetime import datetime, timedelta

# Configuration
NEWSAPI_KEY = os.environ.get('NEWSAPI_KEY', '')
MAX_ARTICLES = 50
ARTICLES_FILE = 'articles.json'

# RSS Feeds for Canadian news
RSS_FEEDS = [
    'https://www.cbc.ca/cmlink/rss-topstories',
    'https://www.cbc.ca/cmlink/rss-canada',
    'https://globalnews.ca/feed/',
    'https://www.cp24.com/feed',
    'https://www.citynews.ca/feed/',
]

def fetch_newsapi_articles():
    """Fetch articles from NewsAPI"""
    articles = []
    
    if not NEWSAPI_KEY:
        print("⚠️  No NewsAPI key found, skipping NewsAPI")
        return articles
    
    url = 'https://newsapi.org/v2/everything'
    params = {
        'q': 'Canada OR Canadian OR Toronto OR Vancouver OR Montreal',
        'language': 'en',
        'sortBy': 'publishedAt',
        'pageSize': 30,
        'apiKey': NEWSAPI_KEY
    }
    
    try:
        print("Fetching from NewsAPI...")
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get('status') == 'ok':
            for article in data.get('articles', []):
                if article.get('title') and article.get('url'):
                    articles.append({
                        'title': article.get('title', '').strip(),
                        'description': article.get('description', '').strip() if article.get('description') else '',
                        'url': article.get('url', ''),
                        'source': article.get('source', {}).get('name', 'Unknown'),
                        'image': article.get('urlToImage', ''),
                        'published': article.get('publishedAt', ''),
                        'fetched_at': datetime.now().isoformat()
                    })
            print(f"✓ Fetched {len(articles)} articles from NewsAPI")
        else:
            print(f"⚠️  NewsAPI error: {data.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"⚠️  NewsAPI exception: {e}")
    
    return articles

def fetch_rss_feeds():
    """Fetch articles from RSS feeds"""
    articles = []
    
    for feed_url in RSS_FEEDS:
        try:
            print(f"Fetching from: {feed_url}")
            feed = feedparser.parse(feed_url)
            
            if not feed.entries:
                print(f"⚠️  No entries found in feed")
                continue
                
            source_name = feed.feed.get('title', 'Unknown Source')
            
            for entry in feed.entries[:10]:
                if not entry.get('link'):
                    continue
                
                # Extract image
                image_url = ''
                try:
                    if hasattr(entry, 'media_content') and len(entry.media_content) > 0:
                        image_url = entry.media_content[0].get('url', '')
                    elif hasattr(entry, 'media_thumbnail') and len(entry.media_thumbnail) > 0:
                        image_url = entry.media_thumbnail[0].get('url', '')
                    elif hasattr(entry, 'enclosures') and len(entry.enclosures) > 0:
                        if 'image' in entry.enclosures[0].get('type', ''):
                            image_url = entry.enclosures[0].get('href', '')
                except:
                    pass
                
                # Clean up description
                description = entry.get('summary', '')
                if description:
                    # Remove HTML tags
                    import re
                    description = re.sub('<[^<]+?>', '', description)
                    description = description.strip()
                
                articles.append({
                    'title': entry.get('title', '').strip(),
                    'description': description,
                    'url': entry.get('link', ''),
                    'source': source_name,
                    'image': image_url,
                    'published': entry.get('published', datetime.now().isoformat()),
                    'fetched_at': datetime.now().isoformat()
                })
            
            print(f"✓ Fetched {len([e for e in feed.entries[:10] if e.get('link')])} articles from {source_name}")
        except Exception as e:
            print(f"⚠️  RSS feed error ({feed_url}): {e}")
            continue
    
    return articles

def remove_duplicates(articles):
    """Remove duplicate articles based on URL"""
    seen_urls = set()
    unique_articles = []
    
    for article in articles:
        url = article.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)
    
    return unique_articles

def filter_by_keywords(articles):
    """Keep only articles with Canadian keywords"""
    canadian_keywords = [
        'canada', 'canadian', 'toronto', 'vancouver', 'montreal', 'ottawa',
        'calgary', 'edmonton', 'quebec', 'winnipeg', 'halifax', 'ontario',
        'british columbia', 'alberta', 'bc', 'trudeau', 'parliament'
    ]
    
    filtered = []
    for article in articles:
        text = (article.get('title', '') + ' ' + article.get('description', '')).lower()
        if any(keyword in text for keyword in canadian_keywords):
            filtered.append(article)
    
    # If we filtered too aggressively, keep all articles
    if len(filtered) < 10 and len(articles) > 0:
        return articles
    
    return filtered

def main():
    print("=" * 60)
    print("🍁 MYCITYNEWS.CA - Fetching Canadian News")
    print("=" * 60)
    
    # Fetch from all sources
    all_articles = []
    
    # Try NewsAPI first
    newsapi_articles = fetch_newsapi_articles()
    all_articles.extend(newsapi_articles)
    
    # Fetch from RSS feeds
    rss_articles = fetch_rss_feeds()
    all_articles.extend(rss_articles)
    
    print(f"\n📊 Total articles fetched: {len(all_articles)}")
    
    if len(all_articles) == 0:
        print("⚠️  No articles fetched! Check your API key and internet connection.")
        # Create empty file so website doesn't break
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
    
    # Filter for Canadian content
    all_articles = filter_by_keywords(all_articles)
    print(f"📊 After filtering for Canadian content: {len(all_articles)}")
    
    # Sort by published date (newest first)
    all_articles.sort(
        key=lambda x: x.get('published', ''), 
        reverse=True
    )
    
    # Limit total articles
    all_articles = all_articles[:MAX_ARTICLES]
    
    # Save to JSON
    output = {
        'last_updated': datetime.now().isoformat(),
        'total_articles': len(all_articles),
        'articles': all_articles
    }
    
    with open(ARTICLES_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Successfully saved {len(all_articles)} articles to {ARTICLES_FILE}")
    print("=" * 60)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
