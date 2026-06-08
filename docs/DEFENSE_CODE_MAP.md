# 答辩代码速查与文件梳理

这份文档按“助教现场问到哪里实现、变量存在哪里、函数干什么”来整理。建议答辩前先背主线，再按表格记几个关键行号和搜索关键词。

## 1. 一句话架构

项目是一个 `Flask + Flask-SocketIO + LiveKit` 在线会议系统：

- `Flask / app.py` 负责账号、页面路由、数据库、会议权限、附件上传、管理员后台、LiveKit token 签发。
- `Socket.IO` 负责实时业务状态：成员进出、聊天、主持人动作、屏幕共享 UI 状态。
- `LiveKit` 负责真正音视频媒体传输：摄像头、麦克风、屏幕共享轨道。
- `templates/` 负责页面结构，`static/js/room/` 负责房间前端交互，`static/css/` 负责样式。

最重要的答辩口径：

> Flask 不转发视频帧。浏览器拿 LiveKit token 后连接 LiveKit SFU，媒体轨道由 LiveKit/WebRTC 传输；Socket.IO 只同步房间业务和 UI 状态。

## 2. 最该记住的代码位置

| 被问内容 | 直接看哪里 | 搜索关键词 |
| --- | --- | --- |
| 项目启动入口 | `app.py` 3991 行附近初始化数据库和管理员，3998 行启动 `socketio.run` | `if __name__ == "__main__"` |
| Flask/Socket/数据库初始化 | `app.py` 58-79 行 | `app = Flask`、`SocketIO`、`SQLAlchemy` |
| 环境变量配置 | `app.py` 82-128 行、466-478 行 | `LIVEKIT_URL`、`EMAIL_SMTP_HOST`、`ADMIN_LOGIN_PATH` |
| 数据库模型 | `app.py` 576-669 行 | `class User`、`class Meeting` |
| 运行时房间状态变量 | `app.py` 495-503 行 | `rooms = {}`、`sid_to_user`、`user_active_sids` |
| 单个房间运行态结构 | `app.py` 1718 行 | `build_runtime_room_state` |
| 创建会议接口 | `app.py` 2561 行 | `/api/create_room`、`api_create_room` |
| 加入会议校验接口 | `app.py` 2595 行 | `/api/join_room`、`api_join_room` |
| 房间页面渲染 | `app.py` 2615 行、`templates/pages/room.html` | `room_page` |
| LiveKit token 签发 | `app.py` 2686 行 | `/api/livekit/token`、`AccessToken` |
| Socket 真正加入房间 | `app.py` 3130 行 | `@socketio.on("join_room")` |
| Socket 离开/断开清理 | `app.py` 3929 行、3981 行 | `leave_room`、`disconnect` |
| 屏幕共享 UI 状态 | `app.py` 1477-1539 行、3871 行 | `active_sharer`、`room_ui_event` |
| 聊天上传接口 | `app.py` 3535 行、3607-3619 行 | `_api_chat_upload_impl` |
| 聊天发送/清空/撤回 | `app.py` 3716、3787、3812 行 | `meeting_chat_send` |
| 录屏转 MP4 后端 | `app.py` 2765 行、1588-1607 行 | `/api/remux-recording` |
| 房间 DOM 布局 | `templates/partials/_room_layout.html` | `videoStage`、`chatWindow` |
| 房间变量注入和组装 | `templates/partials/_room_scripts.html` | `ROOM_ID`、`RoomPageBootstrap.initialize` |
| Socket 前端事件绑定 | `static/js/room/room_bootstrap.js` | `bindSocketEvents`、`join_ok` |
| LiveKit 前端控制器 | `static/js/room/room_livekit.js` | `createController`、`fetchToken` |
| 聊天前端渲染 | `static/js/room/room_chat.js` | `appendChatMessage` |
| 背景虚化 | `static/js/room/room_virtual_background.js` | `SelfieSegmentation` |
| 录屏前端 | `static/js/room/room_recording.js` | `MediaRecorder` |
| 中英文文案 | `i18n/translations.py` | `TRANSLATIONS` |

