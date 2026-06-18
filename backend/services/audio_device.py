from dataclasses import dataclass
from typing import Callable, Mapping


class AudioDeviceNotFoundError(Exception):
    def __init__(self, message: str = "未找到 BlackHole 音频设备"):
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class AudioDevice:
    name: str
    index: int | None = None


class AudioDeviceDiscovery:
    def __init__(self, devices_provider: Callable[[], list[Mapping]] | None = None):
        self.devices_provider = devices_provider or self._sounddevice_devices

    def find_blackhole(self) -> AudioDevice | None:
        for index, device in enumerate(self.devices_provider()):
            name = str(device.get("name", ""))
            if "blackhole" in name.lower():
                return AudioDevice(name=name, index=device.get("index", index))
        return None

    def ensure_blackhole(self) -> AudioDevice:
        device = self.find_blackhole()
        if device is None:
            raise AudioDeviceNotFoundError()
        return device

    def _sounddevice_devices(self) -> list[Mapping]:
        # 懒加载导入，使测试/默认路径不需要主机音频依赖。
        import sounddevice as sd

        return list(sd.query_devices())
