from __future__ import annotations

from pathlib import Path


class SpeechToText:
    def __init__(self, model_name: str, language: str, compute_type: str) -> None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "缺少语音转文字依赖。请先运行 pip install -r requirements.txt。"
            ) from exc

        self.language = language
        self.model = WhisperModel(model_name, device="cpu", compute_type=compute_type)

    def transcribe(self, wav_path: Path) -> str:
        segments, _info = self.model.transcribe(
            str(wav_path),
            language=self.language,
            vad_filter=True,
        )
        return "".join(segment.text for segment in segments).strip()
