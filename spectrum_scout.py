import os
import json
import re
import requests
from xai_sdk import Client
from xai_sdk.chat import user, system
from xai_sdk.tools import web_search

# 1. Setup xAI Client
client = Client(api_key=os.environ.get("XAI_API_KEY"))

# 2. Environment Variables
WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL") 
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

def get_leads():
    print("Step 1: Searching for Delaware Vertical Construction leads (All Counties + Wilmington)...")
    
    system_prompt = """You are a construction market intelligence specialist.
Your mission: Find vertical projects (buildings) in Delaware BEFORE they go to bid.
Focus: 6-18 month window before construction starts. 
Priority: Interior flooring opportunities (Hospitals, Schools, Offices, Multifamily).
Search Strategy:
- Monitor Wilmington and County planning/zoning agendas.
- Track healthcare expansions (ChristianaCare, Bayhealth, Nemours).
- Monitor State of Delaware (OMB) and Higher Ed (UD, DSU) capital projects.
- Find Architect/Designer selections via RFQ/RFP announcements."""

    user_prompt = """Find 10 REAL vertical construction projects in Delaware in PLANNING or DESIGN phase.

CRITICAL CONTEXT:
- TODAY'S DATE: January 14, 2026.
- ONLY include projects with construction start dates in FUTURE (Q2 2026 or later).
- STRICTLY EXCLUDE: Roads, bridges, sewers, or projects already under construction.

REQUIRED SEARCH QUERIES:
1. "City of Wilmington Delaware Planning Commission agenda 2025 2026"
2. "New Castle County Active Plans 2026 commercial"
3. "Kent County DE Regional Planning Commission public hearing 2026"
4. "Sussex County DE Planning and Zoning land use docket 2026"
5. "ChristianaCare Middletown health center expansion status 2026"
6. "Nemours Children's Health Delaware expansion architect"
7. "University of Delaware capital project announcements 2026"
8. "Delaware architect selection announcement 2025 2026"
9. "Middletown DE commercial development proposals 2026"
10. "New medical office building Delaware planning 2026"

THINKING PROCESS:
1. Identify a project from search results.
2. Verify it is a building (vertical construction).
3. Confirm status: Is it in design/planning? Has groundbreaking happened? (Reject if started).
4. Identify the Architect/Designer: This is priority.
5. Estimate flooring scope based on sector and square footage.

Return a JSON array of objects with these fields:
{
  "name": "Project Name",
  "address": "Address or Site Description",
  "city": "City",
  "county": "New Castle|Kent|Sussex",
  "sector": "Healthcare|Education|Corporate|Multi Family|Hospitality|Senior Living|Retail|Mixed Use",
  "budget": "Estimated cost",
  "source_url": "URL to source",
  "designer": "Architect/Firm Name",
  "general_contractor": "GC or 'TBD - Pre-bid'",
  "project_stage": "Planning|Design|Permits",
  "construction_status": "Not Started - Expected [Date]",
  "description": "2-3 sentences on the project",
  "flooring_opportunity": "Estimated flooring scope",
  "flooring_tags": ["LVT", "Carpet", "Tile", "Concrete"],
  "estimated_sqft": 0,
  "last_updated": "2026-01-14"
}"""

    try:
        chat = client.chat.create(
            model="grok-4-1-fast", # Optimized for web-search reasoning
            tools=[web_search()],
        )
        
        chat.append(system(system_prompt))
        chat.append(user(user_prompt))
        
        print("🔍 Grok is analyzing Delaware planning dockets and news...")
        response = chat.sample()
        raw_content = response.content.strip()

        # Robust JSON extraction (handles AI preamble/markdown)
        json_match = re.search(r'\[\s*{.*}\s*\]', raw_content, re.DOTALL)
        if json_match:
            raw_content = json_match.group(0)
        
        leads = json.loads(raw_content)
        
        # Validation Logic
        validated_leads = []
        started_keywords = ['under construction', 'groundbreaking held', 'broke ground', 'topped out']
        
        for lead in leads:
            # 1. Basic check
            if not lead.get('source_url') or 'http' not in lead['source_url']:
                continue
                
            # 2. Construction Status Check
            desc = (lead.get('description', '') + lead.get('construction_status', '')).lower()
            if any(kw in desc for kw in started_keywords):
                print(f"🚫 Rejected: {lead.get('name')} (Already started)")
                continue
            
            # 3. Architect Value Add
            if lead.get('designer') in ['TBD', '', 'N/A']:
                lead['designer'] = "Seeking Architect / RFP Stage"

            validated_leads.append(lead)
            print(f"✅ Found: {lead.get('name')} ({lead.get('city')})")

        return validated_leads
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def send_to_supabase(leads):
    if not leads: return
    print(f"\nStep 2: Uploading {len(leads)} leads to Supabase...")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {SUPABASE_ANON_KEY}"}
    try:
        response = requests.post(WEBHOOK_URL, headers=headers, json={"leads": leads}, timeout=30)
        if response.status_code == 200:
            print("✅ Data synchronized with Supabase.")
        else:
            print(f"❌ Upload failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    results = get_leads()
    send_to_supabase(results)
