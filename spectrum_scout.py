import os
import requests
import json

# Configuration
XAI_API_KEY = os.environ.get("XAI_API_KEY")
WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL")

def scout_delaware_projects():
    print("🚀 Starting Delaware Weekly Scout (Target: 20 Leads)...")
    
    # We explicitly ask for 20 leads and the 2026-2028 timeline
    master_prompt = """
    Identify exactly 20 commercial or public construction projects in Delaware.
    
    CRITICAL FILTERS:
    1. Physical construction start date must be between January 2026 and January 2028.
    2. Focus on Planning, Bidding, Permitting, or Pre-construction phases.
    
    For each project, return a JSON list of objects with: 
    'name', 'address', 'sector', 'budget', 'source_url', 'designer', 'latitude', 'longitude', 'general_contractor', and 'deadline'.
    
    Output ONLY a valid JSON array. No conversational text.
    """

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {XAI_API_KEY}"
    }

    data = {
        "model": "grok-4-1-fast-non-reasoning", 
        "messages": [
            {"role": "system", "content": "You are a professional construction researcher. Return only raw JSON data."},
            {"role": "user", "content": master_prompt}
        ],
        "temperature": 0.1,    # Tiny bit of variety to help find a larger list of 20
        "max_tokens": 3000     # INCREASED: 20 projects require more space to write
    }

    try:
        response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=data)
        response.raise_for_status()
        
        content = response.json()['choices'][0]['message']['content']
        clean_json = content.replace("```json", "").replace("```", "").strip()
        leads = json.loads(clean_json)

        print(f"✅ Successfully found {len(leads)} leads. Sending to Supabase...")
        
        db_response = requests.post(
            WEBHOOK_URL, 
            headers={"Content-Type": "application/json"}, 
            json={"leads": leads}
        )
        
        if db_response.status_code == 200:
            print("🎉 Database updated successfully!")
        else:
            print(f"❌ Supabase Error: {db_response.text}")

    except Exception as e:
        print(f"⚠️ Error: {e}")

if __name__ == "__main__":
    scout_delaware_projects()
