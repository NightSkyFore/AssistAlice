from collections import deque

from PySide6.QtWidgets import QApplication, QGraphicsOpacityEffect, QLabel, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QTimer, Qt
from PySide6.QtGui import QCursor

from ui.subtitle_label import SubtitleLabel

class OSDTextWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.SubWindow |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.init_width = 900
        self.init_height = 100

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.bg_container = QWidget(self)
        self.bg_container.setObjectName("osd_bg_container")
        main_layout.addWidget(self.bg_container)

        container_layout = QVBoxLayout(self.bg_container)
        self.label = SubtitleLabel(parent=self, width=self.init_width, height=self.init_height)
        container_layout.addWidget(self.label)

        self.resize(self.init_width+20, self.init_height+20)
        self._move_to_bottom()

        self.full_text = ""
        self.char_queue = deque()
        self._type_speed_ms = 40
        self._display_time_ms = 3000

        self.opacity_effect = QGraphicsOpacityEffect(self.label)
        self.opacity_effect.setOpacity(0.0)
        self.label.setGraphicsEffect(self.opacity_effect)
        self.anim_in = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.anim_in.setDuration(300)
        self.anim_in.setEndValue(1.0)
        self.anim_in.setEasingCurve(QEasingCurve.OutCubic)
        self.anim_out = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.anim_out.setDuration(800)
        self.anim_out.setEndValue(0.0)
        self.anim_out.setEasingCurve(QEasingCurve.InCubic)
        self.anim_out.finished.connect(self._check_to_clear)

        self.type_timer = QTimer(self)
        self.type_timer.timeout.connect(self._type_next_char)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.fade_out)

    def _move_to_bottom(self):
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        margin = 30
        target_x = (screen_geometry.width() - self.width() - margin) / 2
        target_y = screen_geometry.height() - self.height() - margin
        self.move(target_x, target_y)

    def feed_streaming(self, text):
        self.hide_timer.stop()
        self.label.set_text(text)
        self.hide_timer.start(self._display_time_ms)

    def feed_sentence(self, sentence: str):
        """A builtin streaming typer for sentence input"""
        self.hide_timer.stop()
        self.char_queue.extend(sentence)

        if self.opacity_effect.opacity() < 1.0:
            self.fade_in()

        if not self.type_timer.isActive():
            self.type_timer.start(self._type_speed_ms)

    def _type_next_char(self):
        if self.char_queue:
            char = self.char_queue.popleft()
            self.full_text += char
            self.label.set_text(self.full_text)
        else:
            self.type_timer.stop()
            self.hide_timer.start(self._display_time_ms)
    
    def fade_in(self):
        self.anim_out.blockSignals(True)
        self.anim_out.stop()
        self.anim_out.blockSignals(False)
        
        self.anim_in.setStartValue(self.opacity_effect.opacity())
        self.anim_in.start()

    def fade_out(self):
        self.anim_in.stop()

        self.anim_out.setStartValue(self.opacity_effect.opacity())
        self.anim_out.start()

    def _check_to_clear(self):
        self.full_text = ""
        self.label.set_text("")
        self.char_queue.clear()
    
    def enable_preview(self):
        self.setStyleSheet("""
            #osd_bg_container {
                background-color: rgba(255, 255, 255, 160);
                border: 2px dashed #c0c0c0;
            }
        """)

    def disable_preview(self):
        self.setStyleSheet("""
            #osd_bg_container {
                background-color: rgba(255, 255, 255, 0);
                border: none;
            }
        """)

    def change_label_font(self, upscale: bool = True):
        self.label.change_font_size(upscale)

class OSDHandleWindow(QWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.target_window = parent 

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.SubWindow |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0.1)
        self.setGraphicsEffect(self.opacity_effect)

        self.setObjectName("osd_handle_toolkit")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop | Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        label_move = QLabel("✢", self)
        label_move.setFixedSize(30, 30)
        label_move.setAlignment(Qt.AlignCenter)
        label_move.setStyleSheet("""
            #osd_handle_toolkit > QLabel {
                border: none;
                background-color: rgba(255, 255, 255, 160);
                color: black;
                padding: 0;
                font-size: 14px;
            }
        """)
        btn_font_upscale = QPushButton("Aa+", self)
        self._set_clear_btn(btn_font_upscale)
        btn_font_upscale.clicked.connect(self.upscale_font)
        btn_font_downscale = QPushButton("Aa-", self)
        self._set_clear_btn(btn_font_downscale)
        btn_font_downscale.clicked.connect(self.downscale_font)
        layout.addWidget(label_move)
        layout.addWidget(btn_font_upscale) 
        layout.addWidget(btn_font_downscale)
        self.resize(30, 100)
        self._move_to_attached()

        self._stay_on_ms = 1000
        self.stay_timer = QTimer(self)
        self.stay_timer.setSingleShot(True)
        self.stay_timer.timeout.connect(self._trigger_enter_preview)
        self.leave_watcher = QTimer(self)
        self.leave_watcher.setInterval(100)
        self.leave_watcher.timeout.connect(self._poll_mouse_position)

        self.drag_position = QPoint()
    
    def _move_to_attached(self):
        target_x = self.target_window.pos().x() + self.target_window.width()
        target_y = self.target_window.pos().y()
        self.move(target_x, target_y)
    
    def _set_clear_btn(self, btn: QPushButton):
        btn.setFixedSize(30, 30)
        btn.setStyleSheet("""
            #osd_handle_toolkit > QPushButton {
                border: none;
                outline: none;
                background-color: rgba(255, 255, 255, 160); 
                color: black;
                padding: 0;
                font-size: 14px;
            }
            #osd_handle_toolkit > QPushButton:pressed {
                background-color: #c0c0c0;
            }
        """)
    
    def enterEvent(self, event):
        self.stay_timer.start(self._stay_on_ms)
        self.leave_watcher.start()
        self.opacity_effect.setOpacity(1.0)
        self.update()

        return super().enterEvent(event)
    
    def _trigger_enter_preview(self):
        self.target_window.enable_preview()
    
    def leaveEvent(self, event):
        return super().leaveEvent(event)
    
    def _poll_mouse_position(self):
        local_pos = self.mapFromGlobal(QCursor.pos())
        
        if not self.rect().contains(local_pos):
            self._trigger_leave()

    def _trigger_leave(self):
        if self.stay_timer.isActive():
            self.stay_timer.stop()
        if self.leave_watcher.isActive():
            self.leave_watcher.stop()
        
        self.opacity_effect.setOpacity(0.1)
        self.update()

        self.target_window.disable_preview()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            new_pos = event.globalPos() - self.drag_position
            self.move(new_pos)
            
            self.target_window.move(new_pos.x() - self.target_window.width(), new_pos.y())
            event.accept() 

    def upscale_font(self):
        self.target_window.change_label_font(True)

    def downscale_font(self):
        self.target_window.change_label_font(False)