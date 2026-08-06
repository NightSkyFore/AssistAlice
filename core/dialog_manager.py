import queue

from core.mem_worker import MemoryWorker
from core.memory_manager import MemoryManager
from core.text_utils import LLM_PROMPT_LANG, LLM_PROMPT_LANG_MAP, MSG_TYPE_CHAT, MSG_TYPE_SUBTITLE

# user prompt for coding
BASE_CODING_PROMPT_MAP = {
    "en": "Read the following code, and answer with:\n 1.Explain the code;\n 2.Figure out if there is any bug;\n 3.Consider for optimization.\n\n###Code\n{code}",
    "ja": "以下のコードを読んで、次の質問に答えてください。\n 1.コードを説明する。\n 2.バグがあるかどうかを確認する。\n 3.最適化を検討する。\n\n###コード\n{code}",
    "zh": "阅读以下代码，并回答：\n 1.解释代码；\n 2.找出可能存在的问题；\n 3.思考是否需要优化重构。\n\n###代码\n{code}",
    "zh_mix": "阅读以下代码，并回答：\n 1.解释代码及其运行结果；\n 2.找出可能存在的bug；\n 3.思考是否需要优化重构。\n\n###Code\n{code}",
}

ADVANCE_CODING_PROMPT = """
Read the following code, answer strictly in {language}.

### Code
{code}

### User Request
{text}

### Task:
1. Analyze the question directly if there are some problems to be solved.
2. DO NOT simply repeat the original code unless you have made specific modifications to fix a bug or implement a request.
"""

# user prompt for media
MEDIA_SUBTITLE_PROMPT = """
Based on the previous context, process the current subtitle chunk and answer strictly in {language}.

### Previous Context
{previous_summary}

### Current Subtitle Chunk
{subtitle}

### Task
Summarize the core idea in several concise bullet points.
"""

MEDIA_FINAL_SUMMARY_PROMPT = """
We have just enjoyed a video/audio, generate a final global overview of the media with following segment summaries and subtitle chunk.
Answer strictly in {language}.

### Segment Summaries 
{segment_summaries}

### Subtitle Chunk
{subtitle}

[Task]
1. [One-Sentence Summary]: State the overarching topic in a single sentence.
2. [Key Discussion Points]: Highlight 3-5 major takeaways or key themes discussed.
"""

class DialogManager:
    def __init__(self, lang: str = "en", max_round: int = 6, **kwargs,):
        self.lang = lang if lang in LLM_PROMPT_LANG else "en"
        self.max_history_len = max_round * 2
        # history in the long past would be summarized in a word
        self.summary = "" 
        # history to be summrized
        self.history = []
        # media subtitle and summry
        self.subtitle = ""
        self.subtitle_summry = []

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

    def add(self, role: str, content: str, chat_type: str = "chat", source_code: str = ""):
        if chat_type == MSG_TYPE_SUBTITLE:
            self.add_subtitle_summary(content)
            return
        if chat_type == MSG_TYPE_CHAT:
            self.history.append({"role": role, "content": content})
        task = {"action": "new_dialog", "role": role, "content": content, "chat_type": chat_type, "source_code": source_code}
        self.db_queue.put(task)

    def build(self) -> list:
        """General chat dialog built with history"""
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
            # 多会话并行的方式是build_to_summarize里记录历史快照长度snap_hisotry_len，然后此处裁剪history=hisotry[snap_history_len:]
            self.history.clear()
            task = {"action": "new_summary", "content": new_summary}
            self.db_queue.put(task)

    def build_coding_prompt(self, text: str, code: str) -> list:
        """One-shot dialog for coding"""
        if text:
            return [{
                "role": "user",
                "content": ADVANCE_CODING_PROMPT.format(code=code, text=text, language=LLM_PROMPT_LANG_MAP[self.lang])
            }]
        return [{
            "role": "user",
            "content": BASE_CODING_PROMPT_MAP[self.lang].format(code=code)
        }]

    def add_subtitle(self, text: str):
        self.subtitle += text

    def need_subtitle_summurize(self) -> bool:
        # more than 150 words, only for English
        return len(self.subtitle.split()) > 150
    
    def has_media_data(self) -> bool:
        return self.subtitle or self.subtitle_summry

    def build_media_subtitle_summarize(self) -> list:
        previous_summary = "[None]" if not self.subtitle_summry else self.subtitle_summry[-1]
        messages = [{
            "role": "user",
            "content": MEDIA_SUBTITLE_PROMPT.format(previous_summary=previous_summary, subtitle=self.subtitle, language=LLM_PROMPT_LANG_MAP[self.lang])
        }]
        self.subtitle = ""
        return messages

    def build_media_final_summarize(self) -> list:
        segment_summaries = "[None]" if not self.subtitle_summry else "\n".join(self.subtitle_summry)
        messages = [{
            "role": "user",
            "content": MEDIA_FINAL_SUMMARY_PROMPT.format(segment_summaries=segment_summaries, subtitle=self.subtitle, language=LLM_PROMPT_LANG_MAP[self.lang])
        }]
        self.subtitle = ""
        self.subtitle_summry = []
        return messages

    def add_subtitle_summary(self, summary: str):
        self.subtitle_summry.append(summary)

    def close_mem(self):
        self.mem_worker.stop()
