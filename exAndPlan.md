# Video2MD Execution And Plan

## 里程碑 1：后端 MVP 已落地

日期：2026-06-19

本阶段目标是先交付 PRD 中的后端最小闭环，避免在真实音频设备、Whisper 模型和 Electron UI 尚未稳定前扩大范围。

### 已执行操作

1. 搭建后端目录：
   - `backend/main.py`
   - `backend/models.py`
   - `backend/services/config_manager.py`
   - `backend/services/session_manager.py`
   - `backend/services/file_manager.py`
   - `backend/services/ai_organizer.py`
   - `backend/tests/`
2. 实现 FastAPI 应用入口 `backend.main:create_app`。
3. 实现配置读写：
   - `GET /api/config`
   - `POST /api/config`
4. 实现录制 session MVP：
   - `POST /api/recording/start`
   - `POST /api/recording/{session_id}/transcript`
   - `POST /api/recording/stop`
   - `GET /api/recording/status/{session_id}`
5. 实现文档管理：
   - `GET /api/documents`
   - `GET /api/documents/{document_id}`
6. 实现 DeepSeek Organizer：
   - 默认使用 DeepSeek API。
   - 测试中通过可注入 `AiOrganizer` stub 避免真实网络调用。
7. 实现文件管理规则：
   - 原始转录保存到 session 临时目录。
   - 最终 Markdown 保存到配置的输出目录。
   - 成功生成最终 Markdown 后才清理临时目录。
   - 空转录或失败时保留临时目录，避免数据丢失。
8. 新增后端测试：
   - 配置默认值。
   - 配置持久化。
   - 成功生成文档并清理临时文件。
   - 空转录失败并保留临时目录。
9. 更新项目文档：
   - `README.md`
   - `docs/setup_guide.md`
   - `docs/backend_plan.md`
   - `PRD.md`
   - `AGENTS.md`
   - `CLAUDE.md`

### 当前已具备能力

- 可以启动 FastAPI 后端。
- 可以保存和读取本地配置。
- 可以创建录制 session。
- 可以通过临时 transcript append 接口模拟实时转录输入。
- 可以停止 session，并将转录文本整理为 Markdown。
- 可以列出和读取生成后的 Markdown 文档。
- 可以在成功保存最终文档后清理中间文件。
- 可以通过自动化测试验证后端 MVP 主路径和关键失败路径。

### 当前验证结果

```bash
python -m pytest backend/tests -q
```

结果：

```text
4 passed
```

```bash
python -m compileall backend -q
```

结果：退出码为 0。

## 重要设计决策

### 1. 先做后端 MVP，不直接做全量桌面应用

PRD 范围包含 Electron、系统音频录制、Whisper、WebSocket、DeepSeek、文件清理和发布。一次性全做会让调试面过大，所以先实现后端文档生成闭环。

### 2. 保留 transcript append 作为临时桥接接口

`POST /api/recording/{session_id}/transcript` 不是最终产品交互，而是当前阶段用于模拟未来实时转录输出的后端入口。后续接入 faster-whisper 或 WebSocket 后，仍可复用同一套 session finalization 流程。

### 3. 成功后才清理临时文件

如果整理失败、转录为空或后续设备/模型异常，中间文件应保留，避免用户丢失已录制或已转录内容。

### 4. 点击开始录制必须先进入 starting

后续 UI 不应在用户点击“开始录制”后立即显示录制中。系统应先完成配置、输出目录、音频设备、转录器和 WebSocket 等准备工作，再进入 `recording` 并开始计时。

## 当前缺口

- 还没有真实系统音频录制。
- 还没有 faster-whisper 转录。
- 还没有 WebSocket 实时推送。
- 还没有 Electron 主窗口、配置窗口和悬浮球。
- 还没有 API Key 加密存储。
- 还没有 session 持久化。
- 还没有 DeepSeek 网络错误重试。
- 还没有应用打包发布流程。

## 下一步计划：Startup State Machine

下一步优先实现录制启动状态机，让未来 UI 的 loading、错误提示和计时边界有可靠后端依据。

### 目标

点击“开始录制”后：