## 3. 数据和变量存在哪里

### 3.1 持久化数据库

数据库默认是 `instance/app.db`，由 `app.py` 的 `DB_PATH` 和 `SQLALCHEMY_DATABASE_URI` 指定。模型都在 `app.py` 576 行附近。

| 模型 | 存什么 | 关键字段 |
| --- | --- | --- |
| `User` | 用户账号和偏好 | `username`、`email`、`password_hash`、`is_admin`、`is_active_user`、`display_name`、`region`、默认设备开关 |
| `Meeting` | 会议主记录 | `room_id`、`room_password`、`host_user_id`、`host_name`、`status`、`created_at`、`ended_at` |
| `MeetingParticipant` | 参会历史 | `meeting_id`、`user_id`、`display_name`、`sid`、`joined_at`、`left_at` |
| `PasswordResetRequest` | 找回密码申请 | `username`、`contact`、`note`、`status` |
| `EmailVerificationCode` | 邮箱验证码 | `email`、`purpose`、`code_hash`、`expires_at`、`used_at` |
| `AdminSecurityActionToken` | 管理员安全邮件链接 token | `action`、`context_key`、`token_hash`、`expires_at` |

### 3.2 单进程内存运行态

这些变量在 `app.py` 495 行附近：

| 变量 | 类型/结构 | 作用 |
| --- | --- | --- |
| `runtime_state_lock` | `threading.RLock()` | 保护运行态读写，避免 Socket 事件并发修改房间状态 |
| `rooms` | dict | 每个在线房间的内存状态，包含在线成员、聊天、弹幕、共享屏幕 UI 状态、清理定时器 |
| `sid_to_user` | dict | Socket.IO 的 `sid` 到用户/房间信息的映射 |
| `user_active_sids` | dict | 一个用户当前活跃的 socket 集合，用于多标签、多设备、踢人和清理 |

单个房间结构在 `build_runtime_room_state()` 里创建，字段包括：

- `participants`: 当前在线成员，key 是 Socket sid。
- `host_user_id` / `host_present`: 主持人是谁、是否在线。
- `chat_history`: 当前房间聊天历史，最多保留 200 条。
- `chat_clear_markers`: 普通用户“只清自己聊天视图”的标记。
- `danmaku_enabled`: 弹幕开关。
- `active_sharer_sid` / `active_sharer_user_id`: 当前屏幕共享者的 UI 焦点状态。
- `cleanup_timer` / `expiry_timer`: 空房清理和会议过期定时器。

答辩重点：`rooms` 不是数据库，重启进程会丢；数据库保存会议存在与历史，内存保存在线实时状态。

### 3.3 运行时文件

`instance/` 是运行时目录，通常被忽略，不提交：

| 路径 | 作用 |
| --- | --- |
| `instance/app.db` | SQLite 数据库 |
| `instance/chat_uploads/<room_id>/` | 聊天附件实际文件 |
| `instance/security_lockdown.json` | 安全锁定状态 |
| `instance/security_recovery_code.txt` | 自动生成的安全恢复码 |
| `instance/admin_password.txt` 或相关启动文件 | 首次管理员密码/启动密钥类文件，具体看运行生成情况 |

## 4. 后端 app.py 分段记忆

`app.py` 是单体后端，约 4000 行。答辩时不要说“乱放在一起”，可以说“后端核心集中在 `app.py`，按配置、模型、工具函数、路由、Socket 事件分段组织”。

