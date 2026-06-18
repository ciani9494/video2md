# Video2MD Backend Plan

## Current Capability

- FastAPI backend entry: `backend.main:create_app`.
- Config API: read and write `deepseek_api_key`, `output_directory`, `whisper_model`, and `language`.
- Recording session API: start, append transcript, stop, and query status.
- Document API: list generated Markdown files and read a document by id.
- File cleanup rule: delete temporary session files only after final Markdown is saved.
- Test coverage: config defaults/update, successful recording finalization, document readback, empty transcript failure, recorder/transcriber boundaries, BlackHole readiness, and sounddevice segment capture.

## Completed Step: Startup State Machine

Goal: make “click start recording” safe for the future Electron UI. The UI should show loading while backend resources are preparing, and only show “recording” after all required resources are ready.

### Implemented Backend Changes

1. Added explicit session states used by the backend flow: `starting`, `recording`, `processing`, `completed`, `error`.
2. Added a preparation service that checks:
   - DeepSeek API Key exists.
   - Output directory can be created and written.
   - Audio device readiness placeholder passes in MVP.
   - Transcriber readiness placeholder passes in MVP.
3. Extended recording status response with:
   - `status`
   - `duration`
   - `transcript_preview`
   - `stage_message`
   - `error_message`
4. Made `POST /api/recording/start` create a session in `starting`, run preparation, then switch to `recording`.
5. Preserved temporary files on startup failures by returning the failed `session_id`.

### Verified Tests

1. Starting without DeepSeek API Key returns an error and never enters `recording`.
2. Starting with an invalid output directory returns an error and exposes the failed session.
3. Starting with valid config transitions through preparation and returns `recording`.
4. Status exposes a user-facing stage message and error message.
5. Existing document finalization tests keep passing.

## Completed Step: WebSocket Status And Transcript Push

Goal: make realtime UI integration possible without polling. The frontend should receive status changes and transcript chunks from a stable WebSocket contract.

### Implemented Backend Changes

1. Added `/ws/transcription/{session_id}` WebSocket endpoint.
2. Added a connection manager keyed by `session_id`.
3. Broadcast state messages when sessions enter `recording`, `processing`, `completed`, or `error`.
4. Broadcast transcript messages when transcript text is appended.
5. Kept REST status endpoints as the source of truth for reconnect/recovery.

### Verified Tests

1. Connecting to a missing session closes or errors clearly.
2. Connecting to a valid session receives a status payload.
3. Appending transcript broadcasts a transcript payload.
4. Stopping a session broadcasts `processing` and `completed` states.

## Completed Step: Recorder And Transcriber Interfaces

Goal: replace the manual transcript append bridge with service boundaries that can later connect to sounddevice and faster-whisper without changing the session finalization flow.

### Implemented Backend Changes

1. Added `AudioRecorder` interface with an MVP fake implementation.
2. Added `Transcriber` interface with an MVP fake implementation.
3. Added `CapturePipeline` service that receives recorder/transcriber output and appends transcript text through the existing session path.
4. Kept `/api/recording/{session_id}/transcript` available as a test/debug bridge until real audio capture is stable.
5. Added `/api/recording/{session_id}/capture-once` as the MVP fake pipeline endpoint.

### Verified Tests

1. Fake recorder/transcriber can append transcript text to a session.
2. Generated transcript still broadcasts over WebSocket.
3. Stop/finalize flow remains unchanged.
4. Existing REST and WebSocket tests keep passing.

## Completed Step: Faster-Whisper File Transcription

Goal: replace the fake transcriber with a file-based faster-whisper implementation before touching live system audio capture.

### Implemented Backend Changes

1. Added `FasterWhisperTranscriber` behind the existing `Transcriber` interface.
2. Added lazy `faster_whisper` import so default tests and fake development path stay fast.
3. Added model factory injection for unit tests and future wiring.
4. Kept fake transcriber as default for fast tests and local development.

### Verified Tests

1. Fake transcriber remains the default and all existing tests stay fast.
2. File transcriber passes audio path and language into the model.
3. Auto language maps to `None` for faster-whisper.
4. Non-file fake sources are rejected by the file transcriber.

## Completed Step: Config-Driven Transcriber Selection

Goal: allow the backend to choose fake or faster-whisper transcriber from config without changing API code.

### Implemented Backend Changes

1. Added `transcriber_mode`, defaulting to `fake` for local development.
2. Built `CapturePipeline` from current config in the `capture-once` path.
3. Kept tests on fake mode by default.
4. Added tests for selecting `faster_whisper` mode through the pipeline factory.
5. Invalid transcriber modes are rejected by config validation.

### Verified Tests

1. Default config uses fake transcriber.
2. Explicit faster-whisper mode creates a `FasterWhisperTranscriber`.
3. Invalid transcriber mode returns a clear config validation error.

## Completed Step: File-Based Audio Capture Input

Goal: feed a real audio file path into the capture pipeline before implementing live system audio recording.

