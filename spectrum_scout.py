import os
import json
import requests
from openai import OpenAI

# 1. Setup Client
client = OpenAI(
    api_key=os.environ.get("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
)

# 2. Update these in your GitHub Secrets or Environment
WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL") 
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

def get_leads():
    print("Step 1: Asking Grok for Delaware Vertical Construction leads...")
    
    # Updated Prompt: Strictly excludes Highways/Roads and focuses on Vertical (Building) construction
    prompt = """Find 10 real, major upcoming vertical construction projects in Delaware scheduled for 2026-2028.
    
    STRICT EXCLUSIONS: 
    - NO highway, road, bridge, or paving projects.
    - NO wastewater, sewer, or purely external utility projects.
    - NO DelDOT infrastructure projects.

    FOCUS: Only buildings that require interior finishing and flooring (offices, hospitals, schools, apartments).

    Return ONLY a JSON list of objects. Do not include introductory text.
    Each object MUST have:
    - name: Project name
    - address: Location in Delaware
    - city: City name (e.g., Wilmington, Dover)
    - county: (e.g., New Castle, Kent, Sussex)
    - sector: (Healthcare, Government, Corporate, Education, Multi Family, Hospitality, Senior Living, Retail)
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
                {"role": "system", "content": "You are a data extraction specialist focusing on vertical building construction. Always return valid JSON lists."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        raw_content = response.choices[0].message.content.strip()
        
        # Clean AI markdown markers
        if raw_content.startswith("```"):
            raw_content = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
            if raw_content.startswith("json"):
                raw_content = raw_content[4:].strip()

        leads = json.loads(raw_content)
        return leads

    except Exception as e:
        print(f"ERROR during AI search: {e}")
        return []

def send_to_supabase(leads):
    if not leads:
        print("No leads to send. Skipping Supabase update.")
        return

    print(f"Step 2: Sending {len(leads)} leads to Lovable Cloud...")
    
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
    new_leads = get_leads()
    send_to_supabase(new_leads)
