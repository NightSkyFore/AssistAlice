from datetime import datetime
import queue

from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QHBoxLayout
from PySide6.QtGui import QFontDatabase
from PySide6.QtCore import QPoint

from core.alice_ai import AliceAI 
from core.asr_nemotron_worker import ASRNemotronWorker
from core.dialog_manager import DialogManager
from core.input_monitor import InputMonitor
from core.llm_worker import LLMWorker
from core.stt_nemotron_worker import NemotronSTTWorker
from core.stt_reazon_worker import ReazonSTTWorker
from core.stt_sense_worker import SenseVoiceSTTWorker
from core.stt_streaming_worker import XASRStreamingWorker
from core.text_utils import MSG_TYPE_CHAT, MSG_TYPE_CODE, MSG_TYPE_MEDIA, MSG_TYPE_SUBTITLE, MSG_TYPE_SUMMARY, PUNCTUATIONS
from core.tts_melo_worker import MeloTTSWorker
from core.tts_play_worker import TTSPlayWorker
from core.tts_tonic_jp_worker import TonicTTSWorker
from core.tts_vits_en_worker import VitsTTSWorker
from ui.code_popup import CodeWidget
from ui.main_ai_show import AIShow
from ui.main_chat_input import ChatInputArea
from ui.main_chat_view import ChatDelegate, ChatListView, MessageModel
from ui.media_subtitle_manager import MediaSubtitleManager
from ui.pet_manager import PetSystemManager
from ui.tray_icon import TrayIcon
from ui.voice_wave import VoiceWaveWidget

