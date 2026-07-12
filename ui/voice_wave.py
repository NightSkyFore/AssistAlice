import numpy as np
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Qt, QTimer, Slot

class VoiceWaveWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(120, 40)

        self.bar_width = 4
        self.bar_margin = 4
        self.bar_space = self.bar_width + self.bar_margin
        self.bar_count = 15
        self.min_bar_height = 0.05
        # 初始化柱子
        self.amplitudes = [self.min_bar_height] * self.bar_count
        self.wave_color = QColor("#007ACC") 

        # 如果音频源断开，用一个定时器让声波平滑回落到 0
        self.decay_timer = QTimer(self)
        self.decay_timer.timeout.connect(self._decay_amplitudes)

    @Slot(float)
    def set_amplitude(self, volume: float):
        """
        接收外部传来的音量值 (0.0 ~ 1.0)
        """
        # 限制范围并做一点微小的基础保底，确保完全没声音时也有个小点
        val = max(self.min_bar_height, min(1.0, volume)) 

        self.amplitudes.pop(0)
        self.amplitudes.append(val)

        if val > self.min_bar_height and not self.decay_timer.isActive():
            self.decay_timer.start(50)

        self.update()

    def _decay_amplitudes(self):
        needs_update = False
        for i in range(len(self.amplitudes)):
            if self.amplitudes[i] > self.min_bar_height:
                self.amplitudes[i] = max(self.min_bar_height, self.amplitudes[i] - 0.05)
                needs_update = True
        if needs_update:
            self.update()
        else:
            self.decay_timer.stop()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.wave_color)

        height = self.height()
        wrap_amp_count = (self.width() - self.bar_space * self.bar_count - self.bar_margin) // self.bar_space // 2

        for i in range(wrap_amp_count + self.bar_count + wrap_amp_count):
            x = i * self.bar_space
            if i < wrap_amp_count or i >= wrap_amp_count + self.bar_count:
                # 前后填充
                bar_height = height * self.min_bar_height
            else:
                # 计算当前音量柱子的高度 (预留一点边距防止顶满)
                bar_height = height * self.amplitudes[i - wrap_amp_count] * 0.9
            y = (height - bar_height) / 2
            painter.drawRoundedRect(x, y, self.bar_width, bar_height, self.bar_width/2, self.bar_width/2)
