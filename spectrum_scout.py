import os
import requests
import json

# 1. Configuration - Use your Secret in GitHub Settings for the API Key
XAI_API_KEY = os.environ.get("XAI_API_KEY")
# Your Supabase Edge Function URL
WEBHOOK_URL = "https://eggntbwidigxoapturvn.supabase.co/functions/v1/scrape-leads"

def scout_delaware_projects():
    print("🚀 Starting Delaware Project Scout...")
    
    # The prompt tells Grok exactly what to look for and how to format it
    master_prompt = """
    Search for the latest commercial construction projects, public works, or large-scale residential developments in Delaware from the last 30 days.
    Return a JSON list of exactly 10 projects. 
    For each project, include: 
    'name', 'address', 'sector', 'budget', 'source_url', 'designer', 'latitude', 'longitude', 'general_contractor', and 'deadline'.
    If a field is unknown, use "N/A". 
    Format the output as a valid JSON array of objects.
    """

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {XAI_API_KEY}"
    }

    # 2. Optimized Model Settings
    data = {
        "model": "grok-4-1-fast-non-reasoning", # The fastest and most cost-effective version
        "messages": [
            {"role": "system", "content": "You are a professional construction lead researcher. Output only raw JSON."},
            {"role": "user", "content": master_prompt}
        ],
        "temperature": 0,      # Keeps the AI factual and prevents "rambling"
        "max_tokens": 1200     # Hard cap to prevent high token costs
    }

    try:
        # Request data from xAI
        response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=data)
        response.raise_for_status()
        
        # Extract the JSON content from the AI response
        content = response.json()['choices'][0]['message']['content']
        
        # Clean the string in case Grok adds ```json markdown blocks
        clean_json = content.replace("```json", "").replace("```", "").strip()
        leads = json.loads(clean_json)

        # 3. Send to Supabase
        print(f"✅ Found {len(leads)} leads. Sending to Supabase...")
        db_response = requests.post(
            WEBHOOK_URL, 
            headers={"Content-Type": "application/json"}, 
            json={"leads": leads}
        )
        
        if db_response.status_code == 200:
            print("🎉 Successfully synced leads to Supabase!")
        else:
            print(f"❌ Supabase Error: {db_response.text}")

    except Exception as e:
        print(f"⚠️ An error occurred: {e}")

if __name__ == "__main__":
    scout_delaware_projects()
