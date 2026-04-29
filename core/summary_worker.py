import traceback

from PySide6.QtCore import QThread, Signal

from core.alice_ai import AliceAI

class SummaryWorker(QThread):
    summary_finished = Signal(str)
    error_signal = Signal(str)

    def __init__(self, llm_instance: AliceAI, history_content: str):
        super().__init__()
        self.llm = llm_instance
        self.history_content = history_content

    def run(self):
        try:
            new_summary = self.llm.get_summary_response(self.history_content)
            self.summary_finished.emit(new_summary)
        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"[SummaryWorker] {error_msg}")
            self.error_signal.emit(str(e))