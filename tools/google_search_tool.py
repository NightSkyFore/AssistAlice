import json
import os
import requests

CONFIG_FILE = "./config/setting.json"

class QuickSearch:
    def __init__(self) -> None:
        if os.path.isfile(CONFIG_FILE):
            with open(CONFIG_FILE, encoding="utf-8", mode="r") as fin:
                setting = json.load(fin)
        self.api_key = setting["google_search_key"]
        self.cx = setting["google_search_cx"]
    
    def search(self, query_word:str) -> str:
        query = f'https://www.googleapis.com/customsearch/v1?key={self.api_key}&cx={self.cx}&q={query_word}&start=1&num=10'
        print(query)
        res = requests.get(query)
        return res

if __name__ == "__main__":
    search_tool = QuickSearch();
    print(search_tool.search("lectures"))