```text
idle -> starting -> recording
```

只有准备成功后才进入：

```text
recording
```

异常时进入：

```text
error
```

### 计划改动

1. 扩展状态：
   - `idle`
   - `starting`
   - `recording`
   - `processing`
   - `completed`
   - `error`
2. 新增启动准备服务：
   - 检查 DeepSeek API Key。
   - 检查输出目录可创建、可写入。
   - 预留音频设备 readiness 检查。
   - 预留转录器 readiness 检查。
3. 扩展录制状态响应：
   - `status`
   - `duration`
   - `transcript_preview`
   - `stage_message`
   - `error_message`
4. 修改开始录制流程：
   - 创建 session 后先设为 `starting`。
   - 准备成功后切为 `recording`。
   - 准备失败时切为 `error` 并返回可读错误。
5. 保持失败保留临时文件的规则。

### 测试计划

1. 无 DeepSeek API Key 时，开始录制失败，不进入 `recording`。
2. 输出目录不可写时，开始录制失败，返回明确错误。
3. 配置有效时，开始录制返回 `recording`。
4. 状态接口返回 `stage_message` 和 `error_message`。
5. 现有文档生成和清理测试继续通过。

## 后续里程碑建议

1. 实现 Startup State Machine。
2. 增加 WebSocket 状态和转录推送。
3. 增加 `AudioRecorder` 与 `Transcriber` 服务接口和 fake 实现。
4. 接入 faster-whisper 的文件转录能力。
5. 接入 macOS BlackHole 系统音频录制。
6. 基于稳定后端 API 开始 Electron UI。

## 复盘备注

- `AGENTS.md` 与 `CLAUDE.md` 当前内容保持一致，用于记录本地项目记忆。
- `.gitignore` 忽略 `AGENTS.md`、`CLAUDE.md` 和 `PRD.md`，所以这些本地规划/指令文件不会进入普通 Git 提交。
- 后续如果希望 PRD 和计划进入版本库，需要调整 `.gitignore` 或将公开版本放到 `docs/` 下。

## 里程碑 2：补充里程碑文档维护规则

日期：2026-06-19

### 已执行操作

1. 更新 `AGENTS.md` 和 `CLAUDE.md`，新增 `exAndPlan.md` 维护规则。
2. 明确 AI 执行代码修改时：
   - 若根目录不存在 `exAndPlan.md`，必须创建。
   - 若已存在，必须追加新的里程碑记录。
   - 记录内容应包括本次代码操作、验证结果、影响范围和下一步计划。
3. 将本次规则变更记录回 `exAndPlan.md`，验证该文件作为复盘入口持续可用。

### 影响范围

- 本次仅修改文档和项目记忆，不修改业务代码。
- 后续所有 AI 代码操作都需要同步维护 `exAndPlan.md`。

### 验证计划

- 核对 `AGENTS.md` 和 `CLAUDE.md` 内容一致。
- 核对 `exAndPlan.md` 包含本次里程碑记录。

## 里程碑 3：实现 Startup State Machine

日期：2026-06-19

### 已执行操作

1. 新增 `backend/tests/test_startup_state.py`，先用测试描述启动准备行为：
   - DeepSeek API Key 缺失时，开始录制失败，不进入 `recording`。
   - 输出目录不可用时，开始录制失败并返回失败 session。
   - 配置有效时，开始录制返回 `recording`。
   - 状态接口返回 `stage_message` 和 `error_message`。
2. 新增 `backend/services/startup_preparer.py`：
   - 检查 DeepSeek API Key。
   - 检查输出目录可创建、可写入。
   - 保留音频设备 readiness 和转录器 readiness 占位，后续接真实实现。
3. 扩展 `backend/models.py`：
   - `RecordingStatus` 增加 `stage_message`。
   - `RecordingStatus` 增加 `error_message`。
4. 扩展 `backend/services/session_manager.py`：
   - 新 session 默认进入 `starting`。
   - session 记录可展示阶段文案。
