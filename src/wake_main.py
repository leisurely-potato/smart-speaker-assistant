from __future__ import annotations

from contextlib import suppress

from .audio_input import MicrophoneRecorder
from .config import Settings
from .conversation import Conversation
from .llm_client import LLMClient
from .speech_to_text import SpeechToText
from .text_to_speech import TextToSpeech
from .wake_word import WakeWordListener, wake_word_matches


def main() -> None:
    settings = Settings.from_env()
    recorder = MicrophoneRecorder(sample_rate=settings.sample_rate)

    try:
        client = LLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            enable_web_search=settings.enable_web_search,
            force_web_search=settings.force_web_search,
            search_strategy=settings.search_strategy,
        )
        tts = TextToSpeech(enabled=settings.enable_tts)
        conversation = Conversation(client=client, tts=tts, system_prompt=settings.system_prompt)
        recorder.ensure_input_device()
        wake_stt = SpeechToText(
            model_name=settings.stt_model,
            language=settings.wake_language,
            compute_type=settings.stt_compute_type,
        )
        command_stt = SpeechToText(
            model_name=settings.stt_model,
            language=settings.language,
            compute_type=settings.stt_compute_type,
        )
        listener = WakeWordListener(
            recorder=recorder,
            max_seconds=settings.wake_max_seconds,
            silence_seconds=settings.wake_silence_seconds,
            rms_threshold=settings.wake_rms_threshold,
        )
    except RuntimeError as exc:
        print(f"启动失败：{exc}")
        return

    print("常驻语音唤醒已启动。")
    print(f"请说 “{settings.wake_word}” 唤醒助手。按 Ctrl+C 退出。")

    while True:
        try:
            wake_audio = listener.wait_for_utterance()
            try:
                wake_text = wake_stt.transcribe(wake_audio)
            finally:
                with suppress(OSError):
                    wake_audio.unlink()

            if not wake_word_matches(wake_text, settings.wake_word):
                continue

            print("助手：我在，请说。")
            tts.say("我在，请说。")

            command_audio = recorder.record_to_wav(
                seconds=settings.max_record_seconds,
                silence_timeout_seconds=settings.silence_timeout_seconds,
                silence_rms_threshold=settings.silence_rms_threshold,
            )
            try:
                user_text = command_stt.transcribe(command_audio)
            finally:
                with suppress(OSError):
                    command_audio.unlink()

            if not user_text:
                print("没有识别到有效语音，回到唤醒监听。")
                continue

            print(f"你：{user_text}")
            answer = conversation.ask(
                user_text,
                wait_notice_seconds=settings.answer_wait_notice_seconds,
                on_wait_notice=lambda: print("助手：正在获取答案，请稍等。"),
            )
            print(f"助手：{answer}")
            print(f"已回到唤醒监听。请说 “{settings.wake_word}” 再次唤醒。")
        except KeyboardInterrupt:
            print("\n已退出。")
            return
        except RuntimeError as exc:
            print(f"错误：{exc}")


if __name__ == "__main__":
    main()
