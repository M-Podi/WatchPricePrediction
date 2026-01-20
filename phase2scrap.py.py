import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import json
import time
import random
import os
import logging
import threading
import queue
import csv

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
INPUT_FILE = "chrono24_watches_selenium4.csv"
OUTPUT_FILE = "watches_detailed2.jsonl"  # Changed to JSONL
NUM_THREADS = 32
file_lock = threading.Lock()
driver_init_lock = threading.Lock()

class JSONLWriter:
    """Thread-safe JSONL writer for high-performance appending"""
    def __init__(self, output_file):
        self.output_file = output_file
        self.processed_links = set()

        # Load existing links to support resuming
        if os.path.isfile(output_file):
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                data = json.loads(line)
                                self.processed_links.add(data.get('Link', ''))
                            except json.JSONDecodeError:
                                continue
                logger.info(f"Resumed: {len(self.processed_links)} links already processed")
            except Exception as e:
                logger.error(f"Error reading JSONL: {e}")

    def write_row(self, row):
        """Append a single JSON object to the file immediately"""
        with file_lock:
            try:
                with open(self.output_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(row) + "\n")
            except Exception as e:
                logger.error(f"File write error: {e}")

def extract_data(soup):
    """Deep extraction logic for Chrono24 tables"""
    data = {}
    
    # Locate the specifications table
    table = soup.find('table', class_='table') or soup.find('table')
    if not table:
        return data

    current_section = "General"
    
    for row in table.find_all('tr'):
        cells = row.find_all('td')
        
        # 1. Section Headers (Basic Info, Caliber, etc.)
        header = row.find(['h3', 'h4'])
        if header:
            current_section = header.get_text(strip=True)
            continue

        # 2. Key-Value Rows
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True).rstrip(':')
            val_cell = cells[1]
            
            # Clean noise (Size guides, info icons)
            for noise in val_cell.find_all(['button', 'i', 'span'], class_=['js-lugwidth-btn', 'js-tooltip', 'i-info', 'i-ruler']):
                noise.decompose()
            
            value = val_cell.get_text(" ", strip=True)
            
            if label and value:
                # Basic cleaning for Price column
                if label == "Price":
                    value = value.split('(')[0].split('[')[0].strip()
                data[label] = value

        # 3. Description-style rows (No labels)
        elif len(cells) == 1:
            val_text = cells[0].get_text(" ", strip=True)
            if not val_text or "Show information" in val_text:
                continue
            
            key = f"{current_section} items" if current_section in ["Functions", "Other"] else current_section
            data[key] = f"{data.get(key, '')}, {val_text}".strip(", ")

    # 4. Seller Details
    for btn in soup.find_all('button', class_='js-link-merchant-name'):
        data['Seller type'] = btn.get_text(strip=True)
        break

    rating = soup.find('span', class_='rating')
    if rating:
        data['Seller rating'] = rating.get('title', '')

    reviews = soup.find('button', class_='js-link-merchant-reviews')
    if reviews:
        data['Seller reviews'] = reviews.get_text(strip=True)

    return data

def scrape_url(driver, url, original_data):
    try:
        driver.get(url)
        time.sleep(random.uniform(0.1, 0.2))
        soup = BeautifulSoup(driver.page_source, 'lxml')

        if "Access denied" in soup.text or "Challenge Validation" in soup.text:
            logger.warning("Bot detected or Access Denied")
            return None

        result = original_data.copy()
        extracted = extract_data(soup)
        if not extracted:
            return None
            
        result.update(extracted)
        return result
    except Exception as e:
        logger.debug(f"Scrape error on {url}: {e}")
        return None

class ScrapeThread(threading.Thread):
    def __init__(self, thread_id, task_queue, storage, results):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.task_queue = task_queue
        self.storage = storage
        self.results = results
        self.daemon = True

    def run(self):
        options = uc.ChromeOptions()
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")

        driver = None
        try:
            with driver_init_lock:
                driver = uc.Chrome(options=options)
                driver.set_page_load_timeout(10)

            while True:
                try:
                    idx, row = self.task_queue.get(timeout=5)
                except queue.Empty:
                    break

                url = row.get('Link', '').strip()
                if not url:
                    self.task_queue.task_done()
                    continue

                result = scrape_url(driver, url, row)

                if result:
                    self.storage.write_row(result)
                    self.results['success'] += 1
                    if self.results['success'] % 25 == 0:
                        logger.info(f"Progress: {self.results['success']} watches saved to JSONL")
                else:
                    logger.info("failed link")
                    self.results['failed'] += 1
                    self.results['failed_links'].append(url)

                self.task_queue.task_done()
        except Exception as e:
            logger.error(f"Thread {self.thread_id} fatal error: {e}")
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            logger.info(f"Thread {self.thread_id} stopped")

def main():
    logger.info(f"Starting Scraper using JSONL Storage")
    
    if not os.path.isfile(INPUT_FILE):
        logger.error(f"Input file {INPUT_FILE} not found!")
        return

    # Load work to do
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        all_input_rows = list(csv.DictReader(f))

    # Initialize storage and filter already-scraped links
    storage = JSONLWriter(OUTPUT_FILE)
    remaining_rows = [
        (idx, row) for idx, row in enumerate(all_input_rows, 1)
        if row.get('Link', '') not in storage.processed_links
    ]

    if not remaining_rows:
        logger.info("Dataset already complete.")
        return

    logger.info(f"Items to scrape: {len(remaining_rows)}")

    task_queue = queue.Queue()
    for task in remaining_rows:
        task_queue.put(task)

    results = {'success': 0, 'failed': 0, 'failed_links': []}
    threads = []
    
    for i in range(NUM_THREADS):
        t = ScrapeThread(i, task_queue, storage, results)
        t.start()
        threads.append(t)

    task_queue.join()
    
    for t in threads:
        t.join(timeout=5)

    logger.info(f"Scraping Session Finished.")
    logger.info(f"New successes: {results['success']} | Failures: {results['failed']}")

if __name__ == "__main__":
    main()