5. 更新 `backend/main.py`：
   - `POST /api/recording/start` 创建 session 后先执行准备检查。
   - 准备成功后返回 `recording`。
   - 准备失败时进入 `error`，返回包含 `session_id` 和错误文案的响应，保留临时目录。
   - `processing`、`completed`、整理失败等路径同步维护 `stage_message`。
6. 更新项目文档：
   - `README.md`
   - `docs/setup_guide.md`
   - `docs/backend_plan.md`
   - `AGENTS.md`
   - `CLAUDE.md`

### 影响范围

- 后端 API 行为变更：`POST /api/recording/start` 不再无条件成功。
- 成功启动时，返回状态从原来的 `success` 改为 `recording`。
- 失败启动时，返回 400，并在 `detail` 中包含 `session_id` 和 `message`。
- 状态接口新增 `stage_message` 和 `error_message` 字段。

### 验证结果

```bash
python -m pytest backend/tests/test_startup_state.py -q
```

结果：

```text
3 passed
```

```bash
python -m pytest backend/tests -q
```

结果：

```text
7 passed
```

### 下一步计划

下一步建议实现 WebSocket 状态和转录推送，让 Electron 悬浮球可以订阅状态变化和转录文本，而不是轮询 REST 状态接口。

## 里程碑 4：实现 WebSocket 状态和转录推送

日期：2026-06-19

### 已执行操作

1. 新增 `backend/tests/test_websocket_transcription.py`，先用测试描述 WebSocket 行为：
   - 缺失 session 连接应明确断开。
   - 有效 session 连接后先收到当前 status。
   - 追加转录文本后收到 transcript 事件。
   - 停止录制后收到 `processing` 和 `completed` 状态事件。
2. 新增 `backend/services/websocket_manager.py`：
   - 按 `session_id` 管理连接。
   - 使用事件循环绑定的 `asyncio.Queue`，允许同步 REST handler 安全投递事件。
3. 更新 `backend/main.py`：
   - 新增 `/ws/transcription/{session_id}` WebSocket endpoint。
   - 在转录追加时广播 transcript 事件。
   - 在启动失败、整理失败、processing、completed 等状态变化时广播 status 事件。
   - 保留 REST 状态接口作为重连和恢复时的事实来源。
4. 更新项目文档：
   - `README.md`
   - `docs/setup_guide.md`
   - `docs/backend_plan.md`
   - `AGENTS.md`
   - `CLAUDE.md`

### 影响范围

- 后端新增 WebSocket 实时通道：`/ws/transcription/{session_id}`。
- 前端/悬浮球可以通过 WebSocket 获取初始状态、实时转录和整理状态。
- REST API 行为保持兼容，仍可通过状态接口查询 session 当前状态。

### 验证结果

```bash
python -m pytest backend/tests/test_websocket_transcription.py -q
```

结果：

```text
3 passed
```

```bash
python -m pytest backend/tests -q
```

结果：

```text
10 passed
```

```bash
python -m compileall backend -q
```

结果：退出码为 0。

### 下一步计划

下一步建议新增 `AudioRecorder` 和 `Transcriber` 服务接口及 fake 实现，让后端从“手动 append transcript”过渡到“录音/转录服务输出 transcript”，再接入 faster-whisper 和系统音频录制。

## 里程碑 5：实现 AudioRecorder/Transcriber fake 管线

日期：2026-06-19

### 已执行操作

1. 新增 `backend/tests/test_capture_pipeline.py`，先用测试描述 fake 录音/转录服务边界：
   - `capture-once` 可以通过 fake recorder/transcriber 产出转录文本。
   - 产出的转录文本会进入现有 session transcript。
   - 产出的转录文本会通过 WebSocket 推送。
   - 停止录制后的文档整理流程保持不变。
2. 新增 `backend/services/audio_recorder.py`：
   - 定义 `AudioRecorder` 接口。
   - 定义 `AudioSegment` 数据对象。
   - 提供 `FakeAudioRecorder`。
3. 新增 `backend/services/transcriber.py`：
   - 定义 `Transcriber` 接口。
   - 提供 `FakeTranscriber`。
4. 新增 `backend/services/capture_pipeline.py`：
   - 串联 recorder 和 transcriber。
   - 返回 transcript text，交给现有 session append 流程。
