from PySide6.QtCore import QObject

from ui.osd_subtitle import OSDHandleWindow, OSDTextWindow
from ui.pet_widget import DesktopPet

class PetSystemManager(QObject):
    def __init__(self):
        super().__init__()

        self.pet = DesktopPet()
        self.osd = OSDTextWindow()
        self.osd_handle = OSDHandleWindow(parent=self.osd)
        self.hide_system()

    def show_system(self):
        self.pet.show()
        self.osd.show()
        self.osd_handle.show()

    def hide_system(self):
        self.pet.hide()
        self.osd.hide()
        self.osd_handle.hide()

    def pet_on_summary_thinking(self):
        self.pet.on_summary_thinking()

    def pet_on_summary_finish(self):
        self.pet.on_summary_finish()

    def pet_emotion_change(self, emotion):
        self.pet.emotion_change(emotion)

    def osd_on_streaming(self, text: str):
        self.osd.feed_streaming(text)

    def osd_on_text(self, text: str):
        self.osd.feed_sentence(text)
