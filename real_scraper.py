from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup
import pandas as pd
import time

START_URL = "https://interpro.wisc.edu/wp-admin/tools.php?page=redirection.php&sub=404s"
MAX_EMPTY_PAGES = 5


def parse_table(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = []

    for tr in soup.select("table.wp-list-table tbody tr"):
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue

        # DATE
        date = tds[0].get_text(" ", strip=True)

        # SOURCE URL (robust)
        link = tds[1].find("a")
        source_url = link.get_text(strip=True) if link else tds[1].get_text(strip=True)

        # USER AGENT
        user_agent = tds[2].get_text(" ", strip=True)

        # IP
        ip_link = tds[3].find("a")
        ip = ip_link.get_text(strip=True) if ip_link else tds[3].get_text(strip=True)

        rows.append({
            "date": date,
            "source_url": source_url,
            "user_agent": user_agent,
            "ip": ip
        })

    return rows


def scrape_404s():
    options = Options()
    options.add_experimental_option("detach", True)

    # ✅ FIXED: Let Selenium manage ChromeDriver automatically (no webdriver-manager)
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)

    wait = WebDriverWait(driver, 15)
    driver.get(START_URL)

    print("👉 Log in to WordPress admin in the opened browser, then press ENTER here.")
    input()

    all_rows = []
    page = 1
    empty_streak = 0

    while True:
        print(f"Scraping page {page}...")

        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "table.wp-list-table")
        ))

        html = driver.page_source
        rows = parse_table(html)

        print(f"  → Collected {len(rows)} rows")

        if rows:
            all_rows.extend(rows)
            empty_streak = 0
        else:
            empty_streak += 1
            if empty_streak >= MAX_EMPTY_PAGES:
                print("Too many empty pages — stopping.")
                break

        try:
            next_btn = driver.find_element(By.CLASS_NAME, "next-page")

            if "disabled" in next_btn.get_attribute("class"):
                print("Reached last page.")
                break

            next_btn.click()
            time.sleep(0.6)  # small delay to avoid rate limits
            page += 1

        except Exception:
            print("No next button — stopping.")
            break

    driver.quit()

    df = pd.DataFrame(all_rows)
    df.to_csv("raw_404_logs.csv", index=False)

    print(f"\n✅ Finished. Scraped {len(df)} total rows.")
    print("Saved to raw_404_logs.csv")


if __name__ == "__main__":
    scrape_404s()
