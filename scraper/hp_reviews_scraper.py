from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
import json

# ==========================================
# PRODUCTS TO SCRAPE
# Add more (model_name, url) pairs here for
# other printer models you want to track.
# ==========================================
PRODUCTS = [
    {
        "model_name": "HP DeskJet Ink Advantage 2975",
        "url": "https://www.hp.com/in-en/shop/products/printers/hp-deskjet-ink-advantage-2986-all-in-one-printer-a24j8b-acj#review-section"
    },
    {
        "model_name": "HP Smart Tank 750 All-in-one Series",
        "url": "https://www.hp.com/in-en/shop/products/printers/hp-smart-tank-750-all-in-one-6uu47a-acj#review-section"
    }
    # {
    #     "model_name": "HP Smart Tank 580",
    #     "url": "PASTE HP.COM PRODUCT PAGE URL HERE"
    # }
]

# ==========================================
# LAUNCH CHROME
# ==========================================
driver = webdriver.Chrome(
    service=Service(
        ChromeDriverManager().install()
    )
)

all_reviews = []


def extract_review(section, model_name):
    """
    Pull one review's data out of a <section id="bv-review-{ID}"> block.
    All selectors here are schema.org itemprop attributes (Bazaarvoice's
    stable machine-readable hooks), NOT the bv-rnr__xxx classes, which
    are styled-components hashes that change per build - same problem
    we hit with Amazon's auto-generated classes.
    """

    review_id = section.get_attribute("id").replace("bv-review-", "")

    # ---- Rating ----
    rating_value = None
    best_rating = None
    try:
        rating_el = section.find_element(
            By.CSS_SELECTOR, '[itemprop="reviewRating"]'
        )
        rating_value = rating_el.find_element(
            By.CSS_SELECTOR, 'meta[itemprop="ratingValue"]'
        ).get_attribute("content")
        best_rating = rating_el.find_element(
            By.CSS_SELECTOR, 'meta[itemprop="bestRating"]'
        ).get_attribute("content")
    except Exception as e:
        print(f"  [{review_id}] Could not read rating: {e}")

    # ---- Title ----
    title = ""
    try:
        title = section.find_element(
            By.CSS_SELECTOR, '[itemprop="name"]'
        ).text.strip()
    except Exception:
        pass

    # ---- Review body ----
    body = ""
    try:
        body = section.find_element(
            By.CSS_SELECTOR, '[itemprop="reviewBody"]'
        ).text.strip()
    except Exception as e:
        print(f"  [{review_id}] Could not read review body: {e}")

    # ---- Author ----
    author = ""
    try:
        author = section.find_element(
            By.CSS_SELECTOR,
            '[itemtype="https://schema.org/Person"] [itemprop="name"]'
        ).text.strip()
    except Exception:
        pass

    # ---- Dates ----
    date_created = None
    date_published = None
    try:
        date_created = section.find_element(
            By.CSS_SELECTOR, 'meta[itemprop="dateCreated"]'
        ).get_attribute("content")
        date_published = section.find_element(
            By.CSS_SELECTOR, 'meta[itemprop="datePublished"]'
        ).get_attribute("content")
    except Exception:
        pass

    # ---- Optional HP company response ----
    # HP's replies show up as a sibling block with a header like
    # "Response from HP.com <Country>:" followed by a response body.
    hp_response = ""
    try:
        response_blocks = section.find_elements(
            By.XPATH,
            './/div[contains(text(), "Response from")]'
        )
        if response_blocks:
            # Response text is typically in a following sibling div
            container = response_blocks[0].find_element(
                By.XPATH, "./ancestor::div[3]"
            )
            candidates = container.find_elements(
                By.CSS_SELECTOR, "div"
            )
            # Grab the longest text block as a heuristic for the
            # actual response body (avoids grabbing labels/dates)
            texts = [c.text.strip() for c in candidates if c.text.strip()]
            if texts:
                hp_response = max(texts, key=len)
    except Exception:
        pass

    return {
        "model_name": model_name,
        "source": "HP.com",
        "review_id": review_id,
        "author": author,
        "rating_value": int(rating_value) if rating_value else None,
        "best_rating": int(best_rating) if best_rating else None,
        "title": title,
        "review_body": body,
        "date_created": date_created,
        "date_published": date_published,
        "hp_response": hp_response,
    }


