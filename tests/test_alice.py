from core.alice_ai import AliceAI

if __name__ == "__main__":
    alice = AliceAI(gpu_layer=10)
    user_messages = []
    user_messages.append({"role": "user", "content": "how are you today"})
    print(alice.get_response(user_messages))
    user_messages.append({"role": "user", "content": "google the latest news."})
    print(alice.get_response(user_messages))
    user_messages.append({"role": "user", "content": "google the gold price"})
    print(alice.get_response(user_messages))
    user_messages.append({"role": "user", "content": "what's the time now?"})
    print(alice.get_response(user_messages))
    user_messages.append({"role": "user", "content": "What's the height of TaiShan?"})
    print(alice.get_response(user_messages))
