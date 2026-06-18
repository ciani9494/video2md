from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

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


def test_websocket_rejects_missing_session(tmp_path: Path) -> None:
    client = configured_client(tmp_path)

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/transcription/missing-session"):
            pass

    assert exc_info.value.code == 1008


def test_websocket_receives_initial_status_and_transcript(tmp_path: Path) -> None:
    client = configured_client(tmp_path)
    session_id = client.post("/api/recording/start").json()["session_id"]

    with client.websocket_connect(f"/ws/transcription/{session_id}") as websocket:
        initial = websocket.receive_json()
        client.post(
            f"/api/recording/{session_id}/transcript",
            json={"text": "WebSocket 推送实时转录。"},
        )
        transcript = websocket.receive_json()

    assert initial["type"] == "status"
    assert initial["status"] == "recording"
    assert initial["stage_message"] == "录制中"
    assert transcript == {
        "type": "transcript",
        "text": "WebSocket 推送实时转录。",
        "is_final": False,
    }


def test_websocket_receives_processing_and_completed_statuses(tmp_path: Path) -> None:
    client = configured_client(tmp_path)
    session_id = client.post("/api/recording/start").json()["session_id"]
    client.post(
        f"/api/recording/{session_id}/transcript",
        json={"text": "停止后应推送整理状态。"},
    )

    with client.websocket_connect(f"/ws/transcription/{session_id}") as websocket:
        initial = websocket.receive_json()
        stop_response = client.post("/api/recording/stop", json={"session_id": session_id})
        processing = websocket.receive_json()
        completed = websocket.receive_json()

    assert stop_response.status_code == 200
    assert initial["status"] == "recording"
    assert processing["type"] == "status"
    assert processing["status"] == "processing"
    assert processing["stage_message"] == "整理中"
    assert completed["type"] == "status"
    assert completed["status"] == "completed"
    assert completed["stage_message"] == "完成"
