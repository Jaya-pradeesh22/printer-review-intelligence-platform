# amazon_scraper.py

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time

# Launch Chrome
driver = webdriver.Chrome(
    service=Service(
        ChromeDriverManager().install()
    )
)

try:

    # Open Amazon
    driver.get("https://www.amazon.in")

    time.sleep(3)

    # Search HP Printers
    search_box = driver.find_element(
        By.ID,
        "twotabsearchtextbox"
    )

    search_box.send_keys("HP Printer")

    search_button = driver.find_element(
        By.ID,
        "nav-search-submit-button"
    )

    search_button.click()

    time.sleep(5)

    print("\nPage Title:")
    print(driver.title)

    # Get all search result cards
    products = driver.find_elements(
        By.CSS_SELECTOR,
        '[data-component-type="s-search-result"]'
    )

    print(f"\nProducts Found: {len(products)}")

    hp_products = set()

    for product in products[:15]:

        try:

            text = product.text

            # Skip non-HP products
            if "HP" not in text:
                continue

            # Product URL
            link = product.find_element(
                By.TAG_NAME,
                "a"
            )

            product_url = link.get_attribute("href")

            lines = text.split("\n")

            product_name = None

            for line in lines:

                if (
                    "Smart Tank" in line
                    or "DeskJet" in line
                    or "LaserJet" in line
                    or "Ink Tank" in line
                ):
                    product_name = line
                    break

            if product_name:

                hp_products.add(product_name)

                print("\n==========================")
                print("Product:")
                print(product_name)

                print("\nURL:")
                print(product_url)
                driver.get(product_url)
                time.sleep(5)

                print("\nOpened Product Page: ")
                print(driver.title)

        except Exception as e:
            print("Skipped Product:", e)

    print("\n==============================")
    print("HP MODELS COLLECTED")
    print("==============================")

    for i, product in enumerate(hp_products, start=1):
        print(f"{i}. {product}")

    print(f"\nTotal HP Models Found: {len(hp_products)}")

    input("\nPress Enter to close...")

finally:
    driver.quit()