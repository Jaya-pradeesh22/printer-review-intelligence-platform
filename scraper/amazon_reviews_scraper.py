from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import re
import time
import json

# ==========================================
# PRODUCTS TO SCRAPE
# Each entry needs the Amazon PRODUCT REVIEWS page URL, not the product
# page itself - that's the /product-reviews/{ASIN}/... URL, same pattern
# review_scraper.py already used. Find the ASIN on the product page
# (under "Product details"), or copy the URL from the "See all reviews"
# link on the product page.
# ==========================================
PRODUCTS = [
    {
        "model_name": "HP Smart Tank 580",
        "url": (
            "https://www.amazon.in/product-reviews/"
            "B0BN1S41VH/"
            "ref=cm_cr_dp_d_show_all_top"
            "?_encoding=UTF8&ie=UTF8&reviewerType=all_reviews"
        ),
    },
    {
        "model_name": "HP Laser 1008w Printer",
        "url": (
            "https://www.amazon.in/product-reviews/"
            "B0C2C22DXR/"
            "ref=cm_cr_dp_d_show_all_top"
            "?_encoding=UTF8&ie=UTF8&reviewerType=all_reviews"
        ),
    },
    {
        "model_name": "HP capable AI Ink Advantage 4388",
        "url": (
            "https://www.amazon.in/product-reviews/"
            "B0G6C7P342/"
            "ref=cm_cr_dp_d_show_all_top"
            "?_encoding=UTF8&ie=UTF8&reviewerType=all_reviews"
        ),
    },
]

MAX_PAGES = 10  # safety cap on how many times we click "Show more reviews"
# (each click appends ~10 more reviews to the same list)

# ==========================================
# LAUNCH CHROME
# ==========================================
driver = webdriver.Chrome(
    service=Service(
        ChromeDriverManager().install()
    )
)

all_reviews = []


def extract_review(review_div, model_name):
    """
    Pull one review's data out of a <div data-hook="review" id="R...">
    block. Amazon assigns each review div a stable, globally unique id
    (e.g. "R2XXXXXXXXXX") - that becomes our review_id, same role
    review_id plays in the HP scraper.
    """

    review_id = review_div.get_attribute("id")

    # ---- Rating ----
    # Amazon renders this as hidden text like "5.0 out of 5 stars" inside
    # the star icon element - not a clean numeric attribute like HP's
    # schema.org meta tags, so we regex the leading number out.
    rating_value = None
    try:
        rating_text = review_div.find_element(
            By.CSS_SELECTOR, '[data-hook="review-star-rating"] span.a-icon-alt'
        ).get_attribute("textContent")
        match = re.search(r"([\d.]+)\s+out of", rating_text)
        if match:
            rating_value = int(float(match.group(1)))
    except Exception as e:
        print(f"  [{review_id}] Could not read rating: {e}")

    # ---- Title ----
    # The title <a> also contains the hidden "X.X out of 5 stars" rating
    # text as a sibling element inside it - Selenium's .text can include
    # that even though it's visually screen-reader-only, so we strip any
    # leading "N.N out of 5 stars" prefix defensively either way.
    title = ""
    try:
        raw_title = review_div.find_element(
            By.CSS_SELECTOR, '[data-hook="review-title"]'
        ).text.strip()
        title = re.sub(
            r"^\d+(\.\d+)?\s+out of\s+5\s+stars\s*", "", raw_title
        ).strip()
    except Exception:
        pass

    # ---- Review body ----
    body = ""
    try:
        body = review_div.find_element(
            By.CSS_SELECTOR, '[data-hook="review-body"]'
        ).text.strip()
    except Exception:
        # Some reviews (often shorter ones) render their body under a
        # "collapsed" hook instead until a "Read more" toggle is clicked -
        # try that before giving up on this review's text entirely.
        try:
            body = review_div.find_element(
                By.CSS_SELECTOR, '[data-hook="review-collapsed"]'
            ).text.strip()
        except Exception as e:
            print(f"  [{review_id}] Could not read review body: {e}")

    # ---- Author ----
    author = ""
    try:
        author = review_div.find_element(
            By.CSS_SELECTOR, ".a-profile-name"
        ).text.strip()
    except Exception:
        pass

    # ---- Date ----
    # Amazon's date isn't a clean ISO value like HP's meta tags - it's a
    # sentence like "Reviewed in India on 12 March 2024". We keep the raw
    # text as date_published and leave date_created empty, since Amazon's
    # review page doesn't expose a separate "created" timestamp at all.
    date_published = None
    try:
        date_published = review_div.find_element(
            By.CSS_SELECTOR, '[data-hook="review-date"]'
        ).text.strip()
    except Exception:
        pass

    # ---- Verified Purchase badge ----
    verified_purchase = False
    try:
        review_div.find_element(By.CSS_SELECTOR, '[data-hook="avp-badge"]')
        verified_purchase = True
    except Exception:
        pass

    return {
        "model_name": model_name,
        "source": "Amazon",
        "review_id": review_id,
        "author": author,
        "rating_value": rating_value,
        "best_rating": 5,  # Amazon is always a 5-star scale
        "title": title,
        "review_body": body,
        "date_created": None,
        "date_published": date_published,
        "verified_purchase": verified_purchase,
        "seller_response": "",  # Amazon review pages don't expose seller
        # replies the way HP.com does - kept as an empty string, not None,
        # for schema consistency with the HP scraper's hp_response field.
    }


