import os
import json
import requests
import re
from xai_sdk import Client
from xai_sdk.chat import user, system
from xai_sdk.tools import web_search

client = Client(api_key=os.environ.get("XAI_API_KEY"))

WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

def get_firms():
    print("🔍 Step 1: Searching for Delaware A&D Firms...")
    
    # We broaden the prompt to ensure we get results, then filter in Python
    system_prompt = "You are a business research assistant. Use web search to find active Architecture and Interior Design firms in Delaware."

    user_prompt = """Search for 'Architecture firms in Wilmington DE', 'Interior designers Newark DE', and 'Top Delaware Architects 2026'.
    
    Provide a list of 10 firms that have physical offices in Delaware. 
    For each firm, you MUST provide:
    1. Name
    2. Physical Delaware address
    3. Website URL
    
    Return ONLY a JSON array. 
    Example format: [{"name": "Example Arch", "address": "123 Main St, Wilmington, DE 19801", "website": "https://example.com"}]"""

    try:
        # We enable inline_citations to improve search depth
        chat = client.chat.create(
            model="grok-4-1-fast",
            tools=[web_search()],
            include=["inline_citations"] 
        )
        
        chat.append(system(system_prompt))
        chat.append(user(user_prompt))
        
        print("🌐 Browsing Delaware business directories...")
        response = chat.sample()
        raw_content = response.content.strip()

        # Robust JSON extraction
        json_match = re.search(r'\[\s*\{.*\}\s*\]', raw_content, re.DOTALL)
        if json_match:
            raw_content = json_match.group(0)
        
        # Clean trailing commas
        raw_content = re.sub(r',(\s*[}\]])', r'\1', raw_content)
        
        firms = json.loads(raw_content)
        
        # We do the "Strict Delaware" check here in Python code
        # This prevents the AI from getting 'stage fright' and returning 0 results
        verified = []
        for f in firms:
            addr = f.get('address', '').upper()
            if " DE " in addr or "DELAWARE" in addr or ", DE" in addr:
                verified.append(f)
        
        print(f"✅ Successfully found and verified {len(verified)} firms.")
        return verified

    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def send_to_supabase(firms):
    if not firms:
        print("⚠️ No firms to upload.")
        return
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {SUPABASE_ANON_KEY}"}
    try:
        r = requests.post(WEBHOOK_URL, headers=headers, json={"firms": firms}, timeout=30)
        print("🚀 Data sent to Supabase!" if r.status_code == 200 else f"✗ Error: {r.text}")
    except Exception as e:
        print(f"❌ Upload Error: {e}")

if __name__ == "__main__":
    firms_list = get_firms()
    send_to_supabase(firms_list)
