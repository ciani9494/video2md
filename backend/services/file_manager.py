import shutil
from datetime import datetime
from pathlib import Path

from backend.models import DocumentContent, DocumentSummary


class FileManager:
    def __init__(self, temp_root: Path | str):
        self.temp_root = Path(temp_root)

    def session_dir(self, session_id: str) -> Path:
        path = self.temp_root / session_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_transcript(self, session_id: str, text: str) -> Path:
        # 原始转录为临时文件，仅在最终 markdown 保存后删除。
        transcript_path = self.session_dir(session_id) / "transcript.txt"
        transcript_path.write_text(text, encoding="utf-8")
        return transcript_path

    def save_document(self, markdown: str, output_directory: str) -> Path:
        output_dir = Path(output_directory).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_video_note.md"
        path = output_dir / filename
        path.write_text(markdown, encoding="utf-8")
        return path

    def cleanup(self, session_id: str) -> None:
        path = self.temp_root / session_id
        if path.exists():
            shutil.rmtree(path)

    def list_documents(self, output_directory: str) -> list[DocumentSummary]:
        output_dir = Path(output_directory).expanduser()
        if not output_dir.exists():
            return []

        documents = []
        for path in sorted(output_dir.glob("*.md"), reverse=True):
            stat = path.stat()
            documents.append(
                DocumentSummary(
                    id=path.stem,
                    filename=path.name,
                    created_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    size=stat.st_size,
                )
            )
        return documents

    def read_document(self, output_directory: str, document_id: str) -> DocumentContent | None:
        output_dir = Path(output_directory).expanduser()
        path = output_dir / f"{document_id}.md"
        if not path.exists() or not path.is_file():
            return None

        stat = path.stat()
        return DocumentContent(
            filename=path.name,
            content=path.read_text(encoding="utf-8"),
            created_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
        )
