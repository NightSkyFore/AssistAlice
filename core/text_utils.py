import re
from num2words import num2words

PUNCTUATIONS = set("，。！？；\n!?;,.")

CJK_RANGE = [
    (0x3040, 0x309F),  # 平假名
    (0x30A0, 0x30FF),  # 片假名
    (0x4E00, 0x9FFF),  # 汉字 (CJK Unified Ideographs)
    (0x3400, 0x4DBF),  # 汉字扩展 A
    (0x20000, 0x2A6DF),  # 汉字扩展 B
    # 可以根据需要添加其他汉字扩展范围
]

def is_cjk_char(char) -> bool:
    char_code = ord(char)
    for s, e in CJK_RANGE:
        if s <= char_code <= e:
            return True
    return False


# ==== Number Process ====
DIGIT_SET = set("1234567890")

def text_contains_number(text: str) -> bool:
    return any(ch in DIGIT_SET for ch in text)

NUM_CLEAN_REG = re.compile(
    r"(?<!\d)(\d{1,3}(?:,\d{3})+|\d{1,4}(?: \d{4})+)(?:\.\d+)?(?!\d)"
)

# 使用 (?P<name>...) 为每种匹配类型命名
NUM_SEMANTIC_REG = re.compile(
    r"(?P<cur_pre>[$¥£€￥]\s*\d+(?:\.\d+)?)|"       # $12.50
    r"(?P<cur_suf>\d+(?:\.\d+)?\s*[$¥£€￥])|"       # 12.50$
    r"(?P<num>(?<![\d.])\d+(?:\.\d+)?(?![\d.]))"    # just number: 12.50
)

CURRENCY_MAP = {
    "zh": {"$": "美刀", "¥": "元", "￥": "元", "£": "英镑", "€": "欧元"},
    "ja": {"$": "ドル", "¥": "円", "￥": "円", "£": "ポンド", "€": "ユーロ"},
    "en": {"$": " dollars", "¥": " yuan", "￥": " yuan", "£": " pounds", "€": " euros"}
}

def semantic_replacer(match, target_lang):
    group_dict = match.groupdict()

    cur_text = group_dict.get('cur_pre') or group_dict.get('cur_suf')
    if cur_text:
        sym = re.search(r'[$¥£€￥]', cur_text).group()
        num_str = re.search(r'\d+(?:\.\d+)?', cur_text).group()
        currency_word = CURRENCY_MAP[target_lang].get(sym, sym)
        if target_lang == 'zh':
            return f"{num_str}{currency_word}"
        try:
            return f"{num2words(num_str, lang=target_lang)}{currency_word}"
        except:
            return f"{num_str}{currency_word}"

    if group_dict.get('num'):
        num_str = match.group('num')
        return num_str if target_lang == 'zh' else num2words(num_str, lang=target_lang)

    return match.group(0)

def formating_number_in_text(text: str, lang: str = 'en') -> str:
    lang = 'en' if lang not in CURRENCY_MAP else lang
    text = NUM_CLEAN_REG.sub(lambda m: m.group(0).replace(",", "").replace(" ", ""), text)
    return NUM_SEMANTIC_REG.sub(lambda m: semantic_replacer(m, lang), text)


# ==== Time Process for Chinese ====
TIME_SEMANTIC_REG = re.compile(
    r"(?P<hms>\d{1,2}\:\d{1,2}\:\d{1,2})|"
    r"(?P<hm>\d{1,2}\:\d{1,2})"
)
def timer_replacer(match):
    group_dict = match.groupdict()
    cur_text = group_dict.get('hms')
    if cur_text:
        time_num_list = cur_text.split(':')
        return f"{time_num_list[0]}点{time_num_list[1]}分{time_num_list[2]}秒"
    cur_text = group_dict.get('hm')
    if cur_text:
        time_num_list = cur_text.split(':')
        return f"{time_num_list[0]}、{time_num_list[1]}"
       
    return match.group(0) 

def formating_time_in_text(text: str) -> str:
    return TIME_SEMANTIC_REG.sub(lambda m: timer_replacer(m), text)


# ==== Date or Score or Subtraction for Chinese ====
HYPHEN_SEMANTIC_REG = re.compile(
    r"(?P<date>\d{1,4}\-\d{1,2}\-\d{1,2})|"
    r"(?P<sub>(?<![\d.])(-?\d+(?:\.\d+)?)(?![\d.])\-(?<![\d.])(-?\d+(?:\.\d+)?)(?![\d.])(?==))|"
    r"(?P<score>\d+\-\d+)"
)

