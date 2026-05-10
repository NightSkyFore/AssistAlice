from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait

def bing_search_firefox(query: str):
    service = Service(executable_path="./driver/geckodriver")

    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")

    options.set_preference("permissions.default.image", 2) # 禁图片
    options.set_preference("permissions.default.stylesheet", 2) # 禁 CSS
    options.page_load_strategy = 'eager' # 只要 DOM 好了就开跑，不等图片

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

        #full_text = driver.find_element(By.ID, "b_results").text
        source = driver.page_source
        soup = BeautifulSoup(source, "html.parser")
        
        # 2. 精确提取 title + snippet
        results = []

        top_res = soup.select(".b_top")
        if top_res:
            top_title = top_res[0].find("h2")
            top_content = top_res[0].select_one(".b_hPanel")
            if top_title and top_content:
                title = top_title.get_text().strip()
                snippet = top_content.get_text().strip()
                results.append(f"Title: {title}\nSnippet: {snippet}")
            
        # Bing 的主要搜索条目都在 .b_algo 这个类里
        for item in soup.select(".b_algo"):
            title_el = item.find("h2")
            snippet_el = item.find(".b_caption p") or item.select_one(".b_lineclamp2")
            
            if title_el and snippet_el:
                title = title_el.get_text().strip()
                snippet = snippet_el.get_text().strip()
                # 过滤掉一些无效的简短片段
                if len(snippet) > 10:
                    results.append(f"Title: {title}\nSnippet: {snippet}")
            
            # 只取前 5 个最相关的结果，节省 3B 模型的计算量
            if len(results) >= 8:
                break
        
        if not results:
            return "No relevant search results found."
            
        final_context = "\n\n".join(results)
        return final_context[:4000] # 进一步精简，4000 字符足够了

    except Exception as e:
        return f"Search error: {str(e)}"

    finally:
        driver.quit()

def is_english_query(query: str) -> bool:
    for ch in query:
        if "\u4e00" <= ch <= "\u9fff":
            return False
    return True

if __name__ == "__main__":
    print("🔍 Bing 搜索中...")
    print(bing_search_firefox("2026年最新新闻"))
    print(bing_search_firefox("gold price"))