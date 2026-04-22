import time
import random
import json
from datetime import datetime
from typing import Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Sample
# [{
#     "type": "function",
#     "function": {
#         "name": "user_detail",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "name": {
#                     "type": "string"
#                 },
#                 "age": {
#                     "type": "integer"
#                 }
#             },
#             "required": ["name", "age"]
#         }
#     }
# }]
TOOL_DEFINE=[{
    "type": "function",
    "function": {
        "name": "online_search",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The accurate, clean, and effective search keywords extracted from the user's question."
                }
            },
            "required": ["query"]
        },
        "description": "Use this tool to search online for real-time, unknown, latest, or factual information. You must extract accurate keywords from the user's question."
    }
}]

TOOL_CHOICE={
    "type": "function",
    "function": {"name": "online_search"}
}

def bing_search_firefox(query: str) -> str:
    service = Service(executable_path="./driver/geckodriver")

    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")

    if is_english_query(query):
        search_url = "https://www.bing.com/search?pc=MOZI&form=MOZLBR&q="
        options.set_preference("intl.accept_languages", "en-US,en;q=0.9")
        options.set_preference("browser.country.search.iso", "US")
    else:
        search_url = "https://cn.bing.com/search?pc=MOZI&FORM=BESBTB&q="
        options.set_preference("intl.accept_languages", "zh-CN,zh;q=0.9")
        options.set_preference("browser.country.search.iso", "CN")

    driver = webdriver.Firefox(service=service, options=options)

    driver.execute_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
    """)

    try:
        driver.get(search_url + query)

        WebDriverWait(driver, 5).until(page_load)
        time.sleep(random.uniform(0.5, 0.8))
        full_text = driver.find_element(By.ID, "b_results").text

        # cut 6k text for about 1500 token
        return full_text[:6000]

    finally:
        driver.quit()

def is_english_query(query: str) -> bool:
    for ch in query:
        if "\u4e00" <= ch <= "\u9fff":
            return False
    return True

def page_load(driver: Any) -> bool:
    elem = driver.find_element(By.ID, "b_results")
    return elem.text.strip() != ""

def get_current_time() -> str:
    return datetime.strftime(datetime.now(), "%c")

TOOL_FUNCTION = {
    "online_search": bing_search_firefox,
    "get_current_time": get_current_time
}

def tool_routing(content: str) -> object|str:
    if any(key in content.upper() for key in ["搜索", "查询", "GOOGLE", "SEARCH", "QUERY"]):
        return "llm_function"
    elif any(key in content.upper() for key in ["现在几点", "几点了", "今天日期", "周几", "星期几", "THE TIME", "THE DATE", "WHAT TIME IS IT"]):
        return get_current_time
    else:
        return None

def tool_calling(function_call: dict) -> str:
    tool_func = function_call["name"]
    tool_param = json.loads(function_call["arguments"])
    if tool_func in TOOL_FUNCTION:
        return TOOL_FUNCTION[tool_func](**tool_param)
    else:
        print("unknown tool.")
        return None

if __name__ == "__main__":
    print(bing_search_firefox("最新金价"))
    print(bing_search_firefox("gold price"))
    print(get_current_time())
