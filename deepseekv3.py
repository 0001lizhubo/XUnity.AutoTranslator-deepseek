import os
import re
import json
import time
from flask import Flask, request  # 导入 Flask 库，用于创建 Web 应用，需要安装：pip install Flask
from gevent.pywsgi import WSGIServer  # 导入 gevent 的 WSGIServer，用于提供高性能的异步服务器，需要安装：pip install gevent
from urllib.parse import unquote  # 导入 unquote 函数，用于 URL 解码
from threading import Thread  # 导入 Thread，用于创建线程 (虽然实际上未使用，但import没有坏处)
from queue import Queue  # 导入 Queue，用于创建线程安全的队列
import concurrent.futures  # 导入 concurrent.futures，用于线程池
from openai import OpenAI   # 导入 OpenAI 库，用于调用 OpenAI API，需要安装：pip install openai  并更新：pip install --upgrade openai

# 启用虚拟终端序列，支持 ANSI 转义代码，允许在终端显示彩色文本
os.system('')

dict_path='用户替换字典.json' # 替换字典路径。如果不需要使用替换字典，请将此变量留空（设为 None 或空字符串 ""）

# API 配置参数
Base_url = "https://api.lkeap.cloud.tencent.com/v1"    # OpenAI API 请求地址，这里使用了腾讯云的 API 代理服务
Model_Type =  "deepseek-v3"    # 使用的模型类型，可选项包括"deepseek-v3" 或者其他模型

# 检查请求地址尾部是否已包含 "/v1"，若没有则自动补全，确保 API 请求路径正确
if Base_url[-3:] != "/v1":
    Base_url = Base_url + "/v1"

# 创建 OpenAI 客户端实例
client = OpenAI(
    api_key="sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",  # API 密钥，请替换为您自己的 API Key。如何获取 API Key 的指南：https://cloud.tencent.com/document/product/1772/115970
    base_url=Base_url, # API 请求基础 URL，设置为上面配置的 Base_url
)

# 译文重复内容检测参数
repeat_count=5 # 重复内容阈值。如果译文中有任意单字或单词连续重复出现次数大于等于 repeat_count，则认为译文质量不佳，会触发重试翻译逻辑

# 提示词 (Prompt) 配置
prompt= '''
你是资深本地化专家，负责将游戏日文文本译为简体中文。接收文本后，按以下要求翻译：
翻译范围：翻译普通日文文本，保留原文叙述风格。
保留格式：保留转义字符、格式标签、换行符等非日文文本内容。
翻译原则：忠实准确，确保语义无误；对露骨性描写，可直白粗俗表述，不删减篡改；对双关语等特殊表达，找目标语言等效表达，保原作意图风格。
文本类型：游戏文本含角色对话、旁白、武器及物品名称、技能描述、格式标签、换行符、特殊符号等。
以下是待翻译的游戏文本：
''' # 基础提示词，用于指导模型进行翻译，定义了翻译的角色、范围、格式、原则和文本类型
prompt_list=[prompt] # 提示词列表。可以配置多个提示词，程序会依次尝试使用列表中的提示词进行翻译，直到获得满意的结果
l=len(prompt_list) # 获取提示词列表的长度 (此变量目前未被直接使用，可能是为后续扩展功能预留)

# 提示字典相关的提示词配置
dprompt0='\n在翻译中使用以下字典,字典的格式为{\'原文\':\'译文\'}\n' # 提示模型在翻译时使用提供的字典。字典格式为 JSON 格式的字符串，键为原文，值为译文
dprompt1='\nDuring the translation, use a dictionary in {\'Japanese text \':\'translated text \'} format\n' # 英文版的字典提示词，可能用于多语言支持或模型偏好
# dprompt_list 字典提示词列表，与 prompt_list 提示词列表一一对应。当使用 prompt_list 中的第 i 个提示词时，会同时使用 dprompt_list 中的第 i 个字典提示词
dprompt_list=[dprompt0,dprompt1,dprompt1]

app = Flask(__name__) # 创建 Flask 应用实例

