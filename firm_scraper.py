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
    print("Step 1: Searching web for VERIFIED Delaware Architecture & Design firms...\n")
    
    system_prompt = """You are a business verification specialist with web search capabilities.

Your CRITICAL mission: Find ONLY firms with physical offices located IN Delaware.
DO NOT include firms from other states, even if they do work in Delaware.

Verification Protocol:
1. Search official directories (AIA Delaware, state business registrations)
2. Visit each firm's website to confirm Delaware office address
3. Cross-reference multiple sources
4. REJECT any firm you cannot verify has a Delaware office

Quality over quantity: Better to return 3 verified firms than 10 unverified ones.
Return ONLY valid JSON - no introductory text."""

    user_prompt = """Find REAL Architecture and Interior Design firms with physical offices IN Delaware.

CRITICAL MISSION: ONLY include firms you can VERIFY are physically located in Delaware.

SEARCH STRATEGY (Execute these in order):

STEP 1 - Find authoritative sources:
Search: "AIA Delaware chapter members directory"
Search: "Delaware licensed architects directory"
Search: "Delaware Secretary of State architecture firms"

STEP 2 - For each potential firm found, VERIFY Delaware location:
Search: "[Firm name] Delaware office address"
Search: "[Firm name] contact Wilmington" (or Newark, Dover, etc.)
Visit their website to confirm Delaware address

STEP 3 - STRICT VERIFICATION CHECKLIST:
For EACH firm, you must verify:
✅ Firm's website explicitly lists a Delaware office address
✅ Address includes Delaware city (Wilmington, Newark, Dover, Rehoboth, etc.)
✅ Firm appears in Delaware business directories or professional associations
✅ Recent evidence of Delaware operations (2024-2026)

AUTOMATIC REJECTION CRITERIA:
❌ Firm headquarters is in another state (even if they have DE projects)
❌ Only a mailing address or PO Box (no physical office)
❌ Address cannot be verified on their official website
❌ Firm appears to be closed or inactive
❌ No evidence of Delaware office beyond generic business listings

TARGET DELAWARE CITIES:
- Wilmington (primary)
- Newark
- Dover
- Rehoboth Beach
- Lewes
- Middletown
- Seaford

SEARCH QUERIES TO RUN:
1. "AIA Delaware member architects 2025"
2. "Delaware licensed architects Wilmington"
3. "architecture firms with Delaware office"
4. "interior design firms Dover Delaware"
5. "Delaware architects registration board"

For each firm found, return JSON object:
{
  "name": "Legal business name",
  "address": "Complete street address",
  "city": "Delaware city",
  "state": "DE",
  "zip": "Zip code",
  "county": "New Castle|Kent|Sussex",
  "website": "Official URL (REQUIRED)",
  "phone": "Business phone",
  "contact_email": "General email or null",
  "specialties": ["Commercial Architecture", "Residential Design", "Interior Design", "Healthcare", "Education"],
  "description": "2-3 sentences about their Delaware practice",
  "notable_delaware_projects": ["Project in DE", "Another DE project"] or [],
  "year_established": "Year or null",
  "firm_size": "Small (1-10)|Medium (11-50)|Large (50+)",
  "certifications": ["AIA", "LEED AP", "NCARB"] or [],
  "delaware_license_number": "Architecture license # or null",
  "source_url": "Primary source where you verified this firm",
  "verification_notes": "HOW you confirmed this is a Delaware firm (e.g., 'Listed on AIA Delaware roster with Wilmington address confirmed on company website')",
  "last_verified": "January 12, 2026"
}

CRITICAL REQUIREMENTS:
1. Return ONLY 5-10 firms you can FULLY VERIFY
2. Each firm MUST have Delaware office address confirmed
3. Each firm MUST have working website with Delaware address visible
4. Include detailed verification_notes explaining your verification
5. If you can only verify 3 firms, return 3 (DO NOT guess or pad the list)

EXAMPLE of GOOD verification_notes:
"Found on AIA Delaware Chapter member directory. Website shows Wilmington office at [address]. Delaware license #12345 verified on state board website."

EXAMPLE of INSUFFICIENT (would be REJECTED):
"Appears to do work in Delaware" - NO, must have Delaware OFFICE
"Found in Google search" - NO, must verify with authoritative sources

Return JSON array:
[
  { firm object 1 },
  { firm object 2 },
  ...
]

Remember: Quality over quantity. Only include firms you can PROVE are in Delaware."""

    try:
        # Create chat with web search enabled
        chat = client.chat.create(
            model="grok-4-1-fast",
            tools=[web_search()],  # Enable real-time web search
        )
        
        chat.append(system(system_prompt))
        chat.append(user(user_prompt))
        
        print("🔍 Grok is now searching and VERIFYING Delaware firms...")
        print("   This may take longer due to strict verification requirements...\n")
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
        
        print(f"📋 AI returned {len(firms)} firms. Now performing additional validation...\n")
        
        # STRICT Validation
        validated_firms = []
        rejected_count = 0
        
        for i, firm in enumerate(firms, 1):
            print(f"{'='*60}")
            print(f"Validating Firm {i}: {firm.get('name', 'Unknown')}")
            print(f"{'='*60}")
            
            # Required field checks
            if not firm.get('name'):
                print(f"❌ REJECTED: Missing firm name\n")
                rejected_count += 1
                continue
            
            if not firm.get('website') or not firm['website'].startswith('http'):
                print(f"❌ REJECTED: No valid website URL")
                print(f"   Provided: {firm.get('website', 'None')}\n")
                rejected_count += 1
                continue
            
            if not firm.get('address'):
                print(f"❌ REJECTED: No street address provided\n")
                rejected_count += 1
                continue
            
            # Delaware location check
            city = firm.get('city', '').lower()
            state = firm.get('state', '').upper()
            address = firm.get('address', '').lower()
            
            delaware_cities = ['wilmington', 'newark', 'dover', 'rehoboth', 'lewes', 
                             'middletown', 'seaford', 'milford', 'georgetown', 'smyrna']
            
            is_delaware_city = any(de_city in city for de_city in delaware_cities)
            
            if state != 'DE' and not is_delaware_city:
                print(f"❌ REJECTED: Not in Delaware")
                print(f"   City: {firm.get('city')}, State: {state}\n")
                rejected_count += 1
                continue
            
            # Check for verification notes
            verification_notes = firm.get('verification_notes', '')
            if not verification_notes or len(verification_notes) < 20:
                print(f"⚠️  WARNING: Weak verification notes")
                print(f"   Notes: {verification_notes}")
                print(f"   (Accepting anyway, but quality may be lower)\n")
            
            # Check source URL
            source_url = firm.get('source_url', '')
            if not source_url or not source_url.startswith('http'):
                print(f"⚠️  WARNING: No valid source URL")
                print(f"   Source: {source_url}\n")
            
            # Passed all checks
            validated_firms.append(firm)
            print(f"✅ VERIFIED: {firm.get('name')}")
            print(f"   📍 Address: {firm.get('address')}")
            print(f"   🏙️  City: {firm.get('city')}, {state}")
            print(f"   🌐 Website: {firm.get('website')}")
            print(f"   📚 Source: {source_url[:60]}...")
            print(f"   ✓ Verification: {verification_notes[:80]}...")
            print()
        
        print(f"{'='*60}")
        print(f"VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Verified Delaware firms: {len(validated_firms)}")
        print(f"❌ Rejected firms: {rejected_count}")
        print(f"{'='*60}\n")
        
        if len(validated_firms) == 0:
            print("⚠️  WARNING: No firms passed validation!")
            print("   This suggests the AI may be hallucinating results.")
            print("   Consider manually verifying a few firm websites.\n")
        
        return validated_firms
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        print(f"Response preview:\n{raw_content[:500]}...")
        return []
    except Exception as e:
        print(f"❌ Error during search: {e}")
        import traceback
        traceback.print_exc()
        return []

