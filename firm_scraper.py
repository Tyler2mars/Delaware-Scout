import os
import json
import requests
from openai import OpenAI

# 1. Setup Client using the OpenAI-compatible style
client = OpenAI(
    api_key=os.environ.get("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
)

WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

def get_firms():
    print("🔍 Searching for Delaware A&D firms using Grok 4.1 Fast...")
    
    # This is the strict verification prompt Claude created
    prompt = """Find 10 REAL Architecture and Interior Design firms with physical offices IN Delaware.

    STRICT RULES:
    1. ONLY include firms with a physical street address in Delaware.
    2. REJECT firms that only have a 'Project Office' or 'Virtual Office' in DE.
    3. REJECT firms headquartered in Philly, Baltimore, or NJ unless they have a full DE studio.

    Return JSON list with:
    {
      "name": "Legal name",
      "address": "Street address",
      "city": "DE City",
      "state": "DE",
      "website": "URL",
      "verification_note": "How did you confirm the DE office?"
    }"""

    try:
        response = client.chat.completions.create(
            model="grok-4.1-fast-non-reasoning", # <--- Your specific model
            messages=[
                {"role": "system", "content": "You are a specialized business researcher. Return JSON only."},
                {"role": "user", "content": prompt}
            ],
            # This is how you trigger the Web Search in the OpenAI-style library
            extra_body={"search_parameters": {"mode": "on"}}, 
            temperature=0.1
        )
        
        raw_content = response.choices[0].message.content.strip()
        
        # Strip markdown if present
        if "```json" in raw_content:
            raw_content = raw_content.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_content:
            raw_content = raw_content.split("```")[1].split("```")[0].strip()

        firms = json.loads(raw_content)
        
        # Final Python Check: Double-verify the address contains Delaware
        verified = [f for f in firms if "DE" in f.get('address', '').upper() or "DELAWARE" in f.get('address', '').upper()]
        
        print(f"✅ Found {len(verified)} verified Delaware firms.")
        return verified

    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def send_to_supabase(firms):
    if not firms: return
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {SUPABASE_ANON_KEY}"}
    try:
        r = requests.post(WEBHOOK_URL, headers=headers, json={"firms": firms}, timeout=30)
        print("✓ Data sent to Supabase" if r.status_code == 200 else f"✗ Error: {r.text}")
    except Exception as e:
        print(f"❌ Upload Error: {e}")

if __name__ == "__main__":
    firms_list = get_firms()
    send_to_supabase(firms_list)
