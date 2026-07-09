import sys
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
from PySide6.QtGui import QFontDatabase

from ui.main_chat_view import ChatDelegate, ChatListView, MessageModel

# === 下面是测试运行的脚手架代码 ===
class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(600, 400)
        self.setWindowTitle("QListView 右键菜单测试")

        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)

        layout = QVBoxLayout(self)
        
        self.chat_view = ChatListView()
        self.chat_view.remark_code_signal.connect(self.on_source_code)
        self.model = MessageModel()
        self.delegate = ChatDelegate()
        self.delegate.code_preview_signal.connect(self.on_source_code)

        self.chat_view.setModel(self.model)
        self.chat_view.setItemDelegate(self.delegate)
        self.chat_view.setFont(fixed_font)

        layout.addWidget(self.chat_view)

        self.model.add_message("测试AI回答: Hello，我是Alice。这是一个模拟AI对话的长长长长长文本，以查看气泡显示效果", False)
        self.model.add_message("测试用户回答", True)
        self.model.add_message("Alice thinking...", False, 'loading')
        self.model.add_message("测试系统信息", False, 'system')
        self.model.add_message("测试用户带代码回答: print(True)\nreturn 0", True, source_code="print(True)")
        self.model.add_message("测试AI带代码回答", False, source_code="print(True)")
    
    def on_source_code(self, text):
        print(text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())