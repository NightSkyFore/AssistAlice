from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pet_widget import DesktopPet
from tray_icon import TrayIcon
import sys

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

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
        
        self.mic_btn = QPushButton("🎤 麦克风已关闭")
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
        self.input_edit = QPlainTextEdit()
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

        # 发送按钮
        send_btn = QPushButton("Send")
        send_btn.setFixedHeight(45)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: white;
                border-radius: 10px;
                font-size: 14px;
                padding: 15px;
            }
        """)

        #send_btn.clicked.connect(self.send_message)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(send_btn)

        right_layout.addWidget(self.chat_view)
        right_layout.addLayout(input_layout)

        # ---------- 组装 ----------
        layout.addLayout(left_layout, 1)
        layout.addLayout(right_layout, 2)

        self.model.add_message("你好！这是使用 QListView + Delegate 实现的专业级聊天界面。", False)
    
    # keyborad listener
    def eventFilter(self, watched: QObject, event):
        print(type(event))
        print(event.type())
        if watched == self.input_edit and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() == Qt.ControlModifier:
                    print("send")
                    self.send_msg()
                    return True
        return super().eventFilter(watched, event)
    
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("AIAssistant")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())