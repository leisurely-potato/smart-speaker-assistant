from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_dotenv(path: Path = PROJECT_ROOT / ".env") -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def _bool_from_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_from_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _float_from_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    llm_provider: str = "qwen"
    llm_api_key: str = ""
    llm_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    llm_model: str = "qwen3.6-flash"
    enable_web_search: bool = True
    force_web_search: bool = True
    search_strategy: str = "turbo"
    answer_wait_notice_seconds: int = 5
    wake_word: str = "Monster"
    wake_language: str = "en"
    wake_max_seconds: int = 3
    wake_silence_seconds: int = 1
    wake_rms_threshold: int = 500
    system_prompt: str = "你是一个简洁、可靠的中文语音助手。回答要适合被朗读。"
    enable_tts: bool = True
    tts_engine: str = "auto"
    tts_voice: str = ""
    tts_culture: str = "zh-CN"
    tts_rate: int = 0
    tts_volume: int = 100
    enable_interruption: bool = True
    interrupt_phrase: str = "停一下 Monster"
    interrupt_language: str = "zh"
    interrupt_max_seconds: int = 3
    interrupt_silence_seconds: int = 1
    interrupt_rms_threshold: int = 500
    interrupt_tts_settle_seconds: float = 1.0
    interrupt_prompt_record_delay_seconds: float = 0.8
    language: str = "zh"
    sample_rate: int = 16000
    max_record_seconds: int = 6
    silence_timeout_seconds: int = 5
    silence_rms_threshold: int = 500
    stt_model: str = "small"
    stt_compute_type: str = "int8"

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        provider = os.getenv("LLM_PROVIDER", cls.llm_provider).strip().lower()
        if provider == "qwen":
            api_key = os.getenv("LLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY", "")
            base_url = os.getenv("LLM_BASE_URL", cls.llm_base_url)
            model = os.getenv("LLM_MODEL", cls.llm_model)
        else:
            api_key = os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY", "")
            base_url = os.getenv("LLM_BASE_URL") or os.getenv(
                "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
            )
            model = os.getenv("LLM_MODEL") or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

        return cls(
            llm_provider=provider,
            llm_api_key=api_key,
            llm_base_url=base_url,
            llm_model=model,
            enable_web_search=_bool_from_env("ENABLE_WEB_SEARCH", cls.enable_web_search),
            force_web_search=_bool_from_env("FORCE_WEB_SEARCH", cls.force_web_search),
            search_strategy=os.getenv("SEARCH_STRATEGY", cls.search_strategy),
            answer_wait_notice_seconds=_int_from_env(
                "ANSWER_WAIT_NOTICE_SECONDS", cls.answer_wait_notice_seconds
            ),
            wake_word=os.getenv("WAKE_WORD", cls.wake_word),
            wake_language=os.getenv("WAKE_LANGUAGE", cls.wake_language),
            wake_max_seconds=_int_from_env("WAKE_MAX_SECONDS", cls.wake_max_seconds),
            wake_silence_seconds=_int_from_env(
                "WAKE_SILENCE_SECONDS", cls.wake_silence_seconds
            ),
            wake_rms_threshold=_int_from_env("WAKE_RMS_THRESHOLD", cls.wake_rms_threshold),
            system_prompt=os.getenv("SYSTEM_PROMPT", cls.system_prompt),
            enable_tts=_bool_from_env("ENABLE_TTS", cls.enable_tts),
            tts_engine=os.getenv("TTS_ENGINE", cls.tts_engine),
            tts_voice=os.getenv("TTS_VOICE", cls.tts_voice),
            tts_culture=os.getenv("TTS_CULTURE", cls.tts_culture),
            tts_rate=_int_from_env("TTS_RATE", cls.tts_rate),
            tts_volume=_int_from_env("TTS_VOLUME", cls.tts_volume),
            enable_interruption=_bool_from_env(
                "ENABLE_INTERRUPTION", cls.enable_interruption
            ),
            interrupt_phrase=os.getenv("INTERRUPT_PHRASE", cls.interrupt_phrase),
            interrupt_language=os.getenv("INTERRUPT_LANGUAGE", cls.interrupt_language),
            interrupt_max_seconds=_int_from_env(
                "INTERRUPT_MAX_SECONDS", cls.interrupt_max_seconds
            ),
            interrupt_silence_seconds=_int_from_env(
                "INTERRUPT_SILENCE_SECONDS", cls.interrupt_silence_seconds
            ),
            interrupt_rms_threshold=_int_from_env(
                "INTERRUPT_RMS_THRESHOLD", cls.interrupt_rms_threshold
            ),
            interrupt_tts_settle_seconds=_float_from_env(
                "INTERRUPT_TTS_SETTLE_SECONDS", cls.interrupt_tts_settle_seconds
            ),
            interrupt_prompt_record_delay_seconds=_float_from_env(
                "INTERRUPT_PROMPT_RECORD_DELAY_SECONDS",
                cls.interrupt_prompt_record_delay_seconds,
            ),
            language=os.getenv("LANGUAGE", cls.language),
            sample_rate=_int_from_env("SAMPLE_RATE", cls.sample_rate),
            max_record_seconds=_int_from_env("MAX_RECORD_SECONDS", cls.max_record_seconds),
            silence_timeout_seconds=_int_from_env(
                "SILENCE_TIMEOUT_SECONDS", cls.silence_timeout_seconds
            ),
            silence_rms_threshold=_int_from_env(
                "SILENCE_RMS_THRESHOLD", cls.silence_rms_threshold
            ),
            stt_model=os.getenv("STT_MODEL", cls.stt_model),
            stt_compute_type=os.getenv("STT_COMPUTE_TYPE", cls.stt_compute_type),
        )
