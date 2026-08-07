from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget

from ui.osd_subtitle import OSDHandleWindow, OSDTextWindow
from ui.pet_widget import DesktopPet

class PetSystemManager(QObject):
    def __init__(self, parent: QWidget = None):
        super().__init__()

        self.pet = DesktopPet(parent)
        self.osd = OSDTextWindow(self.pet)
        self.osd_handle = OSDHandleWindow(self.osd, self.pet)
        self.hide_pet_mode()

    def show_pet_mode(self):
        self.pet.show()
        self.osd.show()
        self.osd_handle.show()

    def hide_pet_mode(self):
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
