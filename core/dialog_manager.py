
class DialogManager:
    def __init__(self, max_round = 6):
        self.max_history_len = max_round * 2
        # history in the long past would be summarized in a word
        self.summary = None
        # history to be summrized
        self.history = []

    def add(self, role: str, content: str):
        self.history.append({"role": role, "content": content})

    def build(self) -> list:
        if self.summary:
            return [
                {"role": "assistant", "content": f"Refer to this long-term conversation memory: {self.summary}"},
                *self.history
            ]
        else:
            return list(self.history)
    
    def need_summurize(self) -> bool:
        return len(self.history) > self.max_history_len
    
    def build_to_summarize(self) -> str:
        if self.summary:
            chat_text = f"OLD SUMMARY:\n{self.summary}\n\nRECENT DIALOGUE:\n"
        else:
            chat_text = f"RECENT DIALOGUE:\n"
        chat_text += "\n".join([f"{h['role']}: {h['content']}" for h in self.history])
        return chat_text

    def update_summary(self, new_summary: str):
        if new_summary:
            self.summary = new_summary
            # 本地LLM不允许同时进行推理和总结，主线程做了并发限制，这里直接clear
            # 多线程的方式是buildToSummarize里记录历史快照长度snap_hisotry_len，这里裁剪history=hisotry[snap_history_len:]
            self.history.clear()