| 行号范围 | 内容 | 说明 |
| --- | --- | --- |
| 1-57 | imports | Flask、SocketIO、SQLAlchemy、LiveKit、Pillow、psutil、邮件等依赖 |
| 58-79 | app/db/socket 初始化 | 创建 Flask app、SocketIO、SQLAlchemy、LoginManager |
| 82-148 | 环境变量和安全配置 | 注册开关、Turnstile、人机验证、邮箱、管理员提醒、安全锁定 |
| 168-487 | 通用工具函数 | 邮箱、限流、安全检查、LiveKit 配置、房间号校验 |
| 495-575 | 运行时常量和全局状态 | `rooms`、`sid_to_user`、附件限制、时区列表 |
| 576-669 | 数据库模型 | 用户、会议、参会记录、验证码、安全 token |
| 673-843 | 登录/i18n/数据库初始化辅助 | `load_user`、`t()`、`ensure_user_columns()`、`ensure_admin()` |
| 843-1317 | 安全头、密码、邮件、管理员通知、邮箱验证码 | 登录注册安全链路和邮件链路 |
| 1324-1981 | 房间运行态辅助函数 | 成员 payload、共享屏幕状态、房间清理、踢人、快照 |
| 1993-2040 | 请求前检查 | 默认语言、安全锁定、单会话版本检查 |
| 2042-2554 | 页面路由 | 首页、账号、登录、注册、找回密码、管理员登录、退出 |
| 2561-2816 | REST API | 创建/加入会议、房间页、LiveKit token、历史、录屏、系统统计、健康检查 |
| 2827-3101 | 管理员路由 | 安全锁定/解锁、后台、用户管理、会议管理、重置申请 |
| 3115-3121 | 错误页 | 404、403 |
| 3125-3263 | Socket 连接、加入房间、更新昵称 | 成员实时状态入口 |
| 3267-3703 | 翻译和附件上传/访问 | Google 翻译、文件校验、附件查看/下载 |
| 3716-3982 | 聊天、弹幕、屏幕共享 UI、主持人结束、离会、断开 | 房间实时事件 |
| 3991-3998 | 启动初始化 | 加载锁定状态、建表、确保管理员、启动服务 |

## 5. 核心流程怎么讲

### 5.1 创建会议

1. 用户在首页 `templates/pages/index.html` 点击创建按钮。
2. 前端 `fetch('/api/create_room')`，传 `host_name`。
3. 后端 `app.py` 的 `api_create_room()` 创建 `Meeting` 数据库记录。
4. 后端调用 `build_runtime_room_state()` 和 `init_runtime_room()` 在 `rooms` 里放入运行态。
5. 返回 `room_id`、`password`、`join_url`。
6. 用户点进入房间，跳到 `/room/<room_id>?pwd=...`。

现场可以拉：

- `templates/pages/index.html` 的 `createBtn` 点击逻辑。
- `app.py` `@app.post("/api/create_room")`。
- `app.py` `build_runtime_room_state()`。

### 5.2 加入会议

1. 首页加入按钮先调用 `/api/join_room` 校验会议号和密码。
2. 校验通过后跳转 `/room/<room_id>?pwd=...`。
3. `room_page()` 渲染 `templates/pages/room.html`。
4. `room.html` include `_room_layout.html` 和 `_room_scripts.html`。
5. 前端 Socket 连接后在 `room_bootstrap.js` 里 emit `join_room`。
6. 后端 `on_join_room()` 再次校验登录、会议、密码、容量。
7. 服务端把当前 `request.sid` 写入 `rooms[room_id]["participants"]` 和 `sid_to_user`。
8. 服务端 emit `join_ok`，再广播 `participant_joined` 和 `participant_snapshot`。
9. 前端收到 `join_ok` 后才开始 LiveKit 连接。

关键点：页面加载不等于真正入会，真正入会是 Socket.IO 的 `join_room` 事件。

### 5.3 LiveKit 音视频连接

