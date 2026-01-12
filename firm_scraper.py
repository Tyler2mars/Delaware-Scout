import os
import json
import requests
import re
import time
from xai_sdk import Client
from xai_sdk.chat import user, system
from xai_sdk.tools import web_search

client = Client(api_key=os.environ.get("XAI_API_KEY"))

WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

def get_firms():
    # We rotate through these cities to ensure we find real local offices
    cities = ["Wilmington, DE", "Dover, DE", "Lewes and Bethany Beach, DE", "Newark, DE"]
    all_verified_firms = []
    
    print(f"🚀 Starting Delaware A&D Firm Scout (Target: 10 firms)")

    for city in cities:
        if len(all_verified_firms) >= 10:
            break
            
        print(f"🔍 Searching for firms in {city}...")
        
        system_prompt = "You are a business research agent. Use web search to find active Architecture and Interior Design firms with physical studios in Delaware."
        
        user_prompt = f"""Find 5 unique Architecture or Interior Design firms with physical offices in {city}.
        
        STRICT: The office must be in Delaware.
        Return ONLY a JSON array of objects:
        [
          {{
            "name": "Firm Name",
            "address": "Full DE Street Address",
            "city": "{city.split(',')[0]}",
            "state": "DE",
            "website": "URL"
          }}
        ]"""

        try:
            chat = client.chat.create(
                model="grok-4-1-fast",
                tools=[web_search()]
            )
            chat.append(system(system_prompt))
            chat.append(user(user_prompt))
            
            response = chat.sample()
            raw_content = response.content.strip()

            # Extract JSON from potential markdown/text
            json_match = re.search(r'\[\s*\{.*\}\s*\]', raw_content, re.DOTALL)
            if json_match:
                batch = json.loads(re.sub(r',(\s*[}\]])', r'\1', json_match.group(0)))
                
                # Verify and de-duplicate
                for firm in batch:
                    # Simple filter to ensure we don't add PA/NJ firms
                    addr = firm.get('address', '').upper()
                    name = firm.get('name', '')
                    if ("DE" in addr or "DELAWARE" in addr) and not any(f['name'] == name for f in all_verified_firms):
                        all_verified_firms.append(firm)
                        print(f"  ✅ Added: {name}")
                
            if len(all_verified_firms) < 10:
                print(f"  ⏳ Have {len(all_verified_firms)}/10. Moving to next city...")
                time.sleep(2) # Brief pause to avoid rate limits

        except Exception as e:
            print(f"  ⚠️  Error in {city} batch: {e}")
            continue

    print(f"🎯 Final Count: {len(all_verified_firms)} verified Delaware firms.")
    return all_verified_firms[:10]

def send_to_supabase(firms):
    if not firms:
        print("⚠️ No firms found to upload.")
        return
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {SUPABASE_ANON_KEY}"}
    try:
        r = requests.post(WEBHOOK_URL, headers=headers, json={"firms": firms}, timeout=30)
        print("🚀 Successfully updated Supabase!" if r.status_code == 200 else f"✗ Upload failed: {r.text}")
    except Exception as e:
        print(f"❌ Upload Error: {e}")

if __name__ == "__main__":
    firms_list = get_firms()
    send_to_supabase(firms_list)
