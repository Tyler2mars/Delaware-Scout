import os
import json
import requests
import feedparser
from openai import OpenAI

# 1. Setup Grok Client
client = OpenAI(
    api_key=os.environ.get("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
)

WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

def get_delaware_news():
    print("Step 1: Fetching statewide Delaware construction news (Lookback: 3 days)...")
    
    # IMPROVEMENT #2: Intent-based keywords for early-phase discovery
    intent_query = "%28proposed+OR+approved+OR+zoning+OR+%22breaking+ground%22%29"
    
    rss_sources = [
        # --- STATEWIDE & SECTOR SPECIFIC ---
        f"https://news.google.com/rss/search?q=Delaware+construction+{intent_query}+when:4d&hl=en-US&gl=US&ceid=US:en",
        f"https://news.google.com/rss/search?q=Delaware+hospital+medical+construction+when:4d&hl=en-US&gl=US&ceid=US:en",
        f"https://news.google.com/rss/search?q=Delaware+apartment+multifamily+construction+when:4d&hl=en-US&gl=US&ceid=US:en",
        f"https://news.google.com/rss/search?q=Delaware+commercial+real+estate+new+project+when:4d&hl=en-US&gl=US&ceid=US:en",
        
        # --- COUNTY SWEEPS (Covers rural and suburban Delaware) ---
        f"https://news.google.com/rss/search?q=%22New+Castle+County%22+construction+{intent_query}+when:4d&hl=en-US&gl=US&ceid=US:en",
        f"https://news.google.com/rss/search?q=%22Kent+County%22+Delaware+construction+{intent_query}+when:4d&hl=en-US&gl=US&ceid=US:en",
        f"https://news.google.com/rss/search?q=%22Sussex+County%22+Delaware+construction+{intent_query}+when:4d&hl=en-US&gl=US&ceid=US:en",
        
        # --- MAJOR CITIES & GROWTH HUBS ---
        f"https://news.google.com/rss/search?q=Wilmington+Delaware+construction+{intent_query}+when:4d&hl=en-US&gl=US&ceid=US:en",
        f"https://news.google.com/rss/search?q=Dover+Delaware+construction+{intent_query}+when:4d&hl=en-US&gl=US&ceid=US:en",
        f"https://news.google.com/rss/search?q=Newark+Delaware+construction+{intent_query}+when:4d&hl=en-US&gl=US&ceid=US:en",
        f"https://news.google.com/rss/search?q=Middletown+Delaware+construction+{intent_query}+when:4d&hl=en-US&gl=US&ceid=US:en",
        f"https://news.google.com/rss/search?q=Smyrna+Delaware+construction+{intent_query}+when:4d&hl=en-US&gl=US&ceid=US:en",
        f"https://news.google.com/rss/search?q=Milford+Delaware+construction+{intent_query}+when:4d&hl=en-US&gl=US&ceid=US:en",
        
        # --- COASTAL/REGIONAL ---
        f"https://news.google.com/rss/search?q=%28Rehoboth+OR+Lewes+OR+Seaford%29+construction+{intent_query}+when:4d&hl=en-US&gl=US&ceid=US:en",
    ]
    
    all_articles = []
    seen_urls = set()
    
    for rss_url in rss_sources:
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:10]:
                if entry.link not in seen_urls:
                    seen_urls.add(entry.link)
                    all_articles.append({
                        "title": entry.title,
                        "link": entry.link,
                        "published": entry.published
                    })
        except Exception as e:
            print(f"Error fetching from {rss_url[:40]}...: {e}")
            continue
    
    print(f"Found {len(all_articles)} unique articles across Delaware.")
    return all_articles

def analyze_news_with_grok(articles):
    print("Step 2: Grok analysis and filtering...")
    if not articles: return []

    prompt = f"""
    Analyze these Delaware news headlines.
    
    FILTERING: Include only building construction, renovations, and new facilities.
    EXCLUDE: Pure roadwork, paving, or real estate sales without a construction component.
    
    CATEGORIES: Healthcare, Government, Corporate, Education, Multi Family, Hospitality, Senior Living, or Retail.
    
    EXTRACT: title, source_url, sector, summary (2-3 sentences), location, estimated_sq_ft, project_value, developer, contractor, project_phase, opportunity_score (1-10).
    
    Return ONLY a JSON array. Use null for unknown values.
    Headlines: {json.dumps(articles)}
    """
    
    try:
        response = client.chat.completions.create(
            model="grok-4-1-fast-non-reasoning",
            messages=[
                {"role": "system", "content": "You are a construction analyst. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        content = response.choices[0].message.content.strip()
        # Cleaning markdown formatting if Grok adds it
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        return json.loads(content)
    except Exception as e:
        print(f"Grok Analysis Error: {e}")
        return []

def send_to_lovable(news_items):
    if not news_items:
        print("No relevant news to send.")
        return
    
    print(f"Step 3: Sending {len(news_items)} items to Lovable...")
    try:
        response = requests.post(WEBHOOK_URL, json={"news": news_items}, timeout=30)
        print(f"Status: {response.status_code}")
    except Exception as e:
        print(f"Request Error: {e}")

if __name__ == "__main__":
    raw_news = get_delaware_news()
    filtered_news = analyze_news_with_grok(raw_news)
    send_to_lovable(filtered_news)