1. 前端必须先收到 `join_ok`，因为 LiveKit identity 要使用当前 Socket sid。
2. `_room_scripts.html` 的 `finalizeJoinBootstrap()` 调用 `ensureLiveKitConnected()`。
3. `ensureLiveKitConnected()` 创建 `RoomPageLiveKit` 控制器。
4. `room_livekit.js` 的 `fetchToken()` 请求 `/api/livekit/token`。
5. 后端 `api_livekit_token()` 验证：LiveKit 配置、会议号、密码、当前用户、当前 sid 是否已在 Socket 房间。
6. 后端用 `livekit_api.AccessToken(...).with_identity(participant_sid)` 签发 JWT。
7. 前端 `room.connect()` 连接 LiveKit。
8. 摄像头/麦克风/屏幕共享由 `setCameraEnabled()`、`setMicrophoneEnabled()`、`setScreenShareEnabled()` 发布到 LiveKit。

答辩重点：`participant_sid` 是 Socket.IO 和 LiveKit 对齐的关键 ID，后端故意要求先 Socket 入会再拿 token，避免只拿会议号密码就绕过房间状态。

### 5.4 远端视频如何显示

1. LiveKit 远端 participant 发布 track。
2. `room_livekit.js` 监听 LiveKit track 事件。
3. 根据 participant identity 找到对应 sid。
4. 调用 `_room_scripts.html` 传给控制器的 `addRemoteVideo(sid, stream)`。
5. `ensureCard()` 创建或更新视频卡片。
6. `renderLayout()` 重新排列主区域、侧栏、分页或屏幕共享焦点。

前端相关位置：

- `static/js/room/room_livekit.js`: LiveKit track 订阅和 `syncRemotePublication` 类逻辑。
- `templates/partials/_room_scripts.html`: `addRemoteVideo()`、`ensureCard()`、`renderLayout()`。
- `static/js/room/room_ui.js`: 渲染调度器，避免频繁重排。

### 5.5 屏幕共享

屏幕共享分两层：

- 媒体层：`room_livekit.js` 调 `setScreenShareEnabled()`，把屏幕视频/音频发布到 LiveKit。
- UI 层：前端通过 Socket.IO 发送 `room_ui_event`，后端记录 `active_sharer_sid`，再广播给其他人切换焦点布局。

后端关键函数：

- `set_active_sharer()` / `clear_active_sharer()`: 设置或清空共享者。
- `normalize_active_sharer_state()`: 下发前纠正失效共享者。
- `reconcile_departing_active_sharer()`: 共享者离开时清理或迁移状态。
- `on_room_ui_event()`: 处理 `screen_share_started`、`screen_share_stopped`、`screen_share_denied`。

前端关键函数：

- `_room_scripts.html` 的 `toggleScreenShareAction()`。
- `room_livekit.js` 的 `setScreenShareEnabled()`。
- `room_bootstrap.js` 监听 `room_ui_event` 后调用 `focusParticipant()`。

### 5.6 聊天和附件

普通文字聊天：

1. `_room_scripts.html` 的 `sendChatMessage()` 收集文本、@ 提及、附件。
2. 没有附件时直接 `socket.emit('meeting_chat_send')`。
3. 后端 `on_meeting_chat_send()` 把消息写入 `room["chat_history"]`。
4. 后端向全房间或主持人私聊目标广播 `meeting_chat_message`。
5. 前端 `room_chat.js` 的 `appendChatMessage()` 渲染消息。

附件聊天：

1. 前端选择媒体或文档，保存到 `pendingAttachment`。
2. 发送前先 `fetch('/api/chat_upload_media')` 或 `fetch('/api/chat_upload_doc')`。
3. 后端 `_api_chat_upload_impl()` 校验房间权限、扩展名、MIME、大小、容量。
4. 文件保存到 `instance/chat_uploads/<room_id>/media` 或 `docs`。
5. 后端返回 attachment 元数据。
6. 前端把 attachment 元数据随 `meeting_chat_send` 发送。
7. 查看附件走 `/chat_attachment/<room_id>/<token>`，原始预览走 `/raw`，下载走 `/download`。

权限点：

- `can_user_access_room()` 判断用户是否有资格上传。
- `_can_access_room_attachment()` 判断是否能访问附件。
- attachment 的 `permission` 为 `view` 时不给下载链接；为 `download` 时有下载链接。

### 5.7 录屏

