# 视频会议系统 / Video Meeting System

基于 `Flask + Flask-SocketIO + LiveKit` 的在线视频会议系统，当前版本已经以 LiveKit SFU 作为音视频主链路，Socket.IO 负责房间成员状态、聊天消息、主持人操作与界面同步。

This is an online meeting system built with `Flask + Flask-SocketIO + LiveKit`. The current implementation uses LiveKit SFU as the primary media path, while Socket.IO handles room state, chat, host actions, and UI synchronization.

## 项目概览 / Overview

- 中文：这是一个面向课程项目与功能验证场景的完整 Web 会议应用，不只是音视频 Demo，还包含账号体系、房间管理、历史记录、聊天附件、管理员后台和基础诊断能力。
- English: This is a complete web meeting application for coursework and feature validation, not just an audio/video demo. It includes accounts, room management, meeting history, chat attachments, an admin console, and basic diagnostics.

## 当前技术架构 / Current Architecture

- 后端业务层 / Backend business layer: `Flask`
- 实时状态同步 / Real-time state sync: `Flask-SocketIO`
- 音视频媒体层 / Media transport: `LiveKit SFU`
- 数据存储 / Data storage: `SQLite` by default, overridable via `DATABASE_URL`
- 前端渲染 / Frontend rendering: `Jinja2 + vanilla JavaScript`

## 主要功能 / Main Features

- 用户注册、登录、退出、单账号会话控制
- 创建会议、加入会议、历史会议查看
- 摄像头、麦克风、扬声器、屏幕共享
- 聊天消息、@ 提及、图片/视频/文档附件
- 附件权限控制：仅查看或允许下载
- 虚拟背景
- 浏览器端录屏，必要时调用服务端 `ffmpeg` 转封装为 MP4
- 主持人结束会议、清空聊天、房间内主持权限控制
- 管理员后台：用户管理、会议管理、密码重置申请处理、系统统计
- 中英文界面与基础 i18n 检查
- 房间内 RTC/LiveKit 诊断面板

Main feature set:

- User registration, login, logout, and single-account session control
- Meeting creation, join flow, and history records
- Camera, microphone, speaker, and screen sharing
- Chat messages, mentions, and media/document attachments
- Attachment permission control: view-only or downloadable
- Virtual background
- Browser-side recording with optional server-side `ffmpeg` remux to MP4
- Host controls for ending meetings and clearing chat
- Admin console for user, meeting, and reset-request management
- Bilingual UI with basic i18n checks
- In-room RTC/LiveKit diagnostics

## 项目结构 / Project Structure

- `app.py`: Flask 应用入口、路由、Socket.IO 事件、SQLAlchemy 模型、运行时配置
- `templates/`: 页面模板，房间页重点拆分为 `_room_layout.html` 与 `_room_scripts.html`
- `static/room_livekit.js`: LiveKit 房间连接与媒体发布/订阅逻辑
- `static/room_ui.js`: 房间布局、卡片排序、共享焦点等界面逻辑
- `static/room_chat.js`: 聊天与附件渲染
- `static/room_diagnostics.js`: RTC/LiveKit 诊断摘要整理
- `translations.py`: 中英文翻译表
- `check_i18n.py`: 模板硬编码中文扫描脚本
- `docs/`: 项目文档、部署说明、稳定性审计、答辩讲解稿
- `instance/`: 运行时生成目录，例如 SQLite 数据库、上传文件、管理员初始密码

## 本地运行 / Local Development

### Windows

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

## 依赖 / Dependencies

`requirements.txt` 当前包含：

- `flask`
- `flask-socketio`
- `flask-sqlalchemy`
- `flask-login`
- `python-dotenv`
- `simple-websocket`
- `pillow`
- `psutil`
- `livekit-api`

## 关键环境变量 / Important Environment Variables

### 必填或强相关 / Required or strongly recommended

- `SECRET_KEY`: Flask 会话密钥 / Flask session secret
- `LIVEKIT_URL`: LiveKit 服务地址 / LiveKit server URL
- `LIVEKIT_API_KEY`: LiveKit API key
- `LIVEKIT_API_SECRET`: LiveKit API secret

### 常用业务配置 / Common application config

- `DATABASE_URL`: 数据库连接串，默认使用 `instance/app.db`
- `PUBLIC_HOST`: 对外访问域名或主机名
- `PUBLIC_SCHEME`: `http` 或 `https`
- `ADMIN_USERNAME`: 初始管理员用户名，默认 `root`
- `ADMIN_PASSWORD`: 初始管理员密码；未设置时会生成并写入 `instance/admin_password.txt`
- `DEBUG_ROOM=1`: 输出房间相关调试日志

### 可选部署项 / Optional deployment items

- `TURN_PUBLIC_HOST`: 对外 ICE/TURN 主机名覆盖
- `SESSION_COOKIE_SAMESITE`
- `SESSION_COOKIE_SECURE`
- `REMEMBER_COOKIE_SAMESITE`
- `REMEMBER_COOKIE_SECURE`

## 运行前提与限制 / Runtime Requirements and Constraints

- 当前房间在线态主要保存在单进程内存中，因此默认按单实例部署来理解更安全。
- LiveKit 未配置完成时，房间媒体能力不可用，`/room/<room_id>` 会返回 `503`。
- 录屏转 MP4 依赖服务端安装 `ffmpeg`；未安装时只能保留浏览器原始录制结果。
- 虚拟背景、屏幕共享、录屏都属于高资源占用功能，弱设备上要优先保证稳定性而不是视觉效果。

Current practical constraints:

- Runtime room presence is still mainly stored in single-process memory, so this should be treated as a single-instance deployment by default.
- If LiveKit is not configured, room media features are unavailable and `/room/<room_id>` returns `503`.
- MP4 remux depends on server-side `ffmpeg`.
- Virtual background, screen share, and recording are all resource-heavy features on low-end devices.

## 建议验证项 / Suggested Checks

- `python check_i18n.py`
- 登录、注册、创建房间、加入房间、退出房间
- 双端联调：桌面端和移动端互相进房，确认首次进房即可看到远端媒体
- 屏幕共享开始、停止、刷新恢复
- 聊天、附件上传、附件查看权限
- 中英文界面切换
- 管理员后台常用操作

## 文档索引 / Documentation Index

- [docs/README.md](docs/README.md): 文档总览 / documentation hub
- [docs/STABILITY_AUDIT.md](docs/STABILITY_AUDIT.md): 稳定性与架构风险审计 / stability and architecture risk audit
- [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md): 部署、更新与排障手册 / deployment, update, and troubleshooting guide
- [docs/答辩讲解文档.md](docs/%E7%AD%94%E8%BE%A9%E8%AE%B2%E8%A7%A3%E6%96%87%E6%A1%A3.md): 课程答辩讲解稿 / defense presentation notes
- `docs/视觉媒体通信期末大作业实践报告.docx`: 课程报告原稿，按你的要求保留，不在这次重写范围内
