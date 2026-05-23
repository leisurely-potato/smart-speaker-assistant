# Smart Speaker Assistant

一个在电脑上运行的本地语音助手项目：常驻监听麦克风中的唤醒关键词，触发后语音回应，并进入连续对话；对话能力通过 OpenAI-compatible API 提供，当前默认使用 Qwen Cloud/DashScope 的 `qwen3.6-flash`。

## 目标

- 程序启动后后台监听麦克风。
- 识别预设唤醒词，例如“你好小智”。
- 唤醒后播放或朗读回应，例如“我在，请说”。
- 录制用户接下来的语音输入。
- 将语音转成文字。
- 调用 Qwen API 生成回答。
- 将回答用语音读出来。
- 支持继续多轮对话，超时后回到唤醒词监听状态。

## 推荐技术路线

优先做 Python 桌面版，原因是麦克风、语音识别、语音合成和 API 调用生态比较完整，适合快速做出可运行原型。

### 核心组件

| 模块 | 推荐方案 | 说明 |
| --- | --- | --- |
| 唤醒词检测 | Porcupine 或 openWakeWord | 本地运行，避免一直把音频上传云端 |
| 麦克风采集 | sounddevice 或 pyaudio | 持续读取电脑麦克风 |
| 语音转文字 | faster-whisper 本地模型，或云端 ASR | 本地更隐私，云端更省电脑性能 |
| 对话模型 | Qwen API | 使用 OpenAI-compatible chat completions 接口 |
| 语音合成 | pyttsx3 本地 TTS，或 Edge TTS | pyttsx3 离线但声音一般，Edge TTS 声音更自然 |
| 配置管理 | .env + pydantic-settings | 保存 API key、唤醒词、模型等配置 |

## Qwen API 设计

Qwen Cloud/DashScope 支持 OpenAI-compatible 的 chat completions 调用方式。规划里建议把大模型接入独立成一个 `llm_client.py`，避免后续替换模型供应商时影响语音主流程。

基础配置：

```env
LLM_PROVIDER=qwen
LLM_API_KEY=你的DashScope API Key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.6-flash
ENABLE_WEB_SEARCH=true
FORCE_WEB_SEARCH=true
SEARCH_STRATEGY=turbo
ANSWER_WAIT_NOTICE_SECONDS=5
```

后续实现时，用类似下面的请求结构：

```python
messages = [
    {"role": "system", "content": "你是一个简洁、可靠的中文语音助手。"},
    {"role": "user", "content": user_text},
]
```

## 程序状态机

程序可以按下面的状态流转：

```text
START
  -> LISTEN_WAKE_WORD
  -> WAKE_ACK
  -> RECORD_USER_SPEECH
  -> SPEECH_TO_TEXT
  -> CALL_LLM
  -> TEXT_TO_SPEECH
  -> WAIT_FOLLOW_UP
  -> RECORD_USER_SPEECH 或 LISTEN_WAKE_WORD
```

关键规则：

- `LISTEN_WAKE_WORD`：只做本地唤醒词检测。
- `WAKE_ACK`：检测到唤醒词后立即语音反馈。
- `RECORD_USER_SPEECH`：开始录音，遇到静音或最长录音时间后停止。
- `WAIT_FOLLOW_UP`：回答后等待几秒，如果用户继续说话就进入下一轮，否则回到唤醒监听。

## 建议目录结构

```text
smart-speaker-assistant/
  README.md
  .env.example
  requirements.txt
  src/
    main.py
    config.py
    audio_input.py
    speech_to_text.py
    llm_client.py
    text_to_speech.py
    voice_main.py
    wake_word.py
    wake_main.py
    conversation.py
  tests/
```

## 当前已实现

当前版本是第一阶段的命令行原型：

- 输入唤醒词后进入对话状态。
- 用户输入文字问题。
- 后台调用 Qwen API。
- 默认启用 Qwen 联网搜索，适合天气、新闻、股票价格等实时问题。
- 输出助手回答。
- 可选使用 `pyttsx3` 朗读回答。
- 支持 `/reset` 清空上下文，`/exit` 退出程序。
- 支持按回车录音，把麦克风语音转成文字后继续调用 Qwen。
- 支持常驻监听唤醒词 `Monster`，唤醒后进入语音对话。

这一步先打通核心对话链路。后续只需要把命令行输入替换成“麦克风录音 + 语音转文字”，把手动唤醒替换成“本地唤醒词检测”。

## 运行方式

复制配置模板：

```bash
cp .env.example .env
```

编辑 `.env`，至少填写：

```env
LLM_API_KEY=你的DashScope API Key
```

运行文字版原型：

```bash
python -m src.main
```

使用方式：

```text
> 你好小智
助手：我在，请说。
> 帮我解释一下什么是向量数据库
助手：...
```

安装语音版依赖：

```bash
pip install -r requirements.txt
```

运行常驻唤醒版，也是日常使用推荐入口：

```bash
python -m src.wake_main
```