5. 更新 `backend/main.py`：
   - 抽出 `append_transcript_text`，让手动 append 和 fake capture 共用同一套保存/广播逻辑。
   - 新增 `POST /api/recording/{session_id}/capture-once`。
6. 更新项目文档：
   - `README.md`
   - `docs/setup_guide.md`
   - `docs/backend_plan.md`
   - `AGENTS.md`
   - `CLAUDE.md`

### 影响范围

- 后端新增 fake 录音/转录管线入口：`POST /api/recording/{session_id}/capture-once`。
- 现有 `/api/recording/{session_id}/transcript` 调试桥保留。
- 后续接入 sounddevice/BlackHole 和 faster-whisper 时，可以替换接口实现，减少 API 层改动。

### 验证结果

```bash
python -m pytest backend/tests/test_capture_pipeline.py -q
```

结果：

```text
2 passed
```

```bash
python -m pytest backend/tests -q
```

结果：

```text
12 passed
```

### 下一步计划

下一步建议实现 faster-whisper 文件转录能力：先让 transcriber 能处理已有音频文件，再接实时系统音频录制。

## 里程碑 6：实现 FasterWhisperTranscriber 文件转录适配层

日期：2026-06-19

### 已执行操作

1. 新增 `backend/tests/test_faster_whisper_transcriber.py`，先用测试描述 faster-whisper 适配层行为：
   - 传入音频文件路径。
   - 按配置传入语言参数。
   - `language=auto` 时传入 `None`。
   - 拼接并清理 faster-whisper segment 文本。
   - 拒绝 `fake://` 这类非文件 source。
2. 更新 `backend/services/transcriber.py`：
   - 新增 `FasterWhisperTranscriber`。
   - 懒加载 `faster_whisper.WhisperModel`，避免默认测试路径加载模型。
   - 支持注入 `model_factory`，便于单测和后续配置装配。
3. 更新 `backend/requirements.txt`：
   - 添加 `faster-whisper>=1.0.0`。
4. 更新项目文档：
   - `README.md`
   - `docs/setup_guide.md`
   - `docs/backend_plan.md`
   - `AGENTS.md`
   - `CLAUDE.md`

### 影响范围

- 默认 fake capture 管线不变，现有测试仍保持快速。
- 后端已有真实 faster-whisper 文件转录适配层，但尚未通过配置启用。
- 后续可以在不改 API 的情况下，把 `CapturePipeline` 装配到 `FasterWhisperTranscriber`。

### 验证结果

```bash
python -m pytest backend/tests/test_faster_whisper_transcriber.py -q
```

结果：

```text
3 passed
```

```bash
python -m pytest backend/tests -q
```

结果：

```text
15 passed
```

### 下一步计划

下一步建议实现配置驱动的 transcriber 选择：默认 fake，显式配置时使用 faster-whisper，并对非法模式给出清晰错误。

## 里程碑 7：实现配置驱动的 transcriber 选择

日期：2026-06-19

### 已执行操作

1. 更新 `backend/tests/test_config.py`：
   - 默认配置包含 `transcriber_mode=fake`。
   - 显式 `faster_whisper` 可以保存并持久化。
   - 非法模式返回 422。
2. 新增 `backend/tests/test_transcriber_factory.py`：
   - `fake` 模式构建 `FakeTranscriber`。
   - `faster_whisper` 模式构建 `FasterWhisperTranscriber`，并继承 `whisper_model` 和 `language`。
3. 更新 `backend/models.py`：
   - `AppConfig` 新增 `transcriber_mode`，类型限制为 `fake` 或 `faster_whisper`。
4. 更新 `backend/services/capture_pipeline.py`：
   - 新增 `build_capture_pipeline(config)`。
   - 根据配置选择 fake 或 faster-whisper transcriber。
5. 更新 `backend/main.py`：
   - `capture-once` 根据当前配置构建 pipeline。
   - 将 transcriber 的已知输入错误转换为 400。
6. 更新项目文档：
   - `README.md`
   - `docs/setup_guide.md`
   - `docs/backend_plan.md`
   - `AGENTS.md`
   - `CLAUDE.md`

