import pytest

from backend.services.audio_device import (
    AudioDeviceDiscovery,
    AudioDeviceNotFoundError,
)


def test_audio_device_discovery_finds_blackhole_by_name() -> None:
    discovery = AudioDeviceDiscovery(
        devices_provider=lambda: [
            {"name": "MacBook Pro Microphone", "index": 0},
            {"name": "BlackHole 2ch", "index": 3},
        ]
    )

    device = discovery.find_blackhole()

    assert device.name == "BlackHole 2ch"
    assert device.index == 3


def test_audio_device_discovery_is_case_insensitive() -> None:
    discovery = AudioDeviceDiscovery(
        devices_provider=lambda: [{"name": "blackhole 16ch", "index": 8}]
    )

    device = discovery.find_blackhole()

    assert device.name == "blackhole 16ch"
    assert device.index == 8


def test_audio_device_discovery_raises_clear_error_when_missing() -> None:
    discovery = AudioDeviceDiscovery(
        devices_provider=lambda: [{"name": "MacBook Pro Speakers", "index": 1}]
    )

    with pytest.raises(AudioDeviceNotFoundError, match="未找到 BlackHole 音频设备"):
        discovery.ensure_blackhole()
