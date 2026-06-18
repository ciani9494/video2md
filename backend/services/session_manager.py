from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class RecordingSession:
    id: str
    started_at: datetime
    status: str = "starting"
    stage_message: str = "准备录制中"
    transcript_parts: list[str] = field(default_factory=list)
    document_path: str | None = None
    error: str | None = None

    @property
    def transcript(self) -> str:
        return "\n".join(part for part in self.transcript_parts if part.strip()).strip()

    @property
    def duration(self) -> int:
        return int((datetime.now() - self.started_at).total_seconds())

    @property
    def preview(self) -> str:
        return self.transcript[-120:]


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, RecordingSession] = {}

    def start(self) -> RecordingSession:
        session = RecordingSession(id=str(uuid4()), started_at=datetime.now())
        self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> RecordingSession | None:
        return self._sessions.get(session_id)

    def append_transcript(self, session_id: str, text: str) -> RecordingSession | None:
        session = self.get(session_id)
        if session is None:
            return None
        session.transcript_parts.append(text)
        return session