### 影响范围

- 配置新增 `transcriber_mode` 字段，默认 `fake`，不影响现有快速测试路径。
- 显式设置 `faster_whisper` 后，`capture-once` 会装配 `FasterWhisperTranscriber`。
- 当前 fake recorder 仍会产出 `fake://` source，因此 faster-whisper 模式下 `capture-once` 会返回 400，直到下一步接入文件音频输入。

### 验证结果

```bash
python -m pytest backend/tests/test_config.py backend/tests/test_transcriber_factory.py backend/tests/test_capture_pipeline.py -q
```

结果：

```text
8 passed
```

```bash
python -m pytest backend/tests -q
```

结果：

```text
19 passed
```

### 下一步计划

下一步建议实现文件音频输入：让 API 能接收已有音频文件路径，交给 faster-whisper transcriber 处理，再进入现有 transcript/WebSocket/文档整理流程。

## 里程碑 8：实现文件音频输入

日期：2026-06-19

### 已执行操作

1. 新增 `backend/tests/test_file_capture.py`，先用测试描述文件输入行为：
   - 缺失音频文件返回 400。
   - 已有文件可以进入 capture pipeline。
   - 文件转录结果会进入 session transcript。
   - 文件转录结果会通过 WebSocket 推送。
   - 停止录制后的文档整理流程保持不变。
2. 更新 `backend/models.py`：
   - 新增 `FileCaptureRequest`，包含 `audio_path`。
3. 更新 `backend/services/audio_recorder.py`：
   - 新增 `FileAudioRecorder`。
   - 文件不存在时返回 `音频文件不存在`。
   - 文件存在时返回 `AudioSegment(source=<audio_path>, content=<file text>)`。
4. 更新 `backend/services/capture_pipeline.py`：
   - `build_capture_pipeline` 支持传入 recorder。
5. 更新 `backend/main.py`：
   - 新增 `POST /api/recording/{session_id}/capture-file`。
   - 复用当前 config-driven transcriber 选择。
   - 复用 transcript 保存、WebSocket 推送和后续文档整理流程。
6. 更新项目文档：
   - `README.md`
   - `docs/setup_guide.md`
   - `docs/backend_plan.md`
   - `AGENTS.md`
   - `CLAUDE.md`

### 影响范围

- 后端新增文件输入接口：`POST /api/recording/{session_id}/capture-file`。
- fake 模式下测试文件内容会作为 transcript，用于快速验证链路。
- faster-whisper 模式下会使用文件路径作为 source，供 `FasterWhisperTranscriber` 处理。
- 现有 `capture-once` 和手动 transcript append 调试桥保留。

### 验证结果

```bash
python -m pytest backend/tests/test_file_capture.py -q
```

结果：

```text
3 passed
```

```bash
python -m pytest backend/tests -q
```

结果：

```text
22 passed
```

### 下一步计划

下一步建议实现 macOS 音频设备发现：先用可测试的设备列表检测 BlackHole，给启动准备阶段提供真实录音前的 readiness 判断。

## 里程碑 9：实现 macOS BlackHole 设备发现

日期：2026-06-19

### 已执行操作

1. 新增 `backend/tests/test_audio_device_discovery.py`，先用测试描述设备发现行为：
   - 可从 stub 设备列表中找到 BlackHole。
   - 设备名匹配大小写不敏感。
   - 缺失 BlackHole 时抛出 `未找到 BlackHole 音频设备`。
2. 更新 `backend/tests/test_startup_state.py`：
   - 验证 `StartupPreparer` 可以通过注入的设备发现服务报告缺失 BlackHole。
3. 新增 `backend/services/audio_device.py`：
   - 定义 `AudioDevice`。
   - 定义 `AudioDeviceDiscovery`。
   - 定义 `AudioDeviceNotFoundError`。
   - 懒加载 `sounddevice` 查询设备，避免默认测试路径依赖真实音频硬件。
4. 更新 `backend/services/startup_preparer.py`：
   - 支持注入 `AudioDeviceDiscovery`。
   - 支持 `require_audio_device` 开关。
   - 缺失 BlackHole 时转换为 `StartupPreparationError`。
