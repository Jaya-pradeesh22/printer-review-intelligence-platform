from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

import time
import json
import re
import requests

# ==========================================
# BACKEND API
# ==========================================
BACKEND_URL = "http://127.0.0.1:8000/highlights"

# ==========================================
# PRODUCTS TO SCRAPE
# Add more (model_name, url) pairs here for
# other printer models you want to track.
# ==========================================
PRODUCTS = [
    {
        "model_name": "HP Smart Tank 580",
        "url": "https://www.amazon.in/dp/B0BN1S41VH?th=1"
    },
    {
        "model_name": "HP capable AI Ink Advantage 4388",
        "url": "https://www.amazon.in/HP-Capable-Advantage-Faster-Printer/dp/B0G6C7P342/ref=sr_1_12?crid=2FB6H1Z5FMLTM&dib=eyJ2IjoiMSJ9.PGLZxguTam5Z6gy5d7zB2mWwjXHAmEudXAGdyAD2OJRjNISabIp0Aq2Rk4VmuDy9YdzJlT8_aBHUcw4A_qmrVCON2ikikIeWHfKSIt8f1iLrRNpc4p_bP_72kVIHsfMHIkozrMv-TSX7j3yjw-ZU5iA-tq-aAnJL1aBpqrJf9EwCPg4n7mjfrjtu2A-EgxAl36hYDskJsHAwSIh40dt5jbQDz7HVswiLEsVVN03EfLA.gJtm2L5eOlY1u6IReK68Ntl-MuUL9muK9IF09cwlmLc&dib_tag=se&keywords=hp%2Bprinters&qid=1787768259&sprefix=hp%2Bprinter%2Caps%2C332&sr=8-12&th=1"
    },
    {
            "model_name": "HP Laser 1008w Printer",
            "url": "https://www.amazon.in/HP-Wireless-150-sheet-100-sheet-714Z9A/dp/B0C2C22DXR/ref=sr_1_13?crid=2FB6H1Z5FMLTM&dib=eyJ2IjoiMSJ9.PGLZxguTam5Z6gy5d7zB2mWwjXHAmEudXAGdyAD2OJRjNISabIp0Aq2Rk4VmuDy9YdzJlT8_aBHUcw4A_qmrVCON2ikikIeWHfKSIt8f1iLrRNpc4p_bP_72kVIHsfMHIkozrMv-TSX7j3yjw-ZU5iA-tq-aAnJL1aBpqrJf9EwCPg4n7mjfrjtu2A-EgxAl36hYDskJsHAwSIh40dt5jbQDz7HVswiLEsVVN03EfLA.gJtm2L5eOlY1u6IReK68Ntl-MuUL9muK9IF09cwlmLc&dib_tag=se&keywords=hp%2Bprinters&qid=1787768259&sprefix=hp%2Bprinter%2Caps%2C332&sr=8-13&th=1"
        }

    # {
    #     "model_name": "HP DeskJet 2331",
    #     "url": "PASTE THE PRODUCT PAGE URL HERE (amazon.in/dp/...)"
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

all_highlights = []

try:

    for product in PRODUCTS:

        model_name = product["model_name"]
        url = product["url"]

        driver.get(url)

        input(
            f"\n[{model_name}] Login manually and wait until the "
            "'Customers say' panel is visible,\nthen press Enter..."
        )

        print("\nContinuing...")
        time.sleep(3)

        # ==========================================
        # FIND HIGHLIGHT TERMS
        # ==========================================
        # Amazon's class names here are auto-generated per build
        # (e.g. "__dChsbGMXsw4B") and change on every deployment,
        # so they can't be used as selectors. data-testid is the
        # stable hook Amazon uses for its own automated testing.
        terms = driver.find_elements(
            By.CSS_SELECTOR,
            '[data-testid="aspect-label"]'
        )

        print(f"\n[{model_name}] Highlight terms found:", len(terms))

        for term in terms:

            try:
                text = term.text.strip()

                if not text:
                    continue

                # Expect text like: "Print quality(49)" or "Print quality (49)"
                match = re.match(r"^(.*?)\s*\((\d+)\)$", text)

                if not match:
                    print("Skipped (unexpected format):", text)
                    continue

                category = match.group(1).strip()
                count = int(match.group(2))

                # ==========================================
                # TREND DETECTION
                # ==========================================
                # The trend icon is a SIBLING of this label span, not
                # a child of it, so walk up to a shared container first.
                # Amazon marks the icon itself with a stable data-testid
                # like "aspect-icon-positive" / "aspect-icon-negative" /
                # "aspect-icon-neutral" - use that directly, no color
                # guessing needed.
                trend = "NEUTRAL"
                container = None

                for levels in range(1, 5):
                    try:
                        xpath = "./" + "/".join([".."] * levels)
                        candidate = term.find_element(By.XPATH, xpath)
                        if candidate.find_elements(
                            By.CSS_SELECTOR,
                            '[data-testid*="aspect-icon"]'
                        ):
                            container = candidate
                            break
                    except Exception:
                        continue

                if container:
                    try:
                        icon = container.find_element(
                            By.CSS_SELECTOR,
                            '[data-testid*="aspect-icon"]'
                        )
                        testid = (
                            icon.get_attribute("data-testid") or ""
                        ).lower()

                        print(
                            f"  DEBUG: '{category}' icon testid = "
                            f"'{testid}'"
                        )

                        if "positive" in testid:
                            trend = "UP"
                        elif "negative" in testid:
                            trend = "DOWN"
                        elif "neutral" in testid or "mixed" in testid:
                            trend = "NEUTRAL"

                    except Exception as e:
                        print(
                            f"  Could not determine trend for "
                            f"'{category}': {e}"
                        )
                else:
                    print(
                        f"  No icon container found for '{category}', "
                        f"defaulting NEUTRAL"
                    )

                all_highlights.append({
                    "model_name": model_name,
                    "category": category,
                    "mention_count": count,
                    "trend": trend,
                    "source": "Amazon"
                })

                print(f"  -> {category}: {count} mentions, trend={trend}")

            except Exception as e:
                print("Skipped term:", e)

    # ==========================================
    # SAVE JSON
    # ==========================================
    with open(
        "data/hp_highlights.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            all_highlights,
            f,
            indent=4,
            ensure_ascii=False
        )

    print("\n✅ Highlights saved successfully")
    print("File: data/hp_highlights.json")

    # ==========================================
    # SEND TO BACKEND
    # ==========================================
    # Requires the FastAPI backend to already be running
    # (uvicorn app.main:app --reload) before this scraper runs.
    try:
        response = requests.post(BACKEND_URL, json=all_highlights)

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
            "Data is still saved locally in hp_highlights.json."
        )

    input("\nPress Enter to close...")

finally:
    driver.quit()
