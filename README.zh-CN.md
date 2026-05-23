# Smart Speaker Assistant

[English](README.md) | [简体中文](README.zh-CN.md)

一个运行在桌面环境中的本地语音助手。它可以持续监听唤醒词，从麦克风录制语音，在本地完成语音转文字，调用兼容 OpenAI 接口的 Qwen 大模型 API，并可选择启用 Qwen 联网搜索，最后以文字或语音形式返回回答。

默认唤醒词是 `Monster`。

## 功能特性

- 常驻唤醒监听，默认使用 `Monster` 作为唤醒词。
- 在 WSLg 中通过 PulseAudio 共享录音，在原生 Linux 中通过 PortAudio 录音。
- 使用 `faster-whisper` 在本地完成语音转文字。
- 通过 OpenAI-compatible API 接入 Qwen Cloud / DashScope。
- 可选启用 Qwen 联网搜索，用于天气、新闻、行情和其他实时信息。
- 支持静音检测，用户停止说话后自动结束录音。
- 支持配置模型、唤醒词、联网搜索策略、录音时长和扬声器播报。
- 提供文字模式、手动语音模式和常驻唤醒模式，便于调试和日常使用。

## 架构

```text
麦克风
  -> 唤醒词监听
  -> 语音录制
  -> faster-whisper 转写
  -> Qwen-compatible LLM client
  -> 文本回答
  -> 语音播报
```

核心模块：

| 路径 | 说明 |
| --- | --- |
| `src/wake_main.py` | 常驻唤醒语音助手入口 |
| `src/voice_main.py` | 手动语音输入入口 |
| `src/main.py` | 手动文字输入入口 |
| `src/wake_word.py` | 唤醒词监听和匹配 |
| `src/audio_input.py` | 麦克风录音，支持 PulseAudio 和 PortAudio |
| `src/speech_to_text.py` | 本地 Whisper 语音转文字 |
| `src/llm_client.py` | OpenAI-compatible 大模型 API 客户端 |
| `src/conversation.py` | 对话上下文和回答流程 |
| `src/config.py` | 基于环境变量的配置 |

## 环境要求

- Python 3.11 或更高版本。
- 可用的麦克风。
- Qwen Cloud / DashScope API Key。
- 语音输入依赖：
  - `faster-whisper`
  - `sounddevice`
  - `numpy`
- WSLg 麦克风支持：
  - `pulseaudio-utils`
  - `/mnt/wslg/PulseServer`
- 原生 Linux 麦克风支持：
  - PortAudio，例如 Ubuntu/Debian 上的 `portaudio19-dev`。

安装 Python 依赖：

```bash
pip install -r requirements.txt
```

Ubuntu/Debian 系统依赖：

```bash
sudo apt update
sudo apt install portaudio19-dev pulseaudio-utils alsa-utils
```

## 配置

复制环境变量模板：

```bash
cp .env.example .env
```

在 `.env` 中填写 API Key：

```env
LLM_API_KEY=your_dashscope_api_key
```

默认模型配置：

```env
LLM_PROVIDER=qwen
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.6-flash
```

`.env` 已被 git 忽略，不应提交到仓库。

## 运行

推荐入口：常驻唤醒语音助手。

```bash
python -m src.wake_main
```

正常启动后会看到：

```text
常驻语音唤醒已启动。
请说 “Monster” 唤醒助手。按 Ctrl+C 退出。
```

说出 `Monster` 后，助手会回应“我在，请说。”。随后正常说出问题即可。录音会在检测到持续静音后自动结束，然后将转写后的内容发送给 Qwen。

助手播报期间，可以说 `停一下 Monster` 打断当前回答并继续追问。

手动语音模式：

```bash
python -m src.voice_main
```

该模式需要按回车开始录音，适合验证麦克风、语音识别和模型回答链路。

手动文字模式：

```bash
python -m src.main
```

该模式使用键盘输入，适合验证 API 配置和模型调用。

## 音频设备

检查当前环境是否可以看到麦克风：

```bash
python -m src.voice_main --list-audio-devices
```

在 WSLg 中，正常情况下会看到类似输出：

```text
可用麦克风输入设备：
- 2: RDPSource (PulseAudio)
```

程序使用 PulseAudio 或 PortAudio 的共享录音流，不会主动请求独占麦克风。是否能与其他软件同时使用麦克风，仍取决于 Windows 隐私设置、驱动、音频栈和其他应用的行为。

## 联网搜索

Qwen 联网搜索默认开启：

```env
ENABLE_WEB_SEARCH=true
FORCE_WEB_SEARCH=true
SEARCH_STRATEGY=turbo
```

