from __future__ import annotations

import audioop
import os
import re
import shutil
import subprocess
import tempfile
import threading
import wave
from contextlib import suppress
from pathlib import Path

from .audio_input import SAMPLE_WIDTH_BYTES, MicrophoneRecorder


CHUNK_SECONDS = 0.1


def wake_word_matches(text: str, wake_word: str) -> bool:
    normalized_text = re.sub(r"[^\w\u4e00-\u9fff]+", "", text.lower())
    normalized_wake = re.sub(r"[^\w\u4e00-\u9fff]+", "", wake_word.lower())
    return bool(normalized_wake and normalized_wake in normalized_text)


class WakeWordListener:
    def __init__(
        self,
        recorder: MicrophoneRecorder,
        max_seconds: int,
        silence_seconds: int,
        rms_threshold: int,
    ) -> None:
        self.recorder = recorder
        self.max_seconds = max_seconds
        self.silence_seconds = silence_seconds
        self.rms_threshold = rms_threshold

    def wait_for_utterance(self, stop_event: threading.Event | None = None) -> Path | None:
        if self._can_use_pulse():
            return self._wait_with_pulse(stop_event=stop_event)
        return self._wait_with_sounddevice(stop_event=stop_event)

    def _can_use_pulse(self) -> bool:
        return bool(os.getenv("PULSE_SERVER")) and shutil.which("parecord") is not None

    def _wait_with_pulse(self, stop_event: threading.Event | None = None) -> Path | None:
        command = [
            "parecord",
            "--record",
            "--raw",
            "--format=s16le",
            f"--rate={self.recorder.sample_rate}",
            f"--channels={self.recorder.channels}",
            "--device=@DEFAULT_SOURCE@",
        ]
        chunk_bytes = max(
            SAMPLE_WIDTH_BYTES * self.recorder.channels,
            int(self.recorder.sample_rate * CHUNK_SECONDS)
            * SAMPLE_WIDTH_BYTES
            * self.recorder.channels,
        )

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            if process.stdout is None:
                raise RuntimeError("无法读取 parecord 输出。")

            chunks = self._collect_speech_chunks(
                lambda: process.stdout.read(chunk_bytes),
                stop_event=stop_event,
            )
        except OSError as exc:
            raise RuntimeError("无法启动 parecord。请确认已安装 pulseaudio-utils。") from exc
        finally:
            if "process" in locals():
                process.terminate()
                with suppress(OSError, subprocess.TimeoutExpired):
                    process.wait(timeout=5)

        if not chunks:
            return None

        return self._write_wav(chunks)

    def _wait_with_sounddevice(self, stop_event: threading.Event | None = None) -> Path | None:
        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("缺少 numpy。请先运行 pip install -r requirements.txt。") from exc

        sd = self.recorder._sounddevice()
        self.recorder.ensure_input_device()
        chunk_frames = max(1, int(self.recorder.sample_rate * CHUNK_SECONDS))

        with sd.InputStream(
            samplerate=self.recorder.sample_rate,
            channels=self.recorder.channels,
            dtype="float32",
        ) as stream:
            chunks = self._collect_speech_chunks(
                lambda: self._read_sounddevice_chunk(stream, chunk_frames, np),
                stop_event=stop_event,
            )

        if not chunks:
            return None

        return self._write_wav(chunks)

    def _read_sounddevice_chunk(self, stream, chunk_frames: int, np) -> bytes:
        audio, _overflowed = stream.read(chunk_frames)
        pcm = np.clip(audio, -1.0, 1.0)
        pcm = (pcm * 32767).astype(np.int16)
        return pcm.tobytes()

    def _collect_speech_chunks(
        self,
        read_chunk,
        stop_event: threading.Event | None = None,
    ) -> list[bytes]:
        chunks: list[bytes] = []
        in_speech = False
        speech_seconds = 0.0
        silent_seconds = 0.0

        while stop_event is None or not stop_event.is_set():
            chunk = read_chunk()
            if not chunk:
                continue

            rms = audioop.rms(chunk, SAMPLE_WIDTH_BYTES)
            chunk_seconds = len(chunk) / (
                self.recorder.sample_rate * self.recorder.channels * SAMPLE_WIDTH_BYTES
            )

            if rms >= self.rms_threshold:
                in_speech = True
                silent_seconds = 0.0
            elif in_speech:
                silent_seconds += chunk_seconds

            if not in_speech:
                continue

            chunks.append(chunk)
            speech_seconds += chunk_seconds

            if silent_seconds >= self.silence_seconds or speech_seconds >= self.max_seconds:
                return chunks

        return chunks

    def _write_wav(self, chunks: list[bytes]) -> Path:
        temp = tempfile.NamedTemporaryFile(prefix="wake-", suffix=".wav", delete=False)
        temp_path = Path(temp.name)
        temp.close()

        with wave.open(str(temp_path), "wb") as wav_file:
            wav_file.setnchannels(self.recorder.channels)
            wav_file.setsampwidth(SAMPLE_WIDTH_BYTES)
            wav_file.setframerate(self.recorder.sample_rate)
            wav_file.writeframes(b"".join(chunks))

        return temp_path
