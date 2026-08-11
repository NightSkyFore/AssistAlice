import sqlite3
from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtGui import QFontDatabase
from PySide6.QtCore import QTimer

from ui.main_chat_view import ChatDelegate, ChatListView, MessageModel

class HistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_path = "./data/memory.db"

        self.setWindowTitle("Dialog History")
        self.resize(600, 800)

        self.conn = None
        self.history_max_id = 0
        self.history_offset = 0
        self.history_load_limit = 20
        self.is_loading = False

        init_hist = self.fetch_init_data_from_db()
        if init_hist:
            self.history_max_id = init_hist[-1]["id"]
        self.chat_view = ChatListView(self)
        self.model = MessageModel(self, init_hist)
        self.delegate = ChatDelegate(self)

        self.chat_view.setModel(self.model)
        self.chat_view.setItemDelegate(self.delegate)
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.chat_view.setFont(fixed_font)

        layout = QVBoxLayout(self)
        layout.addWidget(self.chat_view)

        self.chat_view.scrollToBottom()
        self.scrollbar = self.chat_view.verticalScrollBar()
        self.scrollbar.valueChanged.connect(self.on_scroll)
        self.scrollbar.setValue(self.scrollbar.maximum())

    def on_scroll(self, value):
        if value <= 5 and not self.is_loading:
            self.load_older_history()

    def load_older_history(self):
        self.is_loading = True

        older_messages = self.fetch_older_data_from_db()
        if not older_messages:
            self.is_loading = False
            return

        old_maximum = self.scrollbar.maximum()
        old_value = self.scrollbar.value()
        self.model.prepend_history(older_messages)
        self.chat_view.updateGeometries()

        def apply_compensation():
            new_maximum = self.scrollbar.maximum()
            height_difference = new_maximum - old_maximum
            self.scrollbar.setValue(old_value + height_difference)
            self.history_offset += len(older_messages)
            self.is_loading = False
        QTimer.singleShot(100, apply_compensation)

    def refresh_to_latest(self):
        self.is_loading = True
        hist = self.fetch_latest_data_from_db()
        if hist:
            self.history_offset += len(hist)
            self.history_max_id = hist[-1]["id"]
            self.model.append_history(hist)
        self.is_loading = False

    def fetch_init_data_from_db(self) -> list:
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, role, content, source_code FROM dialog_history ORDER BY id DESC LIMIT ?",
            (self.history_load_limit,)
        )
        hist = [{"id": i, "role": r, "text": t, "code": c} for i, r, t, c in cursor.fetchall()]
        self.conn.close()
        self.conn = None
        hist.reverse()
        return hist

    def fetch_older_data_from_db(self) -> list:
        if not self.conn:
            self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, role, content, source_code FROM dialog_history WHERE id <= ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (self.history_max_id, self.history_load_limit, self.history_offset,)
        )
        hist = [{"id": i, "role": r, "text": t, "code": c} for i, r, t, c in cursor.fetchall()]
        hist.reverse()
        return hist

    def fetch_latest_data_from_db(self) -> list:
        if not self.conn:
            self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, role, content, source_code FROM dialog_history WHERE id > ? ORDER BY id ASC",
            (self.history_max_id,)
        )
        hist = [{"id": i, "role": r, "text": t, "code": c} for i, r, t, c in cursor.fetchall()]
        return hist

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        if self.conn:
            self.conn.close()
            self.conn = None
