import os
import requests
from supabase import create_client, Client

# --- 1. SETUP ---
# GitHub Actions will "inject" these from your Secrets
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Initialize the Supabase Assistant
if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: Secrets not found. Check your GitHub Settings!")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. THE SCRAPER FUNCTIONS ---

def get_state_bids():
    """Finds leads from the Delaware OMB/State portals."""
    # This is a 'placeholder' list. As we refine your scraper, 
    # this function will eventually crawl the actual websites.
    return [
        {
            "name": "DE Dept of Agriculture Flooring Upgrades",
            "address": "2320 S. Dupont Highway, Dover, DE",
            "bid_deadline": "2026-01-29",
            "source": "OMB BidConDocs",
            "sector": "Government",
            "description": "Remove and replace 7 phases of flooring. Mandatory pre-bid Jan 14."
        }
    ]

def get_school_bids():
    """Finds leads from DE School District portals."""
    return [
        {
            "name": "CSD School for the Deaf Reno",
            "address": "630 E Chestnut Hill Rd, Newark, DE",
            "bid_deadline": "2026-01-21",
            "source": "Christina School District",
            "sector": "Education",
            "description": "LVT and Broadloom installation."
        },
        {
            "name": "Heritage Elementary Flooring",
            "address": "2815 Highlands Lane, Wilmington, DE",
            "bid_deadline": "2026-02-05",
            "source": "Red Clay School District",
            "sector": "Education",
            "description": "Library wing carpet replacement."
        }
    ]

# --- 3. THE SYNC ENGINE ---

def run_sync():
    print("🚀 Starting Delaware Scout Scraper...")
    
    # Combine all found projects
    all_projects = get_state_bids() + get_school_bids()
    
    for project in all_projects:
        # We skip anything labeled 'Warehouse' to save you time
        if "warehouse" in project['name'].lower() or "warehouse" in project['description'].lower():
            print(f"⏩ Skipping {project['name']} (Reason: Warehouse)")
            continue
            
        # THE MAGIC LINE: .upsert() 
        # This tells Supabase: 'If the project name exists, update it. If not, create it.'
        try:
            supabase.table("projects").upsert(
                project, 
                on_conflict="name"
            ).execute()
            print(f"✅ Synced: {project['name']}")
        except Exception as e:
            print(f"❌ Error on {project['name']}: {e}")

if __name__ == "__main__":
    run_sync()
