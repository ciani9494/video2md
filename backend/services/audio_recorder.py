from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Protocol
import wave

from backend.services.audio_device import AudioDeviceDiscovery, AudioDeviceNotFoundError


@dataclass(frozen=True)
class AudioSegment:
    source: str
    content: str


class AudioRecorder(Protocol):
    def capture_once(self, session_id: str) -> AudioSegment:
        """为录制会话捕获一段音频。"""


class FakeAudioRecorder:
    def capture_once(self, session_id: str) -> AudioSegment:
        # MVP fake 片段使后续转录器边界可在无硬件情况下测试。
        return AudioSegment(
            source=f"fake://{session_id}",
            content="这是 fake 转录内容，用于验证录音和转录服务边界。",
        )


class FileAudioRecorder:
    def __init__(self, audio_path: Path | str):
        self.audio_path = Path(audio_path).expanduser()

    def capture_once(self, session_id: str) -> AudioSegment:
        if not self.audio_path.exists() or not self.audio_path.is_file():
            raise ValueError("音频文件不存在")

        # Fake 转录器使用 content 字段；faster-whisper 使用 source 字段。
        content = self.audio_path.read_text(encoding="utf-8", errors="ignore")
        return AudioSegment(source=str(self.audio_path), content=content)


class SoundDeviceAudioRecorder:
    def __init__(
        self,
        temp_root: Path | str,
        audio_discovery: AudioDeviceDiscovery | None = None,
        sounddevice_module=None,
        segment_seconds: int = 5,
        sample_rate: int = 16000,
        channels: int = 1,
    ):
        self.temp_root = Path(temp_root)
        self.audio_discovery = audio_discovery or AudioDeviceDiscovery()
        self._sounddevice_module = sounddevice_module
        self.segment_seconds = segment_seconds
        self.sample_rate = sample_rate
        self.channels = channels

    def capture_once(self, session_id: str) -> AudioSegment:
        try:
            device = self.audio_discovery.ensure_blackhole()
        except AudioDeviceNotFoundError as exc:
            raise ValueError(exc.message) from exc

        session_dir = self.temp_root / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        audio_path = session_dir / f"audio_{int(time() * 1000)}.wav"

        # 保持短片段捕获；后续循环可重复调用。
        frames = self.segment_seconds * self.sample_rate
        recording = self._sounddevice().rec(
            frames,
            samplerate=self.sample_rate,
            channels=self.channels,
            device=device.index,
            dtype="int16",
        )
        self._sounddevice().wait()
        self._write_wav(audio_path, recording)
        return AudioSegment(source=str(audio_path), content="")

    def _sounddevice(self):
        if self._sounddevice_module is None:
            # 懒加载导入，使 fake/file 测试不需要主机音频访问。
            import sounddevice as sd

            self._sounddevice_module = sd
        return self._sounddevice_module

    def _write_wav(self, audio_path: Path, recording) -> None:
        audio_bytes = recording.tobytes() if hasattr(recording, "tobytes") else bytes(recording)
        with wave.open(str(audio_path), "wb") as audio_file:
            audio_file.setnchannels(self.channels)
            audio_file.setsampwidth(2)
            audio_file.setframerate(self.sample_rate)
            audio_file.writeframes(audio_bytes)
