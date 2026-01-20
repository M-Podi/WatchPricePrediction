import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
import csv
import time
import random
import os

# --- CONFIGURATION ---
START_URL = "https://www.chrono24.com/watches/pre-owned-watches--64.htm?keyword=pre-owned-watches&keywordId=64&pageSize=120&showpage=1"
OUTPUT_FILE = "chrono24_watches_selenium3.csv"
MAX_PAGES_TO_SCRAPE = 1000


def main():
    options = uc.ChromeOptions()
    # options.add_argument('--blink-settings=imagesEnabled=false')

    print("Initializing Browser...")
    driver = uc.Chrome(options=options)

    try:
        # --- FILE SETUP ---
        file_exists = os.path.isfile(OUTPUT_FILE)
        if file_exists:
            print(f"File '{OUTPUT_FILE}' found. Appending new data...")
        else:
            print(f"Creating new file '{OUTPUT_FILE}'...")

        with open(OUTPUT_FILE, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)

            if not file_exists:
                writer.writerow(['Watch Name', 'Price', 'Location', 'Link'])

            # --- NAVIGATION ---
            print(f"--- Navigating to Start URL ---")
            driver.get(START_URL)

            # Initial wait
            time.sleep(random.uniform(8, 12))

            # Try to close cookie banner (Best effort)
            try:
                cookie_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.c24-cookie-consent-notice-buttons__btn"))
                )
                cookie_btn.click()
                print("Initial Cookie Banner closed.")
            except:
                pass

            pages_scraped = 0

            while pages_scraped < MAX_PAGES_TO_SCRAPE:
                print(f"Processing Page Sequence: {108 + pages_scraped}")

                # --- 1. SCRAPE ---
                soup = BeautifulSoup(driver.page_source, 'html.parser')

                if "Access denied" in soup.text or "Challenge Validation" in soup.text:
                    print("!!! SECURITY BLOCK DETECTED !!! Pausing 2 mins...")
                    time.sleep(120)
                    driver.refresh()
                    time.sleep(10)

                watch_cards = soup.find_all('a', class_='wt-listing-item-link')

                if not watch_cards:
                    print("No watches found. Ending.")
                    break

                count = 0
                for card in watch_cards:
                    name_tag = card.find('p', class_='text-bold')
                    name = name_tag.text.strip() if name_tag else "N/A"

                    relative_link = card.get('href')
                    full_link = "https://www.chrono24.com" + relative_link if relative_link else "N/A"

                    price = "N/A"
                    price_div = card.find('div', class_='align-content-end')
                    if price_div:
                        price_p = price_div.find('p', class_='text-bold')
                        if price_p:
                            price = price_p.text.strip()

                    location = "N/A"
                    loc_btn = card.find('button', class_='js-tooltip')
                    if loc_btn and loc_btn.get('data-title'):
                        location = loc_btn.get('data-title')

                    writer.writerow([name, price, location, full_link])
                    count += 1

                print(f" -> Scraped {count} items.")
                pages_scraped += 1

                # --- 2. PAGINATION (UPDATED LOGIC) ---
                time.sleep(random.uniform(2, 4))

                # Scroll to bottom first to trigger loading of footer elements
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)

                try:
                    # 1. Wait for the Next button to be present and clickable
                    # We use the aria-label='Next' as requested
                    next_button = WebDriverWait(driver, 15).until(
                        EC.element_to_be_clickable((By.XPATH, "//i[@aria-label='Next']"))
                    )

                    # 2. Safety Scroll: Even if 'clickable', sticky footers often cover it.
                    # We scroll to the button, then UP by 200px.
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    time.sleep(0.5)
                    driver.execute_script("window.scrollBy(0, -200);")
                    time.sleep(0.5)

                    # 3. Click
                    try:
                        next_button.click()
                    except ElementClickInterceptedException:
                        print(" -> Click intercepted. Forcing JS Click...")
                        driver.execute_script("arguments[0].click();", next_button)

                    print(" -> Clicked 'Next'. Waiting for load...")
                    time.sleep(random.uniform(6, 9))

                    # 4. Coffee Break (Every 30 pages)
                    if pages_scraped > 0 and pages_scraped % 30 == 0:
                        print("Taking a 45s break...")
                        time.sleep(45)

                except TimeoutException:
                    print("Next button not found (Timeout). End of list reached?")
                    break
                except Exception as e:
                    print(f"Pagination Error: {e}")
                    break

    except Exception as e:
        print(f"Global Error: {e}")
    finally:
        print("Closing browser...")
        try:
            driver.quit()
        except:
            pass


if _name_ == "_main_":
    main()

