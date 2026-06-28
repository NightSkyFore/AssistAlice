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

        # tts sentence split in chat
        self.safe_punctuations = set("，。！？；\n!?;")
        self.unsafe_punctuations = set(",.")

        self.is_first_sentence = True
        self.pos = 0
        self.word_count = 0
        self.cjk_count = 0

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
        # code block status 
        is_inside_code = False

        self.is_first_sentence = True
        self.pos = 0
        self.word_count = 0
        self.cjk_count = 0

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
                        self.flush_buffer_to_tts(before_code)

                    # 切换状态，并将剩余部分放回 buffer
                    is_inside_code = not is_inside_code
                    tts_buffer = rest

                if not is_inside_code:
                    # normal chat
                    tts_buffer = self.process_buffer_to_sentence(tts_buffer)
                else:
                    # inside code block
                    if tts_buffer.endswith("``"):
                        tts_buffer = "``"
                    elif tts_buffer.endswith("`"):
                        tts_buffer = "`"
                    else:
                        tts_buffer = "" 

            # deal with buffer tail 
            if not is_inside_code and tts_buffer:
                self.flush_buffer_to_tts(tts_buffer)

            self.finished_signal.emit(full_response)
            
        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"[LLMWorker] {error_msg}")
            self.error_signal.emit(str(e))

    def flush_buffer_to_tts(self, buffer):
        if self.is_first_sentence:
            self.is_first_sentence = False
        self.pos = 0
        self.word_count = 0
        self.cjk_count = 0
        clean = buffer.strip()
        # deal with inline code
        clean = clean.replace('`', '') 
        if clean:
            self.sentence_signal.emit(clean)
    
    def process_buffer_to_sentence(self, buffer):
        """
        Divide large text into long sentence block. 
        more than 10 words(splited by blank) in English or more than 20 char in CJK
        """
        i = self.pos
        current_sentence = buffer[:i]

        has_flush = False
        stop_words = 5 if self.is_first_sentence else 10
        stop_cjk_chars = 6 if self.is_first_sentence else 20

        while i < len(buffer):
            char = buffer[i]
            current_sentence += char

            if char == ' ':
                self.word_count += 1
            elif "\u4e00" <= char <= "\u9fff":
                self.cjk_count += 1

            if self.word_count < stop_words and self.cjk_count < stop_cjk_chars:
                i += 1
                continue

            if char in self.safe_punctuations:
                self.flush_buffer_to_tts(current_sentence)
                has_flush = True
                current_sentence = buffer[i+1:]
                break
            # deal with long number like: 4,630.50
            elif char in self.unsafe_punctuations:
                if i + 1 < len(buffer):
                    next_char = buffer[i + 1]
                    if not next_char.isdigit():
                        self.flush_buffer_to_tts(current_sentence)
                        has_flush = True
                        current_sentence = buffer[i+1:]
                        break
                # step back before punctuation for processing in next token
                else:
                    self.pos = i - 1
                    return current_sentence
            i += 1

        if not has_flush:
            self.pos = i
        return current_sentence

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