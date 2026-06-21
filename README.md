# XUnity.AutoTranslator-翻译插件

本项目是 XUnity.AutoTranslator 的自定义翻译服务端，支持调用云端 API 或本地大模型实现游戏文本自动翻译。

## 功能特性

### 核心功能
- **流式接收** — 采用 SSE 流式传输，实时显示翻译结果。
- **和谐检测** — 自动识别文案是否被云服务商拦截，失败后自动切换服务商重试。
- **热重载** — 实时检测 `config.json` 和 `dictionary.json` 变化，无需重启即可更新配置和字典。
- **GUI 控制台** — 图形界面一键启动 llama-server 和翻译服务，实时显示翻译日志。

### 支持的翻译后端
- **本地模型** — 通过 llama-server 运行 GGUF 格式模型，完全离线翻译。
- **云端 API** — 腾讯云、阿里云、DeepSeek 等 OpenAI 兼容接口。
- 可配置多个后端按优先级自动切换。

### 文本处理
- 优化标点符号预处理与还原。
- 动态调整每次翻译请求的 token 上限。
- 自动过滤无意义文本（如单字母、测试字符串）。
- 支持术语字典，固定人名/地名/技能名优先使用字典翻译。

## 准备工作

### 1. 安装依赖

- **Python 3.x**

```bash
pip install Flask gevent openai
```

### 2. 安装 XUnity.AutoTranslator

在目标游戏的 BepInEx 目录下安装 XUnity.AutoTranslator 插件。

## 使用方式

### 方式一：GUI 启动（推荐）

```bash
python gui.py
```

1. 选择 `llama-server.exe` 路径
2. 选择 GGUF 模型文件
3. 调整模型参数（GPU层数、温度等）
4. 点击 **启动 llama-server**
5. 点击 **启动翻译服务**
6. 控制台区域实时显示翻译日志

### 方式二：命令行启动

#### 1. 启动 llama-server

```bash
llama-server.exe -m model.gguf -ngl 100 --temp 0.7 --top-p 0.6 --top-k 20 --repeat-penalty 1.05 -n 4096 --host 127.0.0.1 --port 8080
```

#### 2. 启动翻译服务

```bash
python run_app.py
```

正确运行时应显示：
```
[服务启动]翻译服务在 http://127.0.0.1:4000/translate 上启动
```

### 3. 配置 XUnity.AutoTranslator

修改游戏的 `AutoTranslatorConfig.ini`：

```ini
[Service]
Endpoint=CustomTranslate

[Custom]
Url=http://127.0.0.1:4000/translate
```

## 配置说明

### config.json

```json
{
  "api_keys": {
    "llama": {
      "api_key": "no-key",
      "base_url": "http://127.0.0.1:8080/v1",
      "model_type": "main"
    }
  },
  "model_params": {
    "temperature": 0.3,
    "max_tokens": 0,
    "min_tokens": 30,
    "max_auto_tokens": 500,
    "token_limit_ratio": 2.0,
    "top_p": 0.8
  },
  "api_priority": ["llama"],
  "prompt_user": "翻译游戏英文UI文本为简体中文。",
  "dict_path": "./dictionary.json"
}
```

### 字典 dictionary.json

键为原文，值为译文，5 秒自动热重载：

```json
{
  "Option": "选项",
  "Ability": "技能",
  "Patrol": "巡逻",
  "Unit": "单位"
}
```

### 提示词 prompt_user

可自定义附加提示词，会拼接到系统提示词之后发送给模型：

```json
"prompt_user": "翻译游戏英文UI文本为简体中文。键位名称保持原文。"
```

## 常见问题

### Q: 游戏显示 405 METHOD NOT ALLOWED
`AutoTranslatorConfig.ini` 的 `Endpoint` 必须设为 `CustomTranslate`，`Url` 指向 `http://127.0.0.1:4000/translate`。

### Q: 翻译无响应
1. 检查 llama-server 是否启动并监听 8080 端口
2. 检查翻译服务是否启动并监听 4000 端口
3. 检查防火墙是否放行本地端口

### Q: 翻译质量不佳
1. 调整 `config.json` 中的 `temperature`（0.1~1.0，越低越稳定）
2. 在 `dictionary.json` 中添加固定术语
3. 在 `prompt_user` 中补充翻译规范

### Q: 想使用云端 API 而非本地模型
修改 `config.json` 的 `api_priority` 和 `api_keys`，填入对应平台的 API 密钥即可。

---

通过以上步骤，您可以轻松实现 Unity 游戏文本的自动翻译。如有问题，可使用 AI 大模型（如 DeepSeek、Claude、GPT 等）根据本项目代码快速定位问题并完成客制化需求。
