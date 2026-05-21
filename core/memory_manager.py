import os
import sqlite3

class MemoryManager:
    def __init__(self, db_path: str = "./data/memory.db"):
        self.db_path = db_path
        if not os.path.isfile(self.db_path):
            self.init_memory()

    def init_memory(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dialog_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                last_msg_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        print("Memory Ready...")

    def load_memory(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT content, last_msg_id FROM summary ORDER BY id DESC LIMIT 1")
        summary_row = cursor.fetchone()
        
        summary_text = ""
        last_id = 0
        if summary_row:
            summary_text, last_id = summary_row

        # load dialog according to last_msg_id
        cursor.execute(
            "SELECT role, content FROM dialog_history WHERE id > ? ORDER BY id ASC", 
            (last_id,)
        )
        last_hist = [{"role": r, "content": c} for r, c in cursor.fetchall()]
        
        conn.close()
        return summary_text, last_hist 
    