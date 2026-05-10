import json
from datetime import datetime
from typing import Any
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.common import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait

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
    options.set_preference("permissions.default.image", 2) 
    options.set_preference("permissions.default.stylesheet", 2)
    # 只要 DOM 好了就开跑，不等图片
    options.page_load_strategy = 'eager' 

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

        wait = WebDriverWait(
            driver, 
            timeout=5, 
            ignored_exceptions=[NoSuchElementException, StaleElementReferenceException]
        )
        wait.until(lambda d: len(d.find_element(By.ID, "b_results").text.strip()) > 20)

        source = driver.page_source
        soup = BeautifulSoup(source, "html.parser")
        
        results = []
        # top result for specific query
        top_res = soup.select(".b_top")
        if top_res:
            top_title = top_res[0].find("h2")
            top_content = top_res[0].select_one(".b_hPanel")
            if top_title and top_content:
                title = top_title.get_text().strip()
                snippet = top_content.get_text().strip()
                results.append(f"Title: {title}\nSnippet: {snippet}")
            
        # search results in .b_algo
        for item in soup.select(".b_algo"):
            title_el = item.find("h2")
            snippet_el = item.find(".b_caption p") or item.select_one(".b_lineclamp2")
            
            if title_el and snippet_el:
                title = title_el.get_text().strip()
                snippet = snippet_el.get_text().strip()
                if len(snippet) > 10:
                    results.append(f"Title: {title}\nSnippet: {snippet}")
            
            if len(results) >= 6:
                break
        
        if not results:
            return "No relevant search results found."
            
        final_context = "\n\n".join(results)
        # cut 4k text for about 1k token to llm
        return final_context[:4000]

    except Exception as e:
        return f"Search error: {str(e)}"

    finally:
        driver.quit()

def is_english_query(query: str) -> bool:
    for ch in query:
        if "\u4e00" <= ch <= "\u9fff":
            return False
    return True

def fast_bing_search(query: str):
    """provide a faster search if you think selenium is too slow"""
    # simulate firefox headers
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
    }

    base_url = "https://www.bing.com/search?q="
    if is_english_query(query):
        headers["Accept-Language"] = "en-US,en;q=0.9"

    try:
        response = requests.get(base_url + query, headers=headers, timeout=5)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        for item in soup.select(".b_algo"):
            title_el = item.find("h2")
            snippet_el = item.find(".b_caption p") or item.select_one(".b_lineclamp2")
            
            if title_el and snippet_el:
                title = title_el.get_text().strip()
                snippet = snippet_el.get_text().strip()
                if len(snippet) > 10:
                    results.append(f"Title: {title}\nSnippet: {snippet}")
            
            if len(results) >= 6:
                break
        
        if not results:
            return "No relevant search results found."
            
        final_context = "\n\n".join(results)
        return final_context[:4000]

    except Exception as e:
        return f"Search error: {str(e)}"

def get_current_time() -> str:
    return datetime.strftime(datetime.now(), "%c")

TOOL_FUNCTION = {
    "online_search": bing_search_firefox, # change to fast_bing_search to enhance response
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
    print(fast_bing_search("最新新闻"))
    print(get_current_time())
