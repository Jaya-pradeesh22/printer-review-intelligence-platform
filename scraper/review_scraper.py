from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

import time
import json

# ==========================================
# USE EXISTING CHROME PROFILE
# ==========================================
driver = webdriver.Chrome(
    service=Service(
        ChromeDriverManager().install()
    )
)

# options = Options()

# options.add_argument(
#     r"--user-data-dir=C:\Users\ADMIN\AppData\Local\Google\Chrome\User Data"
# )

# options.add_argument("--profile-directory=Default")

# driver = webdriver.Chrome(
#     service=Service(
#         ChromeDriverManager().install()
#     ),
#     options=options
# )

try:

    review_url = (
        "https://www.amazon.in/product-reviews/"
        "B0BN1S41VH/"
        "ref=cm_cr_dp_d_show_all_top"
        "?_encoding=UTF8&ie=UTF8&reviewerType=all_reviews"
    )

    driver.get(review_url)

    input(
        "\nLogin manually and wait until reviews are visible,"
        "\nthen press Enter..."
    )

    print("\nContinuing...")

    time.sleep(5)

    print("\nReview Page Loaded")

    print("\nCurrent URL:")
    print(driver.current_url)

    print("\nPage Title:")
    print(driver.title)

    # ==========================================
    # FIND REVIEWS ACROSS MULTIPLE PAGES
    # ==========================================
    # It's not feasible to scrape every review Amazon has posted,
    # so cap this at MAX_PAGES (10 reviews/page typically).
    MAX_PAGES = 5

    reviews_data = []
    page_num = 1

    while page_num <= MAX_PAGES:

        reviews = driver.find_elements(
            By.CSS_SELECTOR,
            'span[data-hook="review-body"]'
        )

        print(f"\nPage {page_num}: Reviews Found: {len(reviews)}")

        for i, review in enumerate(reviews, start=1):

            review_text = review.text.strip()

            print("\n--------------------------")
            print(f"Review {i} (page {page_num})")
            print(review_text)

            reviews_data.append(
                {
                    "product": "HP Smart Tank 580",
                    "review": review_text,
                    "source": "Amazon"
                }
            )

        # Try to go to the next page.
        # NOTE: Verify this selector in your browser -
        # Amazon uses a "Next page" link, commonly matched by
        # data-hook="pagination-next" or link text "Next page".
        try:
            next_button = driver.find_element(
                By.CSS_SELECTOR,
                '[data-hook="pagination-next"] a'
            )
            next_button.click()
            time.sleep(4)
            page_num += 1

        except Exception:
            print("\nNo further pages found. Stopping.")
            break

    # ==========================================
    # SAVE JSON
    # ==========================================

    with open(
        "data/hp_reviews.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            reviews_data,
            f,
            indent=4,
            ensure_ascii=False
        )

    print("\n✅ Reviews saved successfully")
    print("File: data/hp_reviews.json")

    input("\nPress Enter to close...")

finally:
    driver.quit()