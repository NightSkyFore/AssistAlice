import traceback

from PySide6.QtCore import QThread, Signal

from core.alice_ai import AliceAI

class LLMWorker(QThread):
    # 定义两个信号：一个用于返回最终结果，一个用于发生错误时报错
    finished_signal = Signal(str)
    error_signal = Signal(str)

    def __init__(self, llm_instance: AliceAI, messages: list):
        super().__init__()
        self.llm = llm_instance
        self.messages = messages

    def run(self):
        """异步执行，避免卡界面"""
        try:
            reply_text = self.llm.get_response(self.messages)
            self.finished_signal.emit(reply_text)
        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"[LLMWroker] {error_msg}")
            self.error_signal.emit(str(e))