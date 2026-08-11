import sys
from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget

from ui.history_window import HistoryDialog

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.hist_win = HistoryDialog(self)

        self.hist_btn = QPushButton("Show History")
        self.hist_btn.clicked.connect(self.show_history)

        layout = QVBoxLayout(self)
        layout.addWidget(self.hist_btn)

    def show_history(self):
        self.hist_win.show()

    def closeEvent(self, event):
        self.hist_win.close()
        return super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
