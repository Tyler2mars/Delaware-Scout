import os
import json
import requests
from openai import OpenAI

# Setup
client = OpenAI(
    api_key=os.environ.get("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
)

WEBHOOK_URL = os.environ.get("SUPABASE_WEBHOOK_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

def search_web(query):
    """
    Use a real search API to find current businesses.
    Options:
    - SerpAPI (serpapi.com) - $50/mo for 5k searches
    - ScraperAPI (scraperapi.com) - various plans
    - Tavily AI (tavily.com) - AI-optimized search
    """
    SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
    
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": 20  # Get more results to filter from
    }
    
    try:
        response = requests.get("https://serpapi.com/search", params=params)
        return response.json().get("organic_results", [])
    except Exception as e:
        print(f"Search error: {e}")
        return []

def verify_delaware_location(address, city):
    """
    Verify the address is actually in Delaware using a geocoding API
    """
    GEOCODING_KEY = os.environ.get("GEOCODING_API_KEY")  # e.g., Google Maps API
    
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": f"{address}, {city}, DE",
            "key": GEOCODING_KEY
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("results"):
            result = data["results"][0]
            # Check if Delaware is in the address components
            for component in result.get("address_components", []):
                if "administrative_area_level_1" in component.get("types", []):
                    return component.get("short_name") == "DE"
        return False
    except:
        return False

def extract_firm_data(search_results):
    """
    Use AI to parse search results into structured data
    """
    prompt = f"""Analyze these search results and extract information about Architecture and Interior Design firms in Delaware.

Search Results:
{json.dumps(search_results[:10], indent=2)}

Extract ONLY firms that:
1. Are explicitly located in Delaware (DE)
2. Are architecture or interior design firms
3. Have verifiable contact information

Return a JSON list with this structure:
[
  {{
    "name": "Firm legal name",
    "address": "Street address",
    "city": "Delaware city",
    "website": "Official website URL from search result",
    "phone": "Phone number if found",
    "contact_email": "Email if found or null",
    "specialties": ["List", "of", "specialties"],
    "description": "Brief description",
    "source_url": "The URL where this info was found"
  }}
]

If you cannot find enough verified Delaware firms, return fewer results rather than guessing.
CRITICAL: Only include firms you found in the search results. Do not make up firms."""

    try:
        response = client.chat.completions.create(
            model="grok-4-1-fast-non-reasoning",
            messages=[
                {"role": "system", "content": "You are a data extraction specialist. Extract only verified information from provided sources. Never fabricate data."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        raw_content = response.choices[0].message.content.strip()
        
        if raw_content.startswith("```"):
            raw_content = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
            if raw_content.startswith("json"):
                raw_content = raw_content[4:].strip()
        
        return json.loads(raw_content)
    except Exception as e:
        print(f"Extraction error: {e}")
        return []

def get_firms():
    print("Step 1: Searching for Delaware Architecture & Design firms...")
    
    # Search multiple queries for better coverage
    queries = [
        "architecture firms Delaware",
        "interior design firms Wilmington Delaware",
        "architects Newark Delaware",
        "design firms Dover Delaware"
    ]
    
    all_results = []
    for query in queries:
        print(f"  Searching: {query}")
        results = search_web(query)
        all_results.extend(results)
    
    print(f"Step 2: Extracting firm data from {len(all_results)} search results...")
    firms = extract_firm_data(all_results)
    
    print(f"Step 3: Verifying {len(firms)} firms...")
    verified_firms = []
    for firm in firms:
        # Optional: verify location with geocoding
        # is_valid = verify_delaware_location(firm.get("address"), firm.get("city"))
        # if is_valid:
        #     verified_firms.append(firm)
        
        # For now, just check if they have required fields
        if firm.get("name") and firm.get("website") and firm.get("city"):
            verified_firms.append(firm)
            print(f"  ✓ {firm['name']} - {firm['city']}")
        else:
            print(f"  ✗ Skipped incomplete entry")
    
    return verified_firms

def send_to_supabase(firms):
    if not firms:
        print("No firms found to send.")
        return
    
    print(f"\nStep 4: Sending {len(firms)} verified firms to Supabase...")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    }
    
    payload = {"firms": firms}
    
    try:
        response = requests.post(WEBHOOK_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            print("✓ SUCCESS: Firms added to directory.")
        else:
            print(f"✗ FAILED: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    found_firms = get_firms()
    print(f"\nTotal verified firms: {len(found_firms)}")
    send_to_supabase(found_firms)
