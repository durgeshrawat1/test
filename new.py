import requests
import json

API_KEY = 'YOUR_API_KEY'

def geocode_address(address):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": API_KEY}
    response = requests.get(url, params=params).json()
    if response['status'] == 'OK':
        loc = response['results'][0]['geometry']['location']
        return {"latitude": loc['lat'], "longitude": loc['lng']}
    else:
        raise Exception(f"Geocoding failed for {address}: {response['status']}")

def compute_route_matrix(origins, destinations):
    url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "originIndex,destinationIndex,duration,distanceMeters,status"
    }

    body = {
        "origins": [{"waypoint": {"location": {"latLng": o}}} for o in origins],
        "destinations": [{"waypoint": {"location": {"latLng": d}}} for d in destinations],
        "travelMode": "DRIVE"
    }

    response = requests.post(url, headers=headers, data=json.dumps(body))
    if response.status_code != 200:
        raise Exception(f"API call failed: {response.status_code} {response.text}")
    return response.json()

# === Input: 5 Origins and 5 Destinations ===
origin_addresses = [
    "New York, NY",
    "Philadelphia, PA",
    "Boston, MA",
    "Baltimore, MD",
    "Pittsburgh, PA"
]

destination_addresses = [
    "Washington, DC",
    "Richmond, VA",
    "Hartford, CT",
    "Albany, NY",
    "Buffalo, NY"
]

# Geocode
origins = [geocode_address(addr) for addr in origin_addresses]
destinations = [geocode_address(addr) for addr in destination_addresses]

# Compute Route Matrix
matrix = compute_route_matrix(origins, destinations)

# Print results
print("\nRoute Matrix Results (5x5):")
for result in matrix:
    o_idx = result['originIndex']
    d_idx = result['destinationIndex']
    status = result.get("status", "OK")

    if status == "OK":
        miles = result["distanceMeters"] / 1609.34
        seconds = int(result["duration"].replace('s', ''))
        print(f"From {origin_addresses[o_idx]} to {destination_addresses[d_idx]}:")
        print(f"  → Distance: {miles:.2f} miles, Duration: {seconds // 60} mins")
    else:
        print(f"From {origin_addresses[o_idx]} to {destination_addresses[d_idx]}: Error - {status}")
