import os
import json
import requests
from openai import OpenAI

# 1. Setup Client (OpenAI-compatible)
client = OpenAI(
    api_key=os.environ.get("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
)

WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

def get_firms():
    print("🔍 Searching for Delaware A&D firms using Grok 4.1 Fast...")
    
    # We use 'grok-4-1-fast-non-reasoning' (standard API ID as of Jan 2026)
    # The 'non-reasoning' version is optimized for fast web extraction.
    model_id = "grok-4-1-fast-non-reasoning"

    prompt = """Find 10 REAL Architecture and Interior Design firms with physical offices IN Delaware.

    STRICT FILTERS:
    1. ONLY include firms with a physical street address in DE.
    2. REJECT firms that only do 'projects' in DE but are based in PA, MD, or NJ.
    3. Include name, address, city, state (DE), website, and specialties.
    
    Return a valid JSON list. No preamble or conversational text."""

    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": "You are a data extraction specialist. Return JSON only."},
                {"role": "user", "content": prompt}
            ],
            # Triggering live web search via xAI's specific parameter
            extra_body={"search_parameters": {"mode": "on"}},
            temperature=0.1
        )
        
        raw_content = response.choices[0].message.content.strip()
        
        # Clean up any potential markdown formatting from the response
        if "```json" in raw_content:
            raw_content = raw_content.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_content:
            raw_content = raw_content.split("```")[1].split("```")[0].strip()

        firms = json.loads(raw_content)
        
        # Verification layer: Ensure address mentions Delaware
        verified = [f for f in firms if "DE" in f.get('address', '').upper() or "DELAWARE" in f.get('address', '').upper()]
        
        print(f"✅ Found {len(verified)} verified Delaware firms.")
        return verified

    except Exception as e:
        print(f"❌ Error during scrape: {e}")
        return []

def send_to_supabase(firms):
    if not firms:
        print("⚠️ No firms to upload.")
        return
        
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    }
    
    try:
        r = requests.post(WEBHOOK_URL, headers=headers, json={"firms": firms}, timeout=30)
        if r.status_code == 200:
            print("🚀 Successfully sent data to Supabase.")
        else:
            print(f"Failed to send data: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Upload error: {e}")

if __name__ == "__main__":
    firms_list = get_firms()
    send_to_supabase(firms_list)
