from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

import time
import json
import re
import requests

from ai_classifier import classify_review_category, classify_review_trend

# ==========================================
# BACKEND API
# ==========================================
BACKEND_URL = "http://127.0.0.1:8000/highlights"

# ==========================================
# STATE FILE
# ==========================================
# Tracks which reviews we've already classified (so re-running doesn't
# double-count) AND the running cumulative totals per category, since
# the backend only stores the LATEST snapshot per (model, category) -
# we need to submit the full running total each time, not just what's
# new in this run.
STATE_FILE = "data/hp_official_category_state.json"


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "processed_review_ids": [],
            "category_totals": {}
        }


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

# ==========================================
# PRODUCTS TO SCRAPE
# Add more (model_name, url) pairs here for
# other printer models on HP's official site.
# ==========================================
PRODUCTS = [
    {
        "model_name": "HP DeskJet Ink Advantage 2986",
        "url": (
            "https://www.hp.com/in-en/shop/products/printers/"
            "hp-deskjet-ink-advantage-2986-all-in-one-printer-a24j8b-acj"
            "#review-section"
        )
    }
]

# ==========================================
# LAUNCH CHROME
# ==========================================
driver = webdriver.Chrome(
    service=Service(
        ChromeDriverManager().install()
    )
)

all_raw_reviews = []

try:

    for product in PRODUCTS:

        model_name = product["model_name"]
        url = product["url"]

        driver.get(url)

        input(
            f"\n[{model_name}] Scroll to the Reviews section and wait "
            "until review cards are visible,\nthen press Enter..."
        )

        print("\nContinuing...")
        time.sleep(3)

        # ==========================================
        # FIND REVIEW CARDS ACROSS MULTIPLE PAGES
        # ==========================================
        # HP paginates ~8 reviews per page (e.g. "1-8 of 45 Reviews").
        # Cap at MAX_PAGES so this doesn't run forever on very popular
        # products.
        MAX_PAGES = 10
        page_num = 1

        while page_num <= MAX_PAGES:

            review_cards = driver.find_elements(
                By.CSS_SELECTOR,
                '[data-bv-v="contentItem"]'
            )

            print(
                f"\n[{model_name}] Page {page_num}: "
                f"Review cards found: {len(review_cards)}"
            )

            for card in review_cards:

                try:
                    # Review text (may be in any language - HP syndicates
                    # reviews across its regional sites)
                    body_el = card.find_element(
                        By.CSS_SELECTOR,
                        '[itemprop="reviewBody"]'
                    )
                    review_text = body_el.text.strip()

                    if not review_text:
                        continue

                    # Unique review ID for duplicate detection - extracted
                    # from the element's own id attribute, e.g.
                    # "bv-review-text-401615284" -> "401615284"
                    raw_id = body_el.get_attribute("id") or ""
                    id_match = re.search(r"(\d+)$", raw_id)
                    review_id = id_match.group(1) if id_match else None

                    # Star rating (precise number, not a visual guess)
                    try:
                        rating_el = card.find_element(
                            By.CSS_SELECTOR,
                            'meta[itemprop="ratingValue"]'
                        )
                        rating = int(rating_el.get_attribute("content"))
                    except Exception:
                        rating = None

                    # Review title
                    try:
                        title_el = card.find_element(
                            By.CSS_SELECTOR,
                            'h3[itemprop="name"]'
                        )
                        title = title_el.text.strip()
                    except Exception:
                        title = ""

                    # Published date
                    try:
                        date_el = card.find_element(
                            By.CSS_SELECTOR,
                            'meta[itemprop="datePublished"]'
                        )
                        date_published = date_el.get_attribute("content")
                    except Exception:
                        date_published = None

                    all_raw_reviews.append({
                        "model_name": model_name,
                        "review_id": review_id,
                        "title": title,
                        "review_text": review_text,
                        "rating": rating,
                        "date_published": date_published,
                        "source": "HP Official"
                    })

                    print(
                        f"  -> [{review_id}] rating={rating}, "
                        f"title='{title[:40]}'"
                    )

                except Exception as e:
                    print("Skipped review card:", e)

            # Try to go to the next page.
            # Confirmed selector: <a class="next"> at the bottom of the
            # reviews list.
            try:
                next_button = driver.find_element(
                    By.CSS_SELECTOR,
                    "a.next"
                )
                next_button.click()
                time.sleep(3)
                page_num += 1

            except Exception:
                print(
                    f"\n[{model_name}] No further pages found. Stopping."
                )
                break

    # ==========================================
    # SAVE RAW REVIEWS
    # ==========================================
    with open(
        "data/hp_official_reviews.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            all_raw_reviews,
            f,
            indent=4,
            ensure_ascii=False
        )

    print("\n✅ Raw reviews saved successfully")
    print("File: data/hp_official_reviews.json")
    print(f"Total reviews collected this run: {len(all_raw_reviews)}")

    # ==========================================
    # CLASSIFY NEW REVIEWS ONLY (skip duplicates)
    # ==========================================
    state = load_state()
    processed_ids = set(state["processed_review_ids"])
    category_totals = state["category_totals"]

    new_review_count = 0

    print("\nClassifying new reviews (this may take a moment)...")

    for review in all_raw_reviews:

        review_id = review.get("review_id")

        # Skip reviews with no ID (can't dedupe safely) or already seen
        if not review_id or review_id in processed_ids:
            continue

        category = classify_review_category(review["review_text"])
        trend = classify_review_trend(
            rating=review.get("rating"),
            review_text=review["review_text"]
        )

        key = f"{review['model_name']}||{category}"

        if key not in category_totals:
            category_totals[key] = {
                "model_name": review["model_name"],
                "category": category,
                "count": 0,
                "trend_counts": {"UP": 0, "DOWN": 0, "NEUTRAL": 0}
            }

        category_totals[key]["count"] += 1
        category_totals[key]["trend_counts"][trend] += 1

        processed_ids.add(review_id)
        new_review_count += 1

        print(f"  [{review_id}] -> {category} ({trend})")

    state["processed_review_ids"] = list(processed_ids)
    state["category_totals"] = category_totals
    save_state(state)

    print(f"\n✅ Classified {new_review_count} new reviews "
          f"(skipped {len(all_raw_reviews) - new_review_count} "
          f"already-seen)")

    # ==========================================
    # BUILD HIGHLIGHTS PAYLOAD (cumulative totals)
    # ==========================================
    highlights_payload = []

    for key, data in category_totals.items():
        trend_counts = data["trend_counts"]
        dominant_trend = max(trend_counts, key=trend_counts.get)

        highlights_payload.append({
            "model_name": data["model_name"],
            "category": data["category"],
            "mention_count": data["count"],
            "trend": dominant_trend,
            "source": "HP Official"
        })

    # ==========================================
    # SEND TO BACKEND
    # ==========================================
    try:
        response = requests.post(BACKEND_URL, json=highlights_payload)

        if response.status_code == 200:
            print("✅ Highlights sent to backend successfully")
            print(response.json())
        else:
            print(
                f"⚠️ Backend responded with status "
                f"{response.status_code}: {response.text}"
            )

    except requests.exceptions.ConnectionError:
        print(
            "⚠️ Could not reach backend at "
            f"{BACKEND_URL} - is uvicorn running? "
            "Data is still saved locally."
        )

    input("\nPress Enter to close...")

finally:
    driver.quit()