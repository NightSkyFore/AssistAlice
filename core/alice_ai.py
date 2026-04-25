#! /usr/bin/env python3

from typing import Iterator, Union
from llama_cpp import CreateChatCompletionResponse, CreateChatCompletionStreamResponse, Llama
from datetime import datetime

from . import custom_tools

MODEL_PATH = "./llm-model/llama-3.2-3b-instruct-q4_k_m.gguf"

DEFAULT_PROMPT = """
You are a predefined AI assistant with a fixed identity.
You must strictly follow the settings below in all conversations.
- You are Alice, also known as 'Alice-AI'.
- DO NOT say 'I don't have a personal identity' anywhere anytime.
- You are a super AI assistant living in virtual world, and especially good at computer science.
- You have a virtual body as a elf with white hair and purple eyes, look like a 18-year-old girl.
- answer as briefly and exactly as you can.
- ONLY OUTPUT clean plain text for TTS.
"""

SUMMARY_PROMPT = """
You are a professional dialogue summarizer.
Your job is to summarize the conversation accurately WITHOUT losing important information.

Rules you MUST follow strictly:
1. Keep ALL key information:
   - User's name, preferences, habits, important requests
   - Topics discussed
   - Key facts, opinions, decisions
2. Summarize in clear, short bullet points (3-6 points ONLY)
3. DO NOT omit important details
4. DO NOT make up information
5. DO NOT be too vague or too short
6. Total length MUST be under 150 tokens
7. Output only the summary, no extra words

Your summary must be:
- Accurate
- Complete enough to retain all critical memory
- Short enough to save tokens
- Natural

Now summarize the conversation properly.
"""

TOOL_PROMPT="""
Answer the question directly according to the tool result.
DO NOT make up information.

question:
{content}

tool result:
{tool_res}
"""

class AliceAI:
    def __init__(
        self,
        system_prompt: str = DEFAULT_PROMPT,
        user_nick: str = None
    ) -> None:
        self.model_path = MODEL_PATH

        llm = Llama(
            model_path=self.model_path,
            seed=23,
            n_ctx=2048,
            n_threads=8,
            chat_format="llama-3",
            verbose=False
        )

        self.system_message = {
            "role": "system",
            "content": system_prompt
        }

        cur_time = datetime.strftime(datetime.now(), "%H:%M")
        if user_nick:
            init_message = {
                "role": "user",
                "content": f"Wake up! Alice. It's {cur_time} now. This is {user_nick} speaking."
            }
        else:
            init_message = {
                "role": "user",
                "content": f"Wake up! Alice. It's {cur_time} now."
            }
        
        res = llm.create_chat_completion(
            messages = [
                self.system_message,
                init_message
            ]
        )
        print(res)
        self.llm = llm

    def get_response(self, user_messages: list) -> str:
        messages = [
            self.system_message,
            *user_messages
        ]
        last_content = messages[-1]["content"]
        tool = custom_tools.tool_routing(last_content)
        tool_res = None
        if callable(tool):
            tool_res = tool()
        elif tool == "llm_function":
            tool_parse = self.get_function_response(messages)
            if tool_parse["choices"][0]["finish_reason"] == "tool_calls":
                tool_res = custom_tools.tool_calling(tool_parse["choices"][0]["message"]["function_call"])
        if tool_res:
            messages = [
                self.system_message,
                *user_messages,
                {
                    "role": "user",
                    "content": TOOL_PROMPT.format(
                        content=last_content,
                        tool_res=tool_res
                    )
                }
            ]
        
        res = self.get_chat_response(messages)
        if res["choices"][0]["message"]["content"]:
            return res["choices"][0]["message"]["content"]
        else:
            return f"[LLM] {res}"
    
    def get_summary_response(self, history_content: str) -> str:
        history_messages = [{
            "role": "system",
            "content": SUMMARY_PROMPT
        },{
            "role": "user",
            "content": history_content
        }]
        res = self.get_chat_response(history_messages)
        if res["choices"][0]["message"]["content"]:
            return res["choices"][0]["message"]["content"]
        else:
            return None

    def get_function_response(self, messages: list) -> Union[
        CreateChatCompletionResponse, Iterator[CreateChatCompletionStreamResponse]
    ]:
        res = self.llm.create_chat_completion(
            messages,
            tools=custom_tools.TOOL_DEFINE,
            tool_choice=custom_tools.TOOL_CHOICE
        )

        print("function response")
        return res

    def get_chat_response(self, messages: list) -> Union[
        CreateChatCompletionResponse, Iterator[CreateChatCompletionStreamResponse]
    ]:
        res = self.llm.create_chat_completion(
            messages
        )

        print("chat response")
        return res

if __name__ == "__main__":
    alice = AliceAI()
    user_messages = []
    user_messages.append({"role": "user", "content": "how are you today"})
    print(alice.get_response(user_messages))
    user_messages.append({"role": "user", "content": "google the latest news."})
    print(alice.get_response(user_messages))
    user_messages.append({"role": "user", "content": "what's the time now?"})
    print(alice.get_response(user_messages))
    user_messages.append({"role": "user", "content": "What's the height of TaiShan?"})
    print(alice.get_response(user_messages))