录屏是浏览器本地增强，不是 LiveKit 传输的一部分。

1. `room_recording.js` 的 `toggleScreenRecording()` 调用 `navigator.mediaDevices.getDisplayMedia()`。
2. 用 `MediaRecorder` 录制屏幕。
3. 浏览器如果能直接生成 MP4 就下载 MP4。
4. 如果产物是 WebM，则上传到 `/api/remux-recording`。
5. 后端 `api_remux_recording()` 调 `ffmpeg` 转封装为 MP4；没有 ffmpeg 就返回 501。

### 5.8 背景虚化

背景虚化也是浏览器端增强，不是后端处理视频。

1. `room_virtual_background.js` 按需加载 MediaPipe `SelfieSegmentation`。
2. 从当前摄像头 track 克隆一份原始流。
3. 每帧送入 MediaPipe，得到人像 mask。
4. 用 canvas 绘制“人像清晰 + 背景模糊”的画面。
5. 用 `canvas.captureStream()` 得到处理后视频流。
6. 调 LiveKit 控制器的 `replaceCameraTrack()` 替换已发布摄像头轨道。
7. 失败时回退原始摄像头，保证会议基础视频不中断。

## 6. 前端房间文件分工

| 文件 | 主要职责 | 该记的函数/变量 |
| --- | --- | --- |
| `templates/pages/room.html` | 房间页模板入口，只 include 布局和脚本 | `_room_layout.html`、`_room_scripts.html` |
| `templates/partials/_room_layout.html` | 房间 DOM 骨架：顶部栏、控制区、视频舞台、聊天区 | `videoStage`、`videoMain`、`chatWindow`、`shareScreenBtn` |
| `templates/partials/_room_scripts.html` | 注入后端变量、创建状态变量、组装各 JS 模块、定义房间业务函数 | `ROOM_ID`、`socket`、`ensureCard()`、`renderLayout()`、`ensureLiveKitConnected()`、`toggleScreenShareAction()` |
| `static/js/room/room_bootstrap.js` | 房间启动器，集中绑定 Socket 事件、窗口事件、按钮事件 | `bindSocketEvents()`、`bindUiEvents()`、`initialize()` |
| `static/js/room/room_livekit.js` | LiveKit SDK 封装，媒体连接和 track 发布/订阅 | `createController()`、`fetchToken()`、`connect()`、`setCameraEnabled()`、`setScreenShareEnabled()` |
| `static/js/room/room_chat.js` | 聊天 UI 渲染，@ 提及、附件卡片、复制/翻译/撤回按钮 | `appendChatMessage()`、`renderChatMessageState()`、`buildAttachmentHtml()` |
| `static/js/room/room_diagnostics.js` | RTC/LiveKit 诊断面板 | `createRtcDiagnosticsController()`、`refresh()` |
| `static/js/room/room_ui.js` | 通用 UI 调度工具 | `createRenderScheduler()`、`createTaskQueue()` |
| `static/js/room/room_utils.js` | 通用工具函数 | `setStatus()`、`escapeHtml()`、`copyText()`、`stopStreamTracks()` |
| `static/js/room/room_recording.js` | 浏览器录屏和后端转 MP4 | `toggleScreenRecording()`、`transcodeRecordingBlob()` |
| `static/js/room/room_virtual_background.js` | 背景虚化和摄像头轨道替换 | `activateVirtualBackground()`、`replaceLiveKitCameraTrackFromStream()` |

## 7. 模板文件逐个梳理

### 7.1 pages

