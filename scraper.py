import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

BATCH_SIZE = 50   # scrape 50 companies at a time
DELAY = 1         # wait 1 second between batches
OUTPUT_FILE = "companies.json"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=200)
        page = await browser.new_page()
        await page.goto("https://leetcodewizard.io/problem-database", timeout=60000)

        # Open dropdown to collect companies
        await page.locator("button[aria-haspopup='dialog']").first.click()
        await page.wait_for_selector("div[role='option']")
        company_names = await page.locator("div[role='option']").all_inner_texts()
        company_names = [c.strip() for c in company_names if c.strip()]
        await page.keyboard.press("Escape")

        print(f"✅ Found {len(company_names)} companies")

        # If file exists, resume progress
        company_questions = {}
        if Path(OUTPUT_FILE).exists():
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                company_questions = json.load(f)
            print(f"🔄 Resuming, already scraped {len(company_questions)} companies")

        # Start scraping
        for start in range(0, len(company_names), BATCH_SIZE):
            end = min(start + BATCH_SIZE, len(company_names))
            batch = company_names[start:end]

            print(f"\n🚀 Scraping batch {start} → {end} ({len(batch)} companies)")

            for company in batch:
                if company in company_questions:
                    print(f"⏩ Skipping {company} (already scraped)")
                    continue

                print(f"👉 Scraping {company} ...")

                # Always re-locate dropdown fresh
                company_dropdown = page.locator("button[aria-haspopup='dialog']").first

                # Open dropdown if not already open
                await company_dropdown.wait_for(state="visible", timeout=10000)
                await company_dropdown.click()

                # Wait for company options to appear
                await page.wait_for_selector("div[role='option']", timeout=20000)

                # Click company option
                option = page.locator(f"div[role='option']:has-text('{company}')").first
                await option.scroll_into_view_if_needed()
                await option.click()

                # Wait for the table to refresh
                await page.wait_for_selector("tbody tr", timeout=20000)

                # Scrape questions
                rows = await page.query_selector_all("tbody tr")
                questions = []
                for row in rows:
                    first_td = await row.query_selector("td")
                    if first_td:
                        q_name = (await first_td.inner_text()).strip()
                        if q_name:
                            questions.append(q_name)

                company_questions[company] = questions
                print(f"📌 {company}: {len(questions)} questions scraped")

            # ✅ Save progress after each batch
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(company_questions, f, indent=2, ensure_ascii=False)
            print(f"💾 Saved batch {start} → {end} to {OUTPUT_FILE}")

            # Wait before next batch
            await asyncio.sleep(DELAY)

        print("\n✅ All data saved successfully!")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
