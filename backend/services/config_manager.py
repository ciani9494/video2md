import json
from pathlib import Path

from backend.models import AppConfig


class ConfigManager:
    def __init__(self, config_path: Path | str):
        self.config_path = Path(config_path)

    def default_config(self) -> AppConfig:
        output_dir = Path("~/Documents/Video2MD").expanduser()
        return AppConfig(output_directory=str(output_dir))

    def load(self) -> AppConfig:
        if not self.config_path.exists():
            return self.default_config()

        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        defaults = self.default_config().model_dump()
        defaults.update(data)
        return AppConfig(**defaults)

    def save(self, config: AppConfig) -> None:
        # 密钥保留在本地 config.json 中；此文件已被 git 忽略。
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(config.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
