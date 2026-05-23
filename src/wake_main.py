from __future__ import annotations

import threading
import time
from contextlib import suppress
from pathlib import Path

from .audio_input import MicrophoneRecorder
from .config import Settings
from .conversation import Conversation
from .llm_client import LLMClient
from .speech_to_text import SpeechToText
from .text_to_speech import TextToSpeech
from .wake_word import WakeWordListener, wake_word_matches


def _transcribe_and_delete(stt: SpeechToText, audio_path: Path) -> str:
    try:
        return stt.transcribe(audio_path)
    finally:
        with suppress(OSError):
            audio_path.unlink()


def _record_user_command(
    recorder: MicrophoneRecorder,
    command_stt: SpeechToText,
    settings: Settings,
) -> str:
    command_audio = recorder.record_to_wav(
        seconds=settings.max_record_seconds,
        silence_timeout_seconds=settings.silence_timeout_seconds,
        silence_rms_threshold=settings.silence_rms_threshold,
    )
    return _transcribe_and_delete(command_stt, command_audio)


def _listen_for_interrupt(
    listener: WakeWordListener,
    interrupt_stt: SpeechToText,
    phrase: str,
    stop_listening: threading.Event,
    interrupt_detected: threading.Event,
) -> None:
    while not stop_listening.is_set() and not interrupt_detected.is_set():
        try:
            audio_path = listener.wait_for_utterance(stop_event=stop_listening)
            if audio_path is None:
                continue
            text = _transcribe_and_delete(interrupt_stt, audio_path)
        except RuntimeError:
            return

        if wake_word_matches(text, phrase):
            interrupt_detected.set()
            return


def _speak_with_interruption(
    tts: TextToSpeech,
    text: str,
    listener: WakeWordListener,
    interrupt_stt: SpeechToText,
    settings: Settings,
) -> bool:
    if not settings.enable_interruption or not tts.enabled:
        tts.say(text)
        return False

    stop_listening = threading.Event()
    interrupt_detected = threading.Event()
    thread = threading.Thread(
        target=_listen_for_interrupt,
        args=(
            listener,
            interrupt_stt,
            settings.interrupt_phrase,
            stop_listening,
            interrupt_detected,
        ),
        daemon=True,
    )
    thread.start()

    try:
        interrupted = tts.say(text, stop_event=interrupt_detected)
    finally:
        stop_listening.set()

    if interrupt_detected.is_set():
        interrupted = True

    return interrupted


def _answer_and_speak(
    user_text: str,
    conversation: Conversation,
    tts: TextToSpeech,
    interrupt_listener: WakeWordListener,
    interrupt_stt: SpeechToText,
    settings: Settings,
) -> bool:
    print(f"你：{user_text}")
    answer = conversation.ask(
        user_text,
        wait_notice_seconds=settings.answer_wait_notice_seconds,
        on_wait_notice=lambda: print("助手：正在获取答案，请稍等。"),
        speak=False,
    )
    print(f"助手：{answer}")
    return _speak_with_interruption(
        tts=tts,
        text=answer,
        listener=interrupt_listener,
        interrupt_stt=interrupt_stt,
        settings=settings,
    )


def _handle_conversation_turns(
    first_user_text: str,
    recorder: MicrophoneRecorder,
    command_stt: SpeechToText,
    conversation: Conversation,
    tts: TextToSpeech,
    interrupt_listener: WakeWordListener,
    interrupt_stt: SpeechToText,
    settings: Settings,
) -> None:
    user_text = first_user_text
    while user_text:
        interrupted = _answer_and_speak(
            user_text=user_text,
            conversation=conversation,
            tts=tts,
            interrupt_listener=interrupt_listener,
            interrupt_stt=interrupt_stt,
            settings=settings,
        )
        if not interrupted:
            return

        print("助手：已打断，请说。")
        if settings.interrupt_tts_settle_seconds > 0:
            time.sleep(settings.interrupt_tts_settle_seconds)
        tts.say("请说。")
        if settings.interrupt_prompt_record_delay_seconds > 0:
            time.sleep(settings.interrupt_prompt_record_delay_seconds)
        user_text = _record_user_command(recorder, command_stt, settings)
        if not user_text:
            print("没有识别到有效语音，回到唤醒监听。")
            return


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
        interrupt_stt = SpeechToText(
            model_name=settings.stt_model,
            language=settings.interrupt_language,
            compute_type=settings.stt_compute_type,
        )
        listener = WakeWordListener(
            recorder=recorder,
            max_seconds=settings.wake_max_seconds,
            silence_seconds=settings.wake_silence_seconds,
            rms_threshold=settings.wake_rms_threshold,
        )
        interrupt_listener = WakeWordListener(
            recorder=recorder,
            max_seconds=settings.interrupt_max_seconds,
            silence_seconds=settings.interrupt_silence_seconds,
            rms_threshold=settings.interrupt_rms_threshold,
        )
    except RuntimeError as exc:
        print(f"启动失败：{exc}")
        return

    print("常驻语音唤醒已启动。")
    print(f"请说 “{settings.wake_word}” 唤醒助手。按 Ctrl+C 退出。")
    if settings.enable_interruption:
        print(f"播报期间可说 “{settings.interrupt_phrase}” 打断。")

    while True:
        try:
            wake_audio = listener.wait_for_utterance()
            if wake_audio is None:
                continue
            wake_text = _transcribe_and_delete(wake_stt, wake_audio)

            if not wake_word_matches(wake_text, settings.wake_word):
                continue

            print("助手：我在，请说。")
            tts.say("我在，请说。")

            user_text = _record_user_command(recorder, command_stt, settings)

            if not user_text:
                print("没有识别到有效语音，回到唤醒监听。")
                continue

            _handle_conversation_turns(
                first_user_text=user_text,
                recorder=recorder,
                command_stt=command_stt,
                conversation=conversation,
                tts=tts,
                interrupt_listener=interrupt_listener,
                interrupt_stt=interrupt_stt,
                settings=settings,
            )

            print(f"已回到唤醒监听。请说 “{settings.wake_word}” 再次唤醒。")
        except KeyboardInterrupt:
            print("\n已退出。")
            return
        except RuntimeError as exc:
            print(f"错误：{exc}")


if __name__ == "__main__":
    main()
