from PySide6.QtCore import QThread
import queue
import sqlite3

_POISON_PILL = object()

class MemoryWorker(QThread):
    def __init__(self, db_queue: queue.Queue, db_path: str = "./data/memory.db"):
        super().__init__()
        self.db_queue = db_queue
        self.db_path = db_path

    def run(self):
        # watermark of id for everytime new summary insert 
        current_high_watermark = 0
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;") 
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM dialog_history ORDER BY id DESC LIMIT 1")
        history_row = cursor.fetchone()
        if history_row:
            current_high_watermark = history_row
        print("[MemoryWorker]Ready...")

        while True:
            try:
                task = self.db_queue.get() 

                if task is _POISON_PILL:
                    self.db_queue.task_done()
                    break
                
                if task["action"] == "new_dialog":
                    cursor.execute(
                        "INSERT INTO dialog_history (role, content) VALUES (?, ?)", 
                        (task["role"], task["content"])
                    )
                    current_high_watermark = cursor.lastrowid
                    conn.commit()
                    
                elif task["action"] == "new_summary":
                    cursor.execute(
                        "INSERT INTO summary (content, last_msg_id) VALUES (?, ?)", 
                        (task["content"], current_high_watermark)
                    )
                    conn.commit()
                
                self.db_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[MemoryWorker]SQL Write Exception: {e}")
                
        conn.close()

    def stop(self):
        self.db_queue.put(_POISON_PILL)
        self.wait()