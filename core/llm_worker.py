import queue
import re
import traceback

from PySide6.QtCore import QThread, Signal

from core.alice_ai import AliceAI

_POISON_PILL = object()

class LLMWorker(QThread):
    # emotion for desktop pet, word for ui view, and sentence for tts
    emotion_signal = Signal(str)
    word_signal = Signal(str)
    sentence_signal = Signal(str)
    finished_signal = Signal(str)

    # background sumarize
    summary_finished_signal = Signal(str)

    error_signal = Signal(str)

    def __init__(self, llm_instance: AliceAI, msg_queue: queue.Queue):
        super().__init__()
        self.llm = llm_instance
        self.msg_queue = msg_queue

        # 断句
        self.safe_punctuations = set("，。！？；\n!?;")
        self.unsafe_punctuations = set(",.")

    def run(self):
        while True:
            try:
                task = self.msg_queue.get()

                if task is _POISON_PILL:
                    self.msg_queue.task_done()
                    break

                if task["type"] == "chat":
                    self.chat(task["msg"])
                elif task["type"] == "summarize":
                    self.summarize(task["msg"])
                
                self.msg_queue.task_done()
            except queue.Empty:
                continue

    def chat(self, messages: list):
        tts_buffer = ""
        full_response = ""
        # emotion head parsing status
        is_parsing_head= True
        head_buffer = ""
        max_head_scan = 15
        # 状态机：非代码块状态/代码块状态（跳过）
        is_inside_code = False

        try:
            for token in self.llm.generate_stream_response(messages):
                full_response += token

                # parse head emotion like [smile] until meet a "]"
                if is_parsing_head:
                    head_buffer += token
                    
                    if "]" in head_buffer:
                        is_parsing_head = False
                        match = re.search(r'^\[(.+?)\]', head_buffer)
                        if match:
                            emotion = match.group(1)
                            self.emotion_signal.emit(emotion) 
                            
                            real_text_start = head_buffer.split("]", 1)[1].lstrip()
                            token = real_text_start 
                        else:
                            token = head_buffer 
                    elif len(head_buffer) > max_head_scan:
                        is_parsing_head = False
                        token = head_buffer
                    else:
                        continue
                
                if not token:
                    continue

                # send to ui update 
                self.word_signal.emit(token)

                # processing for tts sentence 
                tts_buffer += token

                # detecting code block 
                if "```" in tts_buffer:
                    parts = tts_buffer.split("```", 1)
                    before_code = parts[0]
                    rest = parts[1]

                    if not is_inside_code:
                        # 状态流转：外部 -> 内部 (刚进入代码块)
                        # 把进入代码块之前的正常文本，强制推给 TTS 断句并朗读
                        self.flush_buffer_to_tts(before_code, force_flush=True)

                    # 切换状态，并将剩余部分放回 buffer
                    is_inside_code = not is_inside_code
                    tts_buffer = rest

                if not is_inside_code:
                    sentences, remaining = self.process_buffer(tts_buffer)
                    for sentence in sentences:
                        self.emit_clean_sentence(sentence)
                    tts_buffer = remaining
                else:
                    # 代码块内，除了反引号（为了凑出下一个 ```），其它内容全丢弃
                    if tts_buffer.endswith("``"):
                        tts_buffer = "``"
                    elif tts_buffer.endswith("`"):
                        tts_buffer = "`"
                    else:
                        tts_buffer = "" 

            # deal with buffer tail 
            if not is_inside_code and tts_buffer:
                self.flush_buffer_to_tts(tts_buffer, force_flush=True)

            self.finished_signal.emit(full_response)
            
        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"[LLMWorker] {error_msg}")
            self.error_signal.emit(str(e))

    def flush_buffer_to_tts(self, text, force_flush=False):
        if not text.strip(): 
            return
        sentences, remaining = self.process_buffer(text)
        for s in sentences:
            self.emit_clean_sentence(s)
        if force_flush and remaining.strip():
            self.emit_clean_sentence(remaining)

    def emit_clean_sentence(self, sentence):
        clean = sentence.strip()
        # deal with inline code
        clean = clean.replace('`', '') 
        if clean:
            self.sentence_signal.emit(clean)

    def process_buffer(self, buffer):
        sentences = []
        current_sentence = ""
        i = 0
        
        while i < len(buffer):
            char = buffer[i]
            current_sentence += char
            
            if char in self.safe_punctuations:
                sentences.append(current_sentence)
                current_sentence = ""
            # deal with long number like: 4,630.50
            elif char in self.unsafe_punctuations:
                if i + 1 < len(buffer):
                    next_char = buffer[i + 1]
                    if not next_char.isdigit():
                        sentences.append(current_sentence)
                        current_sentence = ""
                else:
                    current_sentence = current_sentence[:-1]
                    break 
            i += 1
            
        remaining_buffer = current_sentence + buffer[i:]
        return sentences, remaining_buffer
    
    def summarize(self, content: str):
        try:
            new_summary = self.llm.get_summary_response(content)
            self.summary_finished_signal.emit(new_summary)
        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"[LLMWorker]Summarize: {error_msg}")
            self.error_signal.emit(str(e))

    def stop(self):
        self.msg_queue.put(_POISON_PILL)
        self.wait()