| 文件 | 页面/功能 | 后端入口 |
| --- | --- | --- |
| `templates/pages/base.html` | 所有页面的基础骨架，加载 `style.css`，定义 block，包含源码悬浮链接和本地时间渲染脚本 | 所有模板继承 |
| `templates/pages/index.html` | 登录后首页：创建会议、加入会议、快捷入口 | `index()`、`/api/create_room`、`/api/join_room` |
| `templates/pages/login.html` | 普通用户密码登录 | `login()` |
| `templates/pages/login_email_code.html` | 邮箱验证码登录 | `login_email_code()` |
| `templates/pages/register.html` | 注册页，支持邮箱验证码和 Turnstile | `register()` |
| `templates/pages/admin_login.html` | 管理员专用登录页 | `admin_login()`，路径由 `ADMIN_LOGIN_PATH` 控制 |
| `templates/pages/account.html` | 账号偏好：昵称、邮箱、语言、时区、附件权限、默认设备开关 | `account_page()` |
| `templates/pages/history.html` | 会议历史，展示创建/参加过的会议 | `history()` |
| `templates/pages/room.html` | 房间页入口，include 房间布局和脚本 | `room_page()` |
| `templates/pages/room_layout_test.html` | 静态布局测试页，不依赖真实媒体，用来测视频网格/焦点/聊天布局 | `room_layout_test_page()` |
| `templates/pages/admin.html` | 管理员后台：用户、会议、重置申请、系统统计 | `admin_dashboard()` 和 `/admin/...` 路由 |
| `templates/pages/forgot_password.html` | 用户提交找回密码申请 | `forgot_password_page()` |
| `templates/pages/forgot_password_support.html` | 找回密码支持页/补充联系方式 | `forgot_password_support_page()` |
| `templates/pages/security_unlock.html` | 安全锁定后的恢复码解锁页 | `admin_security_unlock()` |
| `templates/pages/attachment_view.html` | 聊天附件查看页，按权限显示预览和下载 | `chat_attachment_view()` |
| `templates/pages/help.html` | 用户指南 | `help_page()` |
| `templates/pages/quickstart.html` | 快速开始页 | `quickstart_page()` |
| `templates/pages/support.html` | 支持信息页 | `support_page()` |
| `templates/pages/404.html` | 404/403/503 等错误展示 | `not_found()`、`forbidden()`、`room_page()` 缺 LiveKit 时 |

### 7.2 partials

| 文件 | 作用 |
| --- | --- |
| `templates/partials/_room_layout.html` | 房间页面主体 DOM，所有按钮和视频/聊天容器都在这里 |
| `templates/partials/_room_scripts.html` | 房间脚本入口，后端变量转成 JS 常量，并把各模块拼成完整房间逻辑 |
| `templates/partials/_language_switch.html` | 中英文切换按钮，链接到 `/set-language/<lang>` |
| `templates/partials/_auth_topbar.html` | 登录/注册/支持类页面共用顶部导航 |
| `templates/partials/_auth_action_card.html` | 登录注册页面的小操作卡片 |
| `templates/partials/_turnstile_block.html` | Cloudflare Turnstile 人机验证容器 |

## 8. 静态资源逐个梳理

### 8.1 CSS

| 文件 | 作用 |
| --- | --- |
| `static/css/style.css` | 全站通用样式：页面背景、顶部栏、按钮、卡片、首页、后台、历史、帮助、支持等 |
| `static/css/auth.css` | 登录/注册/邮箱验证码/Turnstile 相关样式 |
| `static/css/room.css` | 房间页专用响应式布局：控制侧栏、视频舞台、聊天栏、分页、弹幕、窄屏适配 |

### 8.2 auth JS

| 文件 | 作用 |
| --- | --- |
| `static/js/auth/turnstile_loader.js` | 动态加载 Cloudflare Turnstile SDK，渲染验证码，保证提交前 token 存在 |
| `static/js/auth/auth_flow.js` | 登录/注册/邮箱验证码流程辅助，控制发送验证码按钮、提交状态、提示文案 |

### 8.3 room JS

见第 6 节。记忆顺序建议：

1. `room_bootstrap.js`: 先绑定事件，收到 `join_ok`。
2. `_room_scripts.html`: 拼上下文，定义业务函数。
3. `room_livekit.js`: 连接 LiveKit 和发布媒体。
4. `room_chat.js`: 处理聊天显示。
5. `room_recording.js` 和 `room_virtual_background.js`: 增强功能。

