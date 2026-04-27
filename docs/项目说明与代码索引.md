<a id="project-guide-zh"></a>

# 项目说明与代码索引

[中文](#project-guide-zh) | [English](#project-guide-en)

这份文档用于快速理解项目整体逻辑、核心代码位置和答辩讲解口径。它把“系统分层、通信方式、核心流程、功能实现、代码索引、常见追问”放在同一份说明里，既可以按顺序阅读，也可以拆成 PPT 或现场讲解提纲。

## 1. 一句话总览

本项目是一个基于 `Flask + Flask-SocketIO + LiveKit` 的在线视频会议系统，覆盖账号体系、会议创建与加入、多人音视频、屏幕共享、聊天附件、会议历史、管理员后台和基础诊断。

英文备用：

> This is an online meeting system built with Flask, Flask-SocketIO and LiveKit, covering accounts, rooms, multi-party media, screen sharing, chat attachments, administration and meeting history.

可以用一句更工程化的话概括：

> 页面负责展示，JavaScript 负责交互，Flask 负责业务，Socket.IO 负责实时状态，LiveKit 负责音视频媒体传输。

## 2. 项目解决的问题

这个项目不是只做“摄像头能显示”的 Demo，而是把一个会议系统常见的完整流程串了起来：

- 用户注册、登录、退出和会话控制
- 创建会议、加入会议、会议历史
- 房间内摄像头、麦克风和屏幕共享
- 聊天、表情、@ 提及、图片/视频/文档附件
- 主持人操作、管理员后台和密码重置申请
- 中英文界面、RTC/LiveKit 诊断、录屏和背景虚化

答辩时重点强调：它更像一个完整 Web 应用，而不是单独的 WebRTC 实验页面。

## 3. 主要页面入口

| 路径 | 页面 | 代码位置 |
| --- | --- | --- |
| `/` | 首页 / 创建会议 / 加入会议 | `templates/index.html`、`index()` |
| `/login` | 登录页 | `templates/login.html`、`login()` |
| `/register` | 注册页 | `templates/register.html`、`register()` |
| `/forgot-password` | 找回密码申请页 | `templates/forgot_password.html`、`forgot_password_page()` |
| `/quickstart` | 快速开始页 | `templates/quickstart.html`、`quickstart_page()` |
| `/help` | 用户指南 | `templates/help.html`、`help_page()` |
| `/support` | 支持页 | `templates/support.html`、`support_page()` |
| `/account` | 个人账户与偏好 | `templates/account.html`、`account_page()` |
| `/history` | 历史会议 | `templates/history.html`、`history()` |
| `/room/<room_id>` | 会议房间 | `templates/room.html`、`room_page()` |
| `/admin` | 管理员后台 | `templates/admin.html`、`admin_dashboard()` |

这些页面入口和根目录 `README.md` 中的“使用入口”保持一致。

## 4. 技术架构

| 层级 | 主要技术 / 文件 | 职责 |
| --- | --- | --- |
| 页面模板层 | `templates/*.html` | 登录页、首页、会议页、历史页、账号页、管理员后台等页面骨架 |
| 前端交互层 | `static/*.js` | 处理按钮事件、调用接口、连接 Socket.IO 和 LiveKit、渲染聊天与视频界面 |
| Flask 后端层 | `app.py` | 账号、会议、权限、上传、后台管理、翻译、Socket.IO 事件、LiveKit token |
| 实时状态层 | Flask-SocketIO + 内存状态 | 同步成员进出、聊天、共享屏幕、主持人结束会议等状态；关键运行态现在通过 `runtime_state_lock` 收紧并发读写 |
| 音视频媒体层 | LiveKit SFU | 传输摄像头、麦克风、屏幕共享和远端媒体轨道 |
| 持久化层 | SQLite / SQLAlchemy | 用户、会议、参会记录、找回密码申请等数据 |

当前重构巡检结论见 [REFACTOR_AUDIT.md](REFACTOR_AUDIT.md)。维护时应优先保证房间状态一致性，再逐步拆分 `app.py` 和房间前端脚本。

## 4.1 中英文和手机/电脑端适配

中英文适配：

- `translations.py` 是主要翻译表，`zh` 和 `en` key 集当前保持一致。
- 页面模板优先用 `t('key')`；房间内部分运行时提示和浏览器能力提示使用显式中英文分支。
- `check_i18n.py` 用于检查模板中遗漏的硬编码中文，提交前应运行。
- 用户可以通过语言切换入口或 `/account` 默认语言偏好影响后续页面语言。

手机端和电脑端适配：

- 首页手机端有扫码入会入口，电脑端保留会议号、密码和复制邀请链接流程。
- 房间页电脑端是会议网格和右侧聊天栏；手机端聊天区域重排为底部面板，并处理触摸滚动和输入框可见性。
- `room_livekit.js` 会按移动端/桌面端选择不同媒体发布参数，手机端更偏保守。
- `_room_scripts.html` 对移动端全屏、iOS 视频全屏、横屏锁定、触摸恢复播放、屏幕共享观看做了专门处理。
- `style.css` 和 `room.css` 分别维护通用页面、会议页在不同断点下的布局规则。

## 5. 为什么使用 LiveKit，而不是浏览器 Mesh

如果每个浏览器都和其他浏览器直接建立 WebRTC 连接，人数增加后连接数量和每个用户的上行带宽都会快速增长。例如 5 人会议时，每个用户都要同时维护多条连接，浏览器负载、网络压力和调试复杂度都会上升。

当前项目使用 LiveKit SFU：每个用户把自己的媒体发给 LiveKit，再由 LiveKit 转发给其他人。这样更适合多人会议，也更容易处理远端轨道、重连和网络波动。

现场可以这样说：

> 我把媒体传输交给 LiveKit，是为了把项目重点放在会议业务、权限控制和系统集成上，而不是从零实现一套多人媒体服务器。

## 6. 前端和后端如何通信

项目里主要有四种通信方式。答辩时如果被问“前端怎么和后端交互”，优先按这个分类回答。

### 6.1 HTML 表单提交

适合账号和后台管理这类传统页面操作。

| 功能 | 前端模板 | 后端入口 |
| --- | --- | --- |
| 注册 | `templates/register.html` | `/register`，`register()` |
| 登录 | `templates/login.html` | `/login`，`login()` |
| 账号设置 | `templates/account.html` | `/account`，`account_page()` |
| 管理员操作 | `templates/admin.html` | 多个 `/admin/...` 路由 |

特点：

- 前端使用普通 `<form method="post">`。
- 后端通过 `request.form.get(...)` 读取字段。
- 页面提交后由 Flask 返回新页面或重定向。

### 6.2 fetch 调用 Flask API

适合创建会议、校验入会、获取 LiveKit token、上传附件、翻译、录屏转封装等业务接口。

| 功能 | 后端接口 |
| --- | --- |
| 创建会议 | `/api/create_room` |
| 入会校验 | `/api/join_room` |
| 获取 LiveKit token | `/api/livekit/token` |
| 服务健康检查 | `/api/healthz` |
| 上传媒体附件 | `/api/chat_upload_media` |
| 上传文档附件 | `/api/chat_upload_doc` |
| 录屏转 MP4 | `/api/remux-recording` |
| 翻译聊天消息 | `/api/translate_message`、`/api/translate_to_english` |

特点：

- 前端使用 `fetch(...)`。
- 后端使用 `request.get_json()`、`request.form` 或 `request.files`。
- 后端返回 JSON、页面或文件流。

### 6.3 Socket.IO 实时事件

适合会议中不应该刷新页面的实时行为。

| 功能 | Socket 事件 |
| --- | --- |
| 真正加入房间 | `join_room` |
| 更新显示名称 | `update_profile` |
| 发送聊天 | `meeting_chat_send` |
| 清空聊天 | `meeting_chat_clear` |
| 撤回聊天 | `meeting_chat_retract` |
| 同步屏幕共享状态 | `room_ui_event` |
| 主持人结束会议 | `host_end_meeting` |
| 主动离会 | `leave_room` |

特点：

- 前端使用 `socket.emit(...)`。
- 后端收到事件后可以立刻广播给同房间成员。
- Socket.IO 维护的是成员、聊天、主持人动作和 UI 级房间状态。

### 6.4 LiveKit 媒体连接

摄像头、麦克风和屏幕共享媒体不经过 Flask 主应用转发。

| 媒体能力 | 实现位置 |
| --- | --- |
| 摄像头 | `static/room_livekit.js` |
| 麦克风 | `static/room_livekit.js` |
| 屏幕共享视频 | `static/room_livekit.js` |
| 屏幕共享音频 | `static/room_livekit.js` |

Flask 只负责鉴权并签发 LiveKit token，浏览器拿到 token 后直接连接 LiveKit 服务。

## 7. 关键文件索引

### 7.1 后端核心

| 文件 | 说明 |
| --- | --- |
| `app.py` | 项目后端核心，包含路由、数据库模型、管理员逻辑、聊天、附件、翻译、Socket.IO 事件和 LiveKit token 生成 |
| `translations.py` | 中英文界面文案 |
| `check_i18n.py` | 检查模板中未抽取的中文文案 |

### 7.2 页面模板

| 文件 | 说明 |
| --- | --- |
| `templates/login.html` | 登录页 |
| `templates/register.html` | 注册页 |
| `templates/index.html` | 首页，负责创建会议、加入会议、扫码入会 |
| `templates/room.html` | 会议页入口 |
| `templates/_room_layout.html` | 会议页布局骨架 |
| `templates/_room_scripts.html` | 会议页主脚本入口，负责 Socket.IO 事件、按钮绑定和房间业务调度 |
| `templates/account.html` | 用户偏好和账号设置页 |
| `templates/admin.html` | 管理员后台页 |
| `templates/history.html` | 历史会议页 |
| `templates/attachment_view.html` | 聊天附件查看页 |
| `templates/help.html`、`templates/support.html` | 帮助和支持页面 |

### 7.3 前端脚本和样式

| 文件 | 说明 |
| --- | --- |
| `static/room_livekit.js` | LiveKit 连接、摄像头、麦克风、屏幕共享、媒体轨道同步 |
| `static/room_chat.js` | 聊天消息渲染、@ 提及、表情面板、附件消息渲染 |
| `static/room_ui.js` | 会议界面渲染、布局调度、参与者卡片更新 |
| `static/room_utils.js` | 复制文本、HTML 转义、媒体 track 辅助函数等工具 |
| `static/room_diagnostics.js` | RTC / LiveKit 诊断信息展示 |
| `static/room.css` | 会议页样式 |
| `static/style.css` | 通用页面样式 |

## 8. 数据如何存储

### 8.1 数据库存储

数据库模型集中在 `app.py` 中。

| 模型 | 作用 |
| --- | --- |
| `User` | 存用户账号、密码哈希、管理员状态、启用状态、显示名、语言和默认入会偏好 |
| `Meeting` | 存会议号、会议密码、主持人、会议状态、创建时间和结束时间 |
| `MeetingParticipant` | 存参会记录，包括谁加入、何时加入、何时离开 |
| `PasswordResetRequest` | 存找回密码申请，供管理员后台处理 |

### 8.2 内存运行态

数据库负责持久化，会议进行中的实时状态主要存在内存中。

| 变量 | 作用 |
| --- | --- |
| `rooms` | 记录每个房间的在线成员、聊天记录、共享屏幕状态、主持人是否在场等 |
| `sid_to_user` | 把 Socket.IO 的 `request.sid` 映射到当前用户和房间 |
| `user_active_sids` | 记录一个用户当前有哪些活跃 socket，用于会话控制和踢人 |

这也意味着当前项目更适合单实例运行。如果要多实例部署，需要把运行态迁移到 Redis 等共享存储。

## 9. 核心流程

### 9.1 注册与登录

注册流程：

1. `register.html` 通过普通表单提交用户名和密码。
2. Flask `/register` 路由读取表单。
3. 后端检查用户名和密码是否为空、用户名是否已存在。
4. 调用 `user.set_password(password)` 保存密码哈希。
5. 写入数据库后调用 `login_user(user)` 建立登录态。
6. 写入 `session["session_version"]` 后跳转首页。

登录流程：

1. `login.html` 表单提交到 `/login`。
2. 后端按用户名查询 `User`。
3. 调用 `user.check_password(password)` 校验密码哈希。
4. 检查账号是否被禁用。
5. 登录成功后刷新 `session_version`。
6. 调用 `login_user(user)` 建立会话。
7. 调用 `disconnect_user_sockets(...)` 清理旧 socket。

答辩口径：

> 注册和登录都不是前端直接改数据库，而是通过 Flask 路由验证后写入或读取数据库。密码使用哈希存储，登录态由 Flask-Login 维护，`session_version` 用于让旧登录会话失效。

### 9.2 创建会议

流程：

1. 用户在首页点击“创建会议”。
2. 前端调用 `POST /api/create_room`。
3. 后端 `api_create_room()` 生成会议号和密码。
4. 后端创建 `Meeting` 数据库记录。
5. 后端初始化 `rooms[room_id]` 运行时房间状态。
6. 后端返回 `room_id`、`password` 和 `join_url`。
7. 前端显示会议号、密码和邀请链接。

关键点：

- `Meeting` 是持久化记录。
- `rooms[room_id]` 是运行时实时状态。
- 创建会议时两者都会初始化。

### 9.3 加入会议

加入会议分三步，答辩时要分清楚。

第一步：首页做 HTTP 校验：

1. 用户输入会议号和密码。
2. 前端调用 `POST /api/join_room`。
3. 后端检查房间是否存在、是否过期、密码是否正确。
4. 校验通过后，前端跳转到 `/room/<room_id>?pwd=...`。

`/api/join_room` 只负责校验，不是真正进入实时房间。

第二步：房间页加入 Socket.IO 实时房间：

1. 房间页加载 `_room_scripts.html`。
2. 前端执行 `const socket = io()` 建立 Socket.IO 连接。
3. 前端发送 `socket.emit("join_room", { room_id, password, user_name })`。
4. 后端 `on_join_room(data)` 再次校验登录态、房间状态和密码。
5. 后端将当前 `request.sid` 写入 `rooms[room_id]["participants"]`。
6. 后端写入 `sid_to_user`。
7. 后端调用 Socket.IO 的 `join_room(room_id)`。
8. 后端记录 `MeetingParticipant`。
9. 后端通过 `join_ok` 把成员列表、聊天历史、共享状态发回前端。
10. 后端广播 `participant_joined` 给其他成员。

第三步：获取 LiveKit token 并连接媒体房间：

1. 前端拿到当前 Socket.IO 的 `self_sid`。
2. 前端调用 `POST /api/livekit/token`。
3. 请求中带上 `room_id`、`password`、`participant_sid` 和 `name`。
4. 后端 `api_livekit_token()` 检查房间号、密码、sid 是否已登记、sid 是否属于当前用户。
5. 验证通过后，后端用 LiveKit API key / secret 生成 JWT token。
6. 前端在 `room_livekit.js` 中调用 `activeRoom.connect(...)` 连接 LiveKit。

答辩口径：

> 进入会议不是一步完成的。先用 HTTP 校验会议密码，再用 Socket.IO 加入实时房间，最后拿 LiveKit token 连接音视频媒体房间。业务身份校验和媒体连接是分开的。

## 10. 音视频与会议功能

### 10.1 摄像头和麦克风

用户可以在 `account.html` 保存默认入会偏好，后端 `/account` 将偏好保存到 `User.auto_enable_camera`、`User.auto_enable_microphone` 和 `User.auto_enable_speaker`。房间页加载后，`_room_scripts.html` 根据偏好决定是否自动开启摄像头或麦克风。

真正控制媒体轨道的是 `room_livekit.js`：

| 函数 | 作用 |
| --- | --- |
| `buildRoomOptions()` | 定义摄像头、麦克风采集参数和发布参数 |
| `setCameraEnabled(nextEnabled)` | 调用 LiveKit 本地参会者对象控制摄像头 |
| `setMicrophoneEnabled(nextEnabled)` | 调用 LiveKit 本地参会者对象控制麦克风 |

移动端和桌面端会使用不同采集参数。移动端更保守，主要是为了降低功耗、发热和网络压力。

### 10.2 屏幕共享

前端流程：

1. 用户点击“共享屏幕”按钮。
2. `_room_scripts.html` 处理是否共享系统音频、是否保留麦克风等选项。
3. 前端调用 `controller.setScreenShareEnabled(...)`。
4. `room_livekit.js` 调用 LiveKit 的屏幕共享接口。

共享模式：

| 模式 | 适合场景 | 目标 |
| --- | --- | --- |
| `motion` | 视频、动画、光标移动较多的内容 | 优先保证流畅度 |
| `detail` | PPT、文档、代码等文本内容 | 优先保证清晰度 |

后端仍然要参与屏幕共享规则控制：

1. 前端通过 `room_ui_event` 上报 `screen_share_started` 或 `screen_share_stopped`。
2. 后端检查当前房间是否已有共享者。
3. 如果已有其他人共享，则返回 `screen_share_denied`。
4. 如果允许共享，后端写入 `room["active_sharer_sid"]` 和 `room["active_sharer_user_id"]`。
5. 停止共享时，后端清空共享者状态并广播给其他成员。

答辩口径：

> 媒体流共享由前端和 LiveKit 完成，但会议规则由 Flask 后端维护，所以能保证同一时刻只允许一个人共享屏幕。

### 10.3 录屏

录屏核心在 `_room_scripts.html` 的 `toggleScreenRecording()`。

前端过程：

1. 调用 `navigator.mediaDevices.getDisplayMedia(...)` 获取屏幕流。
2. 创建 `MediaRecorder`。
3. 通过 `ondataavailable` 收集录制数据块。
4. 停止录制后把数据块合并成 `Blob`。

格式兼容：

- 如果浏览器原生支持 MP4，前端直接下载 MP4。
- 如果浏览器只录出 WebM，前端调用 `/api/remux-recording`。
- 后端接收 WebM 文件后调用 `ffmpeg` 转封装成 MP4，再返回给浏览器。

答辩口径：

> 录屏采集在前端完成，格式兼容优化在后端完成。前端负责录，后端负责把 WebM 转成更通用的 MP4。

### 10.4 背景虚化

背景虚化属于增强功能，不是基础会议可用性的前置条件。它依赖浏览器端视频处理能力，弱设备上可能增加 CPU 压力、发热和延迟。讲解时可以说明：项目优先保证摄像头、麦克风、屏幕共享和聊天可用，背景虚化作为体验增强能力处理。

实现上，房间页会把原始摄像头流送入 MediaPipe Selfie Segmentation，再把分割结果绘制到 canvas：人物区域保留原始画面，背景区域做模糊处理，最后用 canvas 输出的 track 替换 LiveKit 摄像头 track。为了降低启动失败概率，代码只会使用仍处于 `live` 状态的摄像头 track；失败时会回退到原始摄像头，并清理未成功的处理流。交互上只保留单按钮开关，不再支持上传本地图片替换背景。

## 11. 聊天、附件、表情和 @ 提及

### 11.1 附件为什么不直接走 Socket.IO

附件体积大，不适合直接塞进 Socket.IO 实时消息中。正确流程是：

1. 文件先通过 HTTP 上传。
2. 后端保存文件并返回附件元信息。
3. 前端再通过 Socket.IO 发送聊天消息和附件元信息。
4. 后端广播的是附件描述，不是附件二进制内容。

### 11.2 附件上传流程

前端：

1. 用户选择图片、视频或文档。
2. `_room_scripts.html` 调用 `prepareAttachment(file, uploadKind)`。
3. 如果是图片，前端可先压缩。
4. 前端显示本地预览。
5. 用户点击发送后调用 `uploadPendingAttachment()`。
6. 媒体文件上传到 `/api/chat_upload_media`。
7. 文档文件上传到 `/api/chat_upload_doc`。

后端 `_api_chat_upload_impl(upload_mode)`：

1. 校验 `room_id` 是否有效。
2. 校验当前用户是否在该房间。
3. 校验文件类型。
4. 校验文件大小限制。
5. 校验房间级和全局级存储配额。
6. 保存到 `instance/chat_uploads/<room_id>/...`。
7. 生成 `token`、`viewUrl`、`rawUrl`、`downloadUrl`。
8. 返回附件元信息对象。

附件大小限制：

| 类型 | 限制 |
| --- | --- |
| 图片 | 25 MB |
| 视频 | 120 MB |
| 文档 / 压缩包 | 25 MB |

### 11.3 聊天消息广播

上传成功后，前端发送：

```js
socket.emit("meeting_chat_send", {
  message,
  mode,
  mentions,
  attachment
});
```

后端 `on_meeting_chat_send(data)`：

1. 读取文字内容。
2. 读取附件元信息。
3. 读取 @ 提及列表。
4. 生成消息 ID。
5. 写入 `room["chat_history"]`。
6. 用 `meeting_chat_message` 广播给房间成员。

### 11.4 附件访问控制

附件不会直接暴露服务器磁盘路径，而是通过 token 化接口访问。

| 接口 | 作用 |
| --- | --- |
| `/chat_attachment/<room_id>/<token>` | 查看附件页 |
| `/chat_attachment/<room_id>/<token>/raw` | 原始预览，只给可内嵌预览的文件 |
| `/chat_attachment/<room_id>/<token>/download` | 下载附件，仅在权限允许时开放 |

答辩口径：

> 前端不直接暴露真实文件路径，而是通过 token 化访问地址、登录态校验和下载权限控制来访问附件。

### 11.5 表情和 @ 提及

表情：

1. `room_chat.js` 渲染表情面板。
2. 用户点击某个 emoji。
3. 前端把 emoji 字符插入聊天输入框。
4. 最终仍然按普通文本聊天发送。

@ 提及：

1. `room_chat.js` 从 `participantMeta` 里取当前可提及成员。
2. 前端渲染 @ 提及面板。
3. 用户选择成员后，把 `@用户名` 插入输入框。
4. 发送消息时，前端把 `mentions` 一并发给后端。
5. 后端把 `mentions` 写进聊天消息对象。
6. 前端渲染时用 mention 样式显示。

答辩口径：

> 表情和 @ 提及都发生在前端输入层，真正发送时统一走聊天消息通道，没有单独再开一套协议。

## 12. 管理员后台

后台入口：

| 项 | 位置 |
| --- | --- |
| 页面 | `templates/admin.html` |
| 路由 | `/admin` |
| 后端函数 | `admin_dashboard()` |

管理员后台展示四类内容：

1. 系统状态：CPU、内存、磁盘、在线房间数、活跃 socket 数。
2. 用户列表：管理员状态、禁用状态、注册时间等。
3. 当前会议和历史会议：可结束会议、删除会议记录、批量操作。
4. 找回密码申请：可标记为已解决或拒绝。

时间显示规则：

- 普通用户查看自己的历史会议时，页面按该用户在 `/account` 保存的地区/时区显示创建时间和结束时间。
- 管理员后台按当前管理员账号自己的地区/时区统一显示用户注册时间、当前会议时间和历史会议时间。
- 页面顶部会显示当前使用的时间显示时区，避免多人跨地区排查时混淆。

后台操作多数是传统 POST 表单提交，不是复杂 AJAX。

典型用户管理接口：

| 接口 | 作用 |
| --- | --- |
| `/admin/user/<id>/disable` | 禁用用户 |
| `/admin/user/<id>/enable` | 启用用户 |
| `/admin/user/<id>/delete` | 删除用户 |
| `/admin/user/<id>/reset-password` | 重置密码 |
| `/admin/user/<id>/kick` | 踢出用户并断开 socket |

典型会议管理接口：

| 接口 | 作用 |
| --- | --- |
| `/admin/meeting/<id>/end` | 结束单个会议 |
| `/admin/meetings/bulk-end` | 批量结束会议 |
| `/admin/meeting/<id>/delete` | 删除会议记录 |
| `/admin/meetings/bulk-delete` | 批量删除会议记录 |

权限控制：

- 后台路由使用 `@login_required`。
- 后台路由同时使用 `@admin_required`。
- 用户必须先登录，并且必须是管理员。

答辩口径：

> 管理员后台不是单独项目，而是同一个 Flask 应用里的受保护路由集合。页面层用 form 提交操作，后端用权限装饰器限制访问。

## 13. app.py 核心函数索引

行号可能会随代码调整变化，答辩时优先记函数名和职责。

| 函数 | 作用 |
| --- | --- |
| `account_page()` | 处理账号资料、语言、时区、默认附件权限、默认媒体偏好和改密码 |
| `register()` | 处理注册，校验用户名和密码，保存密码哈希，建立登录态 |
| `login()` | 处理登录，校验密码哈希，检查账号启用状态，刷新 `session_version` |
| `api_create_room()` | 创建会议，写入 `Meeting`，初始化运行时 `rooms` |
| `api_join_room()` | 入会前 HTTP 校验，不负责真正加入实时房间 |
| `room_page()` | 渲染会议页并注入房间配置、LiveKit URL、用户偏好 |
| `api_livekit_token()` | 校验 Socket 身份后签发 LiveKit token |
| `history()` | 查询当前用户的历史会议 |
| `api_remux_recording()` | 接收录屏文件并调用 `ffmpeg` 转封装为 MP4 |
| `admin_dashboard()` | 渲染管理员后台首页 |
| `admin_delete_user()` | 删除用户并清理相关会议、参会记录和 socket |
| `admin_reset_user_password()` | 管理员重置用户密码并断开旧连接 |
| `admin_disable_user()` / `admin_enable_user()` | 禁用或启用用户 |
| `admin_end_meeting()` / `admin_bulk_end_meetings()` | 结束单个或多个会议 |
| `admin_delete_meeting()` / `admin_bulk_delete_meetings()` | 删除会议记录并清理运行时状态 |
| `on_join_room(data)` | 真正把用户加入 Socket.IO 实时房间 |
| `_api_chat_upload_impl()` | 统一处理聊天附件上传 |
| `chat_attachment_view()` | 附件查看页 |
| `chat_attachment_raw()` | 附件原始预览 |
| `chat_attachment_download()` | 附件下载 |
| `api_translate_message()` / `api_translate_to_english()` | 翻译聊天消息 |
| `on_meeting_chat_send()` | 处理聊天发送和广播 |
| `on_meeting_chat_clear()` | 处理清空聊天 |
| `on_meeting_chat_retract()` | 处理撤回聊天 |
| `on_room_ui_event()` | 处理屏幕共享等会议 UI 状态规则 |
| `on_host_end_meeting()` | 主持人结束会议 |
| `on_leave_room()` | 用户主动离开会议 |

## 14. 核心代码跟读

这一章专门解决“看完流程还是不知道代码怎么对应”的问题。下面的代码不是完整源码，而是从关键位置截取出来的最小片段，用来说明每个功能真正是怎么串起来的。

### 14.1 首页创建会议：前端 fetch 到 Flask API

首页创建会议的入口在 `templates/index.html`。用户点击创建按钮后，前端不会刷新页面，而是用 `fetch` 调后端接口。

```js
const res = await fetch('/api/create_room', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ host_name })
});
```

后端对应 `api_create_room()`：

```python
@app.route("/api/create_room", methods=["POST"])
@login_required
def api_create_room():
    room_id = generate_room_id()
    password = generate_password()
    meeting = Meeting(room_id=room_id, room_password=password, status="active")
    db.session.add(meeting)
    db.session.commit()
    rooms[room_id] = build_runtime_room_state(...)
```

这里有两个重点：

- `Meeting` 写进数据库，保证会议记录可持久化。
- `rooms[room_id]` 初始化内存里的实时房间状态，后续 Socket.IO 入房要用它。

### 14.2 首页加入会议：先校验，不是真入会

首页加入会议先调用 `/api/join_room`：

```js
const res = await fetch('/api/join_room', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ room_id, password })
});
```

后端对应 `api_join_room()`，只检查会议是否存在、是否过期、密码是否正确。它不会把用户加入 `rooms[room_id]["participants"]`，也不会广播成员加入。

答辩时要强调：

> `/api/join_room` 只是入会前校验。真正加入会议是在房间页加载后，通过 Socket.IO 的 `join_room` 事件完成。

### 14.3 房间页加载：建立 Socket.IO 连接

房间页核心脚本在 `templates/_room_scripts.html`。页面加载后会先建立 Socket.IO 连接：

```js
const socket = io();
window.socket = socket;
```

连接建立后，前端发送 `join_room`：

```js
socket.emit('join_room', {
  room_id: ROOM_ID,
  password: ROOM_PASSWORD,
  user_name: USER_NAME
});
```

这一步告诉后端：“当前浏览器要真正进入这个实时房间。”

### 14.4 后端 Socket 入房：写入实时状态并回传 join_ok

后端真正处理入房的是 `on_join_room(data)`：

```python
@socketio.on("join_room")
def on_join_room(data):
    room = ensure_runtime_room(meeting)
    room["participants"][request.sid] = {
        "user_id": current_user.id,
        "name": user_name,
    }
    sid_to_user[request.sid] = {
        "room_id": room_id,
        "user_id": current_user.id,
    }
    join_room(room_id)
```

关键变量：

| 变量 | 含义 |
| --- | --- |
| `request.sid` | 当前浏览器 Socket.IO 连接的唯一 ID |
| `rooms[room_id]["participants"]` | 当前房间在线成员列表 |
| `sid_to_user` | 从 socket ID 反查当前用户和房间 |
| `join_room(room_id)` | Socket.IO 自己的房间加入动作，用于后续广播 |

入房成功后，后端给当前用户回传 `join_ok`，同时给其他成员广播 `participant_joined`。

### 14.5 join_ok 之后才连接 LiveKit

前端收到 `join_ok` 后，才正式连接 LiveKit：

```js
socket.on('join_ok', async (data) => {
  SELF_SID = data.self_sid;
  syncParticipants(data.participants || []);
  renderChatHistory(data.chat_history || []);
  await ensureLiveKitConnected();
});
```

为什么要等 `join_ok`：

- `join_ok` 会带回 `self_sid`。
- 换取 LiveKit token 时必须带 `participant_sid`。
- 后端会检查这个 sid 是否已经在 Socket 层登记过。

这就是项目的安全设计：不能只知道会议号和密码就直接连 LiveKit，必须先通过 Flask + Socket.IO 的身份校验。

### 14.6 获取 LiveKit token：前端必须带 participant_sid

`room_livekit.js` 请求媒体 token 时会带上 `participant_sid`：

```js
body: JSON.stringify({
  room_id: roomId,
  password: roomPassword,
  participant_sid: getSelfSid?.(),
  name: getDisplayName?.(),
})
```

后端 `api_livekit_token()` 会验证这个 sid 是否属于当前登录用户和当前房间。验证通过后，才用 LiveKit API key / secret 生成 JWT token。

### 14.7 LiveKit 连接和媒体开关

拿到 token 后，前端连接 LiveKit：

```js
await activeRoom.connect(url || tokenPayload.url, tokenPayload.token, {
  autoSubscribe: true,
});
```

摄像头和麦克风开关都通过 LiveKit 本地参会者对象控制：

```js
await activeRoom.localParticipant.setMicrophoneEnabled(enabled);
await activeRoom.localParticipant.setCameraEnabled(enabled);
```

答辩口径：

> 项目把媒体轨道托管给 LiveKit 的 `localParticipant`。按钮只是切换 LiveKit 本地发布状态，发布和订阅由 LiveKit SDK 管理。

### 14.8 屏幕共享：前端开媒体，后端管规则

前端点击共享按钮后调用 LiveKit 的屏幕共享接口：

```js
await activeRoom.localParticipant.setScreenShareEnabled(enabled, {
  audio: shareAudio,
  contentHint: config.contentHint,
  resolution: config.resolution,
});
```

但“同一时刻只能有一个人共享”不是 LiveKit 自动帮你做的，而是后端通过 `room_ui_event` 维护：

```python
if event_type == "screen_share_started":
    if active_sharer_sid and active_sharer_sid != sid:
        emit("room_ui_event", {"type": "screen_share_denied"}, to=sid)
        return
    room["active_sharer_sid"] = sid
```

所以屏幕共享要分两层讲：

- LiveKit 负责把屏幕画面和声音发出去。
- Flask 后端负责会议规则，例如防止多人同时共享。

### 14.9 录屏：前端录制，后端转封装

前端录屏入口：

```js
recorderStream = await navigator.mediaDevices.getDisplayMedia({
  video: true,
  audio: true
});
activeRecorder = new MediaRecorder(recorderStream, recorderOptions);
```

如果浏览器录出来的是 WebM，前端再上传到 `/api/remux-recording`，后端 `api_remux_recording()` 调用 `ffmpeg` 转成 MP4。这里能解释两个常见问题：

- 录屏依赖浏览器支持 `getDisplayMedia` 和 `MediaRecorder`。
- WebM 转 MP4 依赖服务器安装 `ffmpeg`。

### 14.10 聊天附件：HTTP 上传后再 Socket 广播

发送聊天消息时，前端先处理附件：

```js
if (pendingAttachment) {
  attachmentPayload = await uploadPendingAttachment();
}
socket.emit('meeting_chat_send', {
  message,
  mentions,
  attachment: attachmentPayload
});
```

后端 `_api_chat_upload_impl()` 负责保存附件，`on_meeting_chat_send()` 负责把文字和附件元信息写入 `room["chat_history"]` 并广播。

答辩口径：

> 文件体积大，所以先走 HTTP 上传到服务器；聊天实时通道只广播消息文本和附件元信息。这样既能实时显示，又不会把大文件塞进 Socket.IO。

## 15. 当前局限和后续改进

当前局限：

- 在线态主要保存在单进程内存中，服务重启会丢失，多实例部署不安全。
- `app.py` 偏大，后续维护最好按业务域拆分。
- 背景虚化依赖本地摄像头 live track、浏览器模型和 canvas 处理；屏幕共享和录屏也比较消耗资源，弱设备上可能影响体验。
- 录屏转 MP4 依赖服务器安装 `ffmpeg`。
- LiveKit 是外部基础设施，部署时必须正确配置 `LIVEKIT_URL`、`LIVEKIT_API_KEY` 和 `LIVEKIT_API_SECRET`。

后续改进方向：

- 将 `rooms`、`sid_to_user` 等运行态迁移到 Redis，支持多实例部署。
- 将 `app.py` 按认证、会议、聊天附件、后台管理、录屏等模块拆分。
- 增加自动化测试，覆盖登录、创建会议、入会校验、附件上传和管理员操作。
- 为 LiveKit 连接失败、移动端屏幕共享限制、背景虚化模型加载失败和录屏转封装失败提供更细的前端提示。

## 16. 常见追问回答

### 16.1 为什么不用 C 语言

直接回答：

> C 可以用于底层高性能组件，但不适合把这个项目整体改写成 C。这个项目的核心挑战是 Web 业务集成和多人会议流程，不是从零写媒体引擎。

具体理由：

- 项目重点是账号、房间、权限、数据库、模板和后台，不是纯底层性能。
- Flask 能快速处理路由、会话、模板和数据库，C 在这些方面工程成本更高。
- 音视频重负载已经交给 LiveKit，业务后端改成 C 收益不明显。
- C 的内存管理和安全实现成本更高，不适合当前课程项目的快速迭代。

### 16.2 如何加入会议

先在首页调用 `/api/join_room` 校验会议号和密码，再跳到 `/room/<room_id>`。房间页加载后通过 Socket.IO 的 `join_room` 事件真正加入实时房间，之后再调用 `/api/livekit/token` 获取媒体 token，最后连接 LiveKit。

### 16.3 摄像头和麦克风怎么调用

前端根据用户偏好决定是否自动开启，然后由 `room_livekit.js` 调用 `setCameraEnabled` 和 `setMicrophoneEnabled` 控制 LiveKit 本地参会者的媒体轨道。

### 16.4 屏幕共享怎么做

前端点击按钮后调用 LiveKit 的屏幕共享接口，后端同时通过 `room_ui_event` 维护“当前共享者”状态，防止多人同时共享。

### 16.5 会议里怎么发文档

前端先通过 HTTP 把附件上传到 `/api/chat_upload_media` 或 `/api/chat_upload_doc`，后端保存后返回附件元信息；之后前端再通过 `meeting_chat_send` 把文字和附件元信息一起广播。

### 16.6 管理员后台怎么实现

管理员访问 `/admin`，后端汇总系统状态、用户、会议和找回密码申请，再用 `admin.html` 渲染。具体操作大多通过 POST 表单提交，后端用 `@admin_required` 限制权限。

## 17. 收尾总纲

答辩或讲解时不要把项目说成“前端做了一个视频会议页面”。更准确的说法是：

- Flask 负责账号、会议、权限、上传、后台管理和 LiveKit token 签发。
- Socket.IO 负责会议中的实时状态同步。
- LiveKit 负责真正的摄像头、麦克风和屏幕共享媒体传输。
- SQLite 负责持久化用户、会议和参会记录。
- 前端页面和 JavaScript 负责交互、渲染和调用这些能力。

只要围绕“注册登录、入会流程、音视频、聊天附件、管理员后台”五条主线展开，基本可以覆盖大部分展示和追问。


---

<a id="project-guide-en"></a>

# Project Guide and Code Index

[中文](#project-guide-zh) | [English](#project-guide-en)

This document explains the project logic, core code locations, and presentation talking points. It combines system layering, communication methods, core flows, feature implementation, code index, and common Q&A in one place.

## 1. One-Sentence Overview

This is an online meeting system built with `Flask + Flask-SocketIO + LiveKit`, covering accounts, room creation and joining, multi-party audio/video, screen sharing, chat attachments, meeting history, admin management, and basic diagnostics.

A more engineering-oriented summary:

> Templates render pages, JavaScript handles interaction, Flask owns business logic, Socket.IO syncs real-time room state, and LiveKit transports audio/video media.

## 2. What Problem the Project Solves

This is not just a "camera can display" demo. It connects the common workflow of a meeting product:

- User registration, login, logout, and session control
- Meeting creation, meeting join, and meeting history
- Camera, microphone, and screen sharing inside the room
- Chat, emoji, @ mentions, image/video/document attachments
- Host actions, admin dashboard, and password reset requests
- Chinese/English UI, RTC/LiveKit diagnostics, recording, and background blur

For presentation, emphasize that it is a complete web application, not a single WebRTC experiment page.

## 3. Main Page Entry Points

| Path | Page | Code location |
| --- | --- | --- |
| `/` | Home / create meeting / join meeting | `templates/index.html`, `index()` |
| `/login` | Login | `templates/login.html`, `login()` |
| `/register` | Registration | `templates/register.html`, `register()` |
| `/forgot-password` | Password reset request | `templates/forgot_password.html`, `forgot_password_page()` |
| `/quickstart` | Quickstart | `templates/quickstart.html`, `quickstart_page()` |
| `/help` | User Guide | `templates/help.html`, `help_page()` |
| `/support` | Support | `templates/support.html`, `support_page()` |
| `/account` | Account and preferences | `templates/account.html`, `account_page()` |
| `/history` | Meeting history | `templates/history.html`, `history()` |
| `/room/<room_id>` | Meeting room | `templates/room.html`, `room_page()` |
| `/admin` | Admin dashboard | `templates/admin.html`, `admin_dashboard()` |

These entries match the "User-Facing Pages" table in the root README.

## 4. Technical Architecture

| Layer | Main technology / file | Responsibility |
| --- | --- | --- |
| Template layer | `templates/*.html` | Page skeletons for login, home, room, history, account, admin, and other pages |
| Frontend interaction layer | `static/*.js` | Button events, API calls, Socket.IO and LiveKit connection, chat/video rendering |
| Flask backend layer | `app.py` | Accounts, meetings, permissions, uploads, admin, translation, Socket.IO events, LiveKit token generation |
| Real-time state layer | Flask-SocketIO + in-memory state | Member join/leave, chat, screen share state, and host actions; critical runtime state is now guarded by `runtime_state_lock` |
| Media layer | LiveKit SFU | Camera, microphone, screen sharing, and remote media tracks |
| Persistence layer | SQLite / SQLAlchemy | Users, meetings, participation records, password reset requests |

The current refactor audit is in [REFACTOR_AUDIT.md#refactor-audit](REFACTOR_AUDIT.md#refactor-audit). Maintenance should keep room state consistency first, then gradually split `app.py` and the room frontend script.

## 4.1 i18n and Mobile/Desktop Adaptation

i18n:

- `translations.py` is the main translation table, and the `zh` and `en` key sets currently match.
- Templates prefer `t('key')`; some in-room runtime and browser-capability prompts use explicit Chinese/English branches.
- `check_i18n.py` checks templates for missed hardcoded Chinese and should be run before submitting.
- Users can change the page language through the language switch or the default language preference in `/account`.

Mobile and desktop:

- The home page has mobile QR join on phones, while desktop keeps room ID, password, and invite-link copy workflows.
- The room page uses a meeting grid plus right chat column on desktop; on phones, chat reflows into a bottom panel with touch scrolling and input visibility handling.
- `room_livekit.js` selects different media publishing settings for mobile and desktop, with more conservative settings on phones.
- `_room_scripts.html` handles mobile fullscreen, iOS video fullscreen, landscape orientation lock, touch playback recovery, and screen-share viewing.
- `style.css` and `room.css` keep responsive layout rules for general pages and the meeting room.

## 5. Why LiveKit Instead of Browser Mesh

If every browser directly connects to every other browser, connection count and each user's upload bandwidth grow quickly as the room gets larger. In a five-person meeting, each browser must maintain several connections, which increases browser load, network pressure, and debugging complexity.

This project uses LiveKit SFU: each user sends media to LiveKit, and LiveKit forwards it to the other users. This is more suitable for multi-party meetings and makes remote tracks, reconnection, and unstable networks easier to handle.

Presentation wording:

> I use LiveKit for media transport so the project can focus on meeting business logic, permission control, and system integration instead of implementing a multi-party media server from scratch.

## 6. How Frontend and Backend Communicate

The project uses four communication paths.

### 6.1 HTML Form Submission

Suitable for account and admin pages.

| Feature | Frontend template | Backend entry |
| --- | --- | --- |
| Register | `templates/register.html` | `/register`, `register()` |
| Login | `templates/login.html` | `/login`, `login()` |
| Account settings | `templates/account.html` | `/account`, `account_page()` |
| Admin actions | `templates/admin.html` | Multiple `/admin/...` routes |

Forms use `method="post"`, Flask reads `request.form`, and the server returns a new page or redirect.

### 6.2 `fetch` Calls to Flask APIs

Suitable for room creation, join validation, LiveKit token retrieval, uploads, translation, and recording remux.

| Feature | Backend API |
| --- | --- |
| Create room | `/api/create_room` |
| Validate room join | `/api/join_room` |
| Get LiveKit token | `/api/livekit/token` |
| Service health | `/api/healthz` |
| Upload media attachment | `/api/chat_upload_media` |
| Upload document attachment | `/api/chat_upload_doc` |
| Remux recording to MP4 | `/api/remux-recording` |
| Translate chat message | `/api/translate_message`, `/api/translate_to_english` |

### 6.3 Socket.IO Real-Time Events

Suitable for room actions that should not refresh the page.

| Feature | Socket event |
| --- | --- |
| Actually join the room | `join_room` |
| Update display name | `update_profile` |
| Send chat | `meeting_chat_send` |
| Clear chat | `meeting_chat_clear` |
| Retract chat | `meeting_chat_retract` |
| Sync screen share state | `room_ui_event` |
| Host ends meeting | `host_end_meeting` |
| Leave room | `leave_room` |

Socket.IO owns membership, chat, host actions, and UI-level room state.

### 6.4 LiveKit Media Connection

Camera, microphone, and screen sharing media are not forwarded by the Flask application.

| Media feature | Implementation |
| --- | --- |
| Camera | `static/room_livekit.js` |
| Microphone | `static/room_livekit.js` |
| Screen share video | `static/room_livekit.js` |
| Screen share audio | `static/room_livekit.js` |

Flask authenticates the user and issues a LiveKit token. The browser then connects directly to the LiveKit service.

## 7. Key File Index

### 7.1 Backend Core

| File | Description |
| --- | --- |
| `app.py` | Backend core: routes, models, admin logic, chat, attachments, translation, Socket.IO events, LiveKit token generation |
| `translations.py` | Chinese/English UI text |
| `check_i18n.py` | Checks templates for untranslated Chinese text |

### 7.2 Templates

| File | Description |
| --- | --- |
| `templates/login.html` | Login page |
| `templates/register.html` | Registration page |
| `templates/index.html` | Home page for creating, joining, and QR joining meetings |
| `templates/room.html` | Meeting page entry |
| `templates/_room_layout.html` | Meeting page layout skeleton |
| `templates/_room_scripts.html` | Main room script entry for Socket.IO events, button binding, and room orchestration |
| `templates/account.html` | User preferences and account settings |
| `templates/admin.html` | Admin dashboard |
| `templates/history.html` | Meeting history |
| `templates/attachment_view.html` | Chat attachment view page |
| `templates/help.html`, `templates/support.html` | Help and support pages |

### 7.3 Frontend Scripts and Styles

| File | Description |
| --- | --- |
| `static/room_livekit.js` | LiveKit connection, camera, microphone, screen share, media track sync |
| `static/room_chat.js` | Chat rendering, @ mentions, emoji panel, attachment rendering |
| `static/room_ui.js` | Meeting UI rendering, layout scheduling, participant card updates |
| `static/room_utils.js` | Copying text, HTML escaping, media track helpers |
| `static/room_diagnostics.js` | RTC / LiveKit diagnostics display |
| `static/room.css` | Meeting page styles |
| `static/style.css` | Shared page styles |

## 8. Data Storage

### Database Storage

Database models are concentrated in `app.py`.

| Model | Purpose |
| --- | --- |
| `User` | Account, password hash, admin flag, enabled state, display name, language, default join preferences |
| `Meeting` | Room ID, room password, host, meeting status, creation time, end time |
| `MeetingParticipant` | Participation records: who joined, when they joined, when they left |
| `PasswordResetRequest` | Password reset requests for admin handling |

### Runtime Memory State

The database stores persistent data. Real-time room state during meetings is mainly in memory.

| Variable | Purpose |
| --- | --- |
| `rooms` | Per-room online members, chat history, screen share state, host presence |
| `sid_to_user` | Maps Socket.IO `request.sid` to the current user and room |
| `user_active_sids` | Tracks active sockets for a user, used for session control and kicking users |

This means the current project is best treated as single-instance. Multi-instance deployment requires moving runtime state to Redis or another shared store.

## 9. Core Flows

### 9.1 Registration and Login

Registration:

1. `register.html` submits username and password with a normal form.
2. Flask `/register` reads the form.
3. The backend checks empty values and duplicate username.
4. `user.set_password(password)` stores the password hash.
5. The user is saved and logged in with `login_user(user)`.
6. `session["session_version"]` is written and the user is redirected home.

Login:

1. `login.html` submits to `/login`.
2. The backend queries `User` by username.
3. `user.check_password(password)` verifies the hash.
4. Disabled accounts are rejected.
5. `session_version` is refreshed.
6. `login_user(user)` establishes the session.
7. `disconnect_user_sockets(...)` cleans old sockets.

Presentation wording:

> Registration and login do not let the frontend modify the database directly. Flask validates input, passwords are stored as hashes, Flask-Login maintains the login state, and `session_version` invalidates old sessions.

### 9.2 Creating a Meeting

1. The user clicks "Create meeting" on the home page.
2. The frontend calls `POST /api/create_room`.
3. `api_create_room()` generates a room ID and password.
4. A `Meeting` database record is created.
5. `rooms[room_id]` runtime state is initialized.
6. The backend returns `room_id`, `password`, and `join_url`.
7. The frontend displays the meeting ID, password, and invite link.

Key point: `Meeting` is persistent; `rooms[room_id]` is runtime state.

### 9.3 Joining a Meeting

Joining has three steps.

First, HTTP validation on the home page:

1. The user enters room ID and password.
2. The frontend calls `POST /api/join_room`.
3. The backend checks existence, expiration, and password.
4. On success, the frontend redirects to `/room/<room_id>?pwd=...`.

Second, the room page joins the Socket.IO room:

1. `_room_scripts.html` loads.
2. The frontend creates a Socket.IO connection with `const socket = io()`.
3. It emits `join_room` with `room_id`, `password`, and `user_name`.
4. `on_join_room(data)` validates login, room state, and password again.
5. The backend records `request.sid` in `rooms[room_id]["participants"]`.
6. The backend records `sid_to_user`.
7. Socket.IO joins the room.
8. A `MeetingParticipant` record is written.
9. `join_ok` returns participants, chat history, and share state.
10. `participant_joined` is broadcast to other members.

Third, the frontend gets a LiveKit token and connects media:

1. The frontend receives `self_sid` from `join_ok`.
2. The frontend calls `POST /api/livekit/token`.
3. The request includes `room_id`, `password`, `participant_sid`, and `name`.
4. `api_livekit_token()` verifies the room, password, sid registration, and current user.
5. The backend signs a LiveKit JWT token.
6. `room_livekit.js` connects to LiveKit.

Presentation wording:

> Entering a meeting is not a single step. HTTP validates the room password, Socket.IO joins the real-time room, and only then does the client receive a LiveKit token for media.

## 10. Audio/Video and Meeting Features

### 10.1 Camera and Microphone

Users can save default join preferences in `account.html`. `/account` stores them in `User.auto_enable_camera`, `User.auto_enable_microphone`, and `User.auto_enable_speaker`. Room scripts use those preferences after page load.

`room_livekit.js` controls actual media tracks:

| Function | Purpose |
| --- | --- |
| `buildRoomOptions()` | Camera/microphone capture and publishing parameters |
| `setCameraEnabled(nextEnabled)` | Controls camera through the LiveKit local participant |
| `setMicrophoneEnabled(nextEnabled)` | Controls microphone through the LiveKit local participant |

Mobile devices use more conservative capture settings to reduce power, heat, and network pressure.

### 10.2 Screen Sharing

Frontend flow:

1. The user clicks the screen share button.
2. `_room_scripts.html` handles options such as system audio and microphone behavior.
3. The frontend calls `controller.setScreenShareEnabled(...)`.
4. `room_livekit.js` uses LiveKit screen sharing APIs.

Share modes:

| Mode | Best for | Goal |
| --- | --- | --- |
| `motion` | video, animation, or frequent cursor movement | Prioritize smoothness |
| `detail` | slides, documents, or code | Prioritize clarity |

Backend rule control:

1. The frontend reports `screen_share_started` or `screen_share_stopped` through `room_ui_event`.
2. The backend checks whether another sharer already exists.
3. If another user is sharing, it emits `screen_share_denied`.
4. If allowed, the backend writes `room["active_sharer_sid"]` and `room["active_sharer_user_id"]`.
5. On stop, the backend clears sharer state and broadcasts the update.

Presentation wording:

> LiveKit carries the screen media, while Flask maintains meeting rules such as only allowing one active screen sharer.

### 10.3 Recording

Recording is driven by `toggleScreenRecording()` in `_room_scripts.html`.

Frontend flow:

1. The browser calls `navigator.mediaDevices.getDisplayMedia(...)`.
2. A `MediaRecorder` is created.
3. `ondataavailable` collects recording chunks.
4. On stop, chunks are merged into a `Blob`.

Format compatibility:

- If the browser records MP4 directly, the frontend downloads MP4.
- If the browser only outputs WebM, the frontend uploads it to `/api/remux-recording`.
- The backend receives the WebM file and calls `ffmpeg` to remux it to MP4 before returning it.

Presentation wording:

> Recording capture happens in the browser, while format compatibility is handled on the backend. The browser records the screen, and the backend turns WebM into a more portable MP4 when needed.

### 10.4 Virtual Background

Virtual background is an enhancement feature, not a requirement for baseline meeting stability. It depends on browser-side video processing and may increase CPU usage, heat, and delay on weak devices.

The room page sends the raw camera stream into MediaPipe Selfie Segmentation, draws the segmented output to a canvas, and replaces the LiveKit camera track with the canvas output track. To reduce startup failures, the code only uses camera tracks that are still `live`; on failure it falls back to the raw camera and cleans up the failed processing stream. Common causes include a camera that was just turned off or restarted, local preview not being ready yet, model asset loading failure, and weak device performance.

## 11. Chat, Attachments, Emoji, and @ Mentions

### 11.1 Why Attachments Do Not Go Through Socket.IO Directly

Large attachments are not suitable as Socket.IO real-time payloads. The correct flow is:

1. Upload the file over HTTP.
2. The backend stores the file and returns attachment metadata.
3. The frontend sends chat text and metadata through Socket.IO.
4. The backend broadcasts metadata, not file bytes.

### 11.2 Attachment Upload Flow

Frontend:

1. The user chooses an image, video, or document.
2. `_room_scripts.html` calls `prepareAttachment(file, uploadKind)`.
3. If the file is an image, the frontend may compress it first.
4. The frontend shows a local preview.
5. After the user clicks send, it calls `uploadPendingAttachment()`.
6. Media files go to `/api/chat_upload_media`.
7. Document files go to `/api/chat_upload_doc`.

Backend `_api_chat_upload_impl(upload_mode)`:

1. Validate `room_id`.
2. Validate that the current user is in that room.
3. Validate file type.
4. Validate file size limit.
5. Validate room-level and global storage quotas.
6. Save the file under `instance/chat_uploads/<room_id>/...`.
7. Generate `token`, `viewUrl`, `rawUrl`, and `downloadUrl`.
8. Return attachment metadata.

Attachment size limits:

| Type | Limit |
| --- | --- |
| Image | 25 MB |
| Video | 120 MB |
| Document / archive | 25 MB |

### 11.3 Chat Message Broadcast

After upload succeeds, the frontend sends:

```js
socket.emit("meeting_chat_send", {
  message,
  mode,
  mentions,
  attachment
});
```

Backend `on_meeting_chat_send(data)`:

1. Reads the text content.
2. Reads the attachment metadata.
3. Reads the @ mention list.
4. Generates a message ID.
5. Writes to `room["chat_history"]`.
6. Broadcasts to room members through `meeting_chat_message`.

### 11.4 Attachment Access Control

Attachments do not expose real filesystem paths directly. They use tokenized access endpoints:

| API | Purpose |
| --- | --- |
| `/chat_attachment/<room_id>/<token>` | Attachment view page |
| `/chat_attachment/<room_id>/<token>/raw` | Raw preview for embeddable files |
| `/chat_attachment/<room_id>/<token>/download` | Download endpoint when permission allows it |

Presentation wording:

> The frontend never exposes the real server file path directly. Attachments are accessed through tokenized URLs plus login checks and download-permission checks.

### 11.5 Emoji and @ Mentions

Emoji flow:

1. `room_chat.js` renders the emoji panel.
2. The user clicks an emoji.
3. The frontend inserts the emoji character into the chat input.
4. It is still sent through the normal text-chat path.

@ mention flow:

1. `room_chat.js` reads mentionable members from `participantMeta`.
2. The frontend renders the mention panel.
3. After a user is selected, `@username` is inserted into the input.
4. When the message is sent, the frontend includes `mentions`.
5. The backend stores `mentions` in the chat message object.
6. The frontend renders mentions with mention-specific styling.

Presentation wording:

> Emoji and @ mentions both happen at the frontend input layer. They still use the same chat message channel instead of opening a separate protocol.

## 12. Admin Dashboard

Admin entry:

| Item | Location |
| --- | --- |
| Page | `templates/admin.html` |
| Route | `/admin` |
| Backend function | `admin_dashboard()` |

The admin dashboard shows four groups of content:

1. System status: CPU, memory, disk, online rooms, active sockets.
2. User list: admin state, disabled state, registration time.
3. Current and historical meetings: end meetings, delete records, bulk operations.
4. Password reset requests: mark resolved or rejected.

Time display rules:

- A regular user's meeting history uses that user's region/timezone preference from `/account`.
- The admin dashboard uses the current admin account's region/timezone preference for user registration times and meeting records.
- The page header shows the active display timezone to avoid confusion during cross-region troubleshooting.

Most admin actions are traditional POST forms.

Typical user management routes:

| Route | Purpose |
| --- | --- |
| `/admin/user/<id>/disable` | Disable user |
| `/admin/user/<id>/enable` | Enable user |
| `/admin/user/<id>/delete` | Delete user |
| `/admin/user/<id>/reset-password` | Reset password |
| `/admin/user/<id>/kick` | Kick user and disconnect sockets |

Typical meeting management routes:

| Route | Purpose |
| --- | --- |
| `/admin/meeting/<id>/end` | End one meeting |
| `/admin/meetings/bulk-end` | End meetings in bulk |
| `/admin/meeting/<id>/delete` | Delete one meeting record |
| `/admin/meetings/bulk-delete` | Delete meeting records in bulk |

Permission control:

- Admin routes use `@login_required`.
- Admin routes also use `@admin_required`.
- A user must be logged in and must be an admin.

Presentation wording:

> The admin dashboard is not a separate project. It is a protected route set inside the same Flask application. The page mostly uses form submissions, and backend decorators enforce access control.

## 13. `app.py` Core Function Index

Line numbers may change; remember function names and responsibilities first.

| Function | Purpose |
| --- | --- |
| `account_page()` | Account profile, language, timezone, attachment permission defaults, media preferences, password change |
| `register()` | Registration, username/password validation, password hash, login state |
| `login()` | Login, password hash verification, account enabled check, `session_version` refresh |
| `api_create_room()` | Creates a meeting, writes `Meeting`, initializes runtime `rooms` |
| `api_join_room()` | HTTP validation before joining; does not join the real-time room |
| `room_page()` | Renders room page and injects room config, LiveKit URL, user preferences |
| `api_livekit_token()` | Verifies Socket identity and issues LiveKit token |
| `history()` | Queries current user's meeting history |
| `api_remux_recording()` | Receives recording and calls `ffmpeg` to remux MP4 |
| `admin_dashboard()` | Renders admin dashboard |
| `admin_delete_user()` | Deletes user and cleans related meetings, participation records, sockets |
| `admin_reset_user_password()` | Resets user password and disconnects old sessions |
| `admin_disable_user()` / `admin_enable_user()` | Disables or enables users |
| `admin_end_meeting()` / `admin_bulk_end_meetings()` | Ends one or many meetings |
| `admin_delete_meeting()` / `admin_bulk_delete_meetings()` | Deletes meeting records and runtime state |
| `on_join_room(data)` | Actually joins a user to a Socket.IO room |
| `_api_chat_upload_impl()` | Shared chat attachment upload implementation |
| `chat_attachment_view()` | Attachment view page |
| `chat_attachment_raw()` | Raw attachment preview |
| `chat_attachment_download()` | Attachment download |
| `api_translate_message()` / `api_translate_to_english()` | Chat message translation |
| `on_meeting_chat_send()` | Chat send and broadcast |
| `on_meeting_chat_clear()` | Clear chat |
| `on_meeting_chat_retract()` | Retract chat |
| `on_room_ui_event()` | Screen sharing and other room UI state rules |
| `on_host_end_meeting()` | Host ends meeting |
| `on_leave_room()` | User leaves meeting |

## 14. Code Walkthrough Pointers

This chapter exists for the common question: "I understand the flow, but where is it in the code?" The snippets below are not full source listings. They are the minimum code fragments needed to explain how each feature is actually wired.

### 14.1 Create Meeting: Frontend `fetch` to Flask API

Frontend `templates/index.html` calls:

```js
const res = await fetch('/api/create_room', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ host_name })
});
```

Backend `api_create_room()` creates a `Meeting` record and initializes `rooms[room_id]`.

Two points matter here:

- `Meeting` is written to the database so the room exists as persistent data.
- `rooms[room_id]` initializes the in-memory runtime room state needed by later Socket.IO joins.

### 14.2 Home-Page Join Only Validates; It Is Not the Real Join

The home page first calls `/api/join_room`:

```js
const res = await fetch('/api/join_room', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ room_id, password })
});
```

Backend `api_join_room()` only checks whether the room exists, whether it has expired, and whether the password is correct. It does not write `rooms[room_id]["participants"]` and does not broadcast membership changes.

Presentation wording:

> `/api/join_room` is only the pre-join validation. The real meeting join happens later through the Socket.IO `join_room` event after the room page loads.

### 14.3 Room Page Load: Establish the Socket.IO Connection

`templates/_room_scripts.html` creates the socket:

```js
const socket = io();
window.socket = socket;
```

After the connection is established, the frontend emits `join_room`:

```js
socket.emit('join_room', {
  room_id: ROOM_ID,
  password: ROOM_PASSWORD,
  user_name: USER_NAME
});
```

This tells the backend that the current browser really wants to enter the real-time room.

### 14.4 Backend Socket Join: Write Runtime State and Return `join_ok`

Backend `on_join_room(data)` handles the real room join:

```python
@socketio.on("join_room")
def on_join_room(data):
    room = ensure_runtime_room(meeting)
    room["participants"][request.sid] = {
        "user_id": current_user.id,
        "name": user_name,
    }
    sid_to_user[request.sid] = {
        "room_id": room_id,
        "user_id": current_user.id,
    }
    join_room(room_id)
```

Key variables:

| Variable | Meaning |
| --- | --- |
| `request.sid` | Unique Socket.IO ID for the current browser connection |
| `rooms[room_id]["participants"]` | Current online member list for that room |
| `sid_to_user` | Reverse map from socket ID to current user and room |
| `join_room(room_id)` | Socket.IO room join used by later broadcasts |

After success, the backend sends `join_ok` to the current user and broadcasts `participant_joined` to other members.

### 14.5 LiveKit Connects Only After `join_ok`

After receiving `join_ok`, the frontend connects LiveKit:

```js
socket.on('join_ok', async (data) => {
  SELF_SID = data.self_sid;
  syncParticipants(data.participants || []);
  renderChatHistory(data.chat_history || []);
  await ensureLiveKitConnected();
});
```

Why wait for `join_ok`:

- `join_ok` returns `self_sid`.
- LiveKit token exchange requires `participant_sid`.
- The backend checks whether this sid has already been registered at the Socket layer.

This is part of the security design: knowing the room ID and password is not enough to connect directly to LiveKit. The client must first pass Flask + Socket.IO identity checks.

### 14.6 Frontend Must Send `participant_sid` to Get a LiveKit Token

`room_livekit.js` includes `participant_sid` in the token request:

```js
body: JSON.stringify({
  room_id: roomId,
  password: roomPassword,
  participant_sid: getSelfSid?.(),
  name: getDisplayName?.(),
})
```

Backend `api_livekit_token()` verifies that the sid belongs to the current logged-in user and the current room. Only then does it sign the LiveKit JWT token.

### 14.7 LiveKit Connection and Media Toggles

After the token is returned, the frontend connects to LiveKit:

```js
await activeRoom.connect(url || tokenPayload.url, tokenPayload.token, {
  autoSubscribe: true,
});
```

Camera and microphone toggles are controlled through the LiveKit local participant:

```js
await activeRoom.localParticipant.setMicrophoneEnabled(enabled);
await activeRoom.localParticipant.setCameraEnabled(enabled);
```

Presentation wording:

> The project delegates media tracks to LiveKit `localParticipant`. The buttons only toggle local publication state; actual publish/subscribe behavior is handled by the LiveKit SDK.

### 14.8 Screen Share: Frontend Starts Media, Backend Enforces Rules

When the user clicks the share button, the frontend calls the LiveKit screen-share API:

```js
await activeRoom.localParticipant.setScreenShareEnabled(enabled, {
  audio: shareAudio,
  contentHint: config.contentHint,
  resolution: config.resolution,
});
```

But the rule "only one user can actively share at a time" is not handled by LiveKit automatically. The backend maintains it through `room_ui_event`:

```python
if event_type == "screen_share_started":
    if active_sharer_sid and active_sharer_sid != sid:
        emit("room_ui_event", {"type": "screen_share_denied"}, to=sid)
        return
    room["active_sharer_sid"] = sid
```

So explain screen sharing in two layers:

- LiveKit sends the screen picture and audio.
- Flask enforces meeting rules such as preventing multiple active sharers.

### 14.9 Recording: Frontend Capture, Backend Remux

The browser records with `getDisplayMedia` and `MediaRecorder`. If the output is WebM, `/api/remux-recording` uses `ffmpeg` to convert or remux it to MP4.

```js
recorderStream = await navigator.mediaDevices.getDisplayMedia({
  video: true,
  audio: true
});
activeRecorder = new MediaRecorder(recorderStream, recorderOptions);
```

This also explains two common questions:

- Recording depends on browser support for `getDisplayMedia` and `MediaRecorder`.
- WebM to MP4 conversion depends on server-side `ffmpeg`.

### 14.10 Chat Attachments: HTTP Upload First, Then Socket Broadcast

When a chat message contains an attachment, the frontend handles the file first:

```js
if (pendingAttachment) {
  attachmentPayload = await uploadPendingAttachment();
}
socket.emit('meeting_chat_send', {
  message,
  mentions,
  attachment: attachmentPayload
});
```

Backend `_api_chat_upload_impl()` stores the file. `on_meeting_chat_send()` writes the text and attachment metadata into `room["chat_history"]` and broadcasts the message.

Presentation wording:

> Files can be large, so they are uploaded to the server over HTTP first. The real-time chat channel only broadcasts text and attachment metadata. That keeps Socket.IO responsive without losing real-time chat behavior.

## 15. Current Limits and Future Improvements

Current limits:

- Online state is mainly single-process memory, so restart loses online state and multi-instance deployment is unsafe.
- `app.py` is large and should eventually be split by domain.
- Virtual background depends on a live local camera track, browser-side model loading, and canvas processing. Screen sharing and recording are also resource-heavy.
- MP4 recording export depends on server-side `ffmpeg`.
- LiveKit must be correctly configured with `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET`.

Future improvements:

- Move `rooms`, `sid_to_user`, and other runtime state to Redis for multi-instance deployment.
- Split `app.py` into modules for auth, meetings, chat attachments, admin, and recording.
- Add automated tests for login, room creation, join validation, attachment upload, and admin actions.
- Add clearer frontend messages for LiveKit connection failure, mobile screen sharing limits, background-blur model loading failures, and recording remux failures.

## 16. Common Q&A

### Why Not Use C?

Direct answer:

> C is suitable for low-level high-performance components, but this project's main challenge is web application integration and meeting workflow, not implementing a media engine from scratch.

Reasons:

- The project focuses on accounts, rooms, permissions, database, templates, and admin, not pure low-level performance.
- Flask handles routes, sessions, templates, and database integration quickly.
- Heavy media transport is already delegated to LiveKit.
- C would increase memory management and security implementation cost for this course project.

### How Does a User Join a Meeting?

The home page first calls `/api/join_room` to validate room ID and password. Then it opens `/room/<room_id>`. The room page emits Socket.IO `join_room`, receives `join_ok`, requests `/api/livekit/token`, and finally connects to LiveKit.

### How Are Camera and Microphone Used?

The frontend reads user preferences, then `room_livekit.js` calls `setCameraEnabled` and `setMicrophoneEnabled` on the LiveKit local participant.

### How Is Screen Sharing Implemented?

The frontend calls LiveKit screen sharing APIs. The backend maintains the active sharer state through `room_ui_event` to prevent multiple users from sharing at the same time.

### How Are Documents Sent in a Meeting?

The frontend uploads the attachment over HTTP to `/api/chat_upload_media` or `/api/chat_upload_doc`. The backend stores it and returns metadata. Then the frontend broadcasts text plus metadata through `meeting_chat_send`.

### How Is the Admin Dashboard Implemented?

The admin visits `/admin`. The backend aggregates system status, users, meetings, and password reset requests, then renders `admin.html`. Operations are mostly POST forms protected by `@admin_required`.

## 17. Final Presentation Summary

Do not describe the project as only "a frontend video meeting page." A more accurate summary is:

- Flask handles accounts, meetings, permissions, uploads, admin management, and LiveKit token issuance.
- Socket.IO handles real-time state sync inside meetings.
- LiveKit handles actual camera, microphone, and screen sharing media transport.
- SQLite persists users, meetings, and participation records.
- Frontend templates and JavaScript handle interaction, rendering, and API calls.

If the presentation follows five lines, it will cover most questions: registration/login, join flow, audio/video, chat attachments, and admin dashboard.
