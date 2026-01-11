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
    
    # Updated prompt to ensure proper format
    prompt = f"""
    Analyze the following list of news headlines. 
    1. Filter out anything NOT related to building construction (skip road/highway paving).
    2. For relevant articles, categorize them into EXACTLY ONE of these sectors: Healthcare, Government, Corporate, Education, Multi Family, Hospitality, Senior Living, or Retail.
    3. Return ONLY a valid JSON array with this exact structure:
    [
      {{
        "title": "Article title here",
        "source_url": "Full URL here",
        "sector": "One of the exact sector names listed above",
        "summary": "Brief summary of the project"
      }}
    ]
    
    IMPORTANT: 
    - Use EXACT sector names (case-sensitive): Healthcare, Government, Corporate, Education, Multi Family, Hospitality, Senior Living, or Retail
    - source_url must be the complete URL from the article
    - Return ONLY the JSON array, no explanatory text
    
    Headlines:
    {json.dumps(articles, indent=2)}
    """
    
    try:
        response = client.chat.completions.create(
            model="grok-4-1-fast-non-reasoning",
            messages=[
                {"role": "system", "content": "You are a construction analyst. Return valid JSON only with no markdown formatting."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        # Clean the output
        content = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        parsed = json.loads(content)
        
        # Validate and clean the data
        valid_sectors = ["Healthcare", "Government", "Corporate", "Education", 
                        "Multi Family", "Hospitality", "Senior Living", "Retail"]
        
        cleaned_items = []
        for item in parsed:
            # Ensure all required fields exist
            if not all(key in item for key in ["title", "source_url", "sector"]):
                print(f"Skipping item missing required fields: {item}")
                continue
            
            # Validate sector
            if item["sector"] not in valid_sectors:
                print(f"Invalid sector '{item['sector']}' for article: {item['title']}")
                continue
            
            # Ensure summary exists (use title if missing)
            if "summary" not in item or not item["summary"]:
                item["summary"] = item["title"]
            
            cleaned_items.append({
                "title": str(item["title"]).strip(),
                "source_url": str(item["source_url"]).strip(),
                "sector": str(item["sector"]).strip(),
                "summary": str(item["summary"]).strip()
            })
        
        print(f"Successfully parsed {len(cleaned_items)} valid news items")
        return cleaned_items
        
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        print(f"Raw content: {content}")
        return []
    except Exception as e:
        print(f"Grok Analysis Error: {e}")
        return []

def send_to_lovable(news_items):
    if not news_items:
        print("No relevant news found.")
        return
    
    print(f"Step 3: Sending {len(news_items)} news items to Lovable...")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {"news": news_items}
    
    # Debug: Print what we're sending
    print(f"Payload preview: {json.dumps(payload, indent=2)[:500]}...")
    
    try:
        response = requests.post(
            WEBHOOK_URL, 
            headers=headers, 
            json=payload, 
            timeout=30
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: News updated.")
            result = response.json()
            print(f"Details: {result}")
        else:
            print(f"❌ FAILED: {response.status_code}")
            print(f"Error details: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request Error: {e}")

if __name__ == "__main__":
    raw_news = get_delaware_news()
    filtered_news = analyze_news_with_grok(raw_news)
    send_to_lovable(filtered_news)
