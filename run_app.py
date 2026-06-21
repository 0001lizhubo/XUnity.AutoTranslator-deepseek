import sys
import concurrent.futures
from flask import Flask, request
from gevent.pywsgi import WSGIServer
from queue import Queue
from translation_service import TranslationService

app = Flask(__name__)
translation_service = TranslationService()

executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

@app.route('/translate', methods=['GET'])
def translate():
    """翻译接口（GET，URL参数）"""
    text = request.args.get('text')

    if not text:
        return "缺少text参数", 400

    print(f"\033[36m[原文]\033[0m \033[35m{text}\033[0m")

    translation_queue = Queue()

    future = executor.submit(
        translation_service.handle_translation,
        text,
        translation_queue,
        print_debug=True
    )
    try:
        future.result(timeout=30)
        result = translation_queue.get(timeout=5)

        if result.startswith("[ERROR]"):
            return result, 500

        print(f"\n\033[36m[译文]\033[0m \033[1;32m{result}\n\033[0m")
        return result

    except concurrent.futures.TimeoutError:
        return "[ERROR]翻译超时", 500
    except Exception as e:
        return f"[ERROR]系统错误: {str(e)}", 500

def main():
    print("\033[33m[服务启动]翻译服务在 http://127.0.0.1:4000/translate 上启动\n\033[0m")
    http_server = WSGIServer(('127.0.0.1', 4000), app, log=None, error_log=None)
    http_server.serve_forever()

if __name__ == '__main__':
    main()