## 9. 根目录和支持文件

| 文件/目录 | 作用 |
| --- | --- |
| `app.py` | 后端核心单体文件 |
| `requirements.txt` | Python 依赖：Flask、SocketIO、SQLAlchemy、Login、dotenv、Pillow、psutil、LiveKit API |
| `README.md` | 项目总说明、入口、快速开始、部署前置说明 |
| `AGENTS.md` | 给代码代理/协作者看的仓库约束，记录项目结构、测试要求、LiveKit 回归点 |
| `check_i18n.py` | 根目录包装器，调用 `scripts/check_i18n.py` |
| `translations.py` | 兼容导出入口，实际翻译表在 `i18n/translations.py` |
| `LICENSE` | 开源许可证 |
| `.gitignore` | 忽略虚拟环境、实例目录等不该提交的文件 |
| `venv/` | 本地 Python 虚拟环境，不属于业务代码 |
| `instance/` | 运行时数据库、上传文件、安全状态，不属于源码提交内容 |
| `__pycache__/` | Python 缓存，不属于业务代码 |

## 10. i18n 和检查脚本

| 文件 | 作用 |
| --- | --- |
| `i18n/translations.py` | `TRANSLATIONS = {'zh': ..., 'en': ...}`，所有 `t('key')` 的来源 |
| `i18n/__init__.py` | i18n 包初始化文件 |
| `translations.py` | 从 `i18n.translations` 兼容导出，方便旧代码引用 |
| `scripts/check_i18n.py` | 扫描模板中未通过 `t(...)` 抽取的硬编码中文 |
| `scripts/__init__.py` | scripts 包初始化文件 |

答辩说法：

> 模板里尽量不直接写中文，而是写 `t('key')`。后端通过 `inject_globals()` 把 `t` 注入模板，语言存在 session 里，翻译表在 `i18n/translations.py`。

## 11. docs 文档目录

| 文件 | 作用 |
| --- | --- |
| `docs/README.md` | 文档地图，告诉读者先看哪一份 |
| `docs/项目说明与代码索引.md` | 项目总讲解、架构、核心流程、常见问答 |
| `docs/DEPLOYMENT_GUIDE.md` | 部署手册，包含 Nginx、HTTPS、LiveKit、systemd 等 |
| `docs/STABILITY_AUDIT.md` | 稳定性审计，尤其是房间、LiveKit、屏幕共享、录屏风险 |
| `docs/REFACTOR_AUDIT.md` | 重构审计，说明以后拆分 `app.py` 和前端脚本的方向 |
| `docs/DEFENSE_CODE_MAP.md` | 当前这份答辩代码速查文档 |

## 12. 常见追问怎么回答

### Q1: 视频是在哪里实现的？

答：

> 后端不处理视频帧。后端只在 `app.py` 的 `/api/livekit/token` 签发 LiveKit token。前端在 `room_livekit.js` 里创建 LiveKit Room，调用 `setCameraEnabled()`、`setMicrophoneEnabled()`、`setScreenShareEnabled()` 发布本地媒体。远端 track 由 LiveKit 事件回调同步到页面视频卡片。

现场拉：

- `app.py` `api_livekit_token()`
- `static/js/room/room_livekit.js` `fetchToken()`、`connect()`、`setCameraEnabled()`
- `_room_scripts.html` `ensureLiveKitConnected()`、`addRemoteVideo()`

### Q2: 房间在线人数和成员列表存在哪里？

答：

> 正在开会的在线状态存在 `app.py` 的内存变量 `rooms` 里，具体是 `rooms[room_id]["participants"]`。每个参与者 key 是 Socket sid。数据库的 `MeetingParticipant` 保存历史参会记录，不负责实时在线名单。

现场拉：

- `app.py` 495 行 `rooms = {}`
- `app.py` `build_runtime_room_state()`
- `app.py` `on_join_room()` 写入 `room["participants"][sid]`

### Q3: 会议号和密码存在哪里？

