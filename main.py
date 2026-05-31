#! /usr/bin/env python3

import os
import sys

os.environ["QT_QPA_PLATFORM"] = "xcb"

import json

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow

CONFIG_FILE = "./config/setting.json"

PROMPT_FILE = "./config/system_prompt.txt"

if __name__ == "__main__":
    custom_config = {}
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as fin:
            custom_config = json.load(fin)
    if os.path.isfile(PROMPT_FILE):
        with open(PROMPT_FILE, "r", encoding="utf-8") as fin:
            system_prompt = fin.read()
            if system_prompt:
                custom_config["system_prompt"] = system_prompt
    print(custom_config)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Alice AI")
    win = MainWindow(custom_config)
    win.show()
    sys.exit(app.exec())
