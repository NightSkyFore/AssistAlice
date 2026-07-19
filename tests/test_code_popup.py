import sys
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QPushButton, QTextEdit, QVBoxLayout, QWidget
from PySide6.QtGui import QColor

from ui.code_popup import CodeWidget

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        self.input = QTextEdit()
        self.code_btn = QPushButton("Code")
        self.code_btn.clicked.connect(self.on_code_click)

        layout = QVBoxLayout(self)
        layout.addWidget(self.input)
        layout.addWidget(self.code_btn)

        self.popup = CodeWidget(self)

    def on_code_click(self):
        self.popup.set_code(self.input.toPlainText())
        if not self.popup.isActiveWindow():
            self.popup.show()
            print(self.popup.get_code())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