答：

> 持久化在 `Meeting` 表：`room_id` 和 `room_password`。创建会议时 `api_create_room()` 生成并写数据库，同时在 `rooms` 里保存一份运行态密码用于 Socket 加入校验。

### Q4: 为什么先 Socket.IO 入会，再连接 LiveKit？

答：

> 因为 LiveKit identity 使用 Socket sid。后端 `/api/livekit/token` 会检查这个 sid 是否已经属于当前用户和当前房间，防止只知道会议号密码就绕过 Socket 房间状态直接申请媒体 token。

### Q5: 聊天记录存数据库吗？

答：

> 当前会议中的聊天存在内存 `rooms[room_id]["chat_history"]`，不是数据库持久化历史。附件文件会保存到 `instance/chat_uploads/<room_id>/`，聊天消息里保存附件 token 和 URL 等元数据。房间结束或清理时附件目录会被删除。

### Q6: 管理员怎么来的？

答：

> 启动时 `app.py` 3991 行附近会执行 `ensure_admin()`。它根据环境变量或启动生成的默认信息确保至少有一个管理员。管理员登录走 `ADMIN_LOGIN_PATH`，默认 `/admin-login`，后台页面是 `/admin`。

### Q7: 用户密码安全吗？

答：

> 用户密码不明文保存。`User.set_password()` 用 Werkzeug 的 `generate_password_hash()` 保存哈希，登录时 `check_password_hash()` 校验。管理员也一样。

### Q8: 为什么说当前不适合多实例横向扩展？

答：

> 因为 `rooms`、`sid_to_user`、`user_active_sids` 都是单进程内存状态。如果开多个 Flask 进程，不同进程看不到彼此的在线房间和 socket 状态。要多实例需要 Redis 这类共享状态和 Socket.IO message queue。

### Q9: 背景虚化是后端做的吗？

答：

> 不是。背景虚化在浏览器端 `room_virtual_background.js` 实现，使用 MediaPipe SelfieSegmentation 和 canvas 处理帧，然后把处理后 track 替换给 LiveKit。后端不处理虚化视频。

### Q10: 录屏是不是录服务器的视频？

答：

> 不是。录屏使用浏览器 `getDisplayMedia()` 和 `MediaRecorder` 本地录制。后端 `/api/remux-recording` 只是可选把 WebM 转封装成 MP4，方便下载播放。

## 13. 答辩时建议背的 6 条主线

1. 账号线：`register/login/account` 页面表单 -> `User` 表 -> Flask-Login session。
2. 会议线：首页 `create/join` -> `Meeting` 表 -> `rooms` 运行态 -> `/room/<room_id>`。
3. 实时线：前端 `socket.emit` -> 后端 `@socketio.on` -> `rooms` 状态 -> 广播事件。
4. 媒体线：Socket `join_ok` -> 请求 LiveKit token -> 前端连接 LiveKit -> 发布/订阅 track。
5. 聊天线：文字走 Socket，附件先上传到 Flask，再把附件元数据随聊天事件广播。
6. 管理线：`/admin-login` 登录管理员 -> `/admin` 后台 -> 用户/会议/重置申请/系统统计操作。

## 14. 现场查找关键词

如果现场紧张，可以直接用编辑器搜索：

| 想找 | 搜索 |
| --- | --- |
| 创建房间 | `api_create_room` |
| 加入房间 | `on_join_room` |
| LiveKit token | `api_livekit_token` |
| 运行态房间结构 | `build_runtime_room_state` |
| 在线成员快照 | `participant_snapshot` |
| 屏幕共享状态 | `active_sharer` |
| 聊天发送 | `meeting_chat_send` |
| 附件上传 | `_api_chat_upload_impl` |
| 背景虚化 | `activateVirtualBackground` |
| 录屏 | `toggleScreenRecording` |
| 管理后台 | `admin_dashboard` |
| 安全锁定 | `security_lockdown` |
| 翻译表 | `TRANSLATIONS` |

