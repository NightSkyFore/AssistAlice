from PySide6.QtCore import Qt, QVariantAnimation, QEasingCurve, QRect
from PySide6.QtGui import QPainter, QPainterPath, QColor, QFont, QPen, QFontMetrics
from PySide6.QtWidgets import QWidget

class SubtitleLabel(QWidget):
    def __init__(self, font_size=23, parent=None, width=900, height=100):
        super().__init__(parent)
        self.resize(width, height)

        self.text = ""
        self.text_lines = []
        self.font_size = font_size

        self.margin = 5
        self._set_stoke_width()
        self._set_font_metrics()
        
        self._last_line_count = 0
        self._render_start_line = 0
        self._y_offset = 0.0
        
        self.slide_anim = QVariantAnimation(self)
        self.slide_anim.setDuration(300)
        self.slide_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.slide_anim.valueChanged.connect(self._on_slide_changed)
        self.slide_anim.finished.connect(self._on_slide_finished)
    
    def change_font_size(self, upscale: bool):
        if upscale:
            self.font_size += 1
        else:
            self.font_size -= 1
        self._set_stoke_width()
        self._set_font_metrics()

        self._last_line_count = 0
        self._render_start_line = 0
        self._text_process(False)

    def _set_stoke_width(self):
        if self.font_size < 10:
            self.stroke_width = 1
        elif self.font_size < 20:
            self.stroke_width = 2 + (self.font_size - 10) // 5
        elif self.font_size < 30:
            self.stroke_width = 4
        else:
            self.stroke_width = 5
    
    def _set_font_metrics(self):
        self.display_font = QFont("Noto Sans CJK SC", self.font_size, QFont.Weight.Bold)       
        self.metrics = QFontMetrics(self.display_font)
        self.line_height = self.metrics.height()
        self.line_spacing = self.line_height + max(self.metrics.leading(), 2)
        self.max_lines = (self.height() - self.margin * 2) // self.line_spacing
        self.safe_width = self.width() - self.margin * 2
        
    def set_text(self, text: str):
        if not text:
            self.slide_anim.stop()
            self.text = ""
            self.text_lines = []
            self._last_line_count = 0
            self._render_start_line = 0
            self._y_offset = 0.0
            self.update()
            return
        self.text = text
        self._text_process()
        self.update()
    
    def _text_process(self, trigger_anim: bool = True):
        # reformat long text in lines
        self.text_lines = []
        current_line = ""
        for char in self.text:
            test_line = current_line + char
            if self.metrics.horizontalAdvance(test_line) <= self.safe_width:
                current_line = test_line
            else:
                if current_line:
                    self.text_lines.append(current_line)
                current_line = char
        if current_line:
            self.text_lines.append(current_line)
        
        line_count = len(self.text_lines)
        if trigger_anim:
            # if newline
            if line_count > self._last_line_count:
                # if lines exceeds region, then sliding subtitle.
                if line_count > self.max_lines:
                    current_offset = self._y_offset
                    self.slide_anim.stop()
                    self.slide_anim.setStartValue(current_offset + float(self.line_spacing))
                    self.slide_anim.setEndValue(0.0)
                    self.slide_anim.start()
                self._last_line_count = line_count
        
        else:
            self.slide_anim.stop()
            self._last_line_count = line_count
            self._render_start_line = max(0, line_count - self.max_lines)

    def _on_slide_changed(self, value: float):
        self._y_offset = value
        self.update()
    
    def _on_slide_finished(self):
        self._render_start_line = max(0, len(self.text_lines) - self.max_lines)
        self.update()

    def paintEvent(self, event):
        if not self.text_lines:
            return
        if self.safe_width <= 0 or self.max_lines < 1:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # region clip
        logical_height = (self.margin * 2) + (self.max_lines * self.line_spacing)
        clip_rect = QRect(0, 0, self.width(), logical_height)
        painter.setClipRect(clip_rect)

        total_line_num = len(self.text_lines)
        for i in range(self._render_start_line, total_line_num):
            line = self.text_lines[i]
            line_width = self.metrics.horizontalAdvance(line)
            render_x = self.margin + (self.safe_width - line_width) / 2
            # for line[0,1,2], with max_lines=2, line 0 render at (0,0) when animation start, then slide to (0, -1).
            render_y = self.margin + ((i - total_line_num) + self.max_lines) * self.line_spacing + self._y_offset + self.metrics.ascent()
            path = QPainterPath()
            path.addText(render_x, render_y, self.display_font, line)
            pen = QPen(QColor(148, 0, 211, 220))
            pen.setWidth(self.stroke_width)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.drawPath(path)
            painter.fillPath(path, QColor(255, 255, 255, 255))