def send_to_supabase(firms):
    if not firms:
        print("⚠️  No verified firms to send to Supabase.\n")
        return
    
    print(f"Step 2: Sending {len(firms)} VERIFIED Delaware firms to Supabase...\n")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    }
    
    payload = {"firms": firms}
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ SUCCESS: Verified firms uploaded to database\n")
            print("📊 Uploaded firms:")
            for i, firm in enumerate(firms, 1):
                print(f"  {i}. {firm.get('name')}")
                print(f"     📍 {firm.get('address')}, {firm.get('city')}")
                print(f"     🌐 {firm.get('website')}")
                print(f"     🏗️  {', '.join(firm.get('specialties', [])[:3])}")
                print()
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(f"Response: {response.text[:300]}")
            
    except requests.exceptions.Timeout:
        print("❌ ERROR: Request to Supabase timed out after 30 seconds")
    except Exception as e:
        print(f"❌ ERROR sending to Supabase: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Delaware Architecture & Design Firm Verifier")
    print("Strict Verification Mode - Quality Over Quantity")
    print("="*60 + "\n")
    
    verified_firms = get_firms()
    
    if verified_firms:
        print("\n" + "="*60)
        print(f"🎯 Successfully verified {len(verified_firms)} Delaware firms")
        print("="*60 + "\n")
        send_to_supabase(verified_firms)
    else:
        print("\n⚠️  No firms passed strict verification")
        print("\nPossible reasons:")
        print("  • AI is hallucinating firm names/addresses")
        print("  • Delaware has very few architecture firms")
        print("  • Web search results are limited")
        print("\nRecommendations:")
        print("  • Try running again (web search can vary)")
        print("  • Check XAI_API_KEY has web search permissions")
        print("  • Consider manually seeding with known Delaware firms")
        print("  • Verify xai-sdk is properly installed: pip install xai-sdk\n")
