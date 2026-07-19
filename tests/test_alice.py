import time
from core.alice_ai import AliceAI

if __name__ == "__main__":
    alice = AliceAI(gpu_layer=-1, llm_cpu=4, lang="zh_mix")
    user_messages = []
    start_time = time.time()
    user_messages.append({"role": "user", "content": "how are you today"})
    print(alice.get_response(user_messages))
    end_time = time.time()
    print(f"one-shot time: {end_time - start_time}")
    user_messages.append({"role": "user", "content": "google the latest news."})
    print(alice.get_response(user_messages))
    user_messages.append({"role": "user", "content": "google the gold price"})
    print(alice.get_response(user_messages))
    user_messages.append({"role": "user", "content": "what's the time now?"})
    print(alice.get_response(user_messages))
    user_messages.append({"role": "user", "content": "What's the height of TaiShan?"})
    print(alice.get_response(user_messages))

    # code assist
    code = '''
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
    '''
    code_messages = alice.generate_coding_prompt("具体讲讲这个引用PySide6写代码的作用", code)
    print(alice.get_response(code_messages, "code"))