class MainWindow(QMainWindow):
    def __init__(self, custom_config: dict = {}):
        super().__init__()
        # ui
        self.setWindowTitle("Alice AI Assistant")
        self.setMinimumSize(900, 600)

        self.pet = PetSystemManager(self)
        self.media = MediaSubtitleManager(self)

        self.tray = TrayIcon(self)
        self.tray.show()
        self.tray.show_main.connect(self.show_main_from_tray)
        self.tray.show_pet.connect(self.show_pet_mode)
        self.tray.tray_quit.connect(self.quit_from_tray)

        self.setup_ui()

        self._custom_config = custom_config
        self._actually_quit = False
        self._llm_busy = False

        self._stt_draft_buffer = ""

        self._source_code = ""
        self._remark_code_response = None

        self._last_subtitle = ""
        self._cur_subtitle = ""

        self.llm_queue = queue.Queue()
        self.tts_queue = queue.Queue()
        self.play_queue = queue.Queue()

        # core 
        self.dialog_manager = DialogManager(**custom_config)

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
        self.media_asr_worker = None

        self.tts_worker = self.init_tts(**custom_config)
        self.tts_worker.tts_sentence_signal.connect(self.on_tts_sentence)
        self.play_worker = TTSPlayWorker(self.play_queue, self.tts_worker.sample_rate)
        self.play_worker.volume_signal.connect(self.wave.set_amplitude)
        self.tts_worker.start()
        self.play_worker.start()

        self.moniter = InputMonitor(**custom_config)
        self.moniter.toggle_mic_signal.connect(self.mic_btn.animateClick)
        self.moniter.toggle_media_signal.connect(self.assist_btn.animateClick)
        self.moniter.code_clipboard_signal.connect(self.on_code_clipboard)
        self.moniter.code_clipboard_quick_signal.connect(self.on_quick_code_clipboard)
        self.moniter.remind_status_signal.connect(self.on_reminding)
        self.moniter.work_status_signal.connect(self.on_daily_work_summary)
        self.moniter.start()

        self.first_greeting()

    def setup_ui(self):
        # main
        main_widget = QWidget(self)
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
        self.chat_view.remark_code_signal.connect(self.on_chat_view_remark)

        # 输入工具栏按钮
        self.mic_btn = QPushButton("🎙️ Mic")
        self.mic_btn.setObjectName("mic_btn")
        self.mic_btn.setCheckable(True)
        self.mic_btn.setFixedHeight(45)
        self.mic_btn.setFixedWidth(100)
        self.mic_btn.clicked.connect(self.toggle_microphone)

        self.assist_btn = QPushButton("🎬 Assist")
        self.assist_btn.setCheckable(True)
        self.assist_btn.setFixedHeight(45)
        self.assist_btn.setFixedWidth(100)
        self.assist_btn.clicked.connect(self.toggle_media_assist)

        self.code_btn = QPushButton("📎 Code")
        self.code_btn.setFixedHeight(45)
        self.code_btn.setFixedWidth(100)
        self.code_btn.clicked.connect(self.toggle_code_popup)

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
            QPushButton:disabled {
                background-color: #FFFFFF;
                color: grey;
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

        self.code_popup = CodeWidget(self)

    # microphone event
    def toggle_microphone(self, checked):
        if checked:
            self.start_stt(**self._custom_config)
        else:
            self.stop_stt()
        self.tray.change_status(checked)

    def start_stt(self, lang: str = "en", stt_cpu: int = 2, **kwargs,):
        if lang == "zh_mix":
            self.stt_worker = XASRStreamingWorker(stt_cpu)
            self.stt_worker.text_signal.connect(self.on_streaming_voice_input)
        elif lang == "en":
            self.stt_worker = NemotronSTTWorker(lang, stt_cpu)
            self.stt_worker.text_signal.connect(self.on_streaming_voice_input)
        elif lang == "ja":
            self.stt_worker = ReazonSTTWorker(stt_cpu)
            self.stt_worker.text_signal.connect(self.on_vad_voice_input)
        else:
            # Note that the pure Chinese as 'zh' and Cantonese as 'yue', using SenseVoice
            self.stt_worker = SenseVoiceSTTWorker(lang, stt_cpu)
            self.stt_worker.text_signal.connect(self.on_vad_voice_input)
 
        self.stt_worker.speech_silence_signal.connect(self.handle_silence)
        self.stt_worker.volume_signal.connect(self.wave.set_amplitude)
        self.stt_worker.start()

    def stop_stt(self):
        if self.stt_worker:
            self.stt_worker.stop()
            self.stt_worker = None

    def on_streaming_voice_input(self, text):
        self._stt_draft_buffer = text
        self.input_edit.setPlainText(self._stt_draft_buffer)

        self.pet.osd_on_streaming(text)

    def on_vad_voice_input(self, text):
        self._stt_draft_buffer += text
        self.input_edit.setPlainText(self._stt_draft_buffer)

        self.pet.osd_on_text(text)

    def handle_silence(self):
        if not self._stt_draft_buffer.strip():
            return

        # clean remain punctuation of the last request
        if self._stt_draft_buffer.strip() in PUNCTUATIONS:
            self._stt_draft_buffer = ""
            return

        # when llm is busy, keep recording
        if self._llm_busy:
            return

        final_text = self._stt_draft_buffer
        self._stt_draft_buffer = "" 
        self.handle_send(final_text)

    # code
    def toggle_code_popup(self):
        if not self.code_popup.isActiveWindow():
            global_pos = self.code_btn.mapToGlobal(QPoint(0, 0))
            self.code_popup.move(global_pos)
            self.code_popup.show()

    def on_chat_view_remark(self, msg: dict, code: str):
        self._remark_code_response = msg
        self.code_popup.set_code(code)

    # media speaker asr event
    def toggle_media_assist(self, checked):
        if checked:
            self.stop_stt()
            if self.mic_btn.isChecked():
                self.mic_btn.setChecked(False)
            self.mic_btn.setEnabled(False)
            self.set_ui_busy(True)
            self.media.show_media_subtitle()
            self.start_media_asr(**self._custom_config)
        else:
            self.stop_media_asr()
            self.media.hide_media_subtitle()
            self.mic_btn.setEnabled(True)
            if self.dialog_manager.has_media_data():
                self.append_llm_loading_msg()
                messages = self.dialog_manager.build_media_final_summarize()
                self.llm_queue.put({"type": MSG_TYPE_MEDIA, "msg": messages})
            else:
                self.set_ui_busy(False)
        self.tray.change_status(checked)

    def start_media_asr(self, stt_cpu: int = 2, **kwargs,):
        self.media_asr_worker = ASRNemotronWorker(stt_cpu=stt_cpu)
        self.media_asr_worker.text_signal.connect(self.on_streaming_media)
        self.media_asr_worker.speech_silence_signal.connect(self.handle_media_silence)
        self.media_asr_worker.volume_signal.connect(self.wave.set_amplitude)
        self.media_asr_worker.start()

    def stop_media_asr(self):
        if self.media_asr_worker:
            self.media_asr_worker.stop()
            self.media_asr_worker = None

    def on_streaming_media(self, text):
        self._cur_subtitle = text
        self.media.osd_on_streaming(f"{self._last_subtitle}, {self._cur_subtitle}")

    def handle_media_silence(self):
        if not self._cur_subtitle.strip():
            return
        self.dialog_manager.add_subtitle(self._cur_subtitle)
        self._last_subtitle = self._cur_subtitle
        self._cur_subtitle = ""

        if self.dialog_manager.need_subtitle_summurize():
            self.append_llm_loading_msg()
            messages = self.dialog_manager.build_media_subtitle_summarize()
            self.llm_queue.put({"type": MSG_TYPE_SUBTITLE, "msg": messages})

    # tts initial
    def init_tts(self, lang: str = "en", tts_cpu: int = 4, **kwargs,):
        if lang == "en":
            return VitsTTSWorker(self.tts_queue, self.play_queue, tts_cpu)
        elif lang == "ja":
            return TonicTTSWorker(self.tts_queue, self.play_queue, tts_cpu)
        else:
            return MeloTTSWorker(self.tts_queue, self.play_queue, tts_cpu)

    # llm chat event
    def first_greeting(self):
        self.model.add_message("Alice is waking up...", False, 'loading')
        self.chat_view.scrollToBottom()
        self.thinking_index = self.model.rowCount() - 1
        self.set_ui_busy(True)

        messages = self.alice.init_greeting()
        self.llm_queue.put({"type": MSG_TYPE_CHAT, "msg": messages})

    def trigger_send_from_button(self):
        text = self.input_edit.toPlainText().strip()
        if text:
            self.handle_send(text)
            self.input_edit.clear()

    def handle_send(self, text: str):
        self._source_code = self.code_popup.get_code()
        self.code_popup.set_code("")
        self.code_btn.setText("📎 Code")

        # ui update 
        show_text = text if text else "code analysis"
        self.model.add_message(show_text, True, source_code=self._source_code)
        self.chat_view.scrollToBottom()

        # waiting ui
        self.append_llm_loading_msg()
        self.set_ui_busy(True)

        if self._source_code:
            # history update
            self.dialog_manager.add("user", show_text, MSG_TYPE_CODE, self._source_code)

            messages = self.dialog_manager.build_coding_prompt(text, self._source_code)
            if self._remark_code_response:
                messages = [self._remark_code_response] + messages
                self._remark_code_response = None
            self.llm_queue.put({"type": MSG_TYPE_CODE, "msg": messages})
        else:
            # history update
            self.dialog_manager.add("user", text)

            # wait for worker
            messages = self.dialog_manager.build()
            self.llm_queue.put({"type": MSG_TYPE_CHAT, "msg": messages})

    def on_llm_emotion(self, emotion):
        self.pet.pet_emotion_change(emotion)

    def on_llm_word(self, word):
        # update chat_view
        self.model.update_message(self.thinking_index, word)
        self.model.layoutChanged.emit() 
        self.chat_view.scrollToBottom()

    def on_llm_sentence(self, sentence):
        # keep TTS in silence when listening to media speaker.
        if self.media_asr_worker:
            self.pet.osd_on_text(sentence)
            return
        self.tts_queue.put(sentence)

    def on_llm_reply(self, reply_type, reply_text):
        # history update
        print(f"Alice: {reply_text}")
        self.dialog_manager.add("assistant", reply_text, reply_type, self._source_code)
        if self._source_code:
            self._source_code = ""

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
        self.llm_queue.put({"type": MSG_TYPE_SUMMARY, "msg": history_content})

    def on_summary_done(self, new_summary: str):
        print(f"Memory Update:\n{new_summary}")
        self.dialog_manager.update_summary(new_summary)
        cur_time = datetime.strftime(datetime.now(), "%Y-%m-%D %H:%M:%S")
        print(f"[{cur_time}] Summarize done")

        self.pet.pet_on_summary_finish()
        self.set_ui_busy(False)
    
    def append_llm_loading_msg(self):
        self.model.add_message("Alice thinking...", False, 'loading', self._source_code)
        self.chat_view.scrollToBottom()
        self.thinking_index = self.model.rowCount() - 1

    def set_ui_busy(self, busy: bool):
        # busy in media listening
        if self.media_asr_worker and not busy:
            return

        self._llm_busy = busy
        self.input_edit.toggle_send_enabled(not busy)
        self.send_btn.setEnabled(not busy)

    # tts to subtitle
    def on_tts_sentence(self, text: str):
        self.pet.osd_on_text(text)

    # input moniter
    def on_reminding(self, message):
        print(message)
        self.tts_queue.put(message)
    
    def on_daily_work_summary(self, work_status):
        self.set_ui_busy(True)
        self.trigger_background_summary(work_status)

    def on_code_clipboard(self):
        text = QApplication.clipboard().text()
        self.code_popup.set_code(text)
        line_count = len(text.split("\n"))
        self.code_btn.setText(f"📎 Code({line_count})")

    def on_quick_code_clipboard(self):
        text = QApplication.clipboard().text()
        self.code_popup.set_code(text)
        self.handle_send("")

    # window action
    def closeEvent(self, e):
        if not self._actually_quit:
            self.show_pet_mode()
            e.ignore()
        else:
            self.moniter.stop()

            self.stop_stt()
            self.stop_media_asr()

            self.llm_worker.stop()
            self.tts_worker.stop()
            self.play_worker.stop()

            self.dialog_manager.close_mem()

            QApplication.quit()

    def show_main_from_tray(self):
        self.pet.hide_pet_mode()
        self.showNormal()
        self.activateWindow()

    def show_pet_mode(self):
        self.hide()
        self.pet.show_pet_mode()

    def quit_from_tray(self):
        self._actually_quit = True
        self.close()