def hyphen_replacer(match):
    group_dict = match.groupdict()
    cur_text = group_dict.get('date')
    if cur_text:
        num_list = cur_text.split('-')
        if int(num_list[1]) > 12:
            return f"{num_list[0]}年{num_list[2]}月{num_list[1]}日"
        return f"{num_list[0]}年{num_list[1]}月{num_list[2]}日"
    cur_text = group_dict.get('sub')
    if cur_text:
        num_list = cur_text.split('-')
        return f"{num_list[0]}减{num_list[1]}"
    cur_text = group_dict.get('score')
    if cur_text:
        num_list = cur_text.split('-')
        return f"{num_list[0]}杠{num_list[1]}"
       
    return match.group(0) 

def formating_hyphen_in_text(text: str) -> str:
    return HYPHEN_SEMANTIC_REG.sub(lambda m: hyphen_replacer(m), text)

# ==== Slash for Chinese ====
SLASH_SEMANTIC_REG = re.compile(
    r"(?P<div>(?<![\d.])(-?\d+(?:\.\d+)?)(?![\d.])\/(?<![\d.])(-?\d+(?:\.\d+)?)(?![\d.]))|"
    r"(?P<per>\/(?=[A-Za-z]{1,5}))"
)

def slash_replacer(match):
    group_dict = match.groupdict()
    cur_text = group_dict.get('div')
    if cur_text:
        num_list = cur_text.split('/')
        return f"{num_list[0]}除以{num_list[1]}"
    cur_text = group_dict.get('per')
    if cur_text:
        return "每"
       
    return match.group(0) 

def formating_slash_in_text(text: str) -> str:
    return SLASH_SEMANTIC_REG.sub(lambda m: slash_replacer(m), text)

# ==== Percent for Chinese ====
PERCENT_SEMANTIC_REG = re.compile(
    r"(?<![\d.])(-?\d+(?:\.\d+)?)(?![\d.])\%"
)

def formating_percent_in_text(text: str) -> str:
    return PERCENT_SEMANTIC_REG.sub(lambda m: f"百分之{m[1]}", text)


# ==== Punc for Chinese ====
PUNCT_MAP = {
    "：": "、",
    "——": "、",
    "；": "，",
}
def punctuations_clean(text: str) -> str:
    for k, v in PUNCT_MAP.items():
        text = text.replace(k, v)
    return text


def preprocess_text_for_zh_TTS(text):
    if text_contains_number(text):
        text = formating_number_in_text(text, "zh")
    if ":" in text:
        text = formating_time_in_text(text)
    if "-" in text:
        text = formating_hyphen_in_text(text)
    if "/" in text:
        text = formating_slash_in_text(text)
    if "%" in text:
        text = formating_percent_in_text(text)
    return punctuations_clean(text)


if __name__ == "__main__":
    t1 = "This is a string that contains '中文‘ and 'おはよ' to be test"
    i = 0
    for c in t1:
        if is_cjk_char(c):
            i += 1
    print(f"{t1}\n\tcjk count: {i}")

    t2 = "这是一段包含格式化数字 45,321.40 的字符串"
    print(formating_number_in_text(t2))
    t3 = "这是一段包含格式化数字 4 5321 0000.40 的字符串"
    print(formating_number_in_text(t3))
    t4 = "price is $3,245.40"
    print(formating_number_in_text(t4))
    t5 = "1 2000 3234.60￥"
    print(formating_number_in_text(t5, 'zh'))
    print(formating_number_in_text(t5, 'ja'))
    t6 = "1:09:10"
    print(formating_time_in_text(t6))
    t7 = "2026-7-24 2:01:13"
    print(formating_hyphen_in_text(formating_time_in_text(t7)))
    t8 = "24.3-12="
    print(formating_hyphen_in_text(t8))
    t9 = "比分是3-1"
    print(formating_hyphen_in_text(t9))
    t10 = "24/4的结果是6"
    print(formating_slash_in_text(t10))
    t11 = "价格是 10$/g。"
    print(formating_slash_in_text(t11))
    t12 = "含量为10.8%"
    print(formating_percent_in_text(t12))