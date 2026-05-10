import requests
from bs4 import BeautifulSoup

def fast_bing_search(query: str):
    # 模拟真实浏览器的 Headers，防止被拦截
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
    }
    
    # 自动根据中英文选择 URL
    base_url = "https://www.bing.com/search?q="
    if not any('\u4e00' <= char <= '\u9fff' for char in query):
        headers["Accept-Language"] = "en-US,en;q=0.9"

    try:
        # 1. 纯 HTTP 请求，不加载图片和 JS
        response = requests.get(base_url + query, headers=headers, timeout=5)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 2. 精确提取 title + snippet
        results = []

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
            if len(results) >= 5:
                break
        
        if not results:
            return "No relevant search results found."
            
        final_context = "\n\n".join(results)
        return final_context[:4000] # 进一步精简，4000 字符足够了

    except Exception as e:
        return f"Search error: {str(e)}"

if __name__ == "__main__":
    print(fast_bing_search("最新国内新闻"))
    print(fast_bing_search("gold price"))