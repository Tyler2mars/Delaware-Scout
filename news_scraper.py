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
    print("Step 1: Fetching Delaware construction news from multiple sources...")
    
    # Multiple search queries to catch different types of projects
    rss_sources = [
        # General construction
        "https://news.google.com/rss/search?q=Delaware+construction+development+when:7d&hl=en-US&gl=US&ceid=US:en",
        
        # Specific project types
        "https://news.google.com/rss/search?q=Delaware+hospital+medical+construction+when:7d&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Delaware+apartment+multifamily+construction+when:7d&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Delaware+office+building+construction+when:7d&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Delaware+school+university+construction+when:7d&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Delaware+hotel+hospitality+construction+when:7d&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Delaware+retail+shopping+construction+when:7d&hl=en-US&gl=US&ceid=US:en",
        
        # Major Delaware cities
        "https://news.google.com/rss/search?q=Wilmington+Delaware+construction+when:7d&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Dover+Delaware+construction+when:7d&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Newark+Delaware+construction+when:7d&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Rehoboth+Beach+construction+when:7d&hl=en-US&gl=US&ceid=US:en",
        
        # Commercial real estate terms
        "https://news.google.com/rss/search?q=Delaware+renovation+remodel+when:7d&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Delaware+commercial+real+estate+when:7d&hl=en-US&gl=US&ceid=US:en",
    ]
    
    all_articles = []
    seen_urls = set()
    
    for rss_url in rss_sources:
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:10]:  # Top 10 from each source
                # Deduplicate by URL
                if entry.link not in seen_urls:
                    seen_urls.add(entry.link)
                    all_articles.append({
                        "title": entry.title,
                        "link": entry.link,
                        "published": entry.published
                    })
        except Exception as e:
            print(f"Error fetching from {rss_url[:50]}...: {e}")
            continue
    
    print(f"Found {len(all_articles)} unique articles from {len(rss_sources)} sources")
    return all_articles

def analyze_news_with_grok(articles):
    print("Step 2: Asking Grok to filter for relevant project news...")
    
    # Updated prompt to ensure proper format and extract more details
    prompt = f"""
    Analyze the following list of news headlines. 
    
    FILTERING RULES:
    1. INCLUDE: Building construction, renovations, tenant improvements, new facilities
    2. EXCLUDE: Road/highway paving, bridge construction, infrastructure (unless it includes a building)
    3. EXCLUDE: Articles just about financing, sales, or leasing (unless construction is mentioned)
    
    CATEGORIZATION:
    Categorize into EXACTLY ONE sector: Healthcare, Government, Corporate, Education, Multi Family, Hospitality, Senior Living, or Retail.
    
    EXTRACTION REQUIREMENTS:
    For each relevant article, extract:
    - title: Article headline
    - source_url: Full URL
    - sector: One of the exact sector names above
    - summary: 2-3 sentence summary including project details
    - location: Specific city/area in Delaware (e.g., "Wilmington", "Dover", "Newark")
    - estimated_sq_ft: Square footage if mentioned (number only, or null)
    - project_value: Dollar value if mentioned (number only, or null)
    - developer: Developer/owner name if mentioned (or null)
    - contractor: General contractor if mentioned (or null)
    - project_phase: "Planning", "Permitting", "Under Construction", or "Completed" (best guess)
    - opportunity_score: Rate 1-10 based on: size (bigger=higher), detail level (more detail=higher), timeline urgency (sooner=higher)
    
    Return ONLY a valid JSON array with this exact structure:
    [
      {{
        "title": "Article title",
        "source_url": "Full URL",
        "sector": "Healthcare",
        "summary": "Detailed summary with key facts",
        "location": "Wilmington",
        "estimated_sq_ft": 50000,
        "project_value": 15000000,
        "developer": "ABC Development Corp",
        "contractor": "XYZ Construction",
        "project_phase": "Under Construction",
        "opportunity_score": 8
      }}
    ]
    
    CRITICAL: 
    - Use EXACT sector names (case-sensitive)
    - Return ONLY the JSON array, no explanatory text
    - Use null for fields you can't extract
    
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
            
            # Build cleaned item with all fields
            cleaned_item = {
                "title": str(item["title"]).strip(),
                "source_url": str(item["source_url"]).strip(),
                "sector": str(item["sector"]).strip(),
                "summary": str(item["summary"]).strip(),
            }
            
            # Add optional fields if they exist and aren't null
            optional_fields = ["location", "estimated_sq_ft", "project_value", 
                             "developer", "contractor", "project_phase", "opportunity_score"]
            
            for field in optional_fields:
                if field in item and item[field] is not None and item[field] != "null":
                    cleaned_item[field] = item[field]
            
            cleaned_items.append(cleaned_item)
        
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