try:

    for product in PRODUCTS:

        model_name = product["model_name"]
        url = product["url"]

        driver.get(url)

        input(
            f"\n[{model_name}] Log in / solve any captcha and wait until "
            "reviews are visible, then press Enter..."
        )

        print("\nContinuing...")

        # Amazon's review cards don't always exist in the DOM the instant
        # the page "looks" loaded - on some layouts they mount progressively
        # as you scroll. A fixed sleep() isn't reliable for this, so we
        # scroll down in small increments (to trigger any lazy rendering)
        # and then explicitly wait for at least one review block to appear
        # before doing anything else.
        for _ in range(6):
            driver.execute_script("window.scrollBy(0, 600);")
            time.sleep(0.5)

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[data-hook="review"]')
                )
            )
            print("Review blocks detected on the page.")
        except Exception:
            print(
                "  WARNING: no elements matched [data-hook=\"review\"] "
                "after waiting. Checking fallback selectors for diagnosis:"
            )
            for fallback_selector in [
                "li.review",
                '[data-hook="review-collapsed"]',
                ".a-section.review",
            ]:
                count = len(driver.find_elements(By.CSS_SELECTOR, fallback_selector))
                print(f"    {fallback_selector} -> {count} matches")

        page_num = 1

        while page_num <= MAX_PAGES:

            review_divs = driver.find_elements(
                By.CSS_SELECTOR, '[data-hook="review"]'
            )

            print(
                f"\n[{model_name}] Batch {page_num} - "
                f"Review blocks found on page: {len(review_divs)}"
            )

            reviews_before = len(all_reviews)

            for review_div in review_divs:
                try:
                    review = extract_review(review_div, model_name)

                    if not review["review_id"]:
                        print("  Skipped a review block with no id")
                        continue

                    if any(
                        r["review_id"] == review["review_id"]
                        for r in all_reviews
                    ):
                        # Expected and harmless here: this page's review
                        # list re-includes reviews we already collected in
                        # earlier batches, since "Show more" APPENDS to the
                        # same list rather than replacing it.
                        continue

                    all_reviews.append(review)

                    print(
                        f"  -> [{review['review_id']}] "
                        f"{review['rating_value']}/5 - \"{review['title']}\""
                    )

                except Exception as e:
                    print("  Skipped a review block:", e)

            new_count = len(all_reviews) - reviews_before
            print(f"  New reviews collected this batch: {new_count}")

            # ---- Look for the "Show more reviews" button ----
            # This APPENDS more <li data-hook="review"> elements into the
            # same list via AJAX - it does not navigate to a new URL like
            # HP's "Next" link did. So after clicking, we just re-query the
            # same selector above and rely on the review_id dedup check to
            # skip what we've already seen.
            try:
                show_more_button = driver.find_element(
                    By.CSS_SELECTOR, '[data-hook="show-more-button"]'
                )
            except Exception:
                print(f"  No 'Show more reviews' button - finished at batch {page_num}.")
                break

            if page_num >= MAX_PAGES:
                print(f"  Reached safety cap of {MAX_PAGES} batches - stopping.")
                break

            try:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});",
                    show_more_button
                )
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", show_more_button)
                page_num += 1

                # Wait for new review elements to actually append, rather
                # than trusting a fixed sleep - AJAX append speed varies.
                try:
                    WebDriverWait(driver, 10).until(
                        lambda d: len(
                            d.find_elements(By.CSS_SELECTOR, '[data-hook="review"]')
                        ) > len(review_divs)
                    )
                except Exception:
                    print("  Timed out waiting for new reviews to append.")
                    time.sleep(2)  # fall back to a short pause and try anyway

            except Exception as e:
                print(f"  Could not click 'Show more reviews': {e}")
                break

    # ==========================================
    # SAVE JSON
    # ==========================================
    # NOTE: saves to its own file - data/amazon_reviews.json - NOT
    # data/hp_reviews.json, unlike the older review_scraper.py, which
    # would have silently overwritten your HP scrape data.
    with open(
        "data/amazon_reviews.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            all_reviews,
            f,
            indent=4,
            ensure_ascii=False
        )

    print("\n✅ Amazon reviews saved successfully")
    print("File: data/amazon_reviews.json")
    print(f"Total reviews scraped: {len(all_reviews)}")

    input("\nPress Enter to close...")

finally:
    driver.quit()