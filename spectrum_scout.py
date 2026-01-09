import os
import requests
import json

# Your Supabase details (pointing to your REAL project)
WEBHOOK_URL = "https://eggntbwidigxoapturvn.supabase.co/functions/v1/scrap-leads"
XAI_API_KEY = os.environ.get("XAI_API_KEY")

def get_leads_from_grok():
    print("🤖 Grok is researching Delaware projects...")
    
    # This is your EXACT prompt formatted for the API
    master_prompt = """
    Search for upcoming commercial construction and renovation projects in Delaware from September 2025 through December 2027 that could involve flooring sales opportunities, excluding warehouse buildings as they typically do not use commercial flooring. Include details like project names, locations (include Latitude and Longitude for mapping), timelines, budgets, owners/developers, architects, general contractors, designer, and bid/RFP deadlines. Focus on sectors such as offices, retail, healthcare, education, hospitality, industrial (non-warehouse), and government buildings. Use reliable sources like Delaware state procurement portals (e.g., MyMarketplace, Bid Express), construction databases (e.g., Dodge Data & Analytics, ConstructConnect, BidClerk), local news outlets, real estate reports, industry associations (e.g., Associated Builders and Contractors Delaware Chapter), ENR MidAtlantic (enr.com), Bisnow Philadelphia (bisnow.com/philadelphia), Delaware Online/The News Journal (delawareonline.com), Cape Gazette (capegazette.com), Delaware State Chamber of Commerce (delawarestatechamber.com), Delaware Contractors Association (delawarecontractors.org), and local county planning sites (e.g., New Castle, Sussex, Kent). Prioritize projects where flooring bids or subcontracts might be open, and compile a comprehensive list with contact info for leads. If possible, include any economic development announcements or planned expansions in Delaware during that period.
    
    IMPORTANT: Return the data ONLY as a JSON array of objects. 
    Each object must have these keys: "name", "address", "sector", "budget", "source".
    """

    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "grok-2-latest", 
        "messages": [{"role": "user", "content": master_prompt}]
    }

    response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=data)
    
    # Parse the JSON out of Grok's text response
    raw_content = response.json()['choices'][0]['message']['content']
    return json.loads(raw_content.strip('```json').strip('```'))

def push_to_supabase(leads):
    print(f"🚀 Pushing {len(leads)} Grok-verified leads to your map...")
    # Add your Supabase headers and post request here
    # ...
