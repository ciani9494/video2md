from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services.ai_organizer import AiOrganizer
from backend.services.audio_device import AudioDeviceDiscovery


class StubOrganizer(AiOrganizer):
    def organize(self, transcript_text: str, api_key: str) -> str:
        return f"# 文档\n\n{transcript_text}"


class FakeFrames:
    def tobytes(self) -> bytes:
        return b"\x01\x00\x02\x00"


class FakeSoundDevice:
    def rec(self, frames: int, samplerate: int, channels: int, device: int, dtype: str):
        return FakeFrames()

    def wait(self) -> None:
        return None


def test_sounddevice_capture_mode_auto_captures_audio_segment(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            config_path=tmp_path / "config.json",
            temp_root=tmp_path / "temp",
            organizer=StubOrganizer(),
            audio_discovery=AudioDeviceDiscovery(
                devices_provider=lambda: [{"name": "BlackHole 2ch", "index": 3}]
            ),
            sounddevice_module=FakeSoundDevice(),
            capture_interval_seconds=0,
            capture_max_iterations=1,
        )
    )
    client.post(
        "/api/config",
        json={
            "deepseek_api_key": "sk-test",
            "output_directory": str(tmp_path / "output"),
            "whisper_model": "base",
            "language": "auto",
            "transcriber_mode": "fake",
            "capture_mode": "sounddevice",
            "require_audio_device": True,
        },
    )

    session_id = client.post("/api/recording/start").json()["session_id"]

    status = client.get(f"/api/recording/status/{session_id}").json()
    audio_files = list((tmp_path / "temp" / session_id).glob("*.wav"))

    assert status["status"] == "recording"
    assert audio_files
