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
    print("Step 1: Fetching Delaware construction news from RSS...")
    # Search query: "Delaware construction" OR "Delaware development"
    rss_url = "https://news.google.com/rss/search?q=Delaware+construction+development+when:7d&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(rss_url)
    
    articles = []
    for entry in feed.entries[:15]: # Limit to top 15 recent stories
        articles.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.published
        })
    return articles

def analyze_news_with_grok(articles):
    print("Step 2: Asking Grok to filter for relevant project news...")
    
    prompt = f"""
    Analyze the following list of news headlines. 
    1. Filter out anything NOT related to building construction (skip road/highway paving).
    2. For relevant articles, categorize them into: Healthcare, Government, Corporate, Education, Multi Family, Hospitality, Senior Living, or Retail.
    3. Return a JSON list of objects with: title, source_url, sector, and summary.

    Headlines:
    {json.dumps(articles)}
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
        # Clean the output
        content = response.choices[0].message.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        
        return json.loads(content)
    except Exception as e:
        print(f"Grok Analysis Error: {e}")
        return []

def send_to_lovable(news_items):
    if not news_items:
        print("No relevant news found.")
        return

    print(f"Step 3: Sending {len(news_items)} news items to Lovable...")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    }
    
    # We send it with a 'news' key so your Lovable function knows where to put it
    response = requests.post(WEBHOOK_URL, headers=headers, json={"news": news_items}, timeout=30)
    
    if response.status_code == 200:
        print("SUCCESS: News updated.")
    else:
        print(f"FAILED: {response.status_code}")

if __name__ == "__main__":
    raw_news = get_delaware_news()
    filtered_news = analyze_news_with_grok(raw_news)
    send_to_lovable(filtered_news)
