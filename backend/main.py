import asyncio
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from backend.models import (
    AppConfig,
    DocumentContent,
    DocumentList,
    FileCaptureRequest,
    RecordingStatus,
    StartRecordingResponse,
    StatusMessage,
    StopRecordingRequest,
    TranscriptAppendRequest,
)
from backend.services.ai_organizer import AiOrganizer, DeepSeekOrganizer
from backend.services.audio_device import AudioDeviceDiscovery
from backend.services.capture_pipeline import build_capture_pipeline
from backend.services.audio_recorder import FileAudioRecorder, SoundDeviceAudioRecorder
from backend.services.config_manager import ConfigManager
from backend.services.continuous_capture import CaptureWorker, ContinuousCaptureWorker
from backend.services.file_manager import FileManager
from backend.services.session_manager import SessionManager
from backend.services.startup_preparer import StartupPreparationError, StartupPreparer
from backend.services.websocket_manager import WebSocketManager


def create_app(
    config_path: Path | str = "config.json",
    temp_root: Path | str = "tmp/video2md",
    organizer: AiOrganizer | None = None,
    audio_discovery: AudioDeviceDiscovery | None = None,
    capture_worker: CaptureWorker | None = None,
    sounddevice_module=None,
    capture_interval_seconds: float = 0.1,
    capture_max_iterations: int | None = None,
) -> FastAPI:
    config_manager = ConfigManager(config_path)
    file_manager = FileManager(temp_root)
    session_manager = SessionManager()
    ai_organizer = organizer or DeepSeekOrganizer()
    websocket_manager = WebSocketManager()
    owned_capture_workers: dict[str, CaptureWorker] = {}

    app = FastAPI(title="Video2MD Backend")

    def status_payload(session) -> dict[str, object]:
        return {
            "type": "status",
            "status": session.status,
            "duration": session.duration,
            "transcript_preview": session.preview,
            "stage_message": session.stage_message,
            "error_message": session.error,
        }

    def append_transcript_text(session_id: str, text: str) -> None:
        session = session_manager.append_transcript(session_id, text)
        if session is None:
            raise HTTPException(status_code=404, detail="录制会话不存在")
        file_manager.save_transcript(session_id, session.transcript)
        websocket_manager.broadcast(
            session_id,
            {"type": "transcript", "text": text, "is_final": False},
        )

    def mark_capture_error(session_id: str, message: str) -> None:
        session = session_manager.get(session_id)
        if session is None:
            return
        session.status = "error"
        session.stage_message = "录制失败"
        session.error = message
        websocket_manager.broadcast(session.id, status_payload(session))

    def start_capture_worker(session_id: str, config: AppConfig) -> None:
        if capture_worker is not None:
            capture_worker.start(session_id)
            return
        if config.capture_mode != "sounddevice":
            return

        recorder = SoundDeviceAudioRecorder(
            temp_root=temp_root,
            audio_discovery=audio_discovery,
            sounddevice_module=sounddevice_module,
        )
        worker = ContinuousCaptureWorker(
            capture_pipeline=build_capture_pipeline(config, recorder=recorder),
            append_transcript=append_transcript_text,
            handle_error=mark_capture_error,
            poll_interval_seconds=capture_interval_seconds,
            max_iterations=capture_max_iterations,
        )
        owned_capture_workers[session_id] = worker
        worker.start(session_id)

    def stop_capture_worker(session_id: str) -> None:
        if capture_worker is not None:
            capture_worker.stop(session_id)
            return
        worker = owned_capture_workers.pop(session_id, None)
        if worker is not None:
            worker.stop(session_id)

    @app.get("/api/config", response_model=AppConfig)
    def get_config() -> AppConfig:
        return config_manager.load()

    @app.post("/api/config", response_model=StatusMessage)
    def update_config(config: AppConfig) -> StatusMessage:
        config_manager.save(config)
        return StatusMessage(status="success", message="配置已保存")

    @app.post("/api/recording/start", response_model=StartRecordingResponse)
    def start_recording() -> StartRecordingResponse:
        session = session_manager.start()
        file_manager.session_dir(session.id)
        try:
            config = config_manager.load()
            startup_preparer = StartupPreparer(
                audio_discovery=audio_discovery,
                require_audio_device=config.require_audio_device,
            )
            startup_preparer.prepare(config)
        except StartupPreparationError as exc:
            session.status = "error"
            session.stage_message = "启动准备失败"
            session.error = exc.message
            websocket_manager.broadcast(session.id, status_payload(session))
            raise HTTPException(
                status_code=400,
                detail={"session_id": session.id, "message": exc.message},
            ) from exc

        session.status = "recording"
        session.stage_message = "录制中"
        websocket_manager.broadcast(session.id, status_payload(session))
        start_capture_worker(session.id, config)
        return StartRecordingResponse(
            status="recording",
            session_id=session.id,
            message="录制已开始",
        )

    @app.post("/api/recording/{session_id}/transcript", response_model=StatusMessage)
    def append_transcript(session_id: str, request: TranscriptAppendRequest) -> StatusMessage:
        # MVP 桥接接口，用于将来接入实时转录/音频管线。
        append_transcript_text(session_id, request.text)
        return StatusMessage(status="success", message="转录文本已追加")

    @app.post("/api/recording/{session_id}/capture-once", response_model=StatusMessage)
    def capture_once(session_id: str) -> StatusMessage:
        capture_pipeline = build_capture_pipeline(config_manager.load())
        try:
            text = capture_pipeline.capture_once(session_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        append_transcript_text(session_id, text)
        return StatusMessage(status="success", message="转录文本已追加")

    @app.post("/api/recording/{session_id}/capture-file", response_model=StatusMessage)
    def capture_file(session_id: str, request: FileCaptureRequest) -> StatusMessage:
        capture_pipeline = build_capture_pipeline(
            config_manager.load(),
            recorder=FileAudioRecorder(request.audio_path),
        )
        try:
            text = capture_pipeline.capture_once(session_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        append_transcript_text(session_id, text)
        return StatusMessage(status="success", message="转录文本已追加")

    @app.post("/api/recording/stop", response_model=StatusMessage)
    def stop_recording(request: StopRecordingRequest) -> StatusMessage:
        session = session_manager.get(request.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="录制会话不存在")
        stop_capture_worker(session.id)

        transcript = session.transcript
        if not transcript:
            session.status = "error"
            session.stage_message = "整理失败"
            session.error = "转录文本为空，无法整理文档"
            websocket_manager.broadcast(session.id, status_payload(session))
            raise HTTPException(status_code=400, detail=session.error)

        config = config_manager.load()
        if not config.deepseek_api_key:
            session.status = "error"
            session.stage_message = "整理失败"
            session.error = "DeepSeek API Key 未配置"
            websocket_manager.broadcast(session.id, status_payload(session))
            raise HTTPException(status_code=400, detail=session.error)

        session.status = "processing"
        session.stage_message = "整理中"
        websocket_manager.broadcast(session.id, status_payload(session))
        markdown = ai_organizer.organize(transcript, config.deepseek_api_key)
        document_path = file_manager.save_document(markdown, config.output_directory)
        session.document_path = str(document_path)
        session.status = "completed"
        session.stage_message = "完成"
        file_manager.cleanup(session.id)
        websocket_manager.broadcast(session.id, status_payload(session))
        return StatusMessage(status="completed", message="文档已保存")

    @app.get("/api/recording/status/{session_id}", response_model=RecordingStatus)
    def recording_status(session_id: str) -> RecordingStatus:
        session = session_manager.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="录制会话不存在")
        return RecordingStatus(
            status=session.status,
            duration=session.duration,
            transcript_preview=session.preview,
            stage_message=session.stage_message,
            error_message=session.error,
        )

    @app.get("/api/documents", response_model=DocumentList)
    def list_documents() -> DocumentList:
        config = config_manager.load()
        return DocumentList(documents=file_manager.list_documents(config.output_directory))

    @app.get("/api/documents/{document_id}", response_model=DocumentContent)
    def get_document(document_id: str) -> DocumentContent:
        config = config_manager.load()
        document = file_manager.read_document(config.output_directory, document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="文档不存在")
        return document

    @app.websocket("/ws/transcription/{session_id}")
    async def transcription_socket(websocket: WebSocket, session_id: str) -> None:
        session = session_manager.get(session_id)
        if session is None:
            await websocket.close(code=1008)
            return

        await websocket.accept()
        connection = websocket_manager.connect(session_id)
        try:
            await websocket.send_json(status_payload(session))
            while True:
                receive_task = asyncio.create_task(websocket.receive_text())
                event_task = asyncio.create_task(connection.queue.get())
                done, pending = await asyncio.wait(
                    {receive_task, event_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()
                if receive_task in done:
                    receive_task.result()
                    continue
                await websocket.send_json(event_task.result())
        except WebSocketDisconnect:
            pass
        finally:
            websocket_manager.disconnect(session_id, connection)

    return app


app = create_app()
