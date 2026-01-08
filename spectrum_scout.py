import os
import requests

# 1. Use the EXACT URL Lovable gave you
WEBHOOK_URL = "https://bjblmlrhjbnuseoinzba.supabase.co/functions/v1/scrape-leads"

# 2. Grab your Supabase Key from your GitHub Secrets
# This should be your 'Anon' or 'Service' key
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def run_sync():
    # This matches the "leads_array" format Lovable expects
    data = {
        "leads": [
            {
                "name": "DE Dept of Agriculture Flooring Upgrades",
                "address": "2320 S. Dupont Highway, Dover, DE",
                "city": "Dover",
                "county": "Kent",
                "latitude": 39.1582,
                "longitude": -75.5244,
                "source": "public_bid"
            }
        ]
    }
    
    # 🔑 THESE HEADERS ARE THE SECRET SAUCE
    headers = {
        "Content-Type": "application/json",
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    print(f"🚀 Pushing leads to {WEBHOOK_URL}...")
    
    try:
        response = requests.post(WEBHOOK_URL, json=data, headers=headers)
        
        if response.status_code == 200:
            print("✅ SUCCESS! The lead is now in your database.")
        else:
            print(f"❌ FAILED with status code: {response.status_code}")
            print(f"Error Message: {response.text}")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    run_sync()
