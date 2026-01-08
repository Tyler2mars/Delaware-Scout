import os
import requests
import sys

# Ensure the script doesn't crash if these aren't installed yet
try:
    from bs4 import BeautifulSoup
except ImportError:
    print("📦 Installing missing tools...")
    os.system('pip install beautifulsoup4 requests')
    from bs4 import BeautifulSoup

# --- CONFIGURATION ---
# Double-check this URL matches the one Lovable gave you!
WEBHOOK_URL = "https://eggntbwidigxoapturvn.supabase.co/functions/v1/scrap-leads"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_KEY:
    print("❌ ERROR: SUPABASE_KEY is missing from GitHub Secrets!")
    sys.exit(1)

def run_sync():
    # TEST LEAD: We use this to verify the connection first
    data = {
        "leads": [
            {
                "name": "Manual Lead: Delaware Flooring Opportunity",
                "address": "Dover, DE",
                "sector": "Commercial",
                "latitude": 39.1582,
                "longitude": -75.5244,
                "source": "Scraper Test"
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    print(f"🚀 Pushing data to {WEBHOOK_URL}...")
    
    try:
        response = requests.post(WEBHOOK_URL, json=data, headers=headers)
        print(f"📡 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: Data landed in Supabase.")
        else:
            print(f"⚠️ FAILED: {response.text}")
    except Exception as e:
        print(f"❌ CONNECTION ERROR: {e}")

if __name__ == "__main__":
    run_sync()
