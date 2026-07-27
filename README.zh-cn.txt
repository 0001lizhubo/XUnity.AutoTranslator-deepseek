# XUnity.AutoTranslator-deepseek

This project implements automatic translation of Japanese text in Unity games by calling Tencent's DeepSeek V3 API.

## Prerequisites

### 1. Get API Key
- Visit the [Tencent Cloud API Console](https://console.cloud.tencent.com/lkeap/api) to apply for a DeepSeek API key (free for a limited time).
- You can also use DeepSeek APIs provided by other platforms.

### 2. Install Dependencies
Ensure the following software and libraries are installed:
- **XUnity.AutoTranslator**
- **Python 3.x**

Install necessary Python libraries:
```bash
pip install Flask gevent openai
```

### 3. Configure API
After cloning this project, modify the `api_key` configuration section in `deepseekv3.py`:
```python
client = OpenAI(
    api_key="sk-XXXXXXXXXXXXXXXXXXXXXX",  # Replace with your API key
    base_url=Base_url,  # API request base URL
)
```

### 4. Customize API Configuration
If you are using APIs and models from other cloud providers, please modify the following configuration:
```python
# API configuration parameters
Base_url = "https://api.lkeap.cloud.tencent.com/v1"  # OpenAI API request address
Model_Type = "deepseek-v3"  # Model type to use
```

## Getting Started

### 1. Start Python Script
Ensure the Python script starts successfully; the command line should display:
```
服务器在 http://127.0.0.1:4000 上启动
```

### 2. Configure XUnity.AutoTranslator
Modify the XUnity.AutoTranslator plugin configuration file `AutoTranslatorConfig.ini` or `Config.ini`:
```ini
[Service]
Endpoint=CustomTranslate

[Custom]
Url=http://127.0.0.1:4000/translate
```

## Reference Projects
- [XUnity.AutoTranslator-Sakura](https://github.com/as176590811/XUnity.AutoTranslator-Sakura)

---

By following the steps above, you can easily implement automatic translation of Japanese text in Unity games. If you have any questions, please refer to the relevant documentation or contact the developer.
