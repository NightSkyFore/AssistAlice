import time
from datetime import datetime, date, time as dtime
from PySide6.QtCore import QObject, QThread, Signal
from pynput import mouse, keyboard

WELCOM_MSG = {
    "en": "Welcome back! It's {cur_time}.",
    "ja": "おかえり、今は{cur_time}です。",
    "zh": "欢迎回来，现在是{cur_time}",
    "zh_mix": "欢迎回来，现在是{cur_time}",
}

SLEEP_MSG = {
    "en": "It's {cur_time} now. It's too late to sleep!",
    "ja": "今は{cur_time}です、早く寝ますださい。",
    "zh": "{cur_time}，该去睡觉了。",
    "zh_mix": "{cur_time}，该去睡觉了。",
}

class InputMonitor(QThread):
    # hotkey signal
    toggle_mic_signal = Signal()
    toggle_media_signal = Signal()
    code_clipboard_signal = Signal()
    code_clipboard_quick_signal = Signal()
    # only for TTS reminding
    remind_status_signal = Signal(str)
    # send to LLM
    work_status_signal = Signal(str)

    def __init__(self, lang: str = "en", work_time: str = "9:00", sleep_time: str = "23:30", **kwargs,):
        super().__init__()
        self.is_running = True

        # device input count
        self.key_count = 0
        self.mouse_move_dist = 0
        self.mouse_clicked = False
        self.mouse_scrolled = False

        self.hotkey_handlers = [
            keyboard.HotKey(keyboard.HotKey.parse('<alt>+r'), self.on_hotkey_microphone),
            keyboard.HotKey(keyboard.HotKey.parse('<alt>+c'), self.on_hotkey_clipboard),
            keyboard.HotKey(keyboard.HotKey.parse('<ctrl>+<alt>+c'), self.on_hotkey_clipboard_quick),
            keyboard.HotKey(keyboard.HotKey.parse('<alt>+v'), self.on_hotkey_media),
        ]

        self.status = WorkStatus(lang)
        self.status.rs_internal_signal.connect(self.forward_rs_signal)
        self.status.ws_internal_signal.connect(self.forward_ws_signal)

        self.k_listener = None
        self.m_listener = None

        self.work_time = datetime.strptime(work_time, "%H:%M").time()
        self.sleep_time = datetime.strptime(sleep_time, "%H:%M").time()

    def on_hotkey_microphone(self):
        self.toggle_mic_signal.emit()

    def on_hotkey_clipboard(self):
        self.code_clipboard_signal.emit()

    def on_hotkey_clipboard_quick(self):
        self.code_clipboard_quick_signal.emit()

    def on_hotkey_media(self):
        self.toggle_media_signal.emit()

    def forward_rs_signal(self, msg):
        self.remind_status_signal.emit(msg)

    def forward_ws_signal(self, msg):
        self.work_status_signal.emit(f"### User's Daily Context\n{msg}")

    def on_press(self, key):
        self.key_count += 1
        try:
            if self.k_listener:
                for handler in self.hotkey_handlers:
                    handler.press(self.k_listener.canonical(key))
        except Exception as e:
            print(f"Hotkey press exception: {e}")

    def on_release(self, key):
        try:
            if self.k_listener:
                for handler in self.hotkey_handlers:
                    handler.release(self.k_listener.canonical(key))
        except Exception as e:
            pass

    def on_move(self, x, y):
        self.mouse_move_dist += 1

    def on_click(self, x, y, button, pressed):
        if pressed:
            self.mouse_clicked = True

    def on_scroll(self, x, y, dx, dy):
        self.mouse_scrolled = True

    def run(self):
        self.k_listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.m_listener = mouse.Listener(
            on_move=self.on_move,
            on_click=self.on_click,
            on_scroll=self.on_scroll
        )

        self.k_listener.start()
        self.m_listener.start()

        print("[InputMonitor]Ready...")

        while self.is_running:
            # small steps for 1 min, for every 10 seconds, check if active
            active_step = 0
            for _ in range(60):
                if not self.is_running:
                    break
                active_step += 1
                if active_step >= 10:
                    if self.key_count > 0 or self.mouse_move_dist > 0:
                        self.status.active()
                    active_step = 0
                time.sleep(1)

            cur_datetime = datetime.now()
            self.status.check_too_late(cur_datetime.time(), self.work_time, self.sleep_time)
            self.status.check_cross_day(cur_datetime.date())

            if self.key_count > 20:
                self.status.coding()
            elif self.mouse_move_dist > 100:
                self.status.gaming()
            elif self.key_count > 0 or self.mouse_move_dist > 0 or self.mouse_clicked or self.mouse_scrolled:
                self.status.browsing()
            else:
                self.status.idle()

            self.key_count = 0
            self.mouse_move_dist = 0
            self.mouse_clicked = False
            self.mouse_scrolled = False

    def stop(self):
        self.is_running = False

        if self.k_listener:
            self.k_listener.stop()
        if self.m_listener:
            self.m_listener.stop()
        self.wait()

