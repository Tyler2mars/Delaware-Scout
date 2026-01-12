import os
import json
import re
import requests
from xai_sdk import Client
from xai_sdk.chat import user, system
from xai_sdk.tools import web_search

# Setup xAI Client with web search
client = Client(api_key=os.environ.get("XAI_API_KEY"))

WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

def get_firms():
    print("Step 1: Searching web for Delaware Architecture & Design firms...\n")
    
    system_prompt = """You are a business directory specialist with web search capabilities.

Your mission: Find REAL, currently operating Architecture and Interior Design firms in Delaware.

Search Strategy:
1. Search AIA Delaware chapter member directories
2. Search Google for "architecture firms Delaware"
3. Check professional associations and business directories
4. Look for firms with verified websites and contact information
5. Search individual Delaware cities (Wilmington, Newark, Dover, Rehoboth Beach)

Always verify:
- Firm has an active, working website
- Physical address in Delaware
- Current operations (not closed)
- Recent projects or news

Return ONLY valid JSON - no introductory text."""

    user_prompt = """Find 10 REAL Architecture and Interior Design firms currently operating in Delaware.

SEARCH QUERIES TO RUN:
1. "AIA Delaware chapter members architects"
2. "architecture firms Wilmington Delaware"
3. "interior design firms Newark Delaware"
4. "architects Dover Delaware"
5. "design firms Rehoboth Beach Delaware"
6. "Delaware licensed architects"
7. "architectural services Delaware"

VERIFICATION REQUIREMENTS:
- Each firm MUST have a real, working website URL
- Must have a Delaware address (not just satellite office)
- Must show recent activity (projects, news, updates from 2024-2026)
- Must specialize in architecture or interior design

PROJECT TYPES TO PRIORITIZE:
- Commercial architecture
- Residential design
- Interior design
- Healthcare facilities
- Educational buildings
- Hospitality design

For each firm found, return:
{
  "name": "Legal business name",
  "address": "Full street address or 'Contact for address'",
  "city": "Delaware city (Wilmington, Newark, Dover, etc.)",
  "state": "DE",
  "zip": "ZIP code if available",
  "website": "Full URL - MUST be real and working",
  "phone": "Phone number or null",
  "contact_email": "Email or null",
  "specialties": ["Commercial", "Residential", "Interior Design", etc.],
  "description": "2-3 sentence description of their work and expertise",
  "notable_projects": ["Project 1", "Project 2"] or [],
  "year_established": "Year or null",
  "firm_size": "Number of employees or 'Small/Medium/Large'",
  "certifications": ["AIA", "LEED", "NCARB", etc.] or [],
  "source_url": "Where you found this information",
  "verification_date": "Today's date: January 11, 2026"
}

CRITICAL REQUIREMENTS:
1. MUST have working website URL from your web search
2. MUST be physically located in Delaware
3. MUST show signs of current operation
4. NO GUESSING - only include firms you found through web search

Return JSON array:
[
  { firm object 1 },
  { firm object 2 },
  ...
]"""

    try:
        # Create chat with web search enabled
        chat = client.chat.create(
            model="grok-4-1-fast",  # Use reasoning model for better search
            tools=[web_search()],   # Enable real-time web search
        )
        
        # Add messages
        chat.append(system(system_prompt))
        chat.append(user(user_prompt))
        
        # Get response
        print("🔍 Grok is searching the web for Delaware architecture firms...")
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
        
        # Validate results
        validated_firms = []
        for i, firm in enumerate(firms, 1):
            # Check required fields
            if not firm.get('website') or not firm['website'].startswith('http'):
                print(f"⚠️  Firm {i}: Skipping '{firm.get('name', 'Unknown')}' - No valid website")
                continue
            
            if not firm.get('name'):
                print(f"⚠️  Firm {i}: Skipping - Missing firm name")
                continue
            
            if not firm.get('city'):
                print(f"⚠️  Firm {i}: Skipping '{firm.get('name')}' - No Delaware city listed")
                continue
            
            validated_firms.append(firm)
            print(f"✅ Firm {i}: {firm.get('name')} - {firm.get('city')}")
            print(f"   Website: {firm.get('website')}")
            print(f"   Specialties: {', '.join(firm.get('specialties', []))}")
            print()
        
        print(f"\n✅ Found {len(validated_firms)} verified Delaware firms\n")
        return validated_firms
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        print(f"Raw response: {raw_content[:500]}...")
        return []
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []

def send_to_supabase(firms):
    if not firms:
        print("⚠️  No firms to send.")
        return
    
    print(f"Step 2: Sending {len(firms)} firms to Supabase...\n")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    }
    
    payload = {"firms": firms}
    
    try:
        response = requests.post(WEBHOOK_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            print("✅ SUCCESS: Firms uploaded to database")
            print("\n📊 Summary:")
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
        print(f"🎯 Found {len(found_firms)} verified firms")
        print("="*60 + "\n")
        send_to_supabase(found_firms)
    else:
        print("⚠️  No firms found - check search parameters")
