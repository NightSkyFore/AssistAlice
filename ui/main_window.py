from datetime import datetime
import queue

from PySide6.QtWidgets import QApplication, QListView, QMainWindow, QPushButton, QVBoxLayout, QWidget, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase

from core.alice_ai import AliceAI, init_greeting
from core.dialog_manager import DialogManager
from core.input_monitor import InputMonitor
from core.llm_worker import LLMWorker
from core.stt_nemotron_worker import NemotronWorker
from core.stt_reazon_worker import ReazonSTTWorker
from core.stt_sense_worker import SenseVoiceSTTWorker
from core.stt_streaming_worker import XASRStreamingWorker
from core.tts_melo_worker import MeloTTSWorker
from core.tts_tonic_jp_worker import TonicTTSWorker
from core.tts_vits_en_worker import VitsTTSWorker
from ui.main_ai_show import AIShow
from ui.main_chat_input import ChatInputArea
from ui.main_chat_view import ChatDelegate, ChatListView, MessageModel
from ui.pet_manager import PetSystemManager
from ui.tray_icon import TrayIcon
from ui.voice_wave import VoiceWaveWidget

class MainWindow(QMainWindow):
    def __init__(self, custom_config: dict = {}):
        super().__init__()
        # ui
        self.setWindowTitle("Alice AI Assistant")
        self.setMinimumSize(900, 600)

        self.pet = PetSystemManager()

        self.tray = TrayIcon(self)
        self.tray.show()
        self.tray.show_main.connect(self.show_main_from_tray)
        self.tray.show_pet.connect(self.show_pet_mode)
        self.tray.tray_quit.connect(self.quit_from_tray)

        self.setup_ui()

        self._custom_config = custom_config
        self._actually_quit = False
        self._llm_busy = False
        self._draft_buffer = ""
        self.llm_queue = queue.Queue()
        self.tts_queue = queue.Queue()

        # core 
        self.dialog_manager = DialogManager()

        self.alice = AliceAI(**custom_config)
        self.llm_worker = LLMWorker(self.alice, self.llm_queue)
        self.llm_worker.emotion_signal.connect(self.on_llm_emotion)
        self.llm_worker.word_signal.connect(self.on_llm_word)
        self.llm_worker.sentence_signal.connect(self.on_llm_sentence)
        self.llm_worker.finished_signal.connect(self.on_llm_reply)
        self.llm_worker.summary_finished_signal.connect(self.on_summary_done)
        self.llm_worker.error_signal.connect(self.on_llm_error)
        self.llm_worker.start()

        self.stt_worker = None

        self.tts_worker = self.init_tts(**custom_config)
        self.tts_worker.tts_sentence_signal.connect(self.on_tts_sentence)
        self.tts_worker.start()

        self.moniter = InputMonitor(**custom_config)
        self.moniter.toggle_mic_signal.connect(self.mic_btn.animateClick)
        self.moniter.remind_status_signal.connect(self.on_reminding)
        self.moniter.work_status_signal.connect(self.on_daily_work_summary)
        self.moniter.start()

        self.first_greeting()

    def setup_ui(self):
        # main
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # left
        left_layout = QVBoxLayout()
        left_layout.setSpacing(15)

        self.ai_show = AIShow()

        self.wave = VoiceWaveWidget()
        self.wave.setFixedHeight(120)

        left_layout.addWidget(self.ai_show)
        left_layout.addWidget(self.wave)

        # right
        right_layout = QVBoxLayout()
        right_layout.setSpacing(15)

        # 对话框
        self.chat_view = ChatListView()
        self.model = MessageModel()
        self.delegate = ChatDelegate()

        self.chat_view.setModel(self.model)
        self.chat_view.setItemDelegate(self.delegate)
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.chat_view.setFont(fixed_font)

        # 样式优化：去掉默认蓝框
        self.chat_view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.chat_view.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel) # 丝滑滚动
        self.chat_view.setStyleSheet("QListView { border: none; background-color: #FAFAFA; }")

        # 输入工具栏
        self.mic_btn = QPushButton("🎙️ Mic")
        self.mic_btn.setObjectName("mic_btn")
        self.mic_btn.setCheckable(True)
        self.mic_btn.setFixedHeight(45)
        self.mic_btn.setFixedWidth(80)
        self.mic_btn.clicked.connect(self.toggle_microphone)

        self.assist_btn = QPushButton("🎬 Assist")
        self.assist_btn.setCheckable(True)
        self.assist_btn.setFixedHeight(45)
        self.assist_btn.setFixedWidth(80)

        self.code_btn = QPushButton("📎 Code")
        self.code_btn.setCheckable(True)
        self.code_btn.setFixedHeight(45)
        self.code_btn.setFixedWidth(80)

        button_style = """
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                color: #333333;
                font-size: 13px;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
                border-color: #CCCCCC;
            }
            QPushButton:checked {
                background-color: #E6F4FF; /* 激活时使用浅蓝色背景 */
                border: 1px solid #1677FF; /* 激活时的蓝色边框 */
                color: #1677FF;
                font-weight: bold;
            }
        """
        self.mic_btn.setStyleSheet(button_style)
        self.assist_btn.setStyleSheet(button_style)
        self.code_btn.setStyleSheet(button_style)

        input_tool_layout = QHBoxLayout()
        input_tool_layout.addWidget(self.mic_btn)
        input_tool_layout.addWidget(self.assist_btn)
        input_tool_layout.addWidget(self.code_btn)
        input_tool_layout.addStretch(1)

        # 输入框
        self.input_edit = ChatInputArea()
        self.input_edit.setFixedHeight(60)
        self.input_edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: #FFFFFF;
                border-radius: 10px;
                padding: 10px;
                font-size: 14px;
            }
        """)
        self.input_edit.send_requested.connect(self.handle_send)

        # 发送按钮
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("send_btn")
        self.send_btn.setFixedHeight(60)
        self.send_btn.setStyleSheet("""
            #send_btn {
                background-color: #3a3a3a;
                color: white;
                border-radius: 10px;
                font-size: 14px;
                padding: 15px;
            }
            #send_btn:disabled {
                background-color: #3a3a3a;
                color: grey;
            }
        """)
        self.send_btn.clicked.connect(self.trigger_send_from_button)

        input_text_layout = QHBoxLayout()
        input_text_layout.addWidget(self.input_edit)
        input_text_layout.addWidget(self.send_btn)

        input_layout = QVBoxLayout()
        input_layout.setSpacing(5)
        input_layout.addLayout(input_tool_layout)
        input_layout.addLayout(input_text_layout)

        right_layout.addWidget(self.chat_view)
        right_layout.addLayout(input_layout)

        # ---------- 组装 ----------
        layout.addLayout(left_layout, 1)
        layout.addLayout(right_layout, 2)

    # microphone event
    def toggle_microphone(self, checked):
        if checked:
            self.start_stt(**self._custom_config)
        else:
            self.stop_stt()
        self.tray.change_status(checked)

    def start_stt(self, lang: str = "zh_mix", stt_cpu: int = 2, **kwargs,):
        if lang == "zh_mix":
            self.stt_worker = XASRStreamingWorker(stt_cpu)
            self.stt_worker.text_signal.connect(self.on_streaming_voice_input)
        elif lang == "en":
            self.stt_worker = NemotronWorker(lang, stt_cpu)
            self.stt_worker.text_signal.connect(self.on_streaming_voice_input)
        elif lang == "ja":
            self.stt_worker = ReazonSTTWorker(stt_cpu)
            self.stt_worker.text_signal.connect(self.on_vad_voice_input)
        else:
            # Note that the pure Chinese as 'zh' is using SenseVoice
            self.stt_worker = SenseVoiceSTTWorker(lang, stt_cpu)
            self.stt_worker.text_signal.connect(self.on_vad_voice_input)
 
        self.stt_worker.speech_silence_signal.connect(self.handle_silence)
        self.stt_worker.start()

    def stop_stt(self):
        if self.stt_worker:
            self.stt_worker.stop()
            self.stt_worker = None

    def on_streaming_voice_input(self, text):
        self._draft_buffer = text
        self.input_edit.setPlainText(self._draft_buffer)
        
        self.pet.osd_on_streaming(text)

    def on_vad_voice_input(self, text):
        self._draft_buffer += text
        self.input_edit.setPlainText(self._draft_buffer)
        
        self.pet.osd_on_text(text)

    def handle_silence(self):
        if not self._draft_buffer.strip():
            return

        # when llm is busy, keep recording
        if self._llm_busy:
            return

        final_text = self._draft_buffer
        self._draft_buffer = "" 
        self.handle_send(final_text)

    # tts initial
    def init_tts(self, lang: str = "zh_mix", tts_cpu: int = 4, **kwargs,):
        if lang == "en":
            return VitsTTSWorker(self.tts_queue, tts_cpu)
        elif lang == "ja":
            return TonicTTSWorker(self.tts_queue, tts_cpu)
        else:
            return MeloTTSWorker(self.tts_queue, tts_cpu)

    # llm chat event
    def first_greeting(self):
        self.model.add_message("Alice is waking up...", False, 'loading')
        self.chat_view.scrollToBottom()
        self.thinking_index = self.model.rowCount() - 1
        self.set_ui_busy(True)

        messages = init_greeting(**self._custom_config)
        self.llm_queue.put({"type": "chat", "msg": messages})

    def trigger_send_from_button(self):
        text = self.input_edit.toPlainText().strip()
        if text:
            self.handle_send(text)
            self.input_edit.clear()

    def handle_send(self, text: str):
        # ui update 
        self.model.add_message(text, True)
        self.chat_view.scrollToBottom()

        # history update
        self.dialog_manager.add("user", text)

        # waiting ui
        self.model.add_message("Alice thinking...", False, 'loading')
        self.chat_view.scrollToBottom()
        self.thinking_index = self.model.rowCount() - 1
        self.set_ui_busy(True)

        # wait for worker
        messages = self.dialog_manager.build()
        self.llm_queue.put({"type": "chat", "msg": messages})

    def on_llm_emotion(self, emotion):
        self.pet.pet_emotion_change(emotion)

    def on_llm_word(self, word):
        # update chat_view
        if self.model.messages[self.thinking_index]['msg_type'] == 'loading':
            reply_text = ""
            self.model.messages[self.thinking_index]['msg_type'] = 'normal'
        else:
            reply_text = self.model.messages[self.thinking_index]['text']

        reply_text += word
        self.model.messages[self.thinking_index]['text'] = reply_text
        self.model.layoutChanged.emit() 
        self.chat_view.scrollToBottom()

    def on_llm_sentence(self, sentence):
        self.tts_queue.put(sentence)

    def on_llm_reply(self, reply_text):
        # history update
        print(f"Alice: {reply_text}")
        self.dialog_manager.add("assistant", reply_text)

        if self.dialog_manager.need_summurize():
            self.trigger_background_summary()
        else:
            self.set_ui_busy(False)

    def on_llm_error(self, error_msg):
        cur_time = datetime.strftime(datetime.now(), "%Y-%m-%D %H:%M:%S")
        print(f"[{cur_time}] LLM error")
        self.model.add_message(f"[LLM Error] {error_msg}", False, 'system')
        self.model.layoutChanged.emit()
        self.set_ui_busy(False)

    def trigger_background_summary(self, user_status = ""):
        self.pet.pet_on_summary_thinking()

        history_content = self.dialog_manager.build_to_summarize()
        if user_status:
            history_content = f"{history_content}\n\n{user_status}"
        self.llm_queue.put({"type": "summarize", "msg": history_content})

    def on_summary_done(self, new_summary: str):
        self.dialog_manager.update_summary(new_summary)
        cur_time = datetime.strftime(datetime.now(), "%Y-%m-%D %H:%M:%S")
        print(f"[{cur_time}] Summarize done")

        self.pet.pet_on_summary_finish()
        self.set_ui_busy(False)

    def set_ui_busy(self, busy: bool):
        self._llm_busy = busy

        self.input_edit.toggle_send_enabled(not busy)
        self.send_btn.setEnabled(not busy)
    
    # tts to subtitle
    def on_tts_sentence(self, text: str):
        self.pet.osd_on_text(text)

    # input moniter
    def on_reminding(self, message):
        self.tts_queue.put(message)
    
    def on_daily_work_summary(self, work_status):
        self.set_ui_busy(True)
        self.trigger_background_summary(work_status)

    # window action
    def closeEvent(self, e):
        if not self._actually_quit:
            self.show_pet_mode()
            e.ignore()
        else:
            self.moniter.stop()
            self.stop_stt()
            self.llm_worker.stop()
            self.tts_worker.stop()

            self.dialog_manager.close_mem()

            QApplication.quit()

    def show_main_from_tray(self):
        self.pet.hide_system()
        self.showNormal()
        self.activateWindow()

    def show_pet_mode(self):
        self.hide()
        self.pet.show_system()

    def quit_from_tray(self):
        self._actually_quit = True
        self.close()
