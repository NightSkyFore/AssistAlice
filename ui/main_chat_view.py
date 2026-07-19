from PySide6.QtWidgets import QApplication, QListView, QMenu, QStyle, QStyledItemDelegate
from PySide6.QtCore import QEvent, QModelIndex, QPoint, QRectF, QSize, Qt, QAbstractListModel, Signal
from PySide6.QtGui import QAction, QColor, QFont, QPainter, QPainterStateGuard, QTextDocument

from ui.code_popup import CodeWidget

SOURCE_CODE_ROLE = Qt.ItemDataRole.UserRole + 1

class MessageModel(QAbstractListModel):
    """
    {
        'text': str,
        'is_user': bool,
        'msg_type': ['normal','system','loading'],
        'attached_code': str,
    }
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.messages = []  

    def rowCount(self, parent=QModelIndex()):
        return len(self.messages)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        message = self.messages[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return message['text']
        elif role == Qt.ItemDataRole.UserRole:
            return message['is_user']
        elif role == SOURCE_CODE_ROLE:
            return message['attached_code']
        return None

    def add_message(self, text: str, is_user: bool, msg_type: str = 'normal', source_code : str = None):
        self.beginInsertRows(QModelIndex(), len(self.messages), len(self.messages))
        self.messages.append({
            'text': text,
            'is_user': is_user,
            'msg_type': msg_type,
            'attached_code': source_code})
        self.endInsertRows()

    def update_message(self, i: int, token: str):
        if i >= len(self.messages):
            print(f"[MessageModel]update failed: index: {i}, length: {len(self.messages)}")
            return
        if self.messages[i]['msg_type'] == 'loading':
            reply_text = ""
            self.messages[i]['msg_type'] = 'normal'
        else:
            reply_text = self.messages[i]['text']

        reply_text += token
        self.messages[i]['text'] = reply_text

class ChatDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bubble_margin = 5
        self.padding = 10
        self.code_icon_padding = 5
        # 气泡距离另一侧的留白
        self.margin = 40
        self.radius = 12

        self.code_popup = CodeWidget(parent)

    def _set_text_document(self, option, font, text):
        # 准备文本渲染器（处理换行）
        doc = QTextDocument()
        doc.setDefaultFont(font)
        doc.setPlainText(text)

        # 限制文本最大宽度
        max_width = option.rect.width() - self.margin - (self.padding * 4)
        doc.setTextWidth(max_width)
        return doc

    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 获取数据
        text = index.data(Qt.ItemDataRole.DisplayRole)
        is_user = index.data(Qt.ItemDataRole.UserRole)
        source_code = index.data(SOURCE_CODE_ROLE)

        # 设置字体
        font = QFont(option.font)
        font.setPixelSize(14)
        painter.setFont(font)

        doc = self._set_text_document(option, font, text)
        text_size = doc.size()
        bubble_width = text_size.width() + self.padding * 2
        bubble_height = text_size.height() + self.padding * 2
        if source_code:
            bubble_height += self.code_icon_padding    # for painting icon

        # 计算气泡矩形位置
        if is_user:
            # 用户在右侧，背景色浅灰蓝
            bubble_x = option.rect.right() - bubble_width - self.padding
            bg_color = QColor("#F0F4F9")
            text_color = QColor("#1F1F1F")
        else:
            # AI 在左侧，背景色透明（类似 Gemini）或极浅蓝
            bubble_x = option.rect.left() + self.padding
            bg_color = QColor("#FFFFFF")
            text_color = QColor("#1F1F1F")

        is_selected = bool(option.state & QStyle.State_Selected)
        if is_selected:
            bg_color = QColor("#007ACC")

        bubble_rect = QRectF(bubble_x, option.rect.top() + self.bubble_margin, bubble_width, bubble_height)

        # 画气泡背景
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(bubble_rect, self.radius, self.radius)

        # 画文本
        padding_top = self.padding + self.code_icon_padding if source_code else self.padding
        painter.translate(bubble_rect.x() + self.padding, bubble_rect.y() + padding_top)
        painter.setPen(text_color)
        doc.drawContents(painter)

        painter.restore()

        if source_code:
            font.setPixelSize(11)
            QPainterStateGuard(painter)
            icon_rect = QRectF(bubble_rect.left() + self.padding, bubble_rect.top(), 80, 20)

            icon_text = "[📎 code]"
            painter.setPen("#9C9C9C")
            painter.drawText(icon_rect, Qt.AlignLeft | Qt.AlignTop, icon_text)

    def sizeHint(self, option, index):
        # 告诉 QListView 每一个格子需要多高
        text = index.data(Qt.ItemDataRole.DisplayRole)
        font = QFont(option.font)
        font.setPixelSize(14)
        doc = self._set_text_document(option, font, text)

        source_code = index.data(SOURCE_CODE_ROLE)
        if source_code:
            item_height = doc.size().height() + (self.padding + self.bubble_margin) * 2 + self.code_icon_padding 
        else:
            item_height = doc.size().height() + (self.padding + self.bubble_margin) * 2
        return QSize(option.rect.width(), item_height)

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            source_code = index.data(SOURCE_CODE_ROLE)
            if source_code:
                text = index.data(Qt.ItemDataRole.DisplayRole)
                font = QFont(option.font)
                doc = self._set_text_document(option, font, text)
                text_size = doc.size()
                bubble_width = text_size.width() + self.padding * 2
                is_user = index.data(Qt.ItemDataRole.UserRole)
                if is_user:
                    bubble_x = option.rect.right() - bubble_width - self.padding
                else:
                    bubble_x = option.rect.left() + self.padding
                icon_rect = QRectF(bubble_x + self.padding, option.rect.top() + self.bubble_margin, 80, 20)
                if icon_rect.contains(event.pos()):
                    self.code_popup.set_code(source_code)
                    global_pos = event.globalPosition().toPoint()
                    self.code_popup.move(global_pos)
                    self.code_popup.show()
                    return True

        # 如果没有点中图标，或者不是点击事件，交给父类走默认逻辑（比如选中该行）
        return super().editorEvent(event, model, option, index)

class ChatListView(QListView):
    remark_code_signal = Signal(dict, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QListView.ExtendedSelection)

        # 样式优化：去掉默认蓝框
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # 丝滑滚动
        self.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        # 禁横向滚动
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setStyleSheet("QListView { border: none; background-color: #FAFAFA; }")

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        pos = event.globalPos()

        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(self._copy_selection)
        copy_action.setEnabled(bool(self.selectedIndexes()))
        menu.addAction(copy_action)

        remark_action = QAction("Remark source code", self)
        source_code = ""
        index = self.indexAt(pos)
        remark_action.triggered.connect(lambda: self._remake_code(index))
        if index.isValid():
            source_code = index.data(SOURCE_CODE_ROLE)
        remark_action.setEnabled(bool(self.selectedIndexes()) and index.isValid() and bool(source_code))
        menu.addAction(remark_action)

        menu.exec(event.globalPos())

    def _copy_selection(self):
        indexes = self.selectedIndexes()
        if not indexes:
            return

        # 必须对 index 进行排序，确保复制出的文本顺序与视觉上一致
        indexes.sort(key=lambda x: x.row())

        copied_texts = []
        for index in indexes:
            # 从 Model 中获取当前项的显示文本
            text = self.model().data(index, Qt.ItemDataRole.DisplayRole)
            if text:
                copied_texts.append(str(text))

        text_to_copy = "\n".join(copied_texts)
        QApplication.clipboard().setText(text_to_copy)
    
    def _remake_code(self, index: QModelIndex):
        if not index.isValid():
            return
        msg = {"role": index.data(Qt.ItemDataRole.UserRole), "content": index.data(Qt.ItemDataRole.DisplayRole)}
        code = index.data(SOURCE_CODE_ROLE)
        self.remark_code_signal.emit(msg, code)