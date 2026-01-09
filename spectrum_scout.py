import os
import json
import requests
import re
from openai import OpenAI

# 1. Setup Client
client = OpenAI(
    api_key=os.environ.get("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
)

# Configuration
WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL") 
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

def normalize(text):
    """Cleans text for comparison: lowercase, removes punctuation/common filler words."""
    if not text: return ""
    text = text.lower()
    # Remove common filler words that vary between news sources
    text = re.sub(r'\b(the|expansion|phase|project|inc|corp|llc)\b', '', text)
    # Remove all non-alphanumeric characters and extra spaces
    return re.sub(r'[^a-z0-9]', '', text).strip()

def get_existing_fingerprints():
    """Fetches existing leads from Lovable to prevent duplicates."""
    print("Step 0: Checking website for existing projects...")
    headers = {
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "apikey": SUPABASE_ANON_KEY
    }
    
    # We derive the base REST URL from your Webhook URL
    # Webhook: https://[ID].supabase.co/functions/v1/scrape-leads
    # REST API: https://[ID].supabase.co/rest/v1/projects
    base_rest_url = WEBHOOK_URL.split('/functions/')[0]
    # Adjust 'projects' if your table name in Lovable is different (e.g., 'leads')
    table_url = f"{base_rest_url}/rest/v1/projects?select=name,city"
    
    try:
        response = requests.get(table_url, headers=headers, timeout=15)
        if response.status_code == 200:
            existing = response.json()
            # Create a set of "name+city" fingerprints for fast lookup
            return {f"{normalize(p['name'])}_{normalize(p['city'])}" for p in existing}
        print(f"Note: Could not fetch existing data (Status {response.status_code}).")
        return set()
    except Exception as e:
        print(f"Warning: Could not fetch existing projects ({e}). Proceeding without filter.")
        return set()

def get_leads():
    print("Step 1: Asking Grok for Delaware construction leads...")
    
    prompt = """Find 15 real, major upcoming commercial construction or infrastructure projects in Delaware scheduled for 2026-2028.
    Return ONLY a JSON list of objects. Do not include introductory text.
    Each object MUST have:
    - name: Project name
    - address: Location in Delaware
    - city: City name
    - county: County name
    - sector: (Choose one: Healthcare, Government, Corporate, Education, Multi Family, Hospitality, Senior Living, Retail)
    - budget: Estimated cost
    - source_url: A link to a news article or planning document
    - designer: Architectural or engineering firm
    - general_contractor: GC name or 'TBD'
    - deadline: Estimated completion date
    - latitude: Numeric latitude
    - longitude: Numeric longitude
    - description: Short summary of the project
    - flooring_tags: A list of strings (e.g., ["LVT", "Carpet", "Tile"])
    - estimated_sqft: A numeric value for square footage
    """

    try:
        response = client.chat.completions.create(
            model="grok-4-1-fast-non-reasoning",
            messages=[
                {"role": "system", "content": "You are a data extraction specialist. Always return valid JSON lists."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        raw_content = response.choices[0].message.content.strip()
        if raw_content.startswith("```"):
            raw_content = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
            if raw_content.startswith("json"):
                raw_content = raw_content[4:].strip()

        return json.loads(raw_content)

    except Exception as e:
        print(f"ERROR during AI search: {e}")
        return []

def send_to_supabase(leads):
    if not leads:
        print("No new unique leads to send. Skipping update.")
        return

    print(f"Step 2: Sending {len(leads)} NEW leads to Lovable Cloud...")
    
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
        }
        
        response = requests.post(
            WEBHOOK_URL,
            headers=headers,
            json={"leads": leads},
            timeout=30
        )
        
        if response.status_code == 200:
            print("SUCCESS: Data accepted by Lovable Cloud.")
        else:
            print(f"FAILED: Status {response.status_code} - {response.text}")

    except Exception as e:
        print(f"ERROR sending to Supabase: {e}")

if __name__ == "__main__":
    # 1. See what we already have
    existing_fingerprints = get_existing_fingerprints()
    
    # 2. Get fresh leads from Grok
    raw_leads = get_leads()
    
    # 3. Filter duplicates locally
    final_leads = []
    for lead in raw_leads:
        # Create unique fingerprint for this project
        fingerprint = f"{normalize(lead['name'])}_{normalize(lead['city'])}"
        
        if fingerprint not in existing_fingerprints:
            final_leads.append(lead)
            # Add to local set so we don't duplicate within the same AI run
            existing_fingerprints.add(fingerprint)
        else:
            print(f"Skipping duplicate: {lead['name']} in {lead['city']}")
    
    # 4. Push final results
    send_to_supabase(final_leads)
