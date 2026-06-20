#! /usr/python
import os
import sys
from llama_cpp import GGML_TYPE_Q8_0, Llama

MODEL_PATH = "./model/llm-model/llama-3.2-3b-instruct-q4_k_m.gguf"

if __name__ == "__main__":
    llm = Llama(
            model_path=MODEL_PATH,
            n_gpu_layers=-1,
            seed=23,
            n_ctx=2048,
            n_threads=8,
            n_threads_batch=8,
            flash_attn=True,
            chat_format="llama-3",
            type_k=GGML_TYPE_Q8_0,
            type_v=GGML_TYPE_Q8_0,
            verbose=True
        )

    messages = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]
    
    while True:
        user_input = input("> ").strip()

        if not user_input:
            continue
        
        messages.append({"role": "user", "content": user_input})
        
        full_response = ""
        stream = llm.create_chat_completion(
            messages=messages,
            stream=True,
            max_tokens=512,
            temperature=0.7,
            top_p=0.9,
        )
        
        for chunk in stream:
            if 'choices' in chunk and len(chunk['choices']) > 0:
                delta = chunk['choices'][0].get('delta', {})
                content = delta.get('content', '')
                if content:
                    print(content, end="", flush=True)
                    full_response += content
        
        print("")
        
        if full_response:
            messages.append({"role": "assistant", "content": full_response})
