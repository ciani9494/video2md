from backend.services.audio_recorder import AudioRecorder, FakeAudioRecorder
from backend.models import AppConfig
from backend.services.transcriber import FakeTranscriber, FasterWhisperTranscriber, Transcriber


class CapturePipeline:
    def __init__(
        self,
        recorder: AudioRecorder | None = None,
        transcriber: Transcriber | None = None,
    ):
        self.recorder = recorder or FakeAudioRecorder()
        self.transcriber = transcriber or FakeTranscriber()

    def capture_once(self, session_id: str) -> str:
        audio_segment = self.recorder.capture_once(session_id)
        return self.transcriber.transcribe(audio_segment)


def build_capture_pipeline(
    config: AppConfig,
    recorder: AudioRecorder | None = None,
) -> CapturePipeline:
    if config.transcriber_mode == "faster_whisper":
        transcriber: Transcriber = FasterWhisperTranscriber(
            model_size=config.whisper_model,
            language=config.language,
        )
    else:
        transcriber = FakeTranscriber()
    return CapturePipeline(recorder=recorder, transcriber=transcriber)
