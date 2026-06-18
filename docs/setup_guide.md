# Video2MD Backend Setup

## Install

```bash
conda create -n video2md python=3.11 -y
conda activate video2md
python -m pip install -r backend/requirements.txt
```

## Run

```bash
python -m uvicorn backend.main:app --reload
```

## Test

```bash
python -m pytest backend/tests -q
```

## Current MVP Scope

The backend implements configuration, startup readiness checks, configurable BlackHole audio device readiness, recording session state, fake, file-based, and sounddevice recorder/transcriber service boundaries, configurable sounddevice capture mode, continuous capture worker lifecycle, config-driven transcriber selection, a faster-whisper file transcriber adapter, WebSocket status/transcript push, transcript persistence, final Markdown generation through an injectable AI organizer, document listing, document reading, and temporary file cleanup after successful document generation.

Live faster-whisper streaming is intentionally left as the next integration layer. The temporary transcript append endpoint and fake capture pipeline exist so the Electron frontend and future transcriber can exercise the same session finalization flow while receiving WebSocket updates.

## Audio Device Discovery

`AudioDeviceDiscovery` lazily loads `sounddevice` and can detect BlackHole devices by name. `require_audio_device` defaults to `false`; set it to `true` to require BlackHole during recording startup.

## SoundDevice Recorder

`SoundDeviceAudioRecorder` records a short WAV segment from the discovered BlackHole device index into the session temp directory. It is currently a service boundary for the future continuous capture loop rather than a user-facing API endpoint.

## Continuous Capture Worker

`ContinuousCaptureWorker` loops over capture/transcribe/append for one recording session and can be started or stopped through the recording lifecycle. `capture_mode` defaults to `manual`; set it to `sounddevice` to wire `SoundDeviceAudioRecorder` into the worker and write BlackHole-backed WAV segments into the session temp directory.

Fake transcriber mode does not produce meaningful text from WAV bytes. Use `transcriber_mode=faster_whisper` when validating real audio-to-text behavior.

## File Capture

`POST /api/recording/{session_id}/capture-file` accepts an `audio_path` JSON field. It feeds the file path into the configured transcriber and then reuses the existing transcript/WebSocket/finalization flow.

## Transcriber Mode

`transcriber_mode` defaults to `fake` for fast local development and tests. Set it to `faster_whisper` to select the lazy faster-whisper adapter behind the existing transcriber interface.
