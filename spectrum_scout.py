import os
import json
import re
import requests
from xai_sdk import Client
from xai_sdk.chat import user, system
from xai_sdk.tools import web_search

# 1. Setup xAI Client
client = Client(api_key=os.environ.get("XAI_API_KEY"))

# 2. Environment Variables (from your .yml)
WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL") 
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

def get_leads():
    print("Step 1: Searching for Delaware Vertical Construction leads...")
    
    system_prompt = """You are a construction market intelligence specialist.
Find vertical building projects in Delaware in PLANNING or DESIGN phase.
Target interior flooring opportunities (Hospitals, Schools, Offices, Multifamily)."""

    # We use the exact column names from your CSV: architect, source, status, etc.
    user_prompt = """Find 10 REAL vertical construction projects in Delaware.
TODAY'S DATE: January 14, 2026. 
ONLY include projects with future start dates (Q2 2026+).

Return a JSON array of objects using these exact keys:
{
  "name": "Project Name",
  "address": "Street address",
  "city": "City",
  "county": "New Castle|Kent|Sussex",
  "sector": "Healthcare|Education|Corporate|Multi Family|Hospitality",
  "source": "Direct URL to news or planning doc",
  "status": "Planning|Design Phase|Permit Pending",
  "architect": "Architect Firm Name",
  "general_contractor": "GC Name or TBD",
  "estimated_sqft": 50000,
  "description": "Short summary of project",
  "flooring_tags": ["LVT", "Carpet", "Tile"],
  "latitude": 39.xxxx,
  "longitude": -75.xxxx,
  "notes": "Detailed flooring scope and timeline"
}"""

    try:
        chat = client.chat.create(
            model="grok-4-1-fast",
            tools=[web_search()],
        )
        
        chat.append(system(system_prompt))
        chat.append(user(user_prompt))
        
        print("🔍 Searching...")
        response = chat.sample()
        raw_content = response.content.strip()

        # Extract the JSON array block
        json_match = re.search(r'\[\s*{.*}\s*\]', raw_content, re.DOTALL)
        if json_match:
            raw_content = json_match.group(0)
        
        leads = json.loads(raw_content)
        return leads
        
    except Exception as e:
        print(f"❌ Error during search: {e}")
        return []

def send_to_supabase(leads):
    if not leads:
        print("⚠️ No leads found to send.")
        return
    
    print(f"\nStep 2: Sending {len(leads)} leads to Supabase...")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    }
    
    # THE FIX: Wrap the list in a dictionary with the key "leads"
    # This matches the error requirement: 'Request body must contain a "leads" array'
    payload = {"leads": leads}
    
    try:
        response = requests.post(
            WEBHOOK_URL, 
            headers=headers, 
            json=payload, 
            timeout=30
        )
        
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            print("✅ Data successfully synced to Supabase/Lovable!")
        else:
            print(f"❌ DATABASE REJECTED DATA: {response.status_code}")
            print(f"📝 Error Details: {response.text}")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    results = get_leads()
    send_to_supabase(results)
