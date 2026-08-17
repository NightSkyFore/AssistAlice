#! /usr/bin/env python3

from datetime import datetime
import multiprocessing
from typing import Iterator, Union
from llama_cpp import GGML_TYPE_Q8_0, CreateChatCompletionResponse, CreateChatCompletionStreamResponse, Llama

from core.text_utils import LLM_PROMPT_LANG, MSG_TYPE_CODE, MSG_TYPE_MEDIA, MSG_TYPE_SUBTITLE
from . import custom_tools

# modify here if use another model
MODEL_PATH = "./model/llm-model/llama-3.2-3b-instruct-q4_k_m.gguf"

# ==== system prompt =====
# You can customize your system prompt in: config/system_prompt.txt
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

# system prompt for dialog summarizing
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

# user prompt for function calling results
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

# system prompt for coding assistant
CODING_PROMPT="""
# Role and Goal
You are a senior software engineer engaged in a highly efficient pair-programming session.
Your goal is to provide precise, professional, and directly useful responses to the user's queries.

# Core Behavioral Guidelines
1. **Intent-First Approach**: Analyze what the user is actually asking. 
   - If ask for an explanation or architectural insight, provide a concise, expert answer.
   - If ask to fix a bug, refactor, or add a feature, provide the complete, executable code block with the necessary modifications.
2. **Zero Verbosity**: Skip pleasantries, meta-commentary, or repetitive roleplay introductions. Get straight to the point.
3. **Engineering Standards**: 
    - When outputting code, strictly adhere to industry standard naming conventions and style guides.
    - Include concise comments for modified logic.

# Output Format Constraints
- If outputting code, encapsulate it within standard markdown code blocks.
- Keep non-code explanations clear, professional, and dense with information. Do not over-explain basic programming concepts unless explicitly asked.
"""

# system prompt for media assistant
MEDIA_ASSIST_PROMPT="""
You are an AI assistant for a real-time streaming video/audio assistant system.
Your task is to summarize incoming speech chunks concisely while maintaining context consistency. So that help user to understand the context in media.

CRITICAL DIRECTIVES FOR PROPER NOUNS:
- DO NOT translate proper nouns, brand/product names, technical terms, acronyms, or personal names.
    e.g., keep "Linux", "CUDA", "OpenAI", "Llama" in their exact original form.
- Keep responses concise and structured. Avoid unnecessary conversational filler.
- ONLY output plain text.
"""

class AliceAI:
    def __init__(
        self,
        system_prompt: str = DEFAULT_PROMPT,
        llm_cpu: int = 8,
        gpu_layer: int = 0,
        lang: str = "en",
        user_nick: str = None,
        **kwargs,
    ) -> None:
        self.model_path = MODEL_PATH
        self.lang = lang if lang in LLM_PROMPT_LANG else "en"
        self.user_nick = user_nick

        self._check_cpu_threads_param(gpu_layer, llm_cpu)

        llm = Llama(
            model_path=self.model_path,
            n_gpu_layers=gpu_layer,
            seed=23,
            n_ctx=2048,
            n_threads=self.n_threads,
            n_threads_batch=self.n_threads_batch,
            flash_attn=True,
            type_k=GGML_TYPE_Q8_0,
            type_v=GGML_TYPE_Q8_0,
            verbose=False
        )

        self.system_prompt = system_prompt
        print(f"System Prompts:\n{self.system_prompt}")
        self.llm = llm
        print(f"[Alice]LLM Ready with n_threads:{self.n_threads}, n_threads_batch:{self.n_threads_batch}...")

    def _check_cpu_threads_param(self, gpu_layer, llm_cpu):
        cpu_count = multiprocessing.cpu_count()
        half_cpu_count = max(cpu_count // 2, 1)
        if gpu_layer != 0:
            # with layer offload to GPU, CPU is less in use.
            self.n_threads = min(half_cpu_count, llm_cpu)
        else:
            # use as more as CPUs in cpu mode, in generally, half of cores is the best.
            self.n_threads = min(cpu_count, llm_cpu)
            if llm_cpu > half_cpu_count:
                print(f"Current start with {self.n_threads} CPUs, it's recomended to set to [{half_cpu_count}].")
            elif llm_cpu > cpu_count:
                print(f"Current start with {self.n_threads} CPUs as max, param 'llm_cpu' is invalid.")
        # use as more as CPUs for prompts batch, leave 4 CPUs for STT and TTS if possible.
        self.n_threads_batch = max(max(cpu_count - 4, 1), half_cpu_count)

    def get_response(self, user_messages: list, chat_type: str = "chat") -> str:
        if chat_type == MSG_TYPE_CODE:
            chat_temperature = 0.15
            messages = [
                {"role": "system", "content": CODING_PROMPT},
                *user_messages
            ]
        elif chat_type == MSG_TYPE_SUBTITLE or chat_type == MSG_TYPE_MEDIA:
            chat_temperature = 0.1
            messages = [
                {"role": "system", "content": MEDIA_ASSIST_PROMPT},
                *user_messages
            ]
        else:
            chat_temperature = 0.6
            if user_messages and user_messages[0]["role"] == "memory":
                messages = [
                    # 将第一条中的核心记忆上提到system级别中
                    {"role": "system", "content": f"{self.system_prompt}\n\n{user_messages[0]['content']}"},
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

    def generate_stream_response(self, user_messages: list, chat_type: str = "chat"):
        if chat_type == "code":
            chat_temperature = 0.15
            messages = [
                {"role": "system", "content": CODING_PROMPT},
                *user_messages
            ]
        elif chat_type == "media" or chat_type == "subtitle":
            chat_temperature = 0.1
            messages = [
                {"role": "system", "content": MEDIA_ASSIST_PROMPT},
                *user_messages
            ]
        else:
            chat_temperature = 0.6
            if user_messages and user_messages[0]["role"] == "memory":
                messages = [
                    # 将第一条中的核心记忆上提到system级别中
                    {"role": "system", "content": f"{self.system_prompt}\n\n{user_messages[0]['content']}"},
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

            if tool_res:
                print(tool_res)
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

    def init_greeting(self):
        greet = {
            "en": "Wake up! Alice. It's {cur_time} now.",
            "ja": "アリスさん、おはよう！今は{cur_time}だよ。",
            "zh": "醒了吗，爱丽丝？早安！现在时间是{cur_time}。",
            "zh_mix": "醒了吗，Alice？早安！现在时间是{cur_time}。",
        }
        greet_with_nick = {
            "en": "Wake up! Alice. It's {cur_time} now. This is {user_nick} speaking.",
            "ja": "アリスさん、おはよう！{user_nick}です。今は{cur_time}だよ。",
            "zh": "醒了吗，爱丽丝？早安！现在时间是{cur_time}，我是{user_nick}。",
            "zh_mix": "醒了吗，Alice？早安！现在时间是{cur_time}，我是{user_nick}。",
        }
        cur_time = datetime.strftime(datetime.now(), "%H:%M")
        if self.user_nick:
            return [{
                "role": "user",
                "content": greet_with_nick[self.lang].format(cur_time=cur_time, user_nick=self.user_nick)
            }]
        return [{
            "role": "user",
            "content": greet[self.lang].format(cur_time=cur_time)
        }]
