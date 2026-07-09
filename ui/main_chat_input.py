from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontDatabase, QKeyEvent

class ChatInputArea(QPlainTextEdit):
    # 定义一个发送信号，当触发 Ctrl+Enter 时发射
    send_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Tell Alice...")
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        fixed_font.setPointSize(14)
        self.setFont(fixed_font)

        # 自定义enable状态，disable时允许输入但不可发送
        self._enable_key_send = True

    def keyPressEvent(self, event: QKeyEvent):
        # 捕获回车键 (包括主键盘回车和小键盘回车)
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # 判断是否按下了 Ctrl 键
            if self._enable_key_send and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                # Ctrl + Enter: 触发发送信号，并清空输入框
                text = self.toPlainText().strip()
                if text:
                    self.send_requested.emit(text)
                    self.clear()
                # 必须 return，防止继续执行换行操作
                return 
            else:
                # 只有 Enter: 走系统默认行为 (换行)
                super().keyPressEvent(event)
        else:
            # 其他按键，走默认行为
            super().keyPressEvent(event)

    def toggle_send_enabled(self, enable_send: bool):
        self._enable_key_send = enable_send
