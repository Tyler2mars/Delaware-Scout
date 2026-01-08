import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# --- CONFIGURATION ---
WEBHOOK_URL = "https://bjblmlrhjbnuseoinzba.supabase.co/functions/v1/scrape-leads"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def get_headers():
    return {
        "Content-Type": "application/json",
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

def scrape_delaware_bids():
    """Scrapes the main Delaware state bid portal."""
    print("🔎 Searching Delaware State Bid Portal...")
    url = "https://bids.delaware.gov/"
    leads = []
    
    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Finding the bid table (Standard for Delaware's portal)
        rows = soup.select("table#bid_table tr")[1:] # Skip header
        for row in rows:
            cols = row.find_all("td")
            if len(cols) > 3:
                title = cols[1].text.strip()
                # Filtering out warehouses and non-flooring sectors
                if any(word in title.lower() for word in ['warehouse', 'storage', 'hangar']):
                    continue
                
                leads.append({
                    "name": title,
                    "address": "Delaware (Check Source)",
                    "sector": cols[2].text.strip(),
                    "deadline": cols[3].text.strip(),
                    "source": "State Procurement"
                })
    except Exception as e:
        print(f"Error scraping State Portal: {e}")
    return leads

def scrape_ncc_planning():
    """Scrapes New Castle County Active Plans."""
    print("🔎 Searching NCC Planning Site...")
    url = "https://www.newcastlede.gov/410/Active-Plans"
    leads = []
    
    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # NCC lists projects in 'description' blocks
        projects = soup.select(".description")
        for p in projects:
            text = p.get_text()
            # Look for commercial indicators (Clubhouse, School, Office, Retail)
            if any(k in text.lower() for k in ['clubhouse', 'school', 'office', 'retail', 'renovation']):
                if 'warehouse' in text.lower(): continue
                
                leads.append({
                    "name": text.split('.')[0][:100], # Grab first sentence as title
                    "address": "New Castle County, DE",
                    "sector": "Commercial Development",
                    "source": "NCC Planning"
                })
    except Exception as e:
        print(f"Error scraping NCC: {e}")
    return leads

def run_sync():
    all_leads = scrape_delaware_bids() + scrape_ncc_planning()
    
    if not all_leads:
        print("📭 No new projects found today.")
        return

    data = {"leads": all_leads}
    
    print(f"🚀 Pushing {len(all_leads)} leads to Supabase...")
    res = requests.post(WEBHOOK_URL, json=data, headers=get_headers())
    
    if res.status_code == 200:
        print(f"✅ Success! {len(all_leads)} projects added to your map.")
    else:
        print(f"❌ Failed: {res.status_code} - {res.text}")

if __name__ == "__main__":
    run_sync()
