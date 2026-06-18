from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services.ai_organizer import AiOrganizer


class StubOrganizer(AiOrganizer):
    def organize(self, transcript_text: str, api_key: str) -> str:
        assert api_key == "sk-test"
        return f"# 技术文档\n\n## 核心内容\n\n{transcript_text}"


def test_recording_flow_generates_document_and_cleans_temp_files(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    temp_root = tmp_path / "temp"
    output_dir = tmp_path / "output"
    client = TestClient(
        create_app(
            config_path=config_path,
            temp_root=temp_root,
            organizer=StubOrganizer(),
        )
    )
    client.post(
        "/api/config",
        json={
            "deepseek_api_key": "sk-test",
            "output_directory": str(output_dir),
            "whisper_model": "base",
            "language": "auto",
        },
    )

    start_response = client.post("/api/recording/start")
    session_id = start_response.json()["session_id"]
    append_response = client.post(
        f"/api/recording/{session_id}/transcript",
        json={"text": "FastAPI 使用依赖注入组织后端模块。"},
    )
    stop_response = client.post("/api/recording/stop", json={"session_id": session_id})
    status_response = client.get(f"/api/recording/status/{session_id}")
    documents_response = client.get("/api/documents")

    assert start_response.status_code == 200
    assert append_response.status_code == 200
    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "completed"
    assert status_response.json()["status"] == "completed"
    assert status_response.json()["transcript_preview"] == "FastAPI 使用依赖注入组织后端模块。"
    assert not (temp_root / session_id).exists()
    documents = documents_response.json()["documents"]
    assert len(documents) == 1
    document = client.get(f"/api/documents/{documents[0]['id']}").json()
    assert document["content"].startswith("# 技术文档")
    assert "FastAPI 使用依赖注入组织后端模块。" in document["content"]


def test_stop_without_transcript_returns_error_and_keeps_temp_files(tmp_path: Path) -> None:
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
    session_id = client.post("/api/recording/start").json()["session_id"]

    stop_response = client.post("/api/recording/stop", json={"session_id": session_id})
    status_response = client.get(f"/api/recording/status/{session_id}")

    assert stop_response.status_code == 400
    assert stop_response.json()["detail"] == "转录文本为空，无法整理文档"
    assert status_response.json()["status"] == "error"
    assert (tmp_path / "temp" / session_id).exists()
