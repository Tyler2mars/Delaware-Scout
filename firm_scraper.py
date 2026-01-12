import os
import json
import requests
import re
import time
from xai_sdk import Client
from xai_sdk.chat import user, system
from xai_sdk.tools import web_search

# 1. Setup xAI Client
client = Client(api_key=os.environ.get("XAI_API_KEY"))

# 2. Configuration
WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

# Set to your verified table name
TABLE_NAME = "design_firms" 

def get_firms():
    cities = ["Wilmington, DE", "Dover, DE", "Lewes and Bethany Beach, DE", "Newark, DE"]
    all_verified_firms = []
    
    print(f"🚀 Starting Delaware A&D Firm Scout")

    for city in cities:
        if len(all_verified_firms) >= 15:
            break
            
        print(f"🔍 Searching for firms in {city}...")
        system_prompt = "You are a research agent. Find Architecture and Interior Design firms with physical studios in Delaware."
        user_prompt = f"Find 5 unique Architecture or Interior Design firms in {city}. Return ONLY a JSON array with name, address, city, state, website."

        try:
            chat = client.chat.create(model="grok-4-1-fast", tools=[web_search()])
            chat.append(system(system_prompt))
            chat.append(user(user_prompt))
            
            response = chat.sample()
            raw_content = response.content.strip()

            json_match = re.search(r'\[\s*\{.*\}\s*\]', raw_content, re.DOTALL)
            if json_match:
                batch = json.loads(re.sub(r',(\s*[}\]])', r'\1', json_match.group(0)))
                for firm in batch:
                    addr = firm.get('address', '').upper()
                    if "DE" in addr or "DELAWARE" in addr:
                        all_verified_firms.append(firm)
            time.sleep(1) 
        except Exception as e:
            print(f"  ⚠️ Search Error in {city}: {e}")
            continue

    return all_verified_firms

def check_for_duplicates(firms):
    """Checks the 'design_firms' table for existing website URLs."""
    if not firms:
        return []

    # Strip webhook URL to find the REST base URL
    project_url = WEBHOOK_URL.split('/functions/v1/')[0]
    rest_url = f"{project_url}/rest/v1/{TABLE_NAME}"
    
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json"
    }

    new_firms = []
    print(f"🔎 Filtering {len(firms)} found firms against table: '{TABLE_NAME}'")

    for firm in firms:
        website = firm.get('website')
        if not website:
            continue
            
        try:
            # Check if this website exists using Supabase eq filter
            query_url = f"{rest_url}?website=eq.{website}&select=website"
            response = requests.get(query_url, headers=headers)
            
            if response.status_code == 200:
                existing_data = response.json()
                if len(existing_data) == 0:
                    new_firms.append(firm)
                else:
                    print(f"  ⏭️ Already in database: {firm['name']}")
            else:
                # If checking fails, we include it to be safe
                print(f"  ⚠️ API {response.status_code} check failed for {firm['name']}. Adding anyway.")
                new_firms.append(firm)
        except Exception as e:
            # THIS IS THE FIXED EXCEPT BLOCK THAT WAS MISSING
            print(f"  ❌ Error verifying {firm['name']}: {e}")
            new_firms.append(firm)

    return new_firms

def send_to_supabase(firms):
    if not firms:
        print("✨ No new firms to upload.")
        return
        
    print(f"🚀 Uploading {len(firms)} NEW firms to Supabase...")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {SUPABASE_ANON_KEY}"}
    
    try:
        r = requests.post(WEBHOOK_URL, headers=headers, json={"firms": firms}, timeout=30)
        if r.status_code == 200:
            print("✅ Successfully updated Supabase!")
        else:
            print(f"✗ Webhook Error: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"❌ Upload Error: {e}")

if __name__ == "__main__":
    raw_list = get_firms()
    filtered_list = check_for_duplicates(raw_list)
    send_to_supabase(filtered_list[:10])