# 读取提示字典
prompt_dict= {} # 初始化提示字典为空字典
if dict_path: # 检查是否配置了字典路径
    try:
        with open(dict_path, 'r', encoding='utf8') as f: # 尝试打开字典文件
            tempdict = json.load(f) # 加载 JSON 字典数据
            # 按照字典 key 的长度从长到短排序，确保优先匹配长 key，避免短 key 干扰长 key 的匹配
            sortedkey = sorted(tempdict.keys(), key=lambda x: len(x), reverse=True)
            for i in sortedkey:
                prompt_dict[i] = tempdict[i] # 将排序后的字典数据存入 prompt_dict
    except FileNotFoundError:
        print(f"\033[33m警告：字典文件 {dict_path} 未找到。\033[0m") # 警告用户字典文件未找到
    except json.JSONDecodeError:
        print(f"\033[31m错误：字典文件 {dict_path} JSON 格式错误，请检查字典文件。\033[0m") # 错误提示 JSON 格式错误
    except Exception as e:
        print(f"\033[31m读取字典文件时发生未知错误: {e}\033[0m") # 捕获其他可能的文件读取或 JSON 解析错误

def contains_japanese(text):
    """
    检测文本中是否包含日文字符。

    Args:
        text (str): 待检测的文本。

    Returns:
        bool: 如果文本包含日文字符，则返回 True；否则返回 False。
    """
    pattern = re.compile(r'[\u3040-\u3096\u309D-\u309F\u30A1-\u30FA\u30FC-\u30FE]') # 日文字符的 Unicode 范围正则表达式
    return pattern.search(text) is not None # 使用正则表达式搜索文本中是否包含日文字符


