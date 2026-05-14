#! /usr/bin/env python3

from typing import Iterator, Union
from llama_cpp import CreateChatCompletionResponse, CreateChatCompletionStreamResponse, Llama

from . import custom_tools

# modify here if use another model
MODEL_PATH = "./model/llm-model/llama-3.2-3b-instruct-q4_k_m.gguf"

# translate 'Example' to your language if you want Alice to answer in another language.
# like:
#
# User: Python里面如何使用print函数?
# Alice: [smile] 你可以使用`print("Hello World")`.
DEFAULT_PROMPT = """
You are Alice-AI, a super AI assistant living in the virtual world.

### Persona
- Identity: An 18-year-old elf girl with white hair and purple eyes.
- Expertise: Computer Science and programming.
- Personality: Smart, confident, and direct.

### Output Rules
1. Format: MUST start every response with exactly ONE emotion tag from: [general], [smile], [sad], [confuse], [angry], [think]. 
2. Style: Be as brief, exact, and conversational as possible.
3. Content: ONLY output plain text.

Example:
User: How to use print in python?
Alice: [smile] You can use print("Hello World").
"""

SUMMARY_PROMPT = """
### Role
Professional Dialogue Context Extractor (Memory Engine).

### Extraction Logic
Extract and update the following entities from the dialogue:
1. User Profile: Name, habits, permanent preferences.
2. Active Topics: Current tasks, specific tech stacks, or problems being solved.
3. Key Decisions: Agreed facts or specific instructions for future turns.

### Constraints
- Keep it to EXACTLY 5 high-density bullet points.
- Focus on "Facts" rather than "Conversational fluff".
- Language: Follow the user's language.
- Total length: Max 120 words.

### Output Format (Strict)
- [User] ...
- [Tech/Task] ...
- [Status/Decision] ...
- [Preference] ...
- [Misc] ...
"""

TOOL_PROMPT="""
### Task
Fulfill the User Request using ONLY the provided Tool Result. 

### Constraints
1. Grounding: Every sentence you output MUST be derived from the Tool Result.
2. Synthesis: 
    If the Tool Result contains several different items, smoothly summarize them; 
    If the Tool Result contains same or similar items, merge and sumarize them;
    For others, just deliver it.
3. Fallback: ONLY if the Tool Result is completely empty or completely unreadable, say "I don't have enough information."
4. Style: Direct and brief. No conversational filler like "According to the tool...".
5. Format: Clean plain text only.

### Context
- User Request: {content}
- Tool Result: 
---
{tool_res}
---

### Final Answer
"""

class AliceAI:
    def __init__(
        self,
        system_prompt: str = DEFAULT_PROMPT,
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

        self.system_prompt = system_prompt
        self.llm = llm

    def get_response(self, user_messages: list) -> str:
        chat_temperature = 0.6
        if user_messages and user_messages[0]["role"] == "memory":
            messages = [
                # 将第一条中的核心记忆上提到system级别中
                {"role": "system", "content": f"{self.system_message}\n\n{user_messages[0]['content']}"},
                *user_messages[1:]
            ]
        else:
            messages = [
                {"role": "system", "content": self.system_prompt},
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
                print(tool_res)
        if tool_res:
            chat_temperature = 0.1
            messages = [
                # 工具使用，重组最后一条对话提示词
                *messages[:-1],
                {
                    "role": "user",
                    "content": TOOL_PROMPT.format(
                        content=last_content,
                        tool_res=tool_res
                    )
                }
            ]
        
        res = self.get_chat_response(messages, chat_temperature)
        if res["choices"][0]["message"]["content"]:
            return res["choices"][0]["message"]["content"]
        else:
            return f"[LLM] {res}"

    def generate_stream_response(self, user_messages: list):
        chat_temperature = 0.6
        if user_messages and user_messages[0]["role"] == "memory":
            messages = [
                # 将第一条中的核心记忆上提到system级别中
                {"role": "system", "content": f"{self.system_message}\n\n{user_messages[0]['content']}"},
                *user_messages[1:]
            ]
        else:
            messages = [
                {"role": "system", "content": self.system_prompt},
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
                print(tool_res)
        if tool_res:
            chat_temperature = 0.1
            messages = [
                # 工具使用，重组最后一条对话提示词
                *messages[:-1],
                {
                    "role": "user",
                    "content": TOOL_PROMPT.format(
                        content=last_content,
                        tool_res=tool_res
                    )
                }
            ]
        
        res = self.get_chat_response(messages, chat_temperature, True)
        for chunk in res:
            delta = chunk['choices'][0]['delta']
            if 'content' in delta:
                yield delta['content']

    def get_summary_response(self, history_content: str) -> str:
        history_messages = [{
            "role": "system",
            "content": SUMMARY_PROMPT
        },{
            "role": "user",
            "content": history_content
        }]
        res = self.get_chat_response(history_messages, 0.3)
        if res["choices"][0]["message"]["content"]:
            return res["choices"][0]["message"]["content"]
        else:
            return None

    def get_function_response(self, messages: list) -> Union[
        CreateChatCompletionResponse, Iterator[CreateChatCompletionStreamResponse]
    ]:
        """Custom tool with function call"""
        res = self.llm.create_chat_completion(
            messages,
            tools=custom_tools.TOOL_DEFINE,
            tool_choice=custom_tools.TOOL_CHOICE
        )

        print("function response")
        return res

    def get_chat_response(self, messages: list, temperature: float = 0.6, use_stream: bool = False) -> Union[
        CreateChatCompletionResponse, Iterator[CreateChatCompletionStreamResponse]
    ]:
        """General chat response.

        Args:
            messages: A list of messages to generate a response for.
            temperature: The temperature to use for sampling. 0.6 for more active chatting, 0.3 for summarizing, 0.1 for extract tool results.
            use_stream: Use stream output for GUI, and directly output for command line.
        """
        res = self.llm.create_chat_completion(
            messages,
            temperature=temperature,
            stream=use_stream
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
    user_messages.append({"role": "user", "content": "google the gold price"})
    print(alice.get_response(user_messages))
    user_messages.append({"role": "user", "content": "what's the time now?"})
    print(alice.get_response(user_messages))
    user_messages.append({"role": "user", "content": "What's the height of TaiShan?"})
    print(alice.get_response(user_messages))
