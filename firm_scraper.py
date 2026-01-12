import os
import json
import requests
from openai import OpenAI

# 1. Setup Client
client = OpenAI(
    api_key=os.environ.get("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
)

# Configuration for Lovable/Supabase
# Your existing secrets will work for this too
WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

def get_firms():
    print("Step 1: Searching for Delaware Architect & Design firms...")
    
    prompt = """Find 10 established Architecture and Interior Design firms physically located in Delaware.
    Return ONLY a JSON list of objects.
    
    Each object MUST have:
    - name: Legal business name
    - address: Full street address
    - city: Delaware city
    - website: Official URL
    - phone: Business phone number
    - contact_email: General inquiry email if available
    - specialties: List of strings (e.g. ["Commercial", "Residential", "Healthcare"])
    - description: A 1-2 sentence summary of their work
    """

    try:
        response = client.chat.completions.create(
            model="grok-4-1-fast-non-reasoning",
            messages=[
                {"role": "system", "content": "You are a business directory specialist. Always return valid JSON lists."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        raw_content = response.choices[0].message.content.strip()
        
        # Standard cleaning for AI code blocks
        if raw_content.startswith("```"):
            raw_content = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
            if raw_content.startswith("json"):
                raw_content = raw_content[4:].strip()

        return json.loads(raw_content)

    except Exception as e:
        print(f"ERROR: AI search failed: {e}")
        return []

def send_to_supabase(firms):
    if not firms:
        print("No firms found to send.")
        return

    print(f"Step 2: Sending {len(firms)} firms to Lovable...")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    }
    
    # NOTE: Ensure your Lovable Edge Function can handle a "firms" key 
    # OR change this key to match your existing "leads" receiver
    payload = {"firms": firms} 
    
    try:
        response = requests.post(WEBHOOK_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            print("SUCCESS: Firms added to directory.")
        else:
            print(f"FAILED: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    found_firms = get_firms()
    send_to_supabase(found_firms)
