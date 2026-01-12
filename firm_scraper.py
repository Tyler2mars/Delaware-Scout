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
# IMPORTANT: Set your actual table name here
TABLE_NAME = "architect_firms" 

def get_firms():
    cities = ["Wilmington, DE", "Dover, DE", "Lewes and Bethany Beach, DE", "Newark, DE"]
    all_verified_firms = []
    
    print(f"🚀 Starting Delaware A&D Firm Scout")

    for city in cities:
        if len(all_verified_firms) >= 15: # Aim for a slightly larger pool before filtering
            break
            
        print(f"🔍 Searching for firms in {city}...")
        
        system_prompt = "You are a business research agent. Find active Architecture and Interior Design firms with physical studios in Delaware. Return ONLY valid JSON."
        user_prompt = f"Find 5 unique Architecture or Interior Design firms with physical offices in {city}. Return a JSON array with 'name', 'address', 'city', 'state', 'website'."

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
                    if ("DE" in addr or "DELAWARE" in addr):
                        all_verified_firms.append(firm)
            
            time.sleep(1) 
        except Exception as e:
            print(f"  ⚠️ Error in {city}: {e}")
            continue

    return all_verified_firms

def check_for_duplicates(firms):
    """Checks each firm against the Supabase REST API to see if it already exists."""
    if not firms:
        return []

    # Construct the REST URL from your Webhook URL
    # Webhook: https://project.supabase.co/functions/v1/webhook
    # REST:    https://project.supabase.co/rest/v1/table_name
    project_url = WEBHOOK_URL.split('/functions/v1/')[0]
    rest_url = f"{project_url}/rest/v1/{TABLE_NAME}"
    
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json"
    }

    new_firms = []
    print(f"🔎 Filtering {len(firms)} found firms against Supabase records...")

    for firm in firms:
        website = firm.get('website')
        if not website:
            continue
            
        try:
            # Query: "Select where website equals the current firm's website"
            query_url = f"{rest_url}?website=eq.{website}&select=website"
            response = requests.get(query_url, headers=headers)
            
            if response.status_code == 200:
                existing_data = response.json()
                if len(existing_data) == 0:
                    new_firms.append(firm)
