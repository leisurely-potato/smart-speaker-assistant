from __future__ import annotations

import base64
import shutil
import subprocess
import threading
import time


class TextToSpeech:
    def __init__(
        self,
        enabled: bool,
        engine: str = "auto",
        voice: str = "",
        culture: str = "zh-CN",
        rate: int = 0,
        volume: int = 100,
    ) -> None:
        self.enabled = enabled
        self.engine_name = engine
        self.voice = voice
        self.culture = culture
        self.rate = max(-10, min(10, rate))
        self.volume = max(0, min(100, volume))
        self._engine = None

        if not enabled:
            return

        if engine == "auto":
            self.engine_name = "windows_sapi" if shutil.which("powershell.exe") else "pyttsx3"

        if self.engine_name == "windows_sapi":
            if not shutil.which("powershell.exe"):
                raise RuntimeError("TTS_ENGINE=windows_sapi 需要在 WSL/Windows 环境中运行。")
            return

        if self.engine_name != "pyttsx3":
            raise RuntimeError(f"不支持的 TTS_ENGINE：{self.engine_name}")

        try:
            import pyttsx3
        except ImportError as exc:
            raise RuntimeError("已开启 ENABLE_TTS，但未安装 pyttsx3。请先运行 pip install -r requirements.txt。") from exc

        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", 180 + self.rate * 15)
        self._engine.setProperty("volume", self.volume / 100)

    def say(self, text: str, stop_event: threading.Event | None = None) -> bool:
        if not self.enabled or not text.strip():
            return False

        if self.engine_name == "windows_sapi":
            return self._say_with_windows_sapi(text, stop_event=stop_event)

        if self._engine is None:
            return False

        self._engine.say(text)
        self._engine.runAndWait()
        return False

    def _say_with_windows_sapi(
        self,
        text: str,
        stop_event: threading.Event | None = None,
    ) -> bool:
        encoded_text = base64.b64encode(text.encode("utf-8")).decode("ascii")
        voice = self.voice.replace("'", "''")
        culture = self.culture.replace("'", "''")
        script = f"""
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speaker.SetOutputToDefaultAudioDevice()
$speaker.Rate = {self.rate}
$speaker.Volume = {self.volume}
$voiceName = '{voice}'
$cultureName = '{culture}'
if ($voiceName) {{
    $speaker.SelectVoice($voiceName)
}} elseif ($cultureName) {{
    $culture = [System.Globalization.CultureInfo]::GetCultureInfo($cultureName)
    $speaker.SelectVoiceByHints(
        [System.Speech.Synthesis.VoiceGender]::NotSet,
        [System.Speech.Synthesis.VoiceAge]::NotSet,
        0,
        $culture
    )
}}
$bytes = [Convert]::FromBase64String('{encoded_text}')
$text = [System.Text.Encoding]::UTF8.GetString($bytes)
$speaker.Speak($text)
"""
        encoded_command = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        process = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded_command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        interrupted = False
        while process.poll() is None:
            if stop_event is not None and stop_event.is_set():
                interrupted = True
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
                break
            time.sleep(0.05)

        stdout, stderr = process.communicate()
        if process.returncode != 0 and not interrupted:
            detail = stderr.decode(errors="replace").strip() or stdout.decode(errors="replace").strip()
            raise RuntimeError(f"Windows SAPI 语音播报失败：{detail}")
        return interrupted
