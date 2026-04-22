from collections import deque

class DialogManager:
    def __init__(self, max_round = 6):
        # max round that message would be stored in cache_history
        self.max_round_len = max_round * 2
        # history message that current cache
        self.cache_history = deque()
        # long history in the past would be summarized in a word
        self.summary = None
        # long history to be summrized
        self.long_history = []

    def add(self, role: str, content: str):
        self.cache_history.append({"role": role, "content": content})
        if len(self.cache_history) > self.max_round_len:
            self.long_history.append(self.cache_history.popleft())

    def build(self) -> list:
        if self.summary:
            return [
                {"role": "assistant", "content": f'{self.summary}'},
                *self.cache_history
            ]
        else:
            return [*self.cache_history]
    
    def needSummurize(self) -> bool:
        return len(self.long_history) >= self.max_round_len
    
    def buildToSummarize(self) -> str:
        if self.summary:
            chat_text = f"OLD SUMMARY:\n{self.summary}\n\nRECENT DIALOGUE:\n"
        else:
            chat_text = f"RECENT DIALOGUE:\n"
        chat_text += "\n".join([f"{h['role']}: {h['content']}" for h in self.long_history])
        return chat_text

    def updateSummry(self, summary: str):
        self.summary = summary
        self.long_history.clear()
