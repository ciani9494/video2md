from dataclasses import dataclass

import pytest

from backend.services.audio_recorder import AudioSegment
from backend.services.transcriber import FasterWhisperTranscriber


@dataclass
class Segment:
    text: str


class StubWhisperModel:
    def __init__(self):
        self.calls = []

    def transcribe(self, audio_file: str, **kwargs):
        self.calls.append({"audio_file": audio_file, **kwargs})
        return [Segment(" 第一段 "), Segment("第二段")], object()


def test_faster_whisper_transcriber_passes_audio_path_and_language() -> None:
    model = StubWhisperModel()
    transcriber = FasterWhisperTranscriber(model_factory=lambda: model, language="zh")

    text = transcriber.transcribe(AudioSegment(source="/tmp/sample.wav", content=""))

    assert text == "第一段 第二段"
    assert model.calls == [
        {
            "audio_file": "/tmp/sample.wav",
            "language": "zh",
            "beam_size": 5,
            "vad_filter": True,
        }
    ]


def test_faster_whisper_transcriber_uses_auto_language_as_none() -> None:
    model = StubWhisperModel()
    transcriber = FasterWhisperTranscriber(model_factory=lambda: model, language="auto")

    transcriber.transcribe(AudioSegment(source="/tmp/sample.wav", content=""))

    assert model.calls[0]["language"] is None


def test_faster_whisper_transcriber_requires_file_source() -> None:
    transcriber = FasterWhisperTranscriber(model_factory=StubWhisperModel)

    with pytest.raises(ValueError, match="需要音频文件路径"):
        transcriber.transcribe(AudioSegment(source="fake://session", content="text"))
