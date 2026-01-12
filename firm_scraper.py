import os
import json
import requests
from openai import OpenAI

# 1. Setup xAI Client
# This uses the Grok-4 model which has built-in web search capabilities
client = OpenAI(
    api_key=os.environ.get("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
)

# 2. Configuration - Mapping to your GitHub Action Environment Variables
# These must match the names on the LEFT side of your .yml 'env' section
WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

def get_firms():
    """
    Asks Grok to research and verify 10 Delaware A&D firms using live web data.
    """
    print("Step 1: Asking Grok to browse and verify 10 Delaware A&D Firms...")
    
    prompt = """Search the web to identify 10 real, active Architecture and Interior Design firms 
    with physical commercial offices in Delaware. 

    CRITICAL INSTRUCTIONS:
    1. Only include firms with a verifiable website and a physical DE address.
    2. Focus on firms that handle Vertical Construction (Commercial, Healthcare, Education, or Multi-Family).
    3. If a firm is purely residential or 'work-from-home' without a commercial studio, skip it.
    4. Verify the phone numbers and cities (Wilmington, Newark, Dover, Lewes, etc.).

    Return exactly 10 high-confidence results as a JSON list.
    
    Data structure for each object:
    - name: Legal business name
    - address: Full street address
    - city: Delaware city
    - website: Official URL
    - phone: Business phone number
    - contact_email: General email if found
    - specialties: List of strings (e.g. ["Commercial", "Institutional", "Interior Design"])
    - description: A concise 1-2 sentence summary of their notable Delaware projects or design focus.
    
    Return ONLY the JSON list. Do not include any introductory or concluding text.
    """

    try:
        response = client.chat.completions.create(
            model="grok-4-1-fast-non-reasoning", 
            messages=[
                {"role": "system", "content": "You are a precise business data auditor. You verify web data before returning it. You never hallucinate business names or URLs. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1 # Low temperature for maximum factual accuracy
        )
        
        raw_content = response.choices[0].message.content.strip()
        
        # Clean AI markdown markers if present
        if raw_content.startswith("```"):
            raw_content = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
            if raw_content.startswith("json"):
                raw_content = raw_content[4:].strip()

        firms = json.loads(raw_content)
        print(f"Successfully verified {len(firms)} firms.")
        return firms

    except Exception as e:
        print(f"ERROR during AI search/parsing: {e}")
        return []

def send_to_supabase(firms):
    """
    Sends the extracted JSON data to the Lovable/Supabase Edge Function.
    """
    if not firms:
        print("No firms found to send. Skipping Supabase update.")
        return

    # Safety Check: Ensure the URL exists
    if not WEBHOOK_URL:
        print("CRITICAL ERROR: SUPABASE_WEBHOOK_URL is None. Check GitHub Secrets!")
        return

    print(f"Step 2: Sending {len(firms)} firms to Lovable Webhook...")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    }
    
    # We send it with a 'firms' key so your specific scrape-firms function can handle it
    payload = {"firms": firms} 
    
    try:
        response = requests.post(
            WEBHOOK_URL, 
            headers=headers, 
            json=payload, 
            timeout=30
        )
        
        if response.status_code == 200:
            print("✓ SUCCESS: Firms successfully added to the design_firms table.")
        else:
            print(f"✗ FAILED: Status {response.status_code} - {response.text}")

    except Exception as e:
        print(f"ERROR connecting to Lovable: {e}")

if __name__ == "__main__":
    # Execute the workflow
    found_firms = get_firms()
    send_to_supabase(found_firms)
