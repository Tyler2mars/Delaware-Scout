import os
import json
import re
import requests
from xai_sdk import Client
from xai_sdk.chat import user, system
from xai_sdk.tools import web_search

# Setup xAI Client
client = Client(api_key=os.environ.get("XAI_API_KEY"))

WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

def get_firms():
    print("Step 1: Searching web for Delaware Architecture & Design firms...\n")
    
    system_prompt = """You are a business directory specialist with web search capabilities.

Search Strategy:
1. Search AIA Delaware chapter member directories
2. Search Google for architecture and design firms
3. Check professional associations
4. Verify firms have active websites and Delaware addresses

Always verify information with real sources and include URLs.
Return ONLY valid JSON - no introductory text."""

    user_prompt = """Find 10 REAL Architecture and Interior Design firms currently operating in Delaware.

SEARCH QUERIES TO RUN:
1. "AIA Delaware member architects"
2. "architecture firms Wilmington Delaware"
3. "interior design firms Newark Delaware"
4. "Delaware registered architects 2025"

VERIFICATION:
- Must have working website
- Must be in Delaware
- Must show recent activity (2024-2026)

Return JSON array:
[
  {
    "name": "Legal business name",
    "address": "Full street address",
    "city": "Delaware city",
    "state": "DE",
    "website": "Full URL (must be real)",
    "phone": "Phone number or null",
    "contact_email": "Email or null",
    "specialties": ["Commercial", "Residential", etc.],
    "description": "2-3 sentence description",
    "source_url": "Where you found this info",
    "last_verified": "January 11, 2026"
  }
]

CRITICAL: Only include firms found through web search with real websites."""

    try:
        # Create chat with web search enabled
        chat = client.chat.create(
            model="grok-4-1-fast",
            tools=[web_search()],  # Enable real-time web search
        )
        
        chat.append(system(system_prompt))
        chat.append(user(user_prompt))
        
        print("🔍 Grok is searching the web for real firms...")
        response = chat.sample()
        
        raw_content = response.content.strip()
        print(f"📄 Received response ({len(raw_content)} characters)\n")
        
        # Clean markdown formatting
        if raw_content.startswith("```"):
            lines = raw_content.split("\n")
            raw_content = "\n".join(lines[1:-1])
            if raw_content.startswith("json"):
                raw_content = raw_content[4:].strip()
        
        # Fix trailing commas
        raw_content = re.sub(r',(\s*[}\]])', r'\1', raw_content)
        
        # Parse JSON
        firms = json.loads(raw_content)
        
        # Validate
        validated_firms = []
        for i, firm in enumerate(firms, 1):
            if not firm.get('website') or not firm['website'].startswith('http'):
                print(f"⚠️  Firm {i}: Skipping '{firm.get('name', 'Unknown')}' - No valid website")
                continue
            
            if not firm.get('name') or not firm.get('city'):
                print(f"⚠️  Firm {i}: Skipping - Missing name or city")
                continue
            
            validated_firms.append(firm)
            print(f"✅ Firm {i}: {firm.get('name')}")
            print(f"   📍 {firm.get('city')}, DE")
            print(f"   🌐 {firm.get('website')}")
            print(f"   📚 Source: {firm.get('source_url', 'N/A')[:50]}...")
            print()
        
        print(f"✅ Found {len(validated_firms)} verified firms\n")
        return validated_firms
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        print(f"Response: {raw_content[:500]}...")
        return []
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []

def send_to_supabase(firms):
    if not firms:
        print("⚠️  No firms to send.\n")
        return
    
    print(f"Step 2: Sending {len(firms)} firms to Supabase...\n")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    }
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            headers=headers,
            json={"firms": firms},
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ SUCCESS: Firms uploaded\n")
            for i, firm in enumerate(firms, 1):
                print(f"  {i}. {firm.get('name')} - {firm.get('city')}")
        else:
            print(f"❌ FAILED: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("="*60)
    print("Delaware Architecture & Design Firm Finder")
    print("Using Grok Web Search")
    print("="*60 + "\n")
    
    found_firms = get_firms()
    
    if found_firms:
        print("="*60)
        print(f"🎯 Total: {len(found_firms)} verified firms")
        print("="*60 + "\n")
        send_to_supabase(found_firms)
    else:
        print("⚠️  No firms found")
