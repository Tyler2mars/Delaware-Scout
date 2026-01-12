import os
import json
import requests
import re
from xai_sdk import Client
from xai_sdk.chat import user, system
from xai_sdk.tools import web_search

# 1. Setup xAI Client (Native SDK)
client = Client(api_key=os.environ.get("XAI_API_KEY"))

WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

def get_firms():
    print("🔍 Step 1: Searching for Delaware A&D Firms using Agentic Search...")
    
    system_prompt = """You are a specialized business researcher. Your goal is to find 10 Architecture or Interior Design firms with physical headquarters or studio offices located in Delaware.

STRICT VERIFICATION RULES:
1. ONLY include firms with a physical street address in DE.
2. REJECT "Virtual Offices" or firms that just have a "Project Office" but are based in PA/MD/NJ.
3. Use your web_search tool to verify the office address on the firm's own 'Contact' page.
"""

    user_prompt = """Find 10 REAL Architecture and Interior Design firms with physical offices in Delaware. 
    
    Run multiple searches to confirm:
    1. The firm's name and Delaware street address.
    2. That they are currently active in 2026.
    
    Return ONLY a JSON array of objects:
    [
      {
        "name": "Firm Name",
        "address": "Full DE Street Address",
        "city": "City",
        "state": "DE",
        "website": "URL",
        "verification_note": "Confirmed DE studio via [Source]"
      }
    ]"""

    try:
        # Create chat with AGENTIC web search enabled (Grok 4.1 Fast)
        chat = client.chat.create(
            model="grok-4-1-fast",
            tools=[web_search()],
        )
        
        chat.append(system(system_prompt))
        chat.append(user(user_prompt))
        
        print("🌐 Grok is browsing the web and verifying DE addresses...")
        response = chat.sample()
        raw_content = response.content.strip()

        # Clean JSON formatting
        if "```json" in raw_content:
            raw_content = raw_content.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_content:
            raw_content = raw_content.split("```")[1].split("```")[0].strip()
        
        # Final JSON cleanup for trailing commas
        raw_content = re.sub(r',(\s*[}\]])', r'\1', raw_content)
        
        firms = json.loads(raw_content)
        
        # Final Python-level check to ensure 'DE' is in the address
        verified = [f for f in firms if "DE" in f.get('address', '').upper() or "DELAWARE" in f.get('address', '').upper()]
        
        print(f"✅ Found {len(verified)} verified Delaware firms.")
        return verified

    except Exception as e:
        print(f"❌ Error during Agentic Scrape: {e}")
        return []

def send_to_supabase(firms):
    if not firms:
        print("⚠️ No data to upload.")
        return
        
    print(f"🚀 Step 2: Uploading {len(firms)} firms to Supabase...")
    headers = {
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    }
    
    try:
        r = requests.post(WEBHOOK_URL, headers=headers, json={"firms": firms}, timeout=30)
        if r.status_code == 200:
            print("✓ Successfully sent to Supabase.")
        else:
            print(f"✗ Failed: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"❌ Upload Error: {e}")

if __name__ == "__main__":
    firms_list = get_firms()
    send_to_supabase(firms_list)
