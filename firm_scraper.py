import os, json, requests, re, time
from xai_sdk import Client
from xai_sdk.chat import user
from xai_sdk.tools import web_search

client = Client(api_key=os.environ.get("XAI_API_KEY"))
WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

def get_top_firms():
    print("🚀 Scout starting: Targeting the Top 20 Delaware Firms...")
    
    # We use a broad, high-authority prompt
    prompt = (
        "Search for the top 20 largest and most award-winning architecture and interior design firms "
        "headquartered in Delaware (like StudioJAED, Becker Morgan, BSA+A, ABHA, and Tevebaugh). "
        "Return ONLY a JSON array of objects: [{\"name\": \"...\", \"address\": \"...\", \"city\": \"...\", \"state\": \"DE\", \"website\": \"...\"}]"
    )

    try:
        # We enable web_search to get current 2026 data
        chat = client.chat.create(
            model="grok-4-1-fast", 
            tools=[web_search()],
            max_tokens=1500 # Increased slightly to handle 20 detailed objects
        )
        chat.append(user(prompt))
        
        response = chat.sample()
        raw_content = response.content.strip()

        # Extract JSON from response
        json_match = re.search(r'\[\s*\{.*\}\s*\]', raw_content, re.DOTALL)
        if json_match:
            firms = json.loads(re.sub(r',(\s*[}\]])', r'\1', json_match.group(0)))
            for f in firms:
                print(f"  ⭐ Found: {f.get('name')}")
            return firms
        else:
            print("⚠️ Could not find JSON in response.")
            return []

    except Exception as e:
        print(f"⚠️ Search Error: {e}")
        return []

def send_to_supabase(firms):
    if not firms: return
    print(f"📤 Uploading {len(firms)} premium firms to Supabase...")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {SUPABASE_ANON_KEY}"}
    try:
        r = requests.post(WEBHOOK_URL, headers=headers, json={"firms": firms}, timeout=30)
        print("✅ Supabase Updated!" if r.status_code == 200 else f"✗ Error: {r.text}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    top_firms = get_top_firms()
    send_to_supabase(top_firms)
