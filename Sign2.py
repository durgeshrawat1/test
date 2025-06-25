import csv
import base64
import hashlib
import hmac
import urllib.parse
import requests
import time
import json
import sys

# ========== CONFIGURATION ==========
CSV_FILE = 'input.csv'
OUTPUT_FILE = 'output.txt'
FAILED_LOG = 'failed_batches.log'
BATCH_SIZE = 10
GOOGLE_API_BASE = "https://maps.googleapis.com/maps/api/distancematrix/json"
API_KEY = "your_api_key_here"  # ✅ Replaces CLIENT_ID
SIGNING_SECRET = "your_base64_encoded_secret"
MAX_RETRIES = 5
RETRY_BACKOFF_BASE = 2
# ===================================

def is_complete(fields):
    return all(f.strip() for f in fields)

def valid_rows(filepath):
    with open(filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        row_id = 1
        for row in reader:
            origin_fields = [
                row.get('origin_street', ''),
                row.get('origin_city', ''),
                row.get('origin_state', ''),
                row.get('origin_zip', '')
            ]
            dest_fields = [
                row.get('dest_street', ''),
                row.get('dest_city', ''),
                row.get('dest_state', ''),
                row.get('dest_zip', '')
            ]
            if not is_complete(origin_fields + dest_fields):
                continue
            origin = ', '.join(origin_fields)
            destination = ', '.join(dest_fields)
            yield row_id, origin, destination
            row_id += 1

# ✅ Updated sign_url to use key=... and sign path/query only
def sign_url(input_url: str, secret: str) -> str:
    url = urllib.parse.urlparse(input_url)
    url_to_sign = url.path + "?" + url.query

    decoded_secret = base64.urlsafe_b64decode(secret)
    signature = hmac.new(decoded_secret, url_to_sign.encode(), hashlib.sha1)
    encoded_signature = base64.urlsafe_b64encode(signature.digest()).decode()

    safe_signature = encoded_signature.replace('+', '-').replace('/', '_')
    return f"{url.scheme}://{url.netloc}{url.path}?{url.query}&signature={safe_signature}"

def log_failed_batch(batch, reason):
    with open(FAILED_LOG, 'a', encoding='utf-8') as f:
        batch_ids = [str(b[0]) for b in batch]
        f.write(f"Failed batch IDs: {batch_ids} Reason: {reason}\n")

def safe_api_call(signed_url):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(signed_url, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"API returned status {resp.status_code}, attempt {attempt}", file=sys.stderr)
        except requests.RequestException as e:
            print(f"Request error: {e}, attempt {attempt}", file=sys.stderr)

        sleep_time = RETRY_BACKOFF_BASE ** attempt
        print(f"Retrying after {sleep_time} seconds...", file=sys.stderr)
        time.sleep(sleep_time)

    print("Max retries reached, skipping batch.", file=sys.stderr)
    return None

def process_batch(batch, output_writer):
    origins = [o for (_, o, _) in batch]
    destinations = [d for (_, _, d) in batch]

    origins_str = '|'.join(urllib.parse.quote_plus(o) for o in origins)
    destinations_str = '|'.join(urllib.parse.quote_plus(d) for d in destinations)

    # ✅ Add API key to the unsigned URL
    unsigned_url = (
        f"{GOOGLE_API_BASE}?origins={origins_str}&destinations={destinations_str}"
        f"&departure_time=now&units=imperial&key={API_KEY}"
    )

    # ✅ Now sign it (no client ID involved)
    signed_url = sign_url(unsigned_url, SIGNING_SECRET)

    data = safe_api_call(signed_url)
    if data is None:
        log_failed_batch(batch, "Max retries exceeded or API failure")
        return

    raw_json_str = json.dumps(data)

    rows = data.get("rows", [])
    if len(rows) != len(origins):
        log_failed_batch(batch, f"Mismatch in rows count: expected {len(origins)}, got {len(rows)}")
        return

    for i, row in enumerate(rows):
        elements = row.get("elements", [])
        if len(elements) != len(destinations):
            log_failed_batch(batch, f"Mismatch in elements count for row {i}: expected {len(destinations)}, got {len(elements)}")
            continue

        for j, element in enumerate(elements):
            pair_id = f"{batch[i][0]}-{batch[j][0]}"
            origin = batch[i][1]
            destination = batch[j][2]

            status = element.get("status", "UNKNOWN")
            if status != "OK":
                output_writer.writerow([
                    pair_id, origin, destination, "", "", "", f"Status: {status} | {raw_json_str}"
                ])
                continue

            distance_text = element.get("distance", {}).get("text", "")
            duration_text = element.get("duration", {}).get("text", "")
            traffic_duration = element.get("duration_in_traffic", {}).get("text", "")

            output_writer.writerow([
                pair_id,
                origin,
                destination,
                distance_text,
                duration_text,
                traffic_duration,
                raw_json_str
            ])

def batch_and_process(filepath, output_filepath):
    batch = []
    with open(output_filepath, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile, delimiter='|')
        writer.writerow([
            "id", "origin", "destination", "distance_miles", "duration_time",
            "traffic_duration_time", "raw_output"
        ])

        for record in valid_rows(filepath):
            batch.append(record)
            if len(batch) == BATCH_SIZE:
                process_batch(batch, writer)
                time.sleep(1)
                batch = []

        if batch:
            process_batch(batch, writer)

if __name__ == "__main__":
    print(f"Starting processing of {CSV_FILE} ...")
    batch_and_process(CSV_FILE, OUTPUT_FILE)
    print(f"Processing complete. Output saved to {OUTPUT_FILE}")
    print(f"Any failed batches logged to {FAILED_LOG}")