常驻唤醒版启动后会持续监听短语音段。你说 `Monster` 后，它会回应“我在，请说”，然后录制你的问题并调用 Qwen。这个入口不需要按回车开始录音。

手动录音调试入口：

```bash
python -m src.voice_main
```

这个入口需要按回车开始录音，适合测试麦克风、转写和大模型调用链路。

检查当前环境是否能看到麦克风：

```bash
python -m src.voice_main --list-audio-devices
```

语音版使用方式：

```text
> 
开始录音，请说话。12 秒后自动停止。
你：今天天气适合做什么
助手：...
```

语音版说明：

- 每次按回车开始录音。
- 默认最多录音 `12` 秒，可在 `.env` 里修改 `MAX_RECORD_SECONDS`。
- 连续 `5` 秒没声音会自动停止本次录音，可在 `.env` 里修改 `SILENCE_TIMEOUT_SECONDS`。
- 如果环境噪音较大导致停不下来，可以调高 `SILENCE_RMS_THRESHOLD`；如果说话太轻容易提前停止，可以调低它。
- 默认使用 `faster-whisper` 的 `small` 模型，本地完成语音转文字。
- 第一次运行可能会下载 Whisper 模型，需要等待一段时间。
- 如果系统拒绝麦克风访问，需要先给终端或 Python 开麦克风权限。
- 在 WSLg 环境中，程序会优先使用 PulseAudio 的 `parecord` 从 Windows 麦克风录音。
- 常驻唤醒版也使用 PulseAudio/PortAudio 的共享录音流，不会主动独占麦克风；其他软件是否能同时使用麦克风还取决于 Windows、驱动和音频服务本身。
- 如果 WSL 里显示没有麦克风设备，先检查 Windows 设置里的麦克风权限，以及 `/mnt/wslg/PulseServer` 是否存在。

如果想开启本地语音朗读：

```bash
pip install -r requirements.txt
```

然后把 `.env` 里的配置改成：

```env
ENABLE_TTS=true
```

## 联网搜索

当前默认开启 Qwen 的联网搜索：

```env
ENABLE_WEB_SEARCH=true
FORCE_WEB_SEARCH=true
SEARCH_STRATEGY=turbo
```

参数含义：

- `ENABLE_WEB_SEARCH=true`：在 Qwen 请求中加入 `enable_search`。
- `FORCE_WEB_SEARCH=true`：强制搜索，避免模型自行判断“不需要联网”。
- `SEARCH_STRATEGY=turbo`：搜索策略，速度优先；需要更全面时可改成 `max` 或 `agent`，但响应会更慢、费用可能更高。
- `ANSWER_WAIT_NOTICE_SECONDS=5`：如果 5 秒还没拿到模型回答，只提示“正在获取答案”，请求不会被取消。

如果你不想每次都联网，可以改成：

```env
ENABLE_WEB_SEARCH=false
```

## 第一版实现范围

第一版不要一次做太复杂，建议按下面顺序落地：

1. 能启动程序并读取麦克风。
2. 用键盘输入模拟唤醒，打通 Qwen API。
3. 接入文字转语音，让助手能读出回答。
4. 接入语音转文字，让用户可以直接说话。
5. 接入本地唤醒词检测。
6. 加入连续对话、超时退出、打断和日志。

这样做可以先验证 Qwen 调用和对话体验，再处理麦克风实时监听这类更容易受系统环境影响的部分。

## 配置项规划

```env
LLM_PROVIDER=qwen
LLM_API_KEY=
DASHSCOPE_API_KEY=
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.6-flash
ENABLE_WEB_SEARCH=true
FORCE_WEB_SEARCH=true
SEARCH_STRATEGY=turbo
ANSWER_WAIT_NOTICE_SECONDS=5

WAKE_WORD=Monster
WAKE_LANGUAGE=en
WAKE_MAX_SECONDS=3
WAKE_SILENCE_SECONDS=1
WAKE_RMS_THRESHOLD=500
LANGUAGE=zh
SAMPLE_RATE=16000
MAX_RECORD_SECONDS=12
SILENCE_TIMEOUT_SECONDS=5
SILENCE_RMS_THRESHOLD=500
FOLLOW_UP_TIMEOUT_SECONDS=8
STT_MODEL=small
STT_COMPUTE_TYPE=int8
TTS_ENGINE=pyttsx3
ENABLE_TTS=false
```

## 风险和注意事项

- 持续监听麦克风涉及隐私，唤醒词检测应优先本地完成。
- 不要把 API key 写进代码或提交到仓库。
- Windows、macOS、Linux 的麦克风权限处理不同，需要分别测试。
- 本地 Whisper 模型会占用 CPU/GPU，低配电脑可以先用云端语音识别。
- 唤醒词误触发是常见问题，需要调阈值和增加确认音效。
- 对话上下文需要限制长度，避免 API 成本失控。

## 下一步

已经完成“文字版语音助手骨架”和“按键录音语音输入版”。接下来建议继续做：

- 加入静音检测，用户说完就自动停止录音。
- 加入本地唤醒词检测。
- 加入回答时打断能力。
