from __future__ import annotations

import sys
from contextlib import suppress

from .audio_input import MicrophoneRecorder
from .config import Settings
from .conversation import Conversation
from .llm_client import LLMClient
from .speech_to_text import SpeechToText
from .text_to_speech import TextToSpeech


def main() -> None:
    settings = Settings.from_env()
    recorder = MicrophoneRecorder(sample_rate=settings.sample_rate)

    if "--list-audio-devices" in sys.argv:
        try:
            devices = recorder.input_devices()
        except RuntimeError as exc:
            print(f"音频设备检查失败：{exc}")
            return

        if not devices:
            print("没有检测到可用麦克风输入设备。")
            return

        print("可用麦克风输入设备：")
        for device in devices:
            print(f"- {device}")
        return

    try:
        client = LLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            enable_web_search=settings.enable_web_search,
            force_web_search=settings.force_web_search,
            search_strategy=settings.search_strategy,
        )
        tts = TextToSpeech(
            enabled=settings.enable_tts,
            engine=settings.tts_engine,
            voice=settings.tts_voice,
            culture=settings.tts_culture,
            rate=settings.tts_rate,
            volume=settings.tts_volume,
        )
        conversation = Conversation(client=client, tts=tts, system_prompt=settings.system_prompt)
        recorder.ensure_input_device()
        stt = SpeechToText(
            model_name=settings.stt_model,
            language=settings.language,
            compute_type=settings.stt_compute_type,
        )
    except RuntimeError as exc:
        print(f"启动失败：{exc}")
        return

    print("语音助手原型已启动。")
    print("按回车开始录音，输入 /reset 清空上下文，输入 /exit 退出。")

    while True:
        try:
            command = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            return

        if command == "/exit":
            print("已退出。")
            return

        if command == "/reset":
            conversation.reset()
            print("上下文已清空。")
            continue

        try:
            wav_path = recorder.record_to_wav(
                seconds=settings.max_record_seconds,
                silence_timeout_seconds=settings.silence_timeout_seconds,
                silence_rms_threshold=settings.silence_rms_threshold,
            )
        except RuntimeError as exc:
            print(f"录音失败：{exc}")
            continue

        try:
            user_text = stt.transcribe(wav_path)
        finally:
            with suppress(OSError):
                wav_path.unlink()

        if not user_text:
            print("没有识别到有效语音。")
            continue

        print(f"你：{user_text}")

        try:
            answer = conversation.ask(
                user_text,
                wait_notice_seconds=settings.answer_wait_notice_seconds,
                on_wait_notice=lambda: print("助手：正在获取答案，请稍等。"),
            )
        except RuntimeError as exc:
            print(f"错误：{exc}")
            continue

        print(f"助手：{answer}")


if __name__ == "__main__":
    main()