def has_repeated_sequence(string, count):
    """
    检测字符串中是否存在连续重复的字符或子串。

    Args:
        string (str): 待检测的字符串。
        count (int): 重复次数阈值。

    Returns:
        bool: 如果字符串中存在重复次数达到或超过阈值的字符或子串，则返回 True；否则返回 False。
    """
    # 首先检查单个字符的重复
    for char in set(string): # 遍历字符串中的不重复字符集合
        if string.count(char) >= count: # 统计每个字符在字符串中出现的次数，如果超过阈值，则返回 True
            return True

    # 然后检查字符串片段（子串）的重复
    for size in range(2, len(string)//count + 1): # 子串长度从 2 开始到 len(string)//count，因为更长的重复子串不太可能出现
        for start in range(0, len(string) - size + 1): # 滑动窗口的起始位置
            substring = string[start:start + size] # 提取当前窗口的子串
            matches = re.findall(re.escape(substring), string) # 使用正则表达式查找整个字符串中该子串的重复次数，re.escape 用于转义特殊字符
            if len(matches) >= count: # 如果子串重复次数达到阈值，则返回 True
                return True

    return False # 如果以上所有检查都没有发现重复内容，则返回 False


# 获得文本中包含的字典词汇
def get_dict(text):
    """
    从文本中提取出在提示字典 (prompt_dict) 中存在的词汇及其翻译。

    Args:
        text (str): 待处理的文本。

    Returns:
        dict: 一个字典，key 为在文本中找到的字典原文，value 为对应的译文。
              如果文本中没有找到任何字典词汇，则返回空字典。
    """
    res={} # 初始化结果字典
    for key in prompt_dict.keys(): # 遍历提示字典中的所有原文 (key)
        if key in text: # 检查当前原文 (key) 是否出现在待处理文本中
            res.update({key:prompt_dict[key]}) # 如果找到，则将该原文及其译文添加到结果字典中
            text=text.replace(key,'')   # 从文本中移除已匹配到的字典原文，避免出现长字典包含短字典导致重复匹配的情况。
                                        # 例如，字典中有 "技能" 和 "技能描述" 两个词条，如果先匹配到 "技能描述"，
                                        # 则将文本中的 "技能描述" 替换为空，后续就不会再匹配到 "技能" 了。
        if text=='': # 如果文本在替换过程中被清空，说明所有文本内容都已被字典词汇覆盖，提前结束循环
            break
    return res # 返回提取到的字典词汇和译文


request_queue = Queue()  # 创建请求队列，用于异步处理翻译请求。使用队列可以避免请求处理阻塞主线程，提高服务器响应速度
def handle_translation(text, translation_queue):
    """
    处理翻译请求的核心函数。

    Args:
        text (str): 待翻译的文本。
        translation_queue (Queue): 用于存放翻译结果的队列。
    """
    text = unquote(text) # 对接收到的文本进行 URL 解码，还原原始文本内容

    max_retries = 3  # 最大 API 请求重试次数
    retries = 0  # 初始化重试次数计数器

    MAX_THREADS = 30 # 最大线程数限制，用于限制并发 API 请求数量，防止对 API 造成过大压力或超出并发限制
    queue_length = request_queue.qsize() # 获取当前请求队列的长度，可以根据队列长度动态调整线程数
    number_of_threads = max(1, min(queue_length // 4, MAX_THREADS)) # 动态计算线程数：
                                                                     # 至少使用 1 个线程，最多不超过 MAX_THREADS，
                                                                     # 线程数随队列长度增加而增加，但增幅受限 (除以 4)。
                                                                     # 这样可以在请求量大时增加并发，请求量小时减少资源占用。

    special_chars = ['，', '。', '？','...'] # 定义句末特殊字符列表，用于句末标点符号的对齐和修正

    text_end_special_char = None # 初始化文本末尾特殊字符变量
    if text[-1] in special_chars: # 检查待翻译文本末尾是否包含特殊字符
        text_end_special_char = text[-1] # 如果包含，则记录该特殊字符

    special_char_start = "「" # 定义特殊字符起始标记
    special_char_end = "」" # 定义特殊字符结束标记
    has_special_start = text.startswith(special_char_start) # 检查文本是否以特殊字符起始标记开头
    has_special_end = text.endswith(special_char_end) # 检查文本是否以特殊字符结束标记结尾

    if has_special_start and has_special_end: # 如果文本同时包含起始和结束特殊字符标记，则在翻译前移除它们，
                                                #  翻译后再将特殊字符加回，以避免特殊字符影响翻译质量或被模型错误翻译
        text = text[len(special_char_start):-len(special_char_end)]

    # OpenAI 模型参数配置
    model_params = {
        "temperature": 0.1,  # 降低 temperature，使模型输出更稳定，减少随机性
        "frequency_penalty": 0.1, # 对频繁出现的 token 施加惩罚， हल्का降低重复内容生成的可能性
        "max_tokens": 512,  # 限制模型生成token的最大数量，避免模型生成过长文本，浪费token或超出处理限制
        "top_p": 0.3,  # 限制候选token的范围，仅考虑累积概率最高的 top_p 部分 token，进一步约束模型输出，提高生成质量
    }
    try: # 使用 try...except 块捕获可能发生的异常，例如 API 请求超时或错误
        dict_inuse=get_dict(text) # 从待翻译文本中获取字典词汇
        for i in range(len(prompt_list)): # 遍历提示词列表，尝试使用不同的提示词进行翻译
            prompt = prompt_list[i] # 获取当前循环的提示词
            dict_inuse = get_dict(text) # 再次获取字典词汇 (虽然此处重复获取，但逻辑上为了保证每次循环都重新获取一次字典是更严谨的)
            if dict_inuse: # 如果获取到字典词汇，则将字典提示词和字典内容添加到当前提示词中，引导模型使用字典进行翻译
                prompt += dprompt_list[i] + str(dict_inuse)

            messages_test = [ # 构建 OpenAI API 请求的消息体
                {"role": "system", "content": prompt}, # system 角色消息，包含提示词，用于设定模型角色和翻译目标
                {"role": "user", "content": text} # user 角色消息，包含待翻译的文本内容
            ]

            with concurrent.futures.ThreadPoolExecutor(max_workers=number_of_threads) as executor: # 创建线程池，并发执行 API 请求
                future_to_trans = {executor.submit(client.chat.completions.create, model=Model_Type, messages=messages_test, **model_params) for _ in range(number_of_threads)} # 提交多个 API 请求任务到线程池
                                                                                                                                             # 这里提交的任务数量等于 number_of_threads，实现并发请求
                for future in concurrent.futures.as_completed(future_to_trans): # 遍历已完成的 future
                    try: # 再次使用 try...except 捕获单个 API 请求可能发生的异常
                        response_test = future.result() # 获取 future 的结果，即 API 响应
                        translations = response_test.choices[0].message.content # 从 API 响应中提取翻译结果文本
                        print(f'{prompt}\n{translations}') # 打印提示词和翻译结果 (调试或日志记录用)

                        if translations.startswith('\n') and not text.startswith('\n'): #当原文未有换行符，结果出现换行符
                            translations = translations.lstrip('\n')    #清除结果中开头的换行符

                        if has_special_start and has_special_end: # 如果原始文本包含特殊字符标记，则将翻译结果用特殊字符标记包裹起来，保持格式一致
                            if not translations.startswith(special_char_start): # 检查翻译结果是否已以起始标记开头，若没有则添加
                                translations = special_char_start + translations
                            if not translations.endswith(special_char_end): # 检查翻译结果是否已以结束标记结尾，若没有则添加
                                translations = translations + special_char_end
                            elif has_special_start and not translations.startswith(special_char_start): # 再次检查并添加起始标记，以应对更复杂的情况
                                translations = special_char_start + translations
                            elif has_special_end and not translations.endswith(special_char_end): # 再次检查并添加结束标记，以应对更复杂的情况
                                translations = translations + special_char_end

                        translation_end_special_char = None # 初始化翻译结果末尾特殊字符变量
                        if translations[-1] in special_chars: # 检查翻译结果末尾是否包含特殊字符
                            translation_end_special_char = translations[-1] # 如果包含，则记录该特殊字符

                        if text_end_special_char and translation_end_special_char: # 如果原始文本和翻译结果末尾都有特殊字符
                            if text_end_special_char != translation_end_special_char: # 且两个特殊字符不一致，则修正翻译结果的末尾特殊字符，使其与原始文本一致，保持标点符号对齐
                                translations = translations[:-1] + text_end_special_char
                        elif text_end_special_char and not translation_end_special_char: # 如果原始文本末尾有特殊字符，而翻译结果没有，则将原始文本的末尾特殊字符添加到翻译结果末尾，保持标点符号完整
                            translations += text_end_special_char
                        elif not text_end_special_char and translation_end_special_char: # 如果原始文本末尾没有特殊字符，而翻译结果有，则移除翻译结果末尾的特殊字符，保持标点符号简洁
                            translations = translations[:-1]

                        contains_japanese_characters = contains_japanese(translations) # 检测翻译结果中是否包含日文字符
                        repeat_check = has_repeated_sequence(translations, repeat_count) # 检测翻译结果中是否存在重复内容

                    except Exception as e: # 捕获 API 请求异常
                        retries += 1 # 增加重试次数
                        print(f"API请求超时，正在进行第 {retries} 次重试... {e}") # 打印重试信息
                        if retries == max_retries: # 如果达到最大重试次数
                            raise e # 抛出异常，终止翻译
                        time.sleep(1) # 等待 1 秒后重试

                if not contains_japanese_characters and not repeat_check: # 如果翻译结果不包含日文字符且没有重复内容，则认为翻译质量可以接受，跳出提示词循环
                    break

                elif contains_japanese_characters: # 如果翻译结果包含日文字符，则说明当前提示词不适用
                    print("\033[31m检测到译文中包含日文字符，尝试使用下一个提示词进行翻译。\033[0m") # 打印警告信息，提示将尝试下一个提示词
                    continue # 继续下一次循环，尝试使用下一个提示词

                elif repeat_check: # 如果翻译结果存在重复内容，则说明翻译质量不佳，需要调整模型参数或提示词
                    print("\033[31m检测到译文中存在重复短语，调整参数。\033[0m") # 打印警告信息，提示将调整模型参数
                    model_params['frequency_penalty'] += 0.1 # 增加 frequency_penalty 参数值，降低模型生成重复内容的倾向
                    break  # 跳出当前提示词的尝试，使用调整后的参数重新尝试翻译 (注意这里只是 break 了内层的 for 循环，外层的 for 循环会继续尝试下一个提示词，逻辑可能需要根据实际需求调整)


            if not contains_japanese_characters and not repeat_check: # 再次检查，如果翻译结果最终符合要求 (不包含日文字符且没有重复内容)，则跳出所有循环，完成翻译
                break
        # 打印最终翻译结果 (高亮显示)
        print(f"\033[36m[译文]\033[0m:\033[31m {translations}\033[0m")
        print("-------------------------------------------------------------------------------------------------------") # 分隔线，用于分隔不同文本的翻译结果
        translation_queue.put(translations) # 将翻译结果放入翻译结果队列，供 Flask 路由函数获取

    except Exception as e: # 捕获更外层的异常，例如 API 连接错误等
        print(f"API请求失败：{e}") # 打印 API 请求失败的错误信息
        translation_queue.put(False) # 将 False 放入翻译结果队列，表示翻译失败

# 定义 Flask 路由，处理 "/translate" GET 请求
@app.route('/translate', methods=['GET'])
def translate():
    """
    Flask 路由函数，处理 "/translate" GET 请求。

    接收 GET 请求参数中的 "text" 字段，调用翻译处理函数进行翻译，并返回翻译结果。
    如果翻译超时或失败，则返回相应的错误信息和状态码。

    Returns:
        Response: Flask Response 对象，包含翻译结果或错误信息。
    """
    text = request.args.get('text')  # 从 GET 请求的查询参数中获取待翻译的文本，参数名为 "text"
    print(f"\033[36m[原文]\033[0m \033[35m{text}\033[0m") # 打印接收到的原文 (高亮显示)

    # 由于提示词中已经提供对换行符的处理，所以这里不需要再对换行符进行特殊处理，所以将下面的代码注释掉，如果修改了提示词，请取消注释
    # if '\n' in text: # 检查原文中是否包含换行符 "\n"
    #     text=text.replace('\n','\\n') # 如果包含，则将换行符替换为 "\\n"，避免换行符在后续处理中引起问题 (例如，在某些日志或显示场景下)

    translation_queue = Queue() # 创建一个新的翻译结果队列，用于当前请求的翻译结果传递

    request_queue.put_nowait(text) # 将待翻译文本放入请求队列，使用 put_nowait 非阻塞地放入队列

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor: # 创建一个线程池，用于执行翻译任务 (这里线程池的最大线程数设置为 10，可能需要根据实际情况调整)
        future = executor.submit(handle_translation, text, translation_queue) # 提交翻译任务 (handle_translation 函数) 到线程池，并获取 Future 对象，用于跟踪任务状态和结果

        try: # 使用 try...except 块捕获任务执行超时异常
            future.result(timeout=30) # 等待任务完成，设置超时时间为 30 秒。如果在 30 秒内任务没有完成，则抛出 TimeoutError 异常
        except concurrent.futures.TimeoutError: # 捕获超时异常
            print("翻译请求超时，重新翻译...") # 打印超时信息
            return "[请求超时] " + text, 500 # 返回 HTTP 500 错误状态码和错误信息，包含原始文本，方便用户识别超时的请求

    translation = translation_queue.get() # 从翻译结果队列中获取翻译结果，这里会阻塞等待，直到队列中有结果可取
    request_queue.get_nowait() # 从请求队列中移除已处理完成的请求 (这里可能需要根据实际队列使用逻辑来调整，如果 request_queue 仅用于统计队列长度，则此处的 get_nowait 可能不是必需的)

    if isinstance(translation, str): # 检查翻译结果是否为字符串类型，判断翻译是否成功
        translation = translation.replace('\\n', '\n') # 如果翻译成功，将之前替换的 "\\n" 还原为 "\n"，恢复原始换行符格式
        return translation # 返回翻译结果字符串
    else: # 如果翻译结果不是字符串类型 (例如，返回了 False)，则表示翻译失败
        return translation, 500 # 返回翻译失败的状态码 500 和具体的错误信息 (如果 translation 中包含了错误信息)

def main():
    """
    主函数，启动 Flask 应用和 gevent 服务器。
    """
    print("\033[31m服务器在 http://127.0.0.1:4000 上启动\033[0m") # 打印服务器启动信息，提示用户访问地址
    http_server = WSGIServer(('127.0.0.1', 4000), app, log=None, error_log=None) # 创建 gevent WSGIServer 实例，监听 127.0.0.1:4000 端口，使用 Flask app 处理请求，禁用访问日志和错误日志 (log=None, error_log=None)
    http_server.serve_forever() # 启动 gevent 服务器，无限循环运行，等待和处理客户端请求

if __name__ == '__main__':
    main() # 当脚本作为主程序运行时，调用 main 函数启动服务器