5. 更新 `backend/requirements.txt`：
   - 添加 `sounddevice>=0.4.6`。
6. 更新项目文档：
   - `README.md`
   - `docs/setup_guide.md`
   - `docs/backend_plan.md`
   - `AGENTS.md`
   - `CLAUDE.md`

### 影响范围

- 已具备 BlackHole 设备发现能力。
- 默认 app 启动暂不强制检查真实硬件，避免开发/测试环境无 BlackHole 时无法运行。
- 后续可通过配置开启强制音频设备 readiness。

### 验证结果

```bash
python -m pytest backend/tests/test_audio_device_discovery.py backend/tests/test_startup_state.py -q
```

结果：

```text
7 passed
```

```bash
python -m pytest backend/tests -q
```

结果：

```text
26 passed
```

### 下一步计划

下一步建议实现可配置音频 readiness：新增 `require_audio_device` 配置，默认关闭；开启时启动准备必须检测到 BlackHole。

## 里程碑 10：实现可配置音频 readiness

日期：2026-06-19

### 已执行操作

1. 更新 `backend/tests/test_config.py`：
   - 默认配置包含 `require_audio_device=false`。
   - `require_audio_device=true` 可以保存并持久化。
2. 更新 `backend/tests/test_startup_state.py`：
   - 开启 `require_audio_device` 且缺失 BlackHole 时，启动录制返回 400。
   - 开启 `require_audio_device` 且发现 BlackHole 时，启动录制进入 `recording`。
3. 更新 `backend/models.py`：
   - `AppConfig` 新增 `require_audio_device: bool = False`。
4. 更新 `backend/main.py`：
   - `create_app` 支持注入 `audio_discovery`。
   - `start_recording` 每次按当前配置创建 `StartupPreparer`。
   - 仅当 `require_audio_device=true` 时强制 BlackHole 检查。
5. 更新项目文档：
   - `README.md`
   - `docs/setup_guide.md`
   - `docs/backend_plan.md`
   - `AGENTS.md`
   - `CLAUDE.md`

### 影响范围

- 默认开发/测试环境不强制真实硬件检查。
- 用户显式开启 `require_audio_device` 后，开始录制前必须检测到 BlackHole。
- 该能力为后续真实 macOS 系统音频录制提供 readiness 基础。

### 验证结果

```bash
python -m pytest backend/tests/test_config.py backend/tests/test_startup_state.py -q
```

结果：

```text
9 passed
```

```bash
python -m pytest backend/tests -q
```

结果：

```text
28 passed
```

### 下一步计划

下一步建议实现 macOS 连续音频捕获：新增 `SoundDeviceAudioRecorder`，基于 BlackHole device index 写入 session 临时音频片段。

## 里程碑 11：创建 video2md conda 环境

日期：2026-06-19

### 已执行操作

1. 检查本机 conda 可用性，确认已有环境中不存在 `video2md`。
2. 创建 conda 环境：

```bash
conda create -n video2md python=3.11 -y
```

3. 在 `video2md` 环境中安装后端依赖：

```bash
conda run -n video2md python -m pip install -r backend/requirements.txt
```

4. 更新项目文档：
   - `README.md`
   - `docs/setup_guide.md`
   - `AGENTS.md`
   - `CLAUDE.md`

### 影响范围

- 本地开发环境固定为 `video2md` conda 环境。
- 当前 Python 版本为 3.11.15。
- 后端依赖已包含 FastAPI、uvicorn、pytest、httpx、sounddevice 和 faster-whisper 等 MVP 依赖。
- 本次未修改业务代码。

### 验证结果

```bash
conda run -n video2md python --version
```

结果：

```text
Python 3.11.15
```

```bash
conda run -n video2md python -m pytest backend/tests -q
```

结果：

```text
28 passed, 1 warning
```

```bash
conda run -n video2md python -m compileall backend -q
```

结果：通过。

### 下一步计划

下一步建议继续实现 macOS 连续音频捕获：新增 `SoundDeviceAudioRecorder`，基于 BlackHole device index 写入 session 临时音频片段。