class WorkStatus(QObject):
    """User work status change

    1. [Coding][Browsing][Gaming]: means in busy, just records time.
    2. [Rest]: When idle for more than 5 min not typing.
    3. [Leaving]: When idle for more than 15min, means user leaving out.

    Trigger interaction:
    1. come back from [Leaving] and be active.
    2. too late to sleep.
    3. when one day is over, return the daily record.
    """
    rs_internal_signal = Signal(str)
    ws_internal_signal = Signal(str)

    def __init__(self, lang: str = "en"):
        super().__init__()
        self.lang = lang if lang in WELCOM_MSG.keys() else "en"
        self.status = "Idle"
        # date
        self.last_record_date = datetime.now().date()
        # work time
        self.coding_time = 0
        self.browsing_time = 0
        self.gaming_time = 0
        self.stay_time = 0
        # alarm
        self.night_alarmed = False

    def idle(self):
        self.stay_time += 1
        if self.status == "Leaving":
            pass
        elif self.stay_time >= 15:
            self.status = "Leaving"
            if self.night_alarmed:
                self.night_alarmed = False

        elif self.stay_time >= 5 and self.status != "Rest":
            self.status = "Rest"

    def active(self):
        if self.status == "Leaving":
            cur_time = datetime.now().strftime("%H:%M:%S")
            msg = WELCOM_MSG[self.lang].format(cur_time=cur_time)
            self.rs_internal_signal.emit(msg)
            self.status = "Idle"

    def coding(self):
        self.coding_time += 1
        self.stay_time = 0
        self.status = "Coding"

    def browsing(self):
        self.browsing_time += 1
        self.stay_time = 0
        self.status = "Browsing"

    def gaming(self):
        self.browsing_time += 1
        self.stay_time = 0
        self.status = "Gaming"

    def check_too_late(self, cur_time: dtime, work_time: dtime, sleep_time: dtime):
        if self.time_late(cur_time, work_time, sleep_time) and not self.night_alarmed and self.status not in ["Leaving", "Rest"]:
            msg = SLEEP_MSG[self.lang].format(cur_time=cur_time.strftime("%H:%M:%S"))
            self.rs_internal_signal.emit(msg)
            self.night_alarmed = True

    def time_late(self, cur_time: dtime, work_time: dtime, sleep_time: dtime) -> bool:
        return (sleep_time > work_time and cur_time > sleep_time) \
            or sleep_time < cur_time < work_time

    def check_cross_day(self, cur_date: date):
        if cur_date > self.last_record_date:
            format_minutes = lambda m: f"{m//60}h {m%60}min" if m >= 60 else f"{m}min"

            coding = format_minutes(self.coding_time)
            browsing = format_minutes(self.browsing_time)
            gaming = format_minutes(self.gaming_time)

            work_status_info = f"[{self.last_record_date.strftime('%Y-%m-%d')}]Coding: {coding} Browsing: {browsing} Gaming: {gaming}"
            print(f"[WorkStatus]\n{work_status_info}")

            self.ws_internal_signal.emit(work_status_info)

            self.coding_time = 0
            self.gaming_time = 0
            self.browsing_time = 0

        self.last_record_date = cur_date
