from typing import Tuple, List

SPECIAL_CHARS = [
        '，', '。', '？', '！', '、', '…', '—', '~', '～',
        ',', '.', '?', '!', ' ', '♡'
    ]

PAIRS_TO_CHECK = [
        ("「", "」"),  # 鉤括弧
        ("『", "』"),  # 二重鉤括弧
        ("（", "）"),  # 圆括号
        ("\"", "\""),  # 英文引号（特殊处理）
        ("(", ")"),   # 英文括号
        (""", """)    # 中文引号
    ]

# 将 PAIRS_TO_CHECK 中的每个元组拆分为单个字符并添加到新列表中
new_chars = []
for pair in PAIRS_TO_CHECK:
    new_chars.extend([pair[0], pair[1]])

# 合并两个列表，并去除可能重复的元素
combined_chars = set(SPECIAL_CHARS + new_chars)

def handle_paired_symbols(text: str) -> Tuple[str, List[tuple]]:
    """检测并去除成对符号"""
    removed_symbols = []
    
    while True:
        removed = False
        # 优先检查成对符号（开头和结尾刚好是一对）
        for start_char, end_char in PAIRS_TO_CHECK:
            if text.startswith(start_char) and text.endswith(end_char):
                text = text[len(start_char):-len(end_char)]
                removed_symbols.append(("pair", start_char, end_char))
                removed = True
                break
        if removed:
            continue
            
        # 检查开头单边符号（英文引号特殊处理）
        for start_char, end_char in PAIRS_TO_CHECK:
            if text.startswith(start_char):
                # 英文引号特殊规则
                if start_char == '"':
                    quote_count = text.count('"')
                    if quote_count % 2 == 1:  # 单数则去除
                        text = text[len(start_char):]
                        removed_symbols.append(("start", start_char))
                        removed = True
                        break
                else:
                    # 其他符号保持原规则
                    start_count = text.count(start_char)
                    end_count = text.count(end_char)
                    if start_count > end_count:
                        text = text[len(start_char):]
                        removed_symbols.append(("start", start_char))
                        removed = True
                        break
                        
        # 检查结尾单边符号（英文引号特殊处理）
        for start_char, end_char in PAIRS_TO_CHECK:
            if text.endswith(end_char):
                # 英文引号特殊规则
                if end_char == '"':
                    quote_count = text.count('"')
                    if quote_count % 2 == 1:  # 单数则去除
                        text = text[:-len(end_char)]
                        removed_symbols.append(("end", end_char))
                        removed = True
                        break
                else:
                    # 其他符号保持原规则
                    start_count = text.count(start_char)
                    end_count = text.count(end_char)
                    if end_count > start_count:
                        text = text[:-len(end_char)]
                        removed_symbols.append(("end", end_char))
                        removed = True
                        break
                        
        if not removed:
            break
    
    return text, removed_symbols

def remove_text_special_chars(text: str) -> Tuple[str, List[str], List[str]]:
    """检测句首和句末特殊符号，不做删除，返回完整文本、句首特殊符号列表、句末特殊符号列表"""

    # 检测句首特殊符号
    text_start_special_chars = []
    i = 0
    while i < len(text) and text[i] in combined_chars:
        text_start_special_chars.append(text[i])
        i += 1

    # 检测句末特殊符号
    text_end_special_chars = []
    i = len(text) - 1
    while i >= 0 and text[i] in combined_chars:
        text_end_special_chars.insert(0, text[i])
        i -= 1

    return text, text_start_special_chars, text_end_special_chars


def restore_text_special_chars(
    text: str,
    text_start_special_chars: List[str],
    text_end_special_chars: List[str]
) -> str:
    """去除当前文本句首/句末特殊符号，然后添加指定的句首/句末特殊符号"""

    # 去除现有句首特殊符号
    i = 0
    while i < len(text) and text[i] in combined_chars:
        i += 1
    text = text[i:]

    # 去除现有句末特殊符号
    i = len(text) - 1
    while i >= 0 and text[i] in combined_chars:
        i -= 1
    text = text[:i+1]

    # 添加指定的特殊符号
    text = ''.join(text_start_special_chars) + text + ''.join(text_end_special_chars)
    return text

def restore_paired_symbols(text: str, removed_symbols: List[tuple]) -> str:
    """还原成对符号"""
    # 按相反顺序重新添加符号
    for symbol_info in reversed(removed_symbols):
        if symbol_info[0] == "pair":
            _, start_char, end_char = symbol_info
            text = start_char + text + end_char
        elif symbol_info[0] == "start":
            _, char = symbol_info
            text = char + text
        else:  # "end"
            _, char = symbol_info
            text = text + char
    return text