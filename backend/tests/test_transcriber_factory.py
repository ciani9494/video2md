from backend.models import AppConfig
from backend.services.capture_pipeline import build_capture_pipeline
from backend.services.transcriber import FakeTranscriber, FasterWhisperTranscriber


def config(transcriber_mode: str) -> AppConfig:
    return AppConfig(
        deepseek_api_key="sk-test",
        output_directory="/tmp/video2md",
        whisper_model="tiny",
        language="zh",
        transcriber_mode=transcriber_mode,
    )


def test_build_capture_pipeline_uses_fake_transcriber_by_default() -> None:
    pipeline = build_capture_pipeline(config("fake"))

    assert isinstance(pipeline.transcriber, FakeTranscriber)


def test_build_capture_pipeline_can_select_faster_whisper() -> None:
    pipeline = build_capture_pipeline(config("faster_whisper"))

    assert isinstance(pipeline.transcriber, FasterWhisperTranscriber)
    assert pipeline.transcriber.model_size == "tiny"
    assert pipeline.transcriber.language == "zh"
