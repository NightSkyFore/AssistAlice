from PySide6.QtCore import QThread
import queue
import sqlite3

class MemoryWorker(QThread):
    def __init__(self, db_queue: queue.Queue, db_path: str = "./data/memory.db"):
        super().__init__()
        self.db_queue = db_queue
        self.db_path = db_path
        self.is_running = False

    def run(self):
        self.is_running = True
        # watermark of id for everytime new summary insert 
        current_high_watermark = 0
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;") 
        cursor = conn.cursor()
        print("MemoryWorker Ready...")

        while self.is_running:
            try:
                task = self.db_queue.get(timeout=1.0) 
                
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
        self.is_running = False
        self.wait()