from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services.ai_organizer import AiOrganizer
from backend.services.continuous_capture import ContinuousCaptureWorker


class StubOrganizer(AiOrganizer):
    def organize(self, transcript_text: str, api_key: str) -> str:
        return f"# 文档\n\n{transcript_text}"


class FakePipeline:
    def __init__(self, results: list[str]):
        self.results = results
        self.calls = 0

    def capture_once(self, session_id: str) -> str:
        result = self.results[self.calls]
        self.calls += 1
        return result


class FailingPipeline:
    def capture_once(self, session_id: str) -> str:
        raise ValueError("录制片段失败")


class StubCaptureWorker:
    def __init__(self):
        self.started: list[str] = []
        self.stopped: list[str] = []

    def start(self, session_id: str) -> None:
        self.started.append(session_id)

    def stop(self, session_id: str) -> None:
        self.stopped.append(session_id)


def test_continuous_capture_worker_appends_transcripts_until_limit() -> None:
    appended: list[tuple[str, str]] = []
    pipeline = FakePipeline(["第一段", "第二段"])
    worker = ContinuousCaptureWorker(
        capture_pipeline=pipeline,
        append_transcript=lambda session_id, text: appended.append((session_id, text)),
        handle_error=lambda session_id, message: None,
        poll_interval_seconds=0,
        max_iterations=2,
    )

    worker.start("session-1")
    worker.wait("session-1", timeout=1)

    assert appended == [("session-1", "第一段"), ("session-1", "第二段")]
    assert pipeline.calls == 2
    assert worker.is_running("session-1") is False


def test_continuous_capture_worker_reports_capture_errors() -> None:
    errors: list[tuple[str, str]] = []
    worker = ContinuousCaptureWorker(
        capture_pipeline=FailingPipeline(),
        append_transcript=lambda session_id, text: None,
        handle_error=lambda session_id, message: errors.append((session_id, message)),
        poll_interval_seconds=0,
    )

    worker.start("session-1")
    worker.wait("session-1", timeout=1)

    assert errors == [("session-1", "录制片段失败")]
    assert worker.is_running("session-1") is False


def test_recording_lifecycle_starts_and_stops_injected_capture_worker(tmp_path: Path) -> None:
    capture_worker = StubCaptureWorker()
    client = TestClient(
        create_app(
            config_path=tmp_path / "config.json",
            temp_root=tmp_path / "temp",
            organizer=StubOrganizer(),
            capture_worker=capture_worker,
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
    client.post(f"/api/recording/{session_id}/transcript", json={"text": "已有转录"})
    response = client.post("/api/recording/stop", json={"session_id": session_id})

    assert response.status_code == 200
    assert capture_worker.started == [session_id]
    assert capture_worker.stopped == [session_id]
