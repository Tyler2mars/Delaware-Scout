import os
import json
import requests
from openai import OpenAI

# 1. Setup Clients
# Using OpenAI client because xAI is fully compatible
client = OpenAI(
    api_key=os.environ.get("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
)

WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL")

def get_leads():
    print("Step 1: Asking Grok for Delaware construction leads...")
    
    # We use a highly specific prompt to force valid JSON
    prompt = """Find 20 real, major upcoming commercial construction or infrastructure projects in Delaware scheduled for 2026-2028.
    Return ONLY a JSON list of objects. Do not include introductory text.
    Each object MUST have:
    - name: Project name
    - address: Location in Delaware
    - sector: (e.g., Education, Healthcare, Transport)
    - budget: Estimated cost
    - source_url: A link to a news article or planning document
    - designer: Architectural or engineering firm
    - general_contractor: GC name or 'TBD'
    - deadline: Estimated completion date
    - latitude: Numeric latitude
    - longitude: Numeric longitude
    """

    try:
        response = client.chat.completions.create(
            model="grok-4.1-fast-non-reasoning",
            messages=[
                {"role": "system", "content": "You are a data extraction specialist. Always return valid JSON lists."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2 # Lower temperature = more consistent data
        )
        
        raw_content = response.choices[0].message.content.strip()
        
        # CLEANING STEP: Remove AI "markdown" markers if present
        if raw_content.startswith("```"):
            raw_content = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
            if raw_content.startswith("json"):
                raw_content = raw_content[4:].strip()

        leads = json.loads(raw_content)
        print(f"DEBUG: AI found {len(leads)} leads.")
        return leads

    except Exception as e:
        print(f"ERROR during AI search: {e}")
        print(f"RAW CONTENT RECEIVED: {raw_content if 'raw_content' in locals() else 'None'}")
        return []

def send_to_supabase(leads):
    if not leads:
        print("No leads to send. Skipping Supabase update.")
        return

    print(f"Step 2: Sending {len(leads)} leads to Supabase...")
    
    try:
        # We send the list as a dictionary key "leads" to match your Edge Function
        response = requests.post(
            WEBHOOK_URL,
            headers={"Content-Type": "application/json"},
            json={"leads": leads},
            timeout=30
        )
        
        if response.status_code == 200:
            print("SUCCESS: Data accepted by Supabase.")
        else:
            print(f"FAILED: Supabase returned {response.status_code}")
            print(f"Response Body: {response.text}")

    except Exception as e:
        print(f"ERROR sending to Supabase: {e}")

if __name__ == "__main__":
    new_leads = get_leads()
    send_to_supabase(new_leads)
