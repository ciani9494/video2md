from threading import Event, Thread
from typing import Callable, Protocol

from backend.services.capture_pipeline import CapturePipeline


class CaptureWorker(Protocol):
    def start(self, session_id: str) -> None:
        """开始为录制会话捕获音频。"""

    def stop(self, session_id: str) -> None:
        """停止为录制会话捕获音频。"""


class ContinuousCaptureWorker:
    def __init__(
        self,
        capture_pipeline: CapturePipeline,
        append_transcript: Callable[[str, str], None],
        handle_error: Callable[[str, str], None],
        poll_interval_seconds: float = 0.1,
        max_iterations: int | None = None,
    ):
        self.capture_pipeline = capture_pipeline
        self.append_transcript = append_transcript
        self.handle_error = handle_error
        self.poll_interval_seconds = poll_interval_seconds
        self.max_iterations = max_iterations
        self._workers: dict[str, tuple[Event, Thread]] = {}

    def start(self, session_id: str) -> None:
        if self.is_running(session_id):
            return

        stop_event = Event()
        thread = Thread(target=self._run, args=(session_id, stop_event), daemon=True)
        self._workers[session_id] = (stop_event, thread)
        thread.start()

    def stop(self, session_id: str) -> None:
        worker = self._workers.get(session_id)
        if worker is None:
            return
        worker[0].set()

    def wait(self, session_id: str, timeout: float | None = None) -> None:
        worker = self._workers.get(session_id)
        if worker is None:
            return
        worker[1].join(timeout)

    def is_running(self, session_id: str) -> bool:
        worker = self._workers.get(session_id)
        return worker is not None and worker[1].is_alive()

    def _run(self, session_id: str, stop_event: Event) -> None:
        iterations = 0
        try:
            while not stop_event.is_set():
                text = self.capture_pipeline.capture_once(session_id)
                if text.strip():
                    self.append_transcript(session_id, text)
                iterations += 1
                if self.max_iterations is not None and iterations >= self.max_iterations:
                    break
                if self.poll_interval_seconds > 0:
                    # 短暂休眠使 worker 保持响应而不忙等。
                    stop_event.wait(self.poll_interval_seconds)
        except ValueError as exc:
            self.handle_error(session_id, str(exc))
        finally:
            self._workers.pop(session_id, None)
