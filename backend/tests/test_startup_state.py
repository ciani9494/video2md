from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.models import AppConfig
from backend.services.audio_device import AudioDeviceDiscovery
from backend.services.startup_preparer import StartupPreparationError, StartupPreparer


def test_start_without_api_key_returns_error_session(tmp_path: Path) -> None:
    client = TestClient(create_app(config_path=tmp_path / "config.json", temp_root=tmp_path / "temp"))

    response = client.post("/api/recording/start")

    assert response.status_code == 400
    detail = response.json()["detail"]
    session_id = detail["session_id"]
    assert detail["message"] == "DeepSeek API Key 未配置"
    status = client.get(f"/api/recording/status/{session_id}").json()
    assert status["status"] == "error"
    assert status["stage_message"] == "启动准备失败"
    assert status["error_message"] == "DeepSeek API Key 未配置"
    assert (tmp_path / "temp" / session_id).exists()


def test_start_with_invalid_output_directory_returns_error_session(tmp_path: Path) -> None:
    blocked_output = tmp_path / "not-a-directory"
    blocked_output.write_text("file blocks directory creation", encoding="utf-8")
    client = TestClient(create_app(config_path=tmp_path / "config.json", temp_root=tmp_path / "temp"))
    client.post(
        "/api/config",
        json={
            "deepseek_api_key": "sk-test",
            "output_directory": str(blocked_output),
            "whisper_model": "base",
            "language": "auto",
        },
    )

    response = client.post("/api/recording/start")

    assert response.status_code == 400
    detail = response.json()["detail"]
    session_id = detail["session_id"]
    assert detail["message"] == "输出目录不可用"
    status = client.get(f"/api/recording/status/{session_id}").json()
    assert status["status"] == "error"
    assert status["error_message"] == "输出目录不可用"


def test_start_with_valid_config_returns_recording_state(tmp_path: Path) -> None:
    client = TestClient(create_app(config_path=tmp_path / "config.json", temp_root=tmp_path / "temp"))
    client.post(
        "/api/config",
        json={
            "deepseek_api_key": "sk-test",
            "output_directory": str(tmp_path / "output"),
            "whisper_model": "base",
            "language": "auto",
        },
    )

    response = client.post("/api/recording/start")
    session_id = response.json()["session_id"]
    status = client.get(f"/api/recording/status/{session_id}").json()

    assert response.status_code == 200
    assert response.json()["status"] == "recording"
    assert response.json()["message"] == "录制已开始"
    assert status["status"] == "recording"
    assert status["stage_message"] == "录制中"
    assert status["error_message"] is None


def test_startup_preparer_reports_missing_blackhole(tmp_path: Path) -> None:
    preparer = StartupPreparer(
        audio_discovery=AudioDeviceDiscovery(devices_provider=lambda: [])
    )
    config = AppConfig(
        deepseek_api_key="sk-test",
        output_directory=str(tmp_path / "output"),
        whisper_model="base",
        language="auto",
    )

    try:
        preparer.prepare(config)
    except StartupPreparationError as exc:
        assert exc.message == "未找到 BlackHole 音频设备"
    else:
        raise AssertionError("StartupPreparationError was not raised")


def test_start_with_required_audio_device_reports_missing_blackhole(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            config_path=tmp_path / "config.json",
            temp_root=tmp_path / "temp",
            audio_discovery=AudioDeviceDiscovery(devices_provider=lambda: []),
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
            "require_audio_device": True,
        },
    )

    response = client.post("/api/recording/start")

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "未找到 BlackHole 音频设备"


def test_start_with_required_audio_device_accepts_blackhole(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            config_path=tmp_path / "config.json",
            temp_root=tmp_path / "temp",
            audio_discovery=AudioDeviceDiscovery(
                devices_provider=lambda: [{"name": "BlackHole 2ch", "index": 2}]
            ),
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
            "require_audio_device": True,
        },
    )

    response = client.post("/api/recording/start")

    assert response.status_code == 200
    assert response.json()["status"] == "recording"
