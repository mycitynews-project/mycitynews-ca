#!/usr/bin/env python3
import json
from datetime import datetime

def generate_sitemap():
    try:
        with open('articles.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✓ Loaded {len(data)} articles")
    except FileNotFoundError:
        print("⚠ articles.json not found")
        data = []
    
    current_time = datetime.now().strftime('%Y-%m-%d')
    
    sitemap = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://mycitynews.ca/</loc>
    <lastmod>{current_time}</lastmod>
    <changefreq>hourly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://mycitynews.ca/#indigenous</loc>
    <lastmod>{current_time}</lastmod>
    <changefreq>hourly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://mycitynews.ca/#canada</loc>
    <lastmod>{current_time}</lastmod>
    <changefreq>hourly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://mycitynews.ca/#world</loc>
    <lastmod>{current_time}</lastmod>
    <changefreq>hourly</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>'''
    
    with open('sitemap.xml', 'w', encoding='utf-8') as f:
        f.write(sitemap)
    
    print("✓ Sitemap generated")
    
    # Generate robots.txt
    robots = """User-agent: *
Allow: /
Disallow: /ad-redirect.html

Sitemap: https://mycitynews.ca/sitemap.xml

User-agent: Googlebot
Crawl-delay: 0
"""
    
    with open('robots.txt', 'w', encoding='utf-8') as f:
        f.write(robots)
    
    print("✓ robots.txt generated")

if __name__ == '__main__':
    generate_sitemap()
