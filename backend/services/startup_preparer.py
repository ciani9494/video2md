from pathlib import Path

from backend.models import AppConfig
from backend.services.audio_device import AudioDeviceDiscovery, AudioDeviceNotFoundError


class StartupPreparationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class StartupPreparer:
    def __init__(
        self,
        audio_discovery: AudioDeviceDiscovery | None = None,
        require_audio_device: bool = False,
    ):
        self.audio_discovery = audio_discovery
        self.require_audio_device = require_audio_device

    def prepare(self, config: AppConfig) -> None:
        if not config.deepseek_api_key.strip():
            raise StartupPreparationError("DeepSeek API Key 未配置")

        self._ensure_output_directory(config.output_directory)
        self._ensure_audio_ready()
        self._ensure_transcriber_ready()

    def _ensure_output_directory(self, output_directory: str) -> None:
        path = Path(output_directory).expanduser()
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".video2md_write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        except OSError as exc:
            raise StartupPreparationError("输出目录不可用") from exc

    def _ensure_audio_ready(self) -> None:
        if not self.require_audio_device and self.audio_discovery is None:
            return None
        try:
            discovery = self.audio_discovery or AudioDeviceDiscovery()
            discovery.ensure_blackhole()
        except AudioDeviceNotFoundError as exc:
            raise StartupPreparationError(exc.message) from exc
        return None

    def _ensure_transcriber_ready(self) -> None:
        # 占位：faster-whisper 模型就绪检查，MVP 阶段不加载重量级模型。
        return None