## 里程碑 12：实现 SoundDevice 短片段录制边界

日期：2026-06-19

### 已执行操作

1. 新增 `backend/tests/test_sounddevice_audio_recorder.py`，先用测试描述真实录制边界：
   - `SoundDeviceAudioRecorder` 使用注入的 BlackHole device index 发起录制。
   - 录制结果写入 session 临时目录下的 WAV 文件。
   - 缺失 BlackHole 时抛出 `未找到 BlackHole 音频设备`。
2. 更新 `backend/services/audio_recorder.py`：
   - 新增 `SoundDeviceAudioRecorder`。
   - 支持注入 `AudioDeviceDiscovery` 和 `sounddevice` 模块，避免单测依赖真实硬件。
   - 通过标准库 `wave` 写入 16-bit PCM WAV 片段。
   - 保持 `FakeAudioRecorder` 和 `FileAudioRecorder` 行为不变。
3. 更新项目文档：
   - `README.md`
   - `docs/setup_guide.md`
   - `docs/backend_plan.md`
   - `AGENTS.md`
   - `CLAUDE.md`

### 影响范围

- 后端已有可测试的 sounddevice/BlackHole 短片段录制边界。
- 该实现当前不是后台连续录制 worker，也不是用户直接调用的 REST API。
- 后续连续捕获可以循环调用该 recorder，并把每个 WAV 片段交给现有 transcriber/pipeline。

### 验证结果

```bash
python -m pytest backend/tests/test_sounddevice_audio_recorder.py -q
```

结果：

```text
2 passed
```

```bash
python -m pytest backend/tests -q
```

结果：

```text
30 passed
```

```bash
python -m compileall backend -q
```

结果：通过。

```bash
cmp -s AGENTS.md CLAUDE.md; echo $?
```

结果：

```text
0
```

### 下一步计划

下一步建议实现连续捕获 worker：录制中的 session 循环捕获短音频片段，交给配置选择的 transcriber，并通过既有 WebSocket 推送 transcript/status。

## 里程碑 13：实现连续捕获 worker 生命周期

日期：2026-06-19

### 已执行操作

1. 新增 `backend/tests/test_continuous_capture_worker.py`，先用测试描述连续捕获行为：
   - worker 可循环调用 capture pipeline 并追加 transcript。
   - capture 失败时上报可展示错误并退出。
   - FastAPI 录制生命周期会 start/stop 注入的 capture worker。
2. 新增 `backend/services/continuous_capture.py`：
   - 定义 `CaptureWorker` 协议。
   - 新增 `ContinuousCaptureWorker`，按 session 启动 daemon thread。
   - 循环执行 `capture_once -> append_transcript`，支持 stop event、轮询间隔和测试用迭代上限。
3. 更新 `backend/main.py`：
   - `create_app` 支持注入 `capture_worker`。
   - 启动准备成功并进入 `recording` 后才启动注入 worker。
   - `stop` 收到有效 session 后先停止注入 worker，再执行 transcript 校验和文档整理。
4. 更新项目文档：
   - `README.md`
   - `docs/setup_guide.md`
   - `docs/backend_plan.md`
   - `AGENTS.md`
   - `CLAUDE.md`

### 影响范围

- 后端已有连续捕获 worker 的可测试生命周期边界。
- 默认 `create_app()` 仍不装配真实后台录音 worker，避免本地启动直接访问声卡权限或 BlackHole。
- 后续可在显式配置真实音频捕获时，将 `SoundDeviceAudioRecorder` 和配置选择的 transcriber 装入 `ContinuousCaptureWorker`。

### 验证结果

```bash
python -m pytest backend/tests/test_continuous_capture_worker.py -q
```

结果：

```text
3 passed
```

```bash
python -m pytest backend/tests -q
```

结果：

```text
33 passed
```

```bash
python -m compileall backend -q
```

结果：通过。

```bash
cmp -s AGENTS.md CLAUDE.md; echo $?
```

结果：

```text
0
```

### 下一步计划

下一步建议实现真实连续音频捕获装配：增加显式配置或 API 开关，将 `SoundDeviceAudioRecorder`、`ContinuousCaptureWorker` 和 faster-whisper/file transcriber 串成可控的真实录制链路。

