from __future__ import annotations

import threading
from collections import deque
from typing import Callable, Deque

from .llm_client import LLMClient, Message
from .text_to_speech import TextToSpeech


class Conversation:
    def __init__(
        self,
        client: LLMClient,
        tts: TextToSpeech,
        system_prompt: str,
        max_turns: int = 8,
    ) -> None:
        self.client = client
        self.tts = tts
        self.system_prompt = system_prompt
        self.history: Deque[Message] = deque(maxlen=max_turns * 2)

    def ask(
        self,
        user_text: str,
        wait_notice_seconds: int = 5,
        on_wait_notice: Callable[[], None] | None = None,
    ) -> str:
        self.history.append({"role": "user", "content": user_text})
        messages: list[Message] = [{"role": "system", "content": self.system_prompt}, *self.history]

        timer = None
        if wait_notice_seconds > 0 and on_wait_notice is not None:
            timer = threading.Timer(wait_notice_seconds, on_wait_notice)
            timer.daemon = True
            timer.start()

        try:
            answer = self.client.chat(messages)
        finally:
            if timer is not None:
                timer.cancel()

        self.history.append({"role": "assistant", "content": answer})
        self.tts.say(answer)
        return answer

    def reset(self) -> None:
        self.history.clear()
