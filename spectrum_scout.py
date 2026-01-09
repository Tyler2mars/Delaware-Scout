import os
import requests
import json

# Configuration
WEBHOOK_URL = "https://eggntbwidigxoapturvn.supabase.co/functions/v1/scrape-leads"
XAI_API_KEY = os.environ.get("XAI_API_KEY")

def get_leads_from_grok():
    print("🤖 Grok is researching Delaware projects...")
    
    # Expanded prompt to include all 10 fields matching your database columns
    master_prompt = """
    Search for upcoming commercial construction and renovation projects in Delaware from September 2025 through December 2027 
    that could involve flooring sales opportunities, excluding warehouse buildings. 
    
    Focus on sectors: offices, retail, healthcare, education, hospitality, non-warehouse industrial, and government.
    
    IMPORTANT: Return the data ONLY as a JSON array of objects. 
    Each object must have these EXACT keys: 
    "name", "address", "sector", "budget", "source", "designer", "latitude", "longitude", "general_contractor", "deadline"
    
    Ensure latitude and longitude are numbers, not strings. Use null if data is missing for a specific field.
    """

    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "grok-2-latest", 
        "messages": [{"role": "user", "content": master_prompt}]
    }

    try:
        response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=data)
        response.raise_for_status() # Check for HTTP errors
        
        raw_content = response.json()['choices'][0]['message']['content']
        
        # Clean the response in case Grok includes markdown code blocks
        clean_json = raw_content.strip().replace('```json', '').replace('```', '')
        return json.loads(clean_json)
        
    except Exception as e:
        print(f"❌ Error during Grok research: {e}")
        return []

def push_to_supabase(leads):
    if not leads:
        print("⚠️ No leads found to push.")
        return

    print(f"🚀 Pushing {len(leads)} Grok-verified leads to Supabase...")
    
    # We wrap the array in a 'leads' key to match your Edge Function logic
    payload = {"leads": leads}
    
    try:
        response = requests.post(
            WEBHOOK_URL, 
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("✅ Successfully updated Supabase table editor!")
        else:
            print(f"❌ Database Rejection: {response.status_code}")
            print(f"Details: {response.text}")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

# Entry point for the script
if __name__ == "__main__":
    if not XAI_API_KEY:
        print("❌ Error: XAI_API_KEY not found in environment variables.")
    else:
        leads_data = get_leads_from_grok()
        push_to_supabase(leads_data)
