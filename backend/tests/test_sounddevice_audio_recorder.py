from pathlib import Path

import pytest

from backend.services.audio_device import AudioDeviceDiscovery
from backend.services.audio_recorder import SoundDeviceAudioRecorder


class FakeFrames:
    def __init__(self, data: bytes):
        self.data = data

    def tobytes(self) -> bytes:
        return self.data


class FakeSoundDevice:
    def __init__(self):
        self.recording_request = None
        self.wait_called = False

    def rec(self, frames: int, samplerate: int, channels: int, device: int, dtype: str):
        self.recording_request = {
            "frames": frames,
            "samplerate": samplerate,
            "channels": channels,
            "device": device,
            "dtype": dtype,
        }
        return FakeFrames(b"\x01\x00\x02\x00")

    def wait(self) -> None:
        self.wait_called = True


def blackhole_discovery() -> AudioDeviceDiscovery:
    return AudioDeviceDiscovery(devices_provider=lambda: [{"name": "BlackHole 2ch", "index": 7}])


def test_sounddevice_audio_recorder_writes_session_wav_with_blackhole_device(
    tmp_path: Path,
) -> None:
    sounddevice = FakeSoundDevice()
    recorder = SoundDeviceAudioRecorder(
        temp_root=tmp_path / "temp",
        audio_discovery=blackhole_discovery(),
        sounddevice_module=sounddevice,
        segment_seconds=2,
        sample_rate=16000,
        channels=1,
    )

    segment = recorder.capture_once("session-1")

    audio_path = Path(segment.source)
    assert audio_path.parent == tmp_path / "temp" / "session-1"
    assert audio_path.suffix == ".wav"
    assert audio_path.read_bytes().startswith(b"RIFF")
    assert segment.content == ""
    assert sounddevice.recording_request == {
        "frames": 32000,
        "samplerate": 16000,
        "channels": 1,
        "device": 7,
        "dtype": "int16",
    }
    assert sounddevice.wait_called is True


def test_sounddevice_audio_recorder_raises_clear_error_when_blackhole_is_missing(
    tmp_path: Path,
) -> None:
    recorder = SoundDeviceAudioRecorder(
        temp_root=tmp_path / "temp",
        audio_discovery=AudioDeviceDiscovery(devices_provider=lambda: []),
        sounddevice_module=FakeSoundDevice(),
    )

    with pytest.raises(ValueError, match="未找到 BlackHole 音频设备"):
        recorder.capture_once("session-1")
