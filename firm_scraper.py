import os
import json
import requests
import re
import time
from xai_sdk import Client
from xai_sdk.chat import user, system
from xai_sdk.tools import web_search

# 1. Setup
client = Client(api_key=os.environ.get("XAI_API_KEY"))
WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

# VERIFIED: The table name you confirmed
TABLE_NAME = "design_firms" 

def get_firms():
    # COMPREHENSIVE CITY LIST: Major hubs + boutique growth towns
    cities = [
        "Wilmington, DE", "Newark, DE", "Middletown, DE", "Dover, DE",
        "Hockessin, DE", "Milton, DE", "Smyrna, DE", "Milford, DE", 
        "Georgetown, DE", "Lewes, DE", "Rehoboth Beach, DE", 
        "Selbyville, DE", "Millsboro, DE", "Ocean View, DE"
    ]
    
    all_found_firms = []
    target_count = 20 # Aiming for a higher count with more cities
    
    print(f"🚀 Starting Delaware-wide Firm Scout (Target: {target_count})")

    for city in cities:
        if len(all_found_firms) >= target_count:
            break
            
        print(f"🔍 Scouting {city} and surrounding areas...")
        
        system_prompt = "You are a research agent specializing in the Delaware Architecture and Engineering market."
        
        # We add "nearby" logic to catch firms in tiny unincorporated towns
        user_prompt = f"""Find 5 unique Architecture or Interior Design firms with physical offices in or within 5 miles of {city}.
        
        STRICT: The address must be in Delaware.
        Return ONLY a JSON array of objects:
        [
          {{
            "name": "Firm Name",
            "address": "Full DE Street Address",
            "city": "Specific DE Town Name",
            "state": "DE",
            "website": "URL"
          }}
        ]"""

        try:
            chat = client.chat.create(model="grok-4-1-fast", tools=[web_search()])
            chat.append(system(system_prompt))
            chat.append(user(user_prompt))
            
            response = chat.sample()
            raw_content = response.content.strip()

            json_match = re.search(r'\[\s*\{.*\}\s*\]', raw_content, re.DOTALL)
            if json_match:
                # Clean and parse JSON
                batch = json.loads(re.sub(r',(\s*[}\]])', r'\1', json_match.group(0)))
                
                for firm in batch:
                    addr = firm.get('address', '').upper()
                    name = firm.get('name', '')
                    # Filter for DE and avoid duplicates within this session
                    if ("DE" in addr or "DELAWARE" in addr) and not any(f['name'].lower() == name.lower() for f in all_found_firms):
                        all_found_firms.append(firm)
                        print(f"  ✅ Found: {name}")
                
            time.sleep(1) # Safety delay

        except Exception as e:
            print(f"  ⚠️ Skip {city} due to error: {e}")
            continue

    return all_found_firms

def check_for_duplicates(firms):
    """Database Check: Ensures we don't upload what we already have."""
    if not firms:
        return []

    project_url = WEBHOOK_URL.split('/functions/v1/')[0]
    rest_url = f"{project_url}/rest/v1/{TABLE_NAME}"
    
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json"
    }

    new_firms = []
    print(f"\n🔎 Comparing {len(firms)} firms against database records...")

    for firm in firms:
        website = firm.get('website')
        if not website: continue
            
        try:
            # Check if website is already in the design_firms table
            query_url = f"{rest_url}?website=eq.{website}&select=website"
            res = requests.get(query_url, headers=headers)
            
            if res.status_code == 200 and len(res.json()) == 0:
                new_firms.append(firm)
            else:
                print(f"  ⏭️ Already exists: {firm['name']}")
        except:
            new_firms.append(firm)

    return new_firms

def send_to_supabase(firms):
    if not firms:
        print("✨ Database is already up to date.")
        return
        
    print(f"🚀 Uploading {len(firms)} NEW firms to Supabase...")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {SUPABASE_ANON_KEY}"}
    
    try:
        r = requests.post(WEBHOOK_URL, headers=headers, json={"firms": firms}, timeout=30)
        if r.status_code == 200:
            print("✅ SUCCESS!")
        else:
            print(f"✗ Error: {r.status_code}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    raw_list = get_firms()
    final_list = check_for_duplicates(raw_list)
    send_to_supabase(final_list)
