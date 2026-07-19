from PySide6.QtWidgets import QGraphicsDropShadowEffect, QTextEdit, QVBoxLayout, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFontDatabase

class CodeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.Popup |
            Qt.FramelessWindowHint |
            Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.max_w = 800
        self.max_h = 600

        container = QWidget(self)
        container.setObjectName("CodeContainer")
        container.setAttribute(Qt.WA_StyledBackground, True)
        container.setStyleSheet("""
            #CodeContainer {
                background-color: #FFFFFF; /* 深色模式可改为 #1E1E1E */
                border-radius: 12px;
                border: 1px solid #E5E7EB; /* 加个极细的边框提升质感 */
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4) 
        container.setGraphicsEffect(shadow)

        self.text_edit = QTextEdit(container)
        self.text_edit.setFrameShape(QTextEdit.NoFrame)
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        fixed_font.setPointSize(11)
        self.text_edit.setFont(fixed_font)
        self.text_edit.setLineWrapMode(QTextEdit.NoWrap)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.addWidget(self.text_edit)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20) 
        main_layout.addWidget(container)

    def set_code(self, text):
        self.text_edit.setPlainText(text)
        # margin and scrollbar: 10 * 2 + 20 * 2 + 30
        w = max(self.max_w/2, min(self.text_edit.document().idealWidth() + 90, self.max_w))
        self.setFixedWidth(w)
        h = max(self.max_h/2, min(self.text_edit.document().size().height() + 30, self.max_h))
        self.setFixedHeight(h)
        self.adjustSize()

    def get_code(self):
        return self.text_edit.toPlainText().strip()
