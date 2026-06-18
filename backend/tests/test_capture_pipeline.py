from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services.ai_organizer import AiOrganizer


class StubOrganizer(AiOrganizer):
    def organize(self, transcript_text: str, api_key: str) -> str:
        return f"# 文档\n\n{transcript_text}"


def configured_client(tmp_path: Path) -> TestClient:
    client = TestClient(
        create_app(
            config_path=tmp_path / "config.json",
            temp_root=tmp_path / "temp",
            organizer=StubOrganizer(),
        )
    )
    client.post(
        "/api/config",
        json={
            "deepseek_api_key": "sk-test",
            "output_directory": str(tmp_path / "output"),
            "whisper_model": "base",
            "language": "auto",
        },
    )
    return client


def test_fake_capture_pipeline_appends_transcript_and_broadcasts(tmp_path: Path) -> None:
    client = configured_client(tmp_path)
    session_id = client.post("/api/recording/start").json()["session_id"]

    with client.websocket_connect(f"/ws/transcription/{session_id}") as websocket:
        websocket.receive_json()
        capture_response = client.post(f"/api/recording/{session_id}/capture-once")
        assert capture_response.status_code == 200
        transcript = websocket.receive_json()

    status = client.get(f"/api/recording/status/{session_id}").json()
    assert capture_response.json() == {"status": "success", "message": "转录文本已追加"}
    assert transcript == {
        "type": "transcript",
        "text": "这是 fake 转录内容，用于验证录音和转录服务边界。",
        "is_final": False,
    }
    assert status["transcript_preview"] == "这是 fake 转录内容，用于验证录音和转录服务边界。"


def test_fake_capture_pipeline_keeps_finalize_flow_unchanged(tmp_path: Path) -> None:
    client = configured_client(tmp_path)
    session_id = client.post("/api/recording/start").json()["session_id"]

    capture_response = client.post(f"/api/recording/{session_id}/capture-once")
    stop_response = client.post("/api/recording/stop", json={"session_id": session_id})
    documents = client.get("/api/documents").json()["documents"]

    assert capture_response.status_code == 200
    assert stop_response.status_code == 200
    assert documents
    document = client.get(f"/api/documents/{documents[0]['id']}").json()
    assert "这是 fake 转录内容，用于验证录音和转录服务边界。" in document["content"]


def test_faster_whisper_mode_rejects_fake_audio_source(tmp_path: Path) -> None:
    client = configured_client(tmp_path)
    client.post(
        "/api/config",
        json={
            "deepseek_api_key": "sk-test",
            "output_directory": str(tmp_path / "output"),
            "whisper_model": "base",
            "language": "auto",
            "transcriber_mode": "faster_whisper",
        },
    )
    session_id = client.post("/api/recording/start").json()["session_id"]

    response = client.post(f"/api/recording/{session_id}/capture-once")

    assert response.status_code == 400
    assert response.json()["detail"] == "需要音频文件路径"
