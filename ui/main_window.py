from datetime import datetime

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from core.alice_ai import AliceAI
from core.dialog_manager import DialogManager
from core.llm_worker import LLMWorker
from core.summary_worker import SummaryWorker
from .pet_widget import DesktopPet
from .tray_icon import TrayIcon
import sys

class MainWindow(QMainWindow):
    def __init__(self, custom_config: dict = None):
        super().__init__()
        # ui
        self.setWindowTitle("Alice AI Assistant")
        self.setMinimumSize(900, 600)

        self.pet = DesktopPet()
        self.pet.hide()

        self._actually_quit = False

        self.tray = TrayIcon(self)
        self.tray.show()
        self.tray.show_main.connect(self.show_main_from_tray)
        self.tray.show_pet.connect(self.show_pet_mode)
        self.tray.tray_quit.connect(self.quit_from_tray)

        self.setup_ui()

        # core 
        self.dialog_manager = DialogManager()
        if custom_config:
            self.alice = AliceAI(*custom_config)
        else:
            self.alice = AliceAI()
        self.worker = None
        self.summary_worker = None
    
    def setup_ui(self):
        # main
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # left
        left_layout = QVBoxLayout()
        left_layout.setSpacing(15)
        
        self.viewer = AiViewer()
        
        self.mic_btn = QPushButton("🎤 Microphone Closed")
        self.mic_btn.setCheckable(True)
        self.mic_btn.setFixedHeight(45)
        self.mic_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: white;
                border-radius: 10px;
                font-size: 14px;
            }
            QPushButton:checked {
                background-color: #007acc;
                color: white;
            }
        """)
        button_layout = QVBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 7.5)
        button_layout.addWidget(self.mic_btn)

        left_layout.addWidget(self.viewer)
        left_layout.addLayout(button_layout)

        # right
        right_layout = QVBoxLayout()
        right_layout.setSpacing(15)

        fixed_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        fixed_font.setPointSize(14)

        # 对话框
        self.chat_view = QListView()
        self.model = MessageModel()
        self.delegate = ChatDelegate()
        
        self.chat_view.setModel(self.model)
        self.chat_view.setItemDelegate(self.delegate)
        
        # 样式优化：去掉默认蓝框
        self.chat_view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.chat_view.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel) # 丝滑滚动
        self.chat_view.setStyleSheet("QListView { border: none; background-color: #FAFAFA; }")

        # 输入框
        self.input_edit = ChatInputArea()
        self.input_edit.setPlaceholderText("Tell Alice...")
        self.input_edit.setFont(fixed_font)
        self.input_edit.setFixedHeight(60)
        self.input_edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: #FFFFFF;
                border-radius: 10px;
                padding: 10px;
                font-size: 14px;
            }
        """)
        self.input_edit.send_requested.connect(self.handle_send)

        # 发送按钮
        self.send_btn = QPushButton("Send")
        self.send_btn.setFixedHeight(45)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: white;
                border-radius: 10px;
                font-size: 14px;
                padding: 15px;
            }
        """)
        self.send_btn.clicked.connect(self.trigger_send_from_button)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(self.send_btn)

        right_layout.addWidget(self.chat_view)
        right_layout.addLayout(input_layout)

        # ---------- 组装 ----------
        layout.addLayout(left_layout, 1)
        layout.addLayout(right_layout, 2)
    
    def trigger_send_from_button(self):
        text = self.input_edit.toPlainText().strip()
        if text:
            self.handle_send(text)
            self.input_edit.clear()

    def handle_send(self, text: str):
        # ui update 
        self.model.add_message(text, True)
        self.chat_view.scrollToBottom()

        # history update
        self.dialog_manager.add("user", text)

        # waiting ui
        self.model.add_message("Alice thinking...", False)
        self.chat_view.scrollToBottom()
        self.thinking_index = self.model.rowCount() - 1
        self.set_ui_busy(True)

        # wait for worker
        messages = self.dialog_manager.build()
        self.worker = LLMWorker(self.alice, messages)
        self.worker.finished_signal.connect(self.on_llm_reply)
        self.worker.error_signal.connect(self.on_llm_error)
        self.worker.start()

    def on_llm_reply(self, reply_text):
        # history update
        self.dialog_manager.add("assistant", reply_text)

        # ui update
        self.model.messages[self.thinking_index]['text'] = reply_text
        self.model.layoutChanged.emit() 
        self.chat_view.scrollToBottom()

        if self.dialog_manager.need_summurize():
            self.trigger_background_summary()
        else:
            self.set_ui_busy(False)

    def on_llm_error(self, error_msg):
        cur_time = datetime.strftime(datetime.now(), "%Y-%m-%D %H:%M:%S")
        print(f"[{cur_time}] Summarize error")
        self.model.messages[self.thinking_index]['text'] = f"[LLM Error] {error_msg}"
        self.model.layoutChanged.emit()
        self.set_ui_busy(False)
    
    def trigger_background_summary(self):
        history_content = self.dialog_manager.build_to_summarize()
        self.summary_worker = SummaryWorker(self.alice, history_content)
        self.summary_worker.summary_finished.connect(self.on_summary_done)
        self.summary_worker.error_signal.connect(self.on_summary_error)
        self.summary_worker.finished.connect(self.unlock_ui_safely)
        self.summary_worker.start()
    
    def on_summary_done(self, new_summary: str):
        self.dialog_manager.update_summary(new_summary)
        cur_time = datetime.strftime(datetime.now(), "%Y-%m-%D %H:%M:%S")
        print(f"[{cur_time}] Summarize done")

    def on_summary_error(self, error_msg: str):
        cur_time = datetime.strftime(datetime.now(), "%Y-%m-%D %H:%M:%S")
        print(f"[{cur_time}] Summarize error")
    
    def unlock_ui_safely(self):
        self.set_ui_busy(False)

        self.summary_worker.deleteLater() 
        self.summary_worker = None

    def set_ui_busy(self, busy: bool):
        self.input_edit.setEnabled(not busy)
        self.send_btn.setEnabled(not busy)
   
    def closeEvent(self, e):
        if not self._actually_quit:
            self.show_pet_mode()
            e.ignore()
        else:
            QApplication.quit()
    
    def show_main_from_tray(self):
        self.pet.hide()
        self.showNormal()
        self.activateWindow()
    
    def show_pet_mode(self):
        self.hide()
        self.pet.show()
    
    def quit_from_tray(self):
        self._actually_quit = True
        self.close()

class AiViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.pixmap = QPixmap("./assets/Elf-Alice.png")
        if self.pixmap.isNull():
            print(f"Error: No image!")
            sys.exit(1)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        pixmap_rect = self.pixmap.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        ).rect()

        # 居中画
        x = (self.width() - pixmap_rect.width()) / 2
        y = (self.height() - pixmap_rect.height()) / 2

        painter.drawPixmap(x, y, pixmap_rect.width(), pixmap_rect.height(), self.pixmap)

class MessageModel(QAbstractListModel):
    def __init__(self):
        super().__init__()
        self.messages = []  # 存储格式：{'text': str, 'is_user': bool}

    def rowCount(self, parent=QModelIndex()):
        return len(self.messages)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        message = self.messages[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return message['text']
        if role == Qt.ItemDataRole.UserRole:
            return message['is_user']
        return None

    def add_message(self, text, is_user):
        self.beginInsertRows(QModelIndex(), len(self.messages), len(self.messages))
        self.messages.append({'text': text, 'is_user': is_user})
        self.endInsertRows()

class ChatDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.padding = 10
        self.margin = 40  # 气泡距离另一侧的留白
        self.radius = 12

    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 获取数据
        text = index.data(Qt.ItemDataRole.DisplayRole)
        is_user = index.data(Qt.ItemDataRole.UserRole)

        # 设置字体
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)

        # 准备文本渲染器（处理换行）
        doc = QTextDocument()
        doc.setDefaultFont(font)
        doc.setPlainText(text)
        
        # 限制文本最大宽度
        max_width = option.rect.width() - self.margin - (self.padding * 2)
        doc.setTextWidth(max_width)
        
        text_size = doc.size()
        bubble_width = text_size.width() + self.padding * 2
        bubble_height = text_size.height() + self.padding * 2

        # 计算气泡矩形位置
        if is_user:
            # 用户在右侧，背景色浅灰蓝
            bubble_x = option.rect.right() - bubble_width - 10
            bg_color = QColor("#F0F4F9")
            text_color = QColor("#1F1F1F")
        else:
            # AI 在左侧，背景色透明（类似 Gemini）或极浅蓝
            bubble_x = option.rect.left() + 10
            bg_color = QColor("#FFFFFF")
            text_color = QColor("#1F1F1F")

        bubble_rect = QRectF(bubble_x, option.rect.top() + 5, bubble_width, bubble_height)

        # 画气泡背景
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(bubble_rect, self.radius, self.radius)

        # 画文本
        painter.translate(bubble_rect.x() + self.padding, bubble_rect.y() + self.padding)
        painter.setPen(text_color)
        doc.drawContents(painter)

        painter.restore()

    def sizeHint(self, option, index):
        # 告诉 QListView 每一个格子需要多高
        text = index.data(Qt.ItemDataRole.DisplayRole)
        doc = QTextDocument()
        font = QFont()
        font.setPointSize(10)
        doc.setDefaultFont(font)
        doc.setPlainText(text)
        
        # 这里的宽度要和 paint 保持一致
        doc.setTextWidth(option.rect.width() - self.margin - (self.padding * 2))
        return QSize(option.rect.width(), doc.size().height() + 20)

class ChatInputArea(QPlainTextEdit):
    # 定义一个发送信号，当触发 Ctrl+Enter 时发射
    send_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("在这里输入消息...\n(Enter 换行，Ctrl+Enter 发送)")
        # 使用等宽字体或系统默认字体
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
        font.setPointSize(11)
        self.setFont(font)

    def keyPressEvent(self, event: QKeyEvent):
        # 捕获回车键 (包括主键盘回车和小键盘回车)
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # 判断是否按下了 Ctrl 键
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("AIAssistant")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())