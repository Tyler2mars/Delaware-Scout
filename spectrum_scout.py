import os
import json
import re
import requests
from xai_sdk import Client
from xai_sdk.chat import user, system
from xai_sdk.tools import web_search

# 1. Setup xAI Client with web search capabilities
client = Client(api_key=os.environ.get("XAI_API_KEY"))

# 2. Update these in your GitHub Secrets or Environment
WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL") 
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

def get_leads():
    print("Step 1: Searching web for Delaware Vertical Construction leads with real-time data...")
    
    # System prompt to guide the AI's behavior
    system_prompt = """You are a construction market intelligence specialist with web search capabilities.

Your mission: Find projects BEFORE they go to bid by monitoring:
- Planning board meetings and approvals
- Architectural firm project announcements  
- Zoning and permit applications
- Developer press releases
- Early-stage project news

Search Strategy:
1. Search for recent Delaware planning approvals and zoning decisions
2. Look for architectural/engineering firm announcements in Delaware
3. Find permit applications and development proposals
4. Check local Delaware news for construction announcements
5. Search for specific sectors: healthcare, education, commercial, multifamily

Focus on the 6-18 month window BEFORE bidding begins.
Always verify information with real sources and include URLs.
Return ONLY valid JSON - no introductory text."""

    # User prompt with specific search instructions
    user_prompt = """Find 10 REAL vertical construction projects in Delaware that are currently in PLANNING or DESIGN phase (NOT yet out to bid).

CRITICAL DATE FILTERING:
- TODAY'S DATE: January 10, 2026
- Only include projects where construction has NOT YET STARTED
- Exclude any project with "groundbreaking", "construction began", "under construction", "topped out", "nearing completion"
- Target: Projects with construction start dates in FUTURE (Q2 2026 or later)
- After finding each project, VERIFY it hasn't started construction yet by searching "[project name] construction status 2026"

SEARCH QUERIES TO RUN:
1. "Delaware planning board approval 2025 2026"
2. "Delaware zoning approval commercial development"
3. "Delaware architect firm project announcement"
4. "Delaware construction project design phase"
5. "Delaware building permit application 2025"
6. "New Castle County development proposal"
7. "Kent County Delaware construction plans"
8. "Sussex County Delaware building project"
9. "Delaware architectural firm selected design"
10. "[Project name] architect Delaware" (for each project found)

VERIFICATION STEP (CRITICAL):
For each project found, search to confirm current status:
- "[Project name] Delaware construction status"
- "[Project name] groundbreaking date"
- Look for recent news (last 30 days) about the project
- If you find "construction started", "workers on site", "framing complete" - REJECT IT

CRITICAL: ARCHITECT/DESIGNER INFORMATION IS PRIORITY
For EVERY project, make additional searches to find the architect/designer:
- Search the project name + "architect" or "designer"
- Check architectural firm websites and project portfolios
- Look for design award announcements
- Search permit records which often list architect of record
- Check local AIA chapter announcements
- If not found initially, search "[developer name] architect Delaware"

PROJECT STAGE KEYWORDS TO FIND:
- "Planning approval", "Zoning approved", "Site plan submitted"
- "Design contract awarded to [architect]"
- "Architectural firm announces", "Selected to design"
- "Conceptual review", "Preliminary plans"
- "Developer proposes", "Breaking ground in [future date]"
- "Pre-construction", "Design development phase"

STRICT EXCLUSIONS: 
- NO highway, road, bridge, or paving projects
- NO wastewater, sewer, or external-only utility projects
- NO DelDOT infrastructure
- NO projects already under construction (check for "construction began", "groundbreaking held", "workers on site")
- NO projects completed or nearly complete
- NO projects currently out to bid
- NO projects with construction start dates in the PAST (before January 2026)

FOCUS ON: Buildings requiring interior finishes and flooring:
- Office buildings
- Hospitals and medical facilities
- Schools and universities
- Apartment/multifamily housing
- Hotels and hospitality
- Senior living facilities
- Retail and mixed-use

For each project, return a JSON object with these fields:
{
  "name": "Full project name",
  "address": "Street address or 'Site location TBD'",
  "city": "City in Delaware",
  "county": "New Castle, Kent, or Sussex",
  "sector": "Healthcare|Government|Corporate|Education|Multi Family|Hospitality|Senior Living|Retail|Mixed-Use",
  "budget": "Estimated project cost (e.g., '$50M' or 'TBD')",
  "source_url": "REQUIRED - Direct URL to news article, planning doc, or announcement",
  "designer": "Architectural/engineering firm name or 'Design RFP pending'",
  "general_contractor": "GC name or 'Pre-bid phase - TBD'",
  "project_stage": "Planning Approval|Design Phase|Permits Pending|Pre-Construction|Design RFP",
  "construction_status": "Not Started - Construction begins [date]",
  "timeline": "When construction expected to start (must be FUTURE date)",
  "deadline": "Estimated completion date",
  "latitude": 39.xxxx,
  "longitude": -75.xxxx,
  "description": "2-3 sentences describing the project and its current status",
  "flooring_opportunity": "Brief description of flooring scope (e.g., '50,000 SF mixed LVT/carpet/tile')",
  "flooring_tags": ["LVT", "Carpet", "Tile", "Polished Concrete", "Hardwood"],
  "estimated_sqft": 50000,
  "decision_maker": "Name of developer, owner, or project manager if mentioned",
  "contact_opportunity": "How/when to engage (e.g., 'Contact architect during design phase')",
  "last_updated": "Date of most recent news/update"
}

Return ONLY a JSON array of objects. Each project MUST have:
1. A real, verifiable source_url from your web search
2. Current pre-bid status (not already under construction)
3. Relevance to interior flooring installation
4. ARCHITECT/DESIGNER INFORMATION - Make extra effort to find this. If absolutely not available after thorough searching, mark as "Seeking architect - Design RFP stage"

JSON format:
[
  { project object 1 },
  { project object 2 },
  ...
]"""

    try:
        # Create chat with web search enabled
        chat = client.chat.create(
            model="grok-4-1-fast",  # Use reasoning model for better search capabilities
            tools=[web_search()],   # Enable real-time web search
        )
        
        # Add system and user messages
        chat.append(system(system_prompt))
        chat.append(user(user_prompt))
        
        # Get response with web search
        print("🔍 Grok is now searching the web for real projects...")
        response = chat.sample()
        
        raw_content = response.content.strip()
        print(f"📄 Received response ({len(raw_content)} characters)")
        
        # Clean markdown formatting if present
        if raw_content.startswith("```"):
            lines = raw_content.split("\n")
            raw_content = "\n".join(lines[1:-1])
            if raw_content.startswith("json"):
                raw_content = raw_content[4:].strip()
        
        # Fix common JSON formatting issues from AI responses
        # Remove trailing commas before closing braces/brackets
        raw_content = re.sub(r',(\s*[}\]])', r'\1', raw_content)
        
        # Parse JSON
        leads = json.loads(raw_content)
        
        # Validation: Check for real URLs and pre-bid status
        validated_leads = []
        rejected_count = 0
        seen_addresses = {}  # Track addresses to detect duplicates
        
        for i, lead in enumerate(leads, 1):
            # Check for required fields
            if not lead.get('source_url') or not lead['source_url'].startswith('http'):
                print(f"⚠️  Project {i}: Skipping '{lead.get('name', 'Unknown')}' - No valid source URL")
                rejected_count += 1
                continue
            
            if not lead.get('name'):
                print(f"⚠️  Project {i}: Skipping - Missing project name")
                rejected_count += 1
                continue
            
            # DUPLICATE CHECK: Check if we've seen this address before
            address = lead.get('address', '').lower().strip()
            if address and address != 'site location tbd' and address != 'site tbd':
                # Normalize address for comparison (remove extra spaces, punctuation)
                normalized_address = re.sub(r'[^\w\s]', '', address).strip()
                normalized_address = re.sub(r'\s+', ' ', normalized_address)  # Collapse multiple spaces
                
                if normalized_address in seen_addresses:
                    existing_name = seen_addresses[normalized_address]
                    print(f"🔄 Project {i}: DUPLICATE '{lead.get('name')}' - Same address as '{existing_name}'")
                    print(f"   Address: {address}")
                    rejected_count += 1
                    continue
                
                seen_addresses[normalized_address] = lead.get('name')
            
            # CRITICAL: Check if construction already started
            description = lead.get('description', '').lower()
            stage = lead.get('project_stage', '').lower()
            construction_status = lead.get('construction_status', '').lower()
            timeline = lead.get('timeline', '').lower()
            
            # Red flag keywords that indicate construction has started
            started_keywords = [
                'under construction', 'construction began', 'groundbreaking held',
                'workers on site', 'framing complete', 'topped out', 'nearing completion',
                'construction started', 'breaking ground', 'broke ground', 'construction underway',
                'currently being built', 'construction is ongoing', 'opened in 20'
            ]
            
            # Check if any red flag appears
            is_already_started = any(keyword in description or keyword in construction_status or keyword in timeline 
                                     for keyword in started_keywords)
            
            if is_already_started:
                print(f"🚫 Project {i}: REJECTED '{lead.get('name')}' - Construction already started")
                print(f"   Evidence: {description[:100]}...")
                rejected_count += 1
                continue
            
            # Warn if stage is "construction" without "pre-"
            if 'construction' in stage and 'pre-construction' not in stage and 'pre construction' not in stage:
                print(f"🚫 Project {i}: REJECTED '{lead.get('name')}' - Stage indicates active construction: {lead.get('project_stage')}")
                rejected_count += 1
                continue
            
            # Check for architect/designer information
            designer = lead.get('designer', '')
            if not designer or designer in ['TBD', 'N/A', '']:
                print(f"⚠️  Project {i}: '{lead.get('name')}' - Missing architect/designer info")
            else:
                print(f"🏗️  Project {i}: Architect: {designer}")
            
            validated_leads.append(lead)
            print(f"✅ Project {i}: {lead.get('name')} - {lead.get('project_stage', 'Unknown stage')}")
        
        if rejected_count > 0:
            print(f"\n⚠️  Rejected {rejected_count} projects (duplicates, already under construction, or invalid)")
        
        print(f"\n✅ Found {len(validated_leads)} validated PRE-BID projects with real sources")
        return validated_leads
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        print(f"Raw response preview: {raw_content[:500]}...")
        return []
    except Exception as e:
        print(f"❌ ERROR during AI search: {e}")
        import traceback
        traceback.print_exc()
        return []

