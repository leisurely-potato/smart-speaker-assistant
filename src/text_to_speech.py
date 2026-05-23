from __future__ import annotations


class TextToSpeech:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self._engine = None

        if not enabled:
            return

        try:
            import pyttsx3
        except ImportError as exc:
            raise RuntimeError("已开启 ENABLE_TTS，但未安装 pyttsx3。请先运行 pip install -r requirements.txt。") from exc

        self._engine = pyttsx3.init()

    def say(self, text: str) -> None:
        if not self.enabled or self._engine is None:
            return

        self._engine.say(text)
        self._engine.runAndWait()
