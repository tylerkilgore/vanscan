import json
import csv

def analyze_listing(car):
    # --- DATA EXTRACTION ---
    vin = car.get('vin', 'Unknown')
    year = car.get('year', 0)
    make = car.get('make', {}).get('name', 'Unknown')
    model = car.get('model', {}).get('name', 'Unknown')

    mileage_str = car.get('specifications', {}).get('mileage', {}).get('value', '999999')
    try:
        mileage = int(mileage_str.replace(',', ''))
    except ValueError:
        mileage = 999999

    price = car.get('pricingDetail', {}).get('salePrice', 0)

    engine_size = car.get('displacementUOM', 0.0)
    engine_name = car.get('engine', {}).get('name', '').lower()
    trans_desc = car.get('transmission', {}).get('description', '').lower()
    description_text = car.get('description', {}).get('label', '').lower()

    # Extra fields for the card display
    color = car.get('color', {}).get('exteriorColorSimple', 'Unknown')
    images = car.get('images', {}).get('sources', [])
    image_url = images[0]['src'] if images else ''

    listing_id = car.get('id')
    link = f"https://www.autotrader.com/cars-for-sale/vehicledetails.xhtml?listingId={listing_id}"

    # --- THE TODD FILTER LOGIC ---

    score = 0
    notes = []

    # Global Filters
    if mileage > 110000:
        return None
    if price > 22000:
        return None

    # 1. CHEVY EXPRESS LOGIC
    if "Express" in model:
        if 5.9 <= engine_size <= 6.1:
            score += 100
            notes.append("Good Engine Size (6.0L)")
        elif engine_size == 4.3 or engine_size == 4.8:
             return None

        if "8-speed" in trans_desc:
            return None
        elif "6-speed" in trans_desc:
            score += 50

        if len(vin) == 17 and vin[7] == 'G':
            score += 100
            notes.append("VIN Confirmed L96")

    # 2. FORD TRANSIT LOGIC
    elif "Transit" in model:
        if engine_size == 3.7:
            score += 100
            notes.append("Good Engine Size (3.7L)")
        elif engine_size == 3.5:
            return None

        if "turbo" in engine_name or "ecoboost" in description_text:
            return None

        if "10-speed" in trans_desc:
            return None

        if "high roof" in description_text:
             notes.append("Warning: High Roof")

        if len(vin) == 17 and vin[7] == 'M':
            score += 100
            notes.append("VIN Confirmed 3.7L")

    # Final Verdict
    if score >= 100:
        return {
            "Make": make,
            "Model": model,
            "Year": year,
            "Price": price,
            "Mileage": mileage,
            "Engine_Liters": engine_size,
            "Transmission": trans_desc.title(),
            "Color": color,
            "VIN": vin,
            "Image": image_url,
            "Score": score,
            "Notes": " | ".join(notes),
            "Link": link
        }
    return None

def load_cardata(filepath):
    """Handle both single JSON objects and concatenated multi-object files."""
    with open(filepath, 'r') as f:
        content = f.read()

    # Try single object first
    try:
        data = json.loads(content)
        return data.get('listings', [])
    except json.JSONDecodeError:
        pass

    # Multiple objects separated by commas/whitespace — wrap in array
    try:
        data = json.loads('[' + content + ']')
        listings = []
        for obj in data:
            listings.extend(obj.get('listings', []))
        return listings
    except json.JSONDecodeError as e:
        print(f"Failed to parse data file: {e}")
        return []

# --- MAIN EXECUTION ---
processed_listings = []

try:
    raw_list = load_cardata('cardata')

    print(f"Scanning {len(raw_list)} vehicles...")

    seen_vins = set()
    for car in raw_list:
        result = analyze_listing(car)
        if result:
            vin = result['VIN']
            if vin not in seen_vins:
                seen_vins.add(vin)
                processed_listings.append(result)

    # Sort by score (descending), then price (ascending)
    processed_listings.sort(key=lambda x: (-x['Score'], x['Price']))

    if processed_listings:
        # CSV output
        keys = processed_listings[0].keys()
        with open('van_candidates.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(processed_listings)

        # JSON output for the web page
        with open('van_candidates.json', 'w') as f:
            json.dump(processed_listings, f, indent=2)

        print(f"Found {len(processed_listings)} solid candidates!")
        print(f"  -> van_candidates.csv")
        print(f"  -> van_candidates.json")
    else:
        print("No vans matched the criteria in this batch.")

except FileNotFoundError:
    print("Please save the data as 'cardata' in the same directory.")
