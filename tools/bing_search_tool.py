import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def bing_search_firefox(query: str):
    service = Service(executable_path="./driver/geckodriver")

    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")

    driver = webdriver.Firefox(service=service, options=options)

    try:
        driver.get("https://www.bing.com")

        search_box = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )

        # simulate human typing
        for char in query:
            search_box.send_keys(char)
            time.sleep(random.uniform(0.08, 0.15))
        search_box.submit()

        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "li.b_algo"))
        )

        full_text = driver.find_element(By.TAG_NAME, "body").text

        # cut 6k text for about 1500 token
        return full_text[:6000]

    finally:
        driver.quit()

if __name__ == "__main__":
    print("🔍 Bing 搜索中...")
    res = bing_search_firefox("2026年最新新闻")
    print(res)