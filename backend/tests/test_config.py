from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import create_app


def test_config_defaults_expand_output_directory(tmp_path: Path) -> None:
    client = TestClient(create_app(config_path=tmp_path / "config.json"))

    response = client.get("/api/config")

    assert response.status_code == 200
    body = response.json()
    assert body["deepseek_api_key"] == ""
    assert body["output_directory"].endswith("Documents/Video2MD")
    assert body["whisper_model"] == "base"
    assert body["language"] == "auto"
    assert body["transcriber_mode"] == "fake"
    assert body["capture_mode"] == "manual"
    assert body["require_audio_device"] is False


def test_config_update_persists_valid_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    client = TestClient(create_app(config_path=config_path))
    payload = {
        "deepseek_api_key": "sk-test",
        "output_directory": str(tmp_path / "notes"),
        "whisper_model": "small",
        "language": "zh",
        "transcriber_mode": "faster_whisper",
        "capture_mode": "sounddevice",
        "require_audio_device": True,
    }

    response = client.post("/api/config", json=payload)
    reloaded = TestClient(create_app(config_path=config_path)).get("/api/config")

    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "配置已保存"}
    assert reloaded.json() == payload


def test_config_rejects_invalid_transcriber_mode(tmp_path: Path) -> None:
    client = TestClient(create_app(config_path=tmp_path / "config.json"))

    response = client.post(
        "/api/config",
        json={
            "deepseek_api_key": "sk-test",
            "output_directory": str(tmp_path / "notes"),
            "whisper_model": "base",
            "language": "auto",
            "transcriber_mode": "unknown",
        },
    )

    assert response.status_code == 422


def test_config_rejects_invalid_capture_mode(tmp_path: Path) -> None:
    client = TestClient(create_app(config_path=tmp_path / "config.json"))

    response = client.post(
        "/api/config",
        json={
            "deepseek_api_key": "sk-test",
            "output_directory": str(tmp_path / "notes"),
            "whisper_model": "base",
            "language": "auto",
            "capture_mode": "unknown",
        },
    )

    assert response.status_code == 422
