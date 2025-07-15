import polars as pl
import aiohttp
import asyncio
import time
import json
import os
import sys
import toml
import logging
import shutil
from urllib.parse import urlencode
from datetime import datetime
import ssl
import random

GOOGLE_RATE_LIMIT_PER_SECOND = 10
MAX_RETRIES = 5

def sanitize(text: str) -> str:
    return text.replace('\n', ' ').replace('\r', ' ').replace('\x00', '')

def load_config(path='config.toml'):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file {path} not found.")
    return toml.load(path)

def archive_existing_log(log_file: str):
    if os.path.exists(log_file):
        archive_folder = os.path.join(os.path.dirname(log_file), 'archive_logs')
        os.makedirs(archive_folder, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archived_name = f"log_{timestamp}.log"
        shutil.move(log_file, os.path.join(archive_folder, archived_name))

def setup_logger(log_file: str):
    archive_existing_log(log_file)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logging.basicConfig(
        filename=log_file,
        filemode='a',
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s'
    )
    logging.info("🔧 Logging initialized.")

async def fetch_single(session, rec, api_key, base_url, ssl_context, retry=0):
    await rate_limiter.acquire()
    try:
        params = {
            'origins': rec['source_address'],
            'destinations': rec['destination_address'],
        }
        if api_key:
            params['key'] = api_key

        url = base_url + '?' + urlencode(params)
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

        async with session.get(url, ssl=ssl_context) as response:
            if response.status == 429:
                if retry < MAX_RETRIES:
                    wait_time = 2 ** retry + random.uniform(0.1, 0.5)
                    logging.warning(f"🕒 429 Too Many Requests — retrying in {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                    return await fetch_single(session, rec, api_key, base_url, ssl_context, retry + 1)
                else:
                    logging.error("❌ Max retries reached for rate limiting.")
                    return None

            if response.status != 200:
                logging.error(f"❌ HTTP {response.status} for {rec['employee']}")
                return None

            result = await response.json()

        try:
            element = result['rows'][0]['elements'][0]
            distance = element.get('distance', {})
            duration = element.get('duration', {})
        except Exception as e:
            distance, duration = {}, {}
            logging.warning(f"⚠️ Incomplete data for {rec['employee']}: {sanitize(str(e))}")

        return {
            'employee': rec['employee'],
            'source': rec['source_address'],
            'destination': rec['destination_address'],
            'distance_text': distance.get('text', ''),
            'distance_value': distance.get('value', ''),
            'duration_text': duration.get('text', ''),
            'duration_value': duration.get('value', ''),
            'timestamp': timestamp,
            'raw_response': json.dumps(result)
        }

    finally:
        await asyncio.sleep(1 / GOOGLE_RATE_LIMIT_PER_SECOND)
        rate_limiter.release()

async def fetch_all(records, api_key, base_url, concurrency, ssl_context):
    global rate_limiter
    rate_limiter = asyncio.Semaphore(GOOGLE_RATE_LIMIT_PER_SECOND)
    semaphore = asyncio.Semaphore(concurrency)

    async with aiohttp.ClientSession() as session:
        async def safe_call(rec):
            async with semaphore:
                return await fetch_single(session, rec, api_key, base_url, ssl_context)

        results = await asyncio.gather(*(safe_call(r) for r in records))
        return [r for r in results if r]

async def main():
    config = load_config()
    log_file = config['files']['log_file']
    setup_logger(log_file)

    input_dir = config['files']['input_dir']
    output_path = config['files']['output_path']
    api_key = config['api'].get('api_key')
    base_url = config['api']['base_url']
    concurrency = config['settings'].get('concurrency', 10)

    ssl_cfg = config.get("ssl", {})
    cert_file = ssl_cfg.get("cert_file")
    key_file = ssl_cfg.get("key_file")
    ca_bundle = ssl_cfg.get("ca_bundle")

    ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    if ca_bundle:
        ssl_context.load_verify_locations(cafile=ca_bundle)
    ssl_context.load_cert_chain(certfile=cert_file, keyfile=key_file)

    if len(sys.argv) < 2:
        logging.error("❌ Missing input filename.")
        print("Usage: python script.py <filename>")
        sys.exit(1)

    filename = sys.argv[1]
    input_path = os.path.join(input_dir, filename)

    logging.info(f"📥 Reading: {sanitize(input_path)}")

    try:
        df = pl.read_csv(input_path, separator='|')
    except Exception as e:
        logging.error(f"❌ Failed to read input: {sanitize(str(e))}")
        sys.exit(1)

    source_cols = config['address_columns']['source']
    destination_cols = config['address_columns']['destination']

    df = df.with_columns([
        pl.concat_str(source_cols, separator=' ').alias('source_address'),
        pl.concat_str(destination_cols, separator=' ').alias('destination_address')
    ])

    data = df.select(['employee', 'source_address', 'destination_address']).to_dicts()

    logging.info(f"🚀 Sending {len(data)} records with concurrency={concurrency}")
    results = await fetch_all(data, api_key, base_url, concurrency, ssl_context)

    if results:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        pl.DataFrame(results).write_csv(output_path, separator='|')
        logging.info(f"✅ Output written to {sanitize(output_path)}")
    else:
        logging.warning("⚠️ No results to write.")

    try:
        os.remove(input_path)
        logging.info(f"🗑️ Deleted: {sanitize(input_path)}")
    except Exception as e:
        logging.warning(f"⚠️ Failed to delete: {sanitize(str(e))}")

    logging.info("🏁 Done.")

if __name__ == '__main__':
    start = time.time()
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"💥 Fatal error: {sanitize(str(e))}")
        raise
    print(f"⏱️ Completed in {time.time() - start:.2f} seconds")
