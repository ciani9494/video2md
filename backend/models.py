from typing import Literal

from pydantic import BaseModel


class AppConfig(BaseModel):
    deepseek_api_key: str = ""
    output_directory: str
    whisper_model: str = "base"
    language: str = "auto"
    transcriber_mode: Literal["fake", "faster_whisper"] = "fake"
    capture_mode: Literal["manual", "sounddevice"] = "manual"
    require_audio_device: bool = False


class StatusMessage(BaseModel):
    status: str
    message: str


class StartRecordingResponse(StatusMessage):
    session_id: str


class StopRecordingRequest(BaseModel):
    session_id: str


class TranscriptAppendRequest(BaseModel):
    text: str


class FileCaptureRequest(BaseModel):
    audio_path: str


class RecordingStatus(BaseModel):
    status: str
    duration: int
    transcript_preview: str
    stage_message: str
    error_message: str | None = None


class DocumentSummary(BaseModel):
    id: str
    filename: str
    created_at: str
    size: int


class DocumentList(BaseModel):
    documents: list[DocumentSummary]


class DocumentContent(BaseModel):
    filename: str
    content: str
    created_at: str