配置项：

| 变量 | 说明 |
| --- | --- |
| `ENABLE_WEB_SEARCH` | 在模型请求中启用 Qwen 搜索能力 |
| `FORCE_WEB_SEARCH` | 强制搜索，而不是让模型自行判断 |
| `SEARCH_STRATEGY` | 搜索策略，常见值包括 `turbo`、`max`、`agent` |
| `ANSWER_WAIT_NOTICE_SECONDS` | 如果回答等待超过该秒数，会打印等待提示 |

关闭联网搜索：

```env
ENABLE_WEB_SEARCH=false
```

## 语音配置

常用音频和唤醒词配置：

```env
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
STT_MODEL=small
STT_COMPUTE_TYPE=int8
```

调参建议：

- 环境噪音较大、录音不容易停止时，可以提高 `WAKE_RMS_THRESHOLD` 或 `SILENCE_RMS_THRESHOLD`。
- 说话声音较轻、容易被当成静音时，可以降低这些阈值。
- 问题较长时，可以提高 `MAX_RECORD_SECONDS`。
- 需要更高转写准确率时，可以把 `STT_MODEL` 换成更大的 Whisper 模型，但会占用更多 CPU 和内存。

## 打断播报

语音播报期间可以使用专门的短语打断当前回答：

```env
ENABLE_INTERRUPTION=true
INTERRUPT_PHRASE=停一下 Monster
INTERRUPT_LANGUAGE=zh
INTERRUPT_MAX_SECONDS=3
INTERRUPT_SILENCE_SECONDS=1
INTERRUPT_RMS_THRESHOLD=500
INTERRUPT_TTS_SETTLE_SECONDS=1.0
INTERRUPT_PROMPT_RECORD_DELAY_SECONDS=0.8
```

打断监听只会在助手正在播报时启用。检测到打断词后，程序会停止当前 TTS 播报，提示“请说”，并开始录制新的问题。

`INTERRUPT_TTS_SETTLE_SECONDS` 用于在打断回答后等待扬声器尾音消失。`INTERRUPT_PROMPT_RECORD_DELAY_SECONDS` 用于在“请说”提示音结束后稍等再开始录音，避免把助手自己的尾音录进下一轮问题。

打断后的追问会使用和第一轮相同的回答流程：先在命令行打印回答，再通过 TTS 播报，并且新的播报仍然可以继续用同一个短语打断。

## 语音朗读

TTS 默认开启：

```env
ENABLE_TTS=true
TTS_ENGINE=auto
TTS_VOICE=
TTS_CULTURE=zh-CN
TTS_RATE=0
TTS_VOLUME=100
```

在 WSL/Windows 环境中，`auto` 会通过 `powershell.exe` 调用 Windows SAPI，回答会从 Windows 默认扬声器播出。`TTS_CULTURE=zh-CN` 会优先选择已安装的中文语音，例如 `Microsoft Huihui Desktop`。在其他环境中，`auto` 会回退到 `pyttsx3`。

关闭语音播报：

```env
ENABLE_TTS=false
```

可用引擎：

| 值 | 说明 |
| --- | --- |
| `auto` | 优先使用 Windows SAPI，否则使用 `pyttsx3` |
| `windows_sapi` | 通过 PowerShell 调用 Windows 内置语音合成 |
| `pyttsx3` | 使用本地 `pyttsx3` 引擎 |

如果要强制指定某个 Windows 语音，把 `TTS_VOICE` 设置为已安装的语音名称。

## 安全说明

- 不要提交 `.env`。
- 如果 API Key 曾经被粘贴到日志、终端、截图或聊天记录中，应及时轮换。
- 唤醒词检测和语音转写在本地运行，但大模型请求会发送到配置的大模型服务商。
- 启用联网搜索时，用户请求可能会进入服务商的搜索和模型上下文。

## 故障排查

### API 返回 `invalid_api_key`

确认 API Key 与 endpoint 匹配：

```env
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

中国大陆 DashScope key 通常使用 `dashscope.aliyuncs.com`。国际版 Qwen Cloud key 可能需要使用国际 endpoint。

### WSL 中检测不到麦克风

检查 WSLg PulseAudio：

```bash
echo $PULSE_SERVER
ls -la /mnt/wslg/PulseServer
pactl list short sources
```

如果没有可用 source，检查 Windows 麦克风隐私权限，并重启 WSL。

### `PortAudio library not found`

安装系统 PortAudio 包：

```bash
sudo apt install portaudio19-dev
```

### 第一次语音转写较慢

`faster-whisper` 首次使用时可能需要下载或初始化模型。后续运行通常会更快。
