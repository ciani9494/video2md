from typing import Protocol

from backend.services.audio_recorder import AudioSegment


class Transcriber(Protocol):
    def transcribe(self, audio_segment: AudioSegment) -> str:
        """将一段捕获的音频转换为转录文本。"""


class FakeTranscriber:
    def transcribe(self, audio_segment: AudioSegment) -> str:
        # fake 录制器将期望文本存储在 content 中，直到接入 faster-whisper。
        return audio_segment.content


class FasterWhisperTranscriber:
    def __init__(
        self,
        model_size: str = "base",
        language: str = "auto",
        model_factory=None,
    ):
        self.model_size = model_size
        self.language = None if language == "auto" else language
        self._model_factory = model_factory
        self._model = None

    def transcribe(self, audio_segment: AudioSegment) -> str:
        if not audio_segment.source or "://" in audio_segment.source:
            raise ValueError("需要音频文件路径")

        segments, _info = self._model_instance().transcribe(
            audio_segment.source,
            language=self.language,
            beam_size=5,
            vad_filter=True,
        )
        return " ".join(segment.text.strip() for segment in segments if segment.text.strip())

    def _model_instance(self):
        if self._model is None:
            if self._model_factory is not None:
                self._model = self._model_factory()
            else:
                # 懒加载导入使默认 fake 测试路径保持快速且依赖轻量。
                from faster_whisper import WhisperModel

                self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        return self._model
