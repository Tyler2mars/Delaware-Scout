import os
import requests

# --- 1. SETUP ---
# This is the "Inbox" URL Lovable gave you
WEBHOOK_URL = "https://bjblmlrhjbnuseoinzba.supabase.co/functions/v1/scrape-leads"

# --- 2. DATA TO SEND ---
def get_delaware_leads():
    """These are the real leads we want to send to Lovable."""
    return [
        {
            "name": "DE Dept of Agriculture Flooring Upgrades",
            "address": "2320 S. Dupont Highway, Dover, DE",
            "city": "Dover",
            "county": "Kent",
            "latitude": 39.1582,
            "longitude": -75.5244,
            "source": "OMB BidConDocs"
        },
        {
            "name": "CSD School for the Deaf Reno",
            "address": "630 E Chestnut Hill Rd, Newark, DE",
            "city": "Newark",
            "county": "New Castle",
            "latitude": 39.6837,
            "longitude": -75.7497,
            "source": "Christina School District"
        }
    ]

# --- 3. SENDING THE DATA ---
def run_sync():
    print("🚀 Pushing leads to Lovable Webhook...")
    leads = get_delaware_leads()
    
    for lead in leads:
        try:
            # This sends the project to Lovable's inbox
            response = requests.post(WEBHOOK_URL, json=lead)
            if response.status_code == 200:
                print(f"✅ Success: {lead['name']} is now on the map!")
            else:
                print(f"⚠️ Sent {lead['name']} but got code: {response.status_code}")
        except Exception as e:
            print(f"❌ Error sending {lead['name']}: {e}")

if __name__ == "__main__":
    run_sync()
