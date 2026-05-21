import time
import datetime
from PySide6.QtCore import QObject, QThread, Signal
from pynput import mouse, keyboard

class InputMonitor(QThread):
    toggle_mic_signal = Signal()
    # only for TTS reminding
    remind_status_signal = Signal(str)
    # send to LLM
    work_status_signal = Signal(str)

    def __init__(self, work_time = "9:00", sleep_time = "0:30", **kwargs,):
        super().__init__()
        self.is_running = True

        # device input count
        self.key_count = 0
        self.mouse_move_dist = 0
        
        self.hotkey_handler = keyboard.HotKey(
            keyboard.HotKey.parse('<alt>+r'),
            self.on_hotkey_triggered
        )
        
        self.k_listener = None
        self.m_listener = None

        self.status = WorkStatus()
        self.status.status_internal_signal.connect(self.forward_status_signal)

        self.work_time = datetime.time.strptime(work_time, "%H:%M")
        self.sleep_time = datetime.time.strptime(sleep_time, "%H:%M")

    def on_hotkey_triggered(self):
        self.toggle_mic_signal.emit()

    def forward_rs_signal(self, msg):
        cur_time = datetime.now().strftime("%H:%M")
        self.remind_status_signal.emit(f"It's {cur_time}. {msg}")

    def forward_ws_signal(self, msg):
        self.work_status_signal.emit(f"### User's Daily Context\n{msg}")

    def on_press(self, key):
        self.key_count += 1
        try:
            if self.k_listener:
                self.hotkey_handler.press(self.k_listener.canonical(key))
        except Exception as e:
            print(f"Hotkey press exception: {e}")

    def on_release(self, key):
        try:
            if self.k_listener:
                self.hotkey_handler.release(self.k_listener.canonical(key))
        except Exception as e:
            pass

    def on_move(self, x, y):
        self.mouse_move_dist += 1

    def run(self):
        self.k_listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.m_listener = mouse.Listener(on_move=self.on_move)
        
        self.k_listener.start()
        self.m_listener.start()

        print("[InputMonitor]Ready")

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
            
            cur_datetime = datetime.datetime.now()
            self.status.check_too_late(cur_datetime.time(), self.work_time, self.sleep_time)
            self.status.check_cross_day(cur_datetime.date())
            
            if self.key_count > 40:
                if self.mouse_move_dist < 500:
                    self.status.coding()
                else:
                    self.status.gaming()
            elif self.key_count > 0 or self.mouse_move_dist > 0:
                self.status.browsing()
            else:
                self.status.idle()
            
            self.key_count = 0
            self.mouse_move_dist = 0

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

    def __init__(self):
        super.__init__()
        self.status = "Idle"
        # date
        self.last_record_date = datetime.datetime.now().date()
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
            self.rs_internal_signal.emit("Welcome back!")

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

    def check_too_late(self, cur_time: datetime.time, work_time: datetime.time, sleep_time: datetime.time):
        if self.time_late(cur_time, work_time, sleep_time) and not self.alarmed and self.status not in ["Leaving", "Rest"]:
            self.rs_internal_signal.emit("It's too late to sleep!")
            self.alarmed = True

    def time_late(cur_time: datetime.time, work_time: datetime.time, sleep_time: datetime.time) -> bool:
        return (sleep_time > work_time and cur_time > sleep_time) \
            or sleep_time < cur_time < work_time

    def check_cross_day(self, cur_date: datetime.date):
        if cur_date > self.last_record_date:
            format_minutes = lambda m: f"{m//60}h {m%60}min" if m >= 60 else f"{m}min"

            coding = format_minutes(self.coding_time)
            browsing = format_minutes(self.browsing_time)
            gaming = format_minutes(self.gaming_time)

            work_status_info = f"[{self.last_record_date.strftime("%Y-%m-%d")}]Coding: {coding} Browsing: {browsing} Gaming: {gaming}"
            print(f"[WorkStatus]\n{work_status_info}")

            self.ws_internal_signal.emit(work_status_info)

            self.coding_time = 0
            self.gaming_time = 0
            self.browsing_time = 0

        self.last_record_date = cur_date