### Implemented Backend Changes

1. Added `FileCaptureRequest` with `audio_path`.
2. Added `FileAudioRecorder` that returns `AudioSegment(source=<audio_path>)`.
3. Reused config-driven transcriber selection for fake/faster-whisper.
4. Kept `capture-once` fake endpoint for smoke testing.
5. Added `/api/recording/{session_id}/capture-file`.

### Verified Tests

1. File capture rejects missing/nonexistent files.
2. File capture can use an injected transcriber without changing finalization.
3. Existing fake capture and WebSocket tests keep passing.

## Completed Step: macOS Audio Device Discovery

Goal: prepare for real system audio capture by discovering and validating the BlackHole device before implementing continuous recording.

### Implemented Backend Changes

1. Added an audio device discovery service behind the recorder boundary.
2. Detect BlackHole by device name case-insensitively.
3. Integrated discovery into startup preparation through injection.
4. Return a clear setup error if BlackHole is missing.
5. Keep default app startup from forcing hardware checks until config enables it.

### Verified Tests

1. Device discovery finds BlackHole from a stub device list.
2. Missing BlackHole returns a clear setup error.
3. Startup preparation can use the discovery result without touching real hardware in tests.

## Completed Step: Configurable Audio Readiness

Goal: expose a safe configuration switch so production-like runs can require BlackHole, while tests and development stay hardware-independent.

### Implemented Backend Changes

1. Added `require_audio_device`, defaulting to `false`.
2. Wired `StartupPreparer` to enforce BlackHole discovery when the flag is true.
3. Kept default startup compatible with machines without BlackHole.
4. Added `audio_discovery` injection to `create_app` for hardware-independent tests.

### Verified Tests

1. Default config does not require BlackHole.
2. `require_audio_device=true` fails startup when discovery cannot find BlackHole.
3. `require_audio_device=true` succeeds with a stub BlackHole device.

## Completed Step: SoundDevice Audio Segment Capture

Goal: implement a first real recorder boundary that can capture from BlackHole into temporary audio files, while preserving current session/finalization boundaries.

### Implemented Backend Changes

1. Added `SoundDeviceAudioRecorder` behind `AudioRecorder`.
2. Used discovered BlackHole device index for sounddevice capture.
3. Wrote short WAV segments into the session temp directory.
4. Kept `sounddevice` injectable so tests do not require real hardware.
5. Kept fake and file capture paths available for fast tests.

### Verified Tests

1. Recorder writes a WAV file into the session temp directory using the BlackHole device index.
2. Missing BlackHole returns a clear error.
3. Existing fake and file recorder paths remain unchanged.

## Completed Step: Continuous Capture Worker Lifecycle

Goal: call a capture pipeline repeatedly for an active session, feed each segment into the configured transcriber, and push transcript chunks over WebSocket through the existing append path.

### Implemented Backend Changes

1. Added `ContinuousCaptureWorker` with a daemon-thread loop per session.
2. Worker calls `CapturePipeline.capture_once`, appends non-empty transcript chunks, and reports capture errors.
3. Added injectable `CaptureWorker` lifecycle to `create_app`.
4. `start` starts an injected worker only after startup checks pass.
5. `stop` stops an injected worker before finalization, including error paths.
6. Default app does not wire real background audio capture yet, so existing local runs remain hardware-independent.

### Verified Tests

1. Worker appends transcript chunks until its configured iteration limit.
2. Worker reports capture errors and exits.
3. Recording lifecycle starts and stops an injected worker.

## Completed Step: Configurable SoundDevice Capture Mode

Goal: construct a production worker from `SoundDeviceAudioRecorder` and the configured transcriber when the user enables real audio capture.

### Implemented Backend Changes

1. Added `capture_mode`, defaulting to `manual`.
2. Allowed `capture_mode=sounddevice` to build an owned `ContinuousCaptureWorker`.
3. The owned worker uses `SoundDeviceAudioRecorder` and the config-selected transcriber.
4. `stop` stops and removes the owned worker before finalization.
5. Kept sounddevice injectable for tests, avoiding real hardware access.

### Verified Tests

1. Config defaults to `capture_mode=manual`.
2. Invalid capture modes return 422.
3. `capture_mode=sounddevice` writes a WAV segment into the session temp directory using injected sounddevice and BlackHole discovery.

## Next Step: Real Transcription Validation

Goal: validate real audio-to-text behavior with `capture_mode=sounddevice` and `transcriber_mode=faster_whisper` using a controlled audio fixture or model stub.

### Planned Backend Changes

1. Add tests around sounddevice capture plus faster-whisper stubbed transcription.
2. Surface capture/transcription errors through status/WebSocket while preserving temporary files.
3. Tune segment size and loop timing for practical local recording.

## Later Steps

1. Add live faster-whisper streaming/chunking behavior.
2. Build Electron UI on top of the stable API and WebSocket states.
