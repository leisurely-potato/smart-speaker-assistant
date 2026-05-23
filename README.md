# Smart Speaker Assistant

A local voice assistant for desktop environments. It listens for a wake word, records speech from the microphone, transcribes it locally, calls a Qwen-compatible LLM API, optionally uses Qwen web search, and returns spoken or printed responses.

The default wake word is `Monster`.

## Features

- Always-on wake word listener with `Monster` as the default trigger.
- Shared microphone capture through PulseAudio on WSLg or PortAudio on native Linux.
- Local speech-to-text with `faster-whisper`.
- Qwen Cloud / DashScope integration through an OpenAI-compatible chat API.
- Optional Qwen web search for weather, news, market data, and other live information.
- Silence detection for automatic end-of-speech handling.
- Configurable model, wake word, search behavior, recording timeout, and TTS.
- Manual CLI and manual voice modes for debugging.

## Architecture

```text
Microphone
  -> Wake word listener
  -> Speech recorder
  -> faster-whisper transcription
  -> Qwen-compatible LLM client
  -> Text response
  -> Optional text-to-speech
```

Key modules:

| Path | Purpose |
| --- | --- |
| `src/wake_main.py` | Always-on wake word assistant entrypoint |
| `src/voice_main.py` | Manual voice input entrypoint |
| `src/main.py` | Manual text input entrypoint |
| `src/wake_word.py` | Wake word listening and matching |
| `src/audio_input.py` | Microphone recording, PulseAudio and PortAudio backends |
| `src/speech_to_text.py` | Local Whisper transcription |
| `src/llm_client.py` | OpenAI-compatible LLM API client |
| `src/conversation.py` | Conversation context and response flow |
| `src/config.py` | Environment-based configuration |

## Requirements

- Python 3.11 or newer.
- A working microphone.
- A Qwen Cloud / DashScope API key.
- For voice input:
  - `faster-whisper`
  - `sounddevice`
  - `numpy`
- For WSLg microphone support:
  - `pulseaudio-utils`
  - WSLg PulseAudio socket at `/mnt/wslg/PulseServer`
- For native Linux microphone support:
  - PortAudio, for example `portaudio19-dev` on Ubuntu/Debian.

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Ubuntu/Debian system packages:

```bash
sudo apt update
sudo apt install portaudio19-dev pulseaudio-utils alsa-utils
```

## Configuration

Create a local environment file:

```bash
cp .env.example .env
```

Set your API key in `.env`:

```env
LLM_API_KEY=your_dashscope_api_key
```

Default model configuration:

```env
LLM_PROVIDER=qwen
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.6-flash
```

The `.env` file is ignored by git and should not be committed.

## Running

Recommended mode: always-on wake word assistant.

```bash
python -m src.wake_main
```

Expected startup output:

```text
常驻语音唤醒已启动。
请说 “Monster” 唤醒助手。按 Ctrl+C 退出。
```

Say `Monster` to wake the assistant. After it responds with “我在，请说。”, ask your question normally. The recorder stops automatically after sustained silence and then sends the transcribed request to Qwen.

Manual voice mode:

```bash
python -m src.voice_main
```

This mode starts recording after Enter is pressed. It is useful for validating microphone capture, speech recognition, and model responses.

Manual text mode:

```bash
python -m src.main
```

This mode uses keyboard input and is useful for validating API configuration.

## Audio Devices

Check whether the current environment can see a microphone:

```bash
python -m src.voice_main --list-audio-devices
```

On WSLg, a healthy setup typically reports a PulseAudio source such as:

```text
可用麦克风输入设备：
- 2: RDPSource (PulseAudio)
```

The assistant uses shared PulseAudio or PortAudio recording streams. It does not intentionally request exclusive microphone access. Actual simultaneous microphone availability still depends on Windows privacy settings, drivers, the active audio stack, and other applications.

## Web Search

Qwen web search is enabled by default:

```env
ENABLE_WEB_SEARCH=true
FORCE_WEB_SEARCH=true
SEARCH_STRATEGY=turbo
```

Settings:

| Variable | Description |
| --- | --- |
| `ENABLE_WEB_SEARCH` | Adds Qwen search support to model requests |
| `FORCE_WEB_SEARCH` | Forces search instead of letting the model decide |
| `SEARCH_STRATEGY` | Search mode, commonly `turbo`, `max`, or `agent` |
| `ANSWER_WAIT_NOTICE_SECONDS` | Prints a waiting notice if the response takes longer than this many seconds |

Disable web search:

```env
ENABLE_WEB_SEARCH=false
```

## Voice Settings

Common audio and wake word settings:

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

Guidance:

- Increase `WAKE_RMS_THRESHOLD` or `SILENCE_RMS_THRESHOLD` if background noise prevents recording from stopping.
- Decrease those thresholds if quiet speech is missed.
- Increase `MAX_RECORD_SECONDS` for longer questions.
- Change `STT_MODEL` to a larger Whisper model for better transcription accuracy, at the cost of more CPU and memory.

## Text To Speech

Text-to-speech is optional and disabled by default:

```env
ENABLE_TTS=false
```

Enable it:

```env
ENABLE_TTS=true
```

The current implementation uses `pyttsx3`.

## Security

- Do not commit `.env`.
- Rotate any API key that has been pasted into logs, terminals, screenshots, or chat messages.
- Wake word detection and transcription run locally, but LLM requests are sent to the configured API provider.
- Web search may include the user request in provider-side search and model context.

## Troubleshooting

### API returns `invalid_api_key`

Confirm that your API key matches the configured endpoint:

```env
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

China mainland DashScope keys generally use `dashscope.aliyuncs.com`. International Qwen Cloud keys may require the international endpoint.

### No microphone is detected in WSL

Check WSLg PulseAudio:

```bash
echo $PULSE_SERVER
ls -la /mnt/wslg/PulseServer
pactl list short sources
```

If no source is listed, verify Windows microphone privacy permissions and restart WSL.

### `PortAudio library not found`

Install the system PortAudio package:

```bash
sudo apt install portaudio19-dev
```

### First transcription is slow

`faster-whisper` may download or initialize the selected model on first use. Subsequent runs are typically faster.
