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


async def fetch_distance(session, batch, api_key):
    employees, origins, destinations = zip(*[
        (rec['employee'], rec['source_address'], rec['destination_address']) for rec in batch
    ])

    params = {
        'origins': '|'.join(origins),
        'destinations': '|'.join(destinations),
        'key': api_key
    }

    url = 'https://maps.googleapis.com/maps/api/distancematrix/json?' + urlencode(params)
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

    try:
        async with session.get(url) as response:
            result = await response.json()
    except Exception as e:
        logging.error(f"❌ API request failed: {sanitize(str(e))}")
        return []

    results = []
    for i, rec in enumerate(batch):
        try:
            element = result['rows'][i]['elements'][i]
            distance = element.get('distance', {})
            duration = element.get('duration', {})
        except Exception as e:
            distance, duration = {}, {}
            logging.warning(f"⚠️ Missing element for employee {sanitize(rec['employee'])}: {sanitize(str(e))}")

        results.append({
            'employee': rec['employee'],
            'source': rec['source_address'],
            'destination': rec['destination_address'],
            'distance_text': distance.get('text', ''),
            'distance_value': distance.get('value', ''),
            'duration_text': duration.get('text', ''),
            'duration_value': duration.get('value', ''),
            'timestamp': timestamp,
            'raw_response': json.dumps(result)
        })

    return results


async def main():
    config = load_config()
    log_file = config['files']['log_file']
    setup_logger(log_file)

    input_dir = config['files']['input_dir']
    output_path = config['files']['output_path']
    api_key = config['google_api']['api_key']

    source_cols = config['address_columns']['source']
    destination_cols = config['address_columns']['destination']
    batch_size = config['settings'].get('batch_size', 10)
    delay = config['settings'].get('delay_seconds', 1.0)

    if len(sys.argv) < 2:
        logging.error("❌ Missing input filename argument.")
        print("Usage: python script.py <input_filename>")
        sys.exit(1)

    input_filename = sys.argv[1]
    input_path = os.path.join(input_dir, input_filename)

    logging.info(f"📥 Reading input file: {sanitize(input_path)}")
    logging.info(f"📤 Output will be saved to: {sanitize(output_path)}")

    try:
        df = pl.read_csv(input_path, separator='|')
    except Exception as e:
        logging.error(f"❌ Failed to read input: {sanitize(str(e))}")
        sys.exit(1)

    df = df.with_columns([
        pl.concat_str(source_cols, separator=' ').alias('source_address'),
        pl.concat_str(destination_cols, separator=' ').alias('destination_address'),
    ])

    data = df.select(['employee', 'source_address', 'destination_address']).to_dicts()
    batches = [data[i:i + batch_size] for i in range(0, len(data), batch_size)]
    all_results = []

    async with aiohttp.ClientSession() as session:
        for idx, batch in enumerate(batches):
            logging.info(f"🚀 Sending batch {idx + 1}/{len(batches)}")
            results = await fetch_distance(session, batch, api_key)
            all_results.extend(results)
            await asyncio.sleep(delay)

    if not all_results:
        logging.warning("⚠️ No results returned. Nothing to write.")
    else:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        pl.DataFrame(all_results).write_csv(output_path, separator='|')
        logging.info(f"✅ Output written to {sanitize(output_path)}")

    # Delete input file after successful processing
    try:
        os.remove(input_path)
        logging.info(f"🗑️ Deleted input file: {sanitize(input_path)}")
    except Exception as e:
        logging.warning(f"⚠️ Failed to delete input file: {sanitize(str(e))}")

    logging.info("🏁 Script finished.")


if __name__ == '__main__':
    start = time.time()
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"💥 Uncaught exception: {sanitize(str(e))}")
        raise
    print(f"⏱️ Done in {time.time() - start:.2f} seconds")
