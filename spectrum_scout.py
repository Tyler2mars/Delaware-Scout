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

WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL") 
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

def normalize(text):
    """Cleans text/numbers for comparison."""
    if text is None: return ""
    # Convert to string, lowercase, and remove all non-alphanumeric
    text = str(text).lower()
    text = re.sub(r'\b(the|expansion|phase|project|inc|corp|llc|sqft|square|feet)\b', '', text)
    return re.sub(r'[^a-z0-9]', '', text).strip()

def get_existing_fingerprints():
    """Fetches existing leads to build Name+City+SqFt fingerprints."""
    print("Step 0: Checking website for existing projects...")
    headers = {
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "apikey": SUPABASE_ANON_KEY
    }
    
    # Deriving the REST URL from your Webhook URL
    base_rest_url = WEBHOOK_URL.split('/functions/')[0]
    # We now fetch name, city, AND estimated_sqft
    table_url = f"{base_rest_url}/rest/v1/projects?select=name,city,estimated_sqft"
    
    try:
        response = requests.get(table_url, headers=headers, timeout=15)
        if response.status_code == 200:
            existing = response.json()
            # New Fingerprint: name + city + sqft
            return {
                f"{normalize(p['name'])}_{normalize(p['city'])}_{normalize(p['estimated_sqft'])}" 
                for p in existing
            }
        return set()
    except Exception as e:
        print(f"Warning: Could not fetch existing projects ({e})")
        return set()

def get_leads():
    print("Step 1: Asking Grok for Delaware construction leads...")
    prompt = """Find 15 real, major upcoming commercial construction or infrastructure projects in Delaware (2026-2028).
    Return ONLY a JSON list. 
    Each object MUST have: name, address, city, county, sector, budget, source_url, designer, 
    general_contractor, deadline, latitude, longitude, description, flooring_tags, estimated_sqft.
    """
    try:
        response = client.chat.completions.create(
            model="grok-4-1-fast-non-reasoning",
            messages=[{"role": "system", "content": "Return valid JSON lists only."},
                      {"role": "user", "content": prompt}],
            temperature=0.1
        )
        raw_content = response.choices[0].message.content.strip()
        if raw_content.startswith("```"):
            raw_content = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
            if raw_content.startswith("json"): raw_content = raw_content[4:].strip()
        return json.loads(raw_content)
    except Exception as e:
        print(f"ERROR: {e}")
        return []

def send_to_supabase(leads):
    if not leads: return
    print(f"Step 2: Sending {len(leads)} NEW leads to Lovable...")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {SUPABASE_ANON_KEY}"}
    try:
        response = requests.post(WEBHOOK_URL, headers=headers, json={"leads": leads}, timeout=30)
        if response.status_code == 200: print("SUCCESS: Data accepted.")
        else: print(f"FAILED: {response.status_code}")
    except Exception as e: print(f"ERROR: {e}")

if __name__ == "__main__":
    existing_fingerprints = get_existing_fingerprints()
    raw_leads = get_leads()
    
    final_leads = []
    for lead in raw_leads:
        # Build the 3-part fingerprint
        name_part = normalize(lead.get('name'))
        city_part = normalize(lead.get('city'))
        sqft_part = normalize(lead.get('estimated_sqft'))
        
        fingerprint = f"{name_part}_{city_part}_{sqft_part}"
        
        if fingerprint not in existing_fingerprints:
            final_leads.append(lead)
            existing_fingerprints.add(fingerprint)
        else:
            print(f"Duplicate found: {lead.get('name')} ({lead.get('estimated_sqft')} sqft)")
    
    send_to_supabase(final_leads)
