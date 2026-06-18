# Video2MD

Video2MD is a desktop audio-to-Markdown tool. This repository currently contains the backend MVP from the PRD: configuration management, startup readiness checks, configurable BlackHole audio device readiness, recording session state, fake, file-based, and sounddevice recorder/transcriber service boundaries, configurable sounddevice capture mode, continuous capture worker lifecycle, config-driven transcriber selection, a faster-whisper file transcriber adapter, WebSocket status/transcript push, transcript accumulation, DeepSeek-based Markdown organization, document management, and cleanup of temporary transcript files after successful processing.

## Backend

Create and activate the conda environment:

```bash
conda create -n video2md python=3.11 -y
conda activate video2md
```

Install dependencies:

```bash
python -m pip install -r backend/requirements.txt
```

Run the API:

```bash
python -m uvicorn backend.main:app --reload
```

Run tests:

```bash
python -m pytest backend/tests -q
```

## MVP Notes

The current backend exposes a transcript append endpoint, a fake `capture-once` pipeline, and a file-based `capture-file` endpoint as bridges for the future audio recorder and realtime transcriber. `capture_mode` defaults to `manual`; setting it to `sounddevice` wires `SoundDeviceAudioRecorder` into a continuous capture worker so recording startup can write BlackHole-backed WAV segments into the session temp directory. `transcriber_mode` defaults to `fake`; setting it to `faster_whisper` selects the lazy `FasterWhisperTranscriber` adapter. `require_audio_device` defaults to `false`; when enabled, startup requires BlackHole discovery before recording. Live faster-whisper streaming and Electron UI integration are the next implementation phases.