## 里程碑 14：将项目中英文注释转为中文

日期：2026-06-19

### 已执行操作

1. 扫描 `backend/` 下所有 `.py` 文件，识别英文注释（`#` 行内注释和 `"""..."""` docstring）。
2. 将英文注释逐一转为中文，覆盖以下文件：
   - `backend/__init__.py`：包 docstring。
   - `backend/main.py`：2 处行内注释（持续捕获注入、MVP 桥接接口）。
   - `backend/services/ai_organizer.py`：1 处 docstring + 1 处行内注释。
   - `backend/services/audio_device.py`：1 处行内注释（懒加载）。
   - `backend/services/audio_recorder.py`：2 处 docstring + 3 处行内注释。
   - `backend/services/config_manager.py`：1 处行内注释（密钥本地保存）。
   - `backend/services/continuous_capture.py`：2 处 docstring + 1 处行内注释。
   - `backend/services/file_manager.py`：1 处行内注释（临时文件清理）。
   - `backend/services/startup_preparer.py`：1 处行内注释（占位）。
   - `backend/services/transcriber.py`：1 处 docstring + 2 处行内注释。
   - `backend/services/websocket_manager.py`：1 处行内注释（事件循环调度）。
3. 测试文件（`backend/tests/`）中无英文注释，无需修改。

### 影响范围

- 仅修改注释文本，不涉及业务逻辑、API 行为或测试断言。
- 函数名、变量名、类型注解等代码标识符未修改。

### 验证结果

```bash
python -m pytest backend/tests -q
```

结果：

```text
33 passed
```

所有已有测试继续通过，注释翻译未引入回归。

### 下一步计划

继续推进真实连续音频捕获装配。

## 里程碑 15：实现 capture_mode=sounddevice 装配路径

日期：2026-06-19

### 已执行操作

1. 更新 `backend/tests/test_config.py`，先用测试描述配置行为：
   - 默认 `capture_mode=manual`。
   - `capture_mode=sounddevice` 可以保存并持久化。
   - 非法 capture mode 返回 422。
2. 新增 `backend/tests/test_sounddevice_capture_mode.py`：
   - 通过注入 fake sounddevice 和 BlackHole discovery，验证 `capture_mode=sounddevice` 启动录制后会自动写入 session WAV 片段。
3. 更新 `backend/models.py`：
   - `AppConfig` 新增 `capture_mode: manual | sounddevice`，默认 `manual`。
4. 更新 `backend/main.py`：
   - 支持注入 `sounddevice_module`、`capture_interval_seconds`、`capture_max_iterations`，用于测试和显式装配。
   - `capture_mode=sounddevice` 时构建 `SoundDeviceAudioRecorder`。
   - 将 recorder 注入 `build_capture_pipeline`，再装入 `ContinuousCaptureWorker`。
   - 按 session 保存 owned worker，停止录制时先 stop 并移除 worker。
5. 更新项目文档：
   - `README.md`
   - `docs/setup_guide.md`
   - `docs/backend_plan.md`
   - `AGENTS.md`
   - `CLAUDE.md`

### 影响范围

- 默认行为仍是 `capture_mode=manual`，不会自动碰真实音频硬件。
- 显式设置 `capture_mode=sounddevice` 后，开始录制会自动启动 sounddevice 连续捕获 worker。
- fake transcriber 不会从 WAV 字节生成真实文本；真实音频转文本验证应配合 `transcriber_mode=faster_whisper` 或模型 stub。

### 验证结果

```bash
python -m pytest backend/tests -q
```

结果：

```text
35 passed
```

```bash
python -m compileall backend -q
```

结果：通过。

```bash
cmp -s AGENTS.md CLAUDE.md; echo $?
```

结果：

```text
0
```

### 下一步计划

下一步建议验证 `capture_mode=sounddevice + transcriber_mode=faster_whisper` 的真实转录装配路径：通过模型工厂/stub 或短音频 fixture 验证 WAV 片段进入 faster-whisper 并产出 transcript/WebSocket 事件。
