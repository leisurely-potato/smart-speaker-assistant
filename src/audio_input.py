from __future__ import annotations

import tempfile
import audioop
import os
import shutil
import subprocess
import wave
from contextlib import suppress
from pathlib import Path


SAMPLE_WIDTH_BYTES = 2
CHUNK_SECONDS = 0.1


class MicrophoneRecorder:
    def __init__(self, sample_rate: int, channels: int = 1) -> None:
        self.sample_rate = sample_rate
        self.channels = channels

    def _sounddevice(self):
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError(
                "缺少麦克风录音依赖。请先运行 pip install -r requirements.txt。"
            ) from exc
        except OSError as exc:
            raise RuntimeError(
                "缺少系统级 PortAudio 库。Ubuntu/Debian 可运行：sudo apt install portaudio19-dev。"
            ) from exc

        return sd

    def input_devices(self) -> list[str]:
        pulse_devices = self._pulse_input_devices()
        if pulse_devices:
            return pulse_devices

        sd = self._sounddevice()
        devices = sd.query_devices()
        return [
            f"{index}: {device['name']}"
            for index, device in enumerate(devices)
            if device.get("max_input_channels", 0) > 0
        ]

    def ensure_input_device(self) -> None:
        if self.input_devices():
            return

        raise RuntimeError(
            "没有检测到可用麦克风输入设备。若在 WSL/Docker/远程容器中运行，需要先把宿主机麦克风映射进来，"
            "或改用本机 Windows/macOS/Linux 终端运行。"
        )

    def record_to_wav(
        self,
        seconds: int,
        silence_timeout_seconds: int = 5,
        silence_rms_threshold: int = 500,
    ) -> Path:
        if self._can_use_pulse():
            return self._record_with_pulse(
                seconds=seconds,
                silence_timeout_seconds=silence_timeout_seconds,
                silence_rms_threshold=silence_rms_threshold,
            )

        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError(
                "缺少 numpy。请先运行 pip install -r requirements.txt。"
            ) from exc

        sd = self._sounddevice()
        self.ensure_input_device()

        print(f"开始录音，请说话。连续 {silence_timeout_seconds} 秒没声音会自动停止。")
        chunks = []
        silent_seconds = 0.0
        elapsed_seconds = 0.0
        chunk_frames = max(1, int(self.sample_rate * CHUNK_SECONDS))

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
        ) as stream:
            while elapsed_seconds < seconds:
                audio, _overflowed = stream.read(chunk_frames)
                pcm = np.clip(audio, -1.0, 1.0)
                pcm = (pcm * 32767).astype(np.int16)
                chunks.append(pcm.tobytes())

                rms = audioop.rms(chunks[-1], SAMPLE_WIDTH_BYTES)
                chunk_seconds = len(audio) / self.sample_rate
                elapsed_seconds += chunk_seconds

                if rms < silence_rms_threshold:
                    silent_seconds += chunk_seconds
                else:
                    silent_seconds = 0.0

                if silent_seconds >= silence_timeout_seconds:
                    print("检测到连续静音，结束本次录音。")
                    break

        temp = tempfile.NamedTemporaryFile(prefix="assistant-", suffix=".wav", delete=False)
        temp_path = Path(temp.name)
        temp.close()

        with wave.open(str(temp_path), "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(b"".join(chunks))

        return temp_path

    def _can_use_pulse(self) -> bool:
        return bool(os.getenv("PULSE_SERVER")) and shutil.which("parecord") is not None

    def _pulse_input_devices(self) -> list[str]:
        if not self._can_use_pulse() or shutil.which("pactl") is None:
            return []

        try:
            completed = subprocess.run(
                ["pactl", "list", "short", "sources"],
                check=True,
                text=True,
                capture_output=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            return []

        devices = []
        for line in completed.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and not parts[1].endswith(".monitor"):
                devices.append(f"{parts[0]}: {parts[1]} (PulseAudio)")

        return devices

    def _record_with_pulse(
        self,
        seconds: int,
        silence_timeout_seconds: int,
        silence_rms_threshold: int,
    ) -> Path:
        temp = tempfile.NamedTemporaryFile(prefix="assistant-", suffix=".wav", delete=False)
        temp_path = Path(temp.name)
        temp.close()

        print(f"开始录音，请说话。连续 {silence_timeout_seconds} 秒没声音会自动停止。")
        command = [
            "parecord",
            "--record",
            "--raw",
            "--format=s16le",
            f"--rate={self.sample_rate}",
            f"--channels={self.channels}",
            "--device=@DEFAULT_SOURCE@",
        ]

        chunk_bytes = max(
            SAMPLE_WIDTH_BYTES * self.channels,
            int(self.sample_rate * CHUNK_SECONDS) * SAMPLE_WIDTH_BYTES * self.channels,
        )
        chunks = []
        silent_seconds = 0.0
        elapsed_seconds = 0.0

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            if process.stdout is None:
                raise RuntimeError("无法读取 parecord 输出。")

            while elapsed_seconds < seconds:
                chunk = process.stdout.read(chunk_bytes)
                if not chunk:
                    break

                chunks.append(chunk)
                rms = audioop.rms(chunk, SAMPLE_WIDTH_BYTES)
                chunk_seconds = len(chunk) / (
                    self.sample_rate * self.channels * SAMPLE_WIDTH_BYTES
                )
                elapsed_seconds += chunk_seconds

                if rms < silence_rms_threshold:
                    silent_seconds += chunk_seconds
                else:
                    silent_seconds = 0.0

                if silent_seconds >= silence_timeout_seconds:
                    print("检测到连续静音，结束本次录音。")
                    break

            process.terminate()
            process.wait(timeout=5)
        except OSError as exc:
            with suppress(OSError):
                temp_path.unlink()
            raise RuntimeError("无法启动 parecord。请确认已安装 pulseaudio-utils。") from exc
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

        with wave.open(str(temp_path), "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(SAMPLE_WIDTH_BYTES)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(b"".join(chunks))

        return temp_path
