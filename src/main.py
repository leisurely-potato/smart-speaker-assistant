from __future__ import annotations

from .config import Settings
from .conversation import Conversation
from .llm_client import LLMClient
from .text_to_speech import TextToSpeech


def main() -> None:
    settings = Settings.from_env()
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
    except RuntimeError as exc:
        print(f"启动失败：{exc}")
        return

    print("智能音箱原型已启动。")
    print(f"输入唤醒词“{settings.wake_word}”开始对话，输入 /reset 清空上下文，输入 /exit 退出。")

    awake = False
    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            return

        if not user_input:
            continue

        if user_input == "/exit":
            print("已退出。")
            return

        if user_input == "/reset":
            conversation.reset()
            awake = False
            print("上下文已清空，已回到等待唤醒状态。")
            continue

        if not awake:
            if settings.wake_word in user_input:
                awake = True
                print("助手：我在，请说。")
                tts.say("我在，请说。")
            else:
                print("等待唤醒中。")
            continue

        try:
            answer = conversation.ask(
                user_input,
                wait_notice_seconds=settings.answer_wait_notice_seconds,
                on_wait_notice=lambda: print("助手：正在获取答案，请稍等。"),
            )
        except RuntimeError as exc:
            print(f"错误：{exc}")
            continue

        print(f"助手：{answer}")


if __name__ == "__main__":
    main()