try:

    for product in PRODUCTS:

        model_name = product["model_name"]
        url = product["url"]

        driver.get(url)

        input(
            f"\n[{model_name}] Wait for the page to fully load, "
            "then press Enter (the script will click the Reviews tab "
            "and handle the rest automatically)..."
        )

        print("\nContinuing...")
        time.sleep(2)

        # ==========================================
        # CLICK THE "REVIEWS" TAB
        # ==========================================
        # HP's Bazaarvoice widget only mounts its content (inside a
        # Shadow DOM - see below) once this tab is clicked. It won't
        # be present in the page on initial load.
        try:
            reviews_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//*[contains(text(), 'REVIEWS') or contains(text(), 'Reviews')]")
                )
            )
            reviews_tab.click()
            print("Clicked the Reviews tab.")
        except Exception as e:
            print(f"  Could not click Reviews tab (may already be open): {e}")

        time.sleep(2)

        # ==========================================
        # PIERCE THE SHADOW DOM
        # ==========================================
        # Confirmed via DevTools: HP's Bazaarvoice reviews widget mounts
        # inside a Shadow DOM. The shadow host is a div with the stable,
        # product-agnostic attribute data-bv-show="reviews" (the
        # data-bv-product-id value changes per product, so we don't
        # depend on it). Selenium 4+ can access .shadow_root directly,
        # but normal driver.find_elements() cannot see past this
        # boundary at all - hence why this step is required.
        try:
            shadow_host = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'div[data-bv-show="reviews"]')
                )
            )
            shadow_root = shadow_host.shadow_root
            print("Successfully accessed the reviews shadow root.")
        except Exception as e:
            print(f"  Could not access reviews shadow root: {e}")
            continue

        # ==========================================
        # FIND REVIEW SECTIONS (inside the shadow root)
        # WITH PAGINATION HANDLING
        # ==========================================
        # Only <section> tags match this id pattern - the review body
        # div uses id="bv-review-text-{ID}" (a <div>, not a <section>),
        # so this selector can't accidentally grab it. Searching must
        # happen on shadow_root, not driver, since driver cannot see
        # inside the shadow boundary at all.
        #
        # Pagination confirmed via DevTools: reviews are split across
        # real pages, navigated by an <a class="next" href="...?bvstate=
        # pg:N/ct:r#review-section"> link inside the same shadow root.
        # Since it's a real link (not lazy-load/infinite scroll), we
        # click it and re-read the shadow root each time until it's
        # no longer present - that's the signal we've reached the last
        # page of reviews for this product.
        page_num = 1
        max_pages = 100  # safety cap to avoid an infinite loop

        while True:
            review_sections = shadow_root.find_elements(
                By.CSS_SELECTOR, 'section[id^="bv-review-"]'
            )

            print(
                f"\n[{model_name}] Page {page_num} - "
                f"Review blocks found: {len(review_sections)}"
            )

            for section in review_sections:
                try:
                    review = extract_review(section, model_name)

                    # Skip if we've already seen this review_id
                    # (belt-and-suspenders; real dedup happens at DB
                    # level via review_id as a unique key)
                    if any(
                        r["review_id"] == review["review_id"]
                        for r in all_reviews
                    ):
                        print(
                            f"  Skipped duplicate review_id "
                            f"{review['review_id']}"
                        )
                        continue

                    all_reviews.append(review)

                    print(
                        f"  -> [{review['review_id']}] "
                        f"{review['rating_value']}/{review['best_rating']} - "
                        f"\"{review['title']}\""
                    )

                except Exception as e:
                    print("  Skipped a review block:", e)

            # ---- Look for the "Next Reviews" link ----
            try:
                next_link = shadow_root.find_element(
                    By.CSS_SELECTOR, 'a.next'
                )
            except Exception:
                print(f"  No more pages - finished at page {page_num}.")
                break

            if page_num >= max_pages:
                print(
                    f"  Reached safety cap of {max_pages} pages - stopping."
                )
                break

            try:
                # A plain .click() can fail with "element click
                # intercepted" if the link isn't scrolled into view or
                # something else visually overlaps it at that pixel
                # position (sticky headers, banners, etc). Scrolling it
                # into view first, then clicking via JavaScript, bypasses
                # that visibility/overlap check entirely.
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});",
                    next_link
                )
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", next_link)
                page_num += 1
                time.sleep(2)

                # Clicking navigates to a new URL, so the page reloads -
                # previous element references (including shadow_root)
                # go stale. Re-fetch the shadow host and shadow root
                # fresh on the new page before continuing the loop.
                shadow_host = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, 'div[data-bv-show="reviews"]')
                    )
                )
                shadow_root = shadow_host.shadow_root

            except Exception as e:
                print(f"  Could not navigate to next page: {e}")
                break

        # Print total-vs-scraped info using the last known aria-label,
        # for a sanity check against what the page reports.
        try:
            last_batch = shadow_root.find_elements(
                By.CSS_SELECTOR, 'section[id^="bv-review-"]'
            )
            if last_batch:
                last_label = last_batch[0].get_attribute("aria-label")
                total_reviews = int(
                    last_label.split(" out of ")[1].split(" ")[0]
                )
                print(
                    f"\n[{model_name}] Page reports {total_reviews} total "
                    f"reviews for this product."
                )
        except Exception:
            pass

    # ==========================================
    # SAVE JSON
    # ==========================================
    with open(
        "data/hp_reviews.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            all_reviews,
            f,
            indent=4,
            ensure_ascii=False
        )

    print("\n✅ HP reviews saved successfully")
    print("File: data/hp_reviews.json")
    print(f"Total reviews scraped: {len(all_reviews)}")

    input("\nPress Enter to close...")

finally:
    driver.quit()