import os, json, requests, re, time
from xai_sdk import Client
from xai_sdk.chat import user

client = Client(api_key=os.environ.get("XAI_API_KEY"))
WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

def get_firms():
    # Focused list of cities to keep tokens low
    cities = ["Bear, DE", "Camden, DE", "Wilmington, DE"]
    all_found_firms = []
    
    print("🚀 Running Scraper (Direct Upload Mode)")

    for city in cities:
        print(f"🔍 Searching {city}...")
        
        # Concise prompt to save input tokens
        prompt = f"Return a JSON array of 5 architecture/interior design firms in {city}, DE. Fields: name, address, website. No conversational filler."

        try:
            # We use tools=[] if you want it to use its internal knowledge or add tools=[web_search()]
            chat = client.chat.create(model="grok-4-1-fast", max_tokens=600)
            chat.append(user(prompt))
            
            response = chat.sample()
            raw_content = response.content.strip()

            # Extract JSON
            json_match = re.search(r'\[\s*\{.*\}\s*\]', raw_content, re.DOTALL)
            if json_match:
                batch = json.loads(re.sub(r',(\s*[}\]])', r'\1', json_match.group(0)))
                for firm in batch:
                    all_found_firms.append(firm)
                    print(f"  + Added: {firm.get('name')}")
            
            time.sleep(1) # Small delay to avoid hitting xAI limits

        except Exception as e:
            print(f"  ⚠️ Error in {city}: {e}")
            continue

    return all_found_firms

def send_to_supabase(firms):
    if not firms:
        print("⚠️ No firms found.")
        return
        
    print(f"📤 Uploading {len(firms)} firms to Supabase...")
    headers = {
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    }
    
    try:
        r = requests.post(WEBHOOK_URL, headers=headers, json={"firms": firms}, timeout=30)
        if r.status_code == 200:
            print("✅ Successfully updated Supabase!")
        else:
            print(f"✗ Upload failed: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    found_leads = get_firms()
    send_to_supabase(found_leads)
