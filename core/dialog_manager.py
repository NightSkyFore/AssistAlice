import queue

from core.mem_worker import MemoryWorker
from core.memory_manager import MemoryManager

class DialogManager:
    def __init__(self, max_round = 6):
        self.max_history_len = max_round * 2
        # history in the long past would be summarized in a word
        self.summary = "" 
        # history to be summrized
        self.history = []

        self.db_path = "./data/memory.db"
        self.load_from_memory()

        self.db_queue = queue.Queue()
        self.mem_worker = MemoryWorker(self.db_queue, self.db_path)
        self.mem_worker.start()
    
    def load_from_memory(self):
        memory_manager = MemoryManager(self.db_path)
        summary_text, last_hist = memory_manager.load_memory()
        if summary_text:
            self.summary = summary_text
            print(f"Load memory:\n{summary_text}")
        if last_hist:
            self.history = last_hist
            print(f"Load dialog history: {len(last_hist)}")

    def add(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        task = {"action": "new_dialog", "role": role, "content": content}
        self.db_queue.put(task)

    def build(self) -> list:
        if self.summary:
            return [
                {"role": "memory", "content": f"###Long-term Memory\n{self.summary}"},
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
            task = {"action": "new_summary", "content": new_summary}
            self.db_queue.put(task)
    
    def close_mem(self):
        self.mem_worker.stop()