def send_to_supabase(leads):
    if not leads:
        print("⚠️  No leads to send. Skipping Supabase update.")
        return
    
    print(f"\nStep 2: Sending {len(leads)} pre-bid leads to Supabase...")
    
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
        }
        
        response = requests.post(
            WEBHOOK_URL,
            headers=headers,
            json={"leads": leads},
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ SUCCESS: Pre-bid intelligence uploaded to Supabase")
            print("\n📊 Summary of uploaded projects:")
            for i, lead in enumerate(leads, 1):
                print(f"  {i}. {lead.get('name')}")
                print(f"     Stage: {lead.get('project_stage', 'Unknown')}")
                print(f"     Sector: {lead.get('sector', 'Unknown')}")
                print(f"     Source: {lead.get('source_url', 'N/A')[:60]}...")
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
    print("=" * 60)
    print("Delaware Pre-Bid Construction Intelligence Finder")
    print("=" * 60)
    
    new_leads = get_leads()
    
    if new_leads:
        print(f"\n{'=' * 60}")
        print(f"🎯 Found {len(new_leads)} early-stage opportunities")
        print(f"{'=' * 60}")
        send_to_supabase(new_leads)
    else:
        print("\n⚠️  No projects found - consider adjusting search parameters")
        print("Recommendations:")
        print("  • Check if xAI API key has web search permissions")
        print("  • Try broadening search to include more Delaware counties")
        print("  • Adjust date ranges in search queries")
