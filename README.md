# Video Meeting Replace

基于 `Flask + Flask-SocketIO + LiveKit` 的在线视频会议系统，支持双语界面、账号体系、房间管理、聊天与附件、主持人控制、会议录屏转封装，以及房间侧 RTC 诊断信息展示。

## 当前架构

- 后端业务层：`Flask`
- 实时状态同步：`Flask-SocketIO`
- 音视频传输：`LiveKit SFU`
- 数据存储：`SQLite`（默认，可通过 `DATABASE_URL` 覆盖）
- 前端页面：`Jinja2 + 原生 JavaScript`

当前代码已经固定走 `LiveKit` 媒体模式，房间页通过 Socket.IO 同步成员、聊天、主持人动作和 UI 状态，不再维护旧的浏览器 Mesh 信令主路径。

## 主要功能

- 用户注册、登录、登出、单账号会话控制
- 创建会议、加入会议、会议历史
- 主持人结束会议、聊天室清空、后台管理
- 摄像头、麦克风、扬声器、屏幕共享
- 虚拟背景、房间内录屏并转封装为 MP4
- 聊天消息、@提及、图片/视频/文档附件
- 中英文界面和基础 i18n 检查
- 房间内 RTC/LiveKit 诊断摘要

## 项目结构

- `app.py`: 主 Flask 应用、路由、Socket.IO 事件、SQLAlchemy 模型、运行时配置
- `templates/`: Jinja 页面模板，房间页拆分为 `_room_layout.html` 和 `_room_scripts.html`
- `static/style.css`: 全站通用样式
- `static/room.css`: 房间页样式
- `static/room_utils.js`: 房间页通用工具函数
- `static/room_ui.js`: 房间布局与 UI 调度
- `static/room_chat.js`: 聊天消息与附件渲染
- `static/room_diagnostics.js`: RTC/LiveKit 诊断信息整理
- `static/room_livekit.js`: LiveKit 房间连接与本地/远端媒体控制
- `translations.py`: 中英文翻译表
- `check_i18n.py`: 模板中硬编码中文扫描脚本
- `docs/`: 说明文档、稳定性审计、答辩讲稿
- `instance/`: 运行期生成内容，例如 SQLite、上传文件、管理员初始密码

## 本地运行

Windows:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

## 依赖

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

## 环境变量

必需或常用配置：

- `SECRET_KEY`: Flask 会话密钥
- `DATABASE_URL`: 数据库连接串，默认使用 `instance/app.db`
- `PUBLIC_HOST`: 对外访问主机名或域名
- `PUBLIC_SCHEME`: `http` 或 `https`
- `ADMIN_USERNAME`: 初始管理员用户名，默认 `root`
- `ADMIN_PASSWORD`: 初始管理员密码；若未设置，程序会生成并写入 `instance/admin_password.txt`
- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`

可选配置：

- `TURN_PUBLIC_HOST`: TURN/ICE 公网主机名覆盖
- `SESSION_COOKIE_SAMESITE`
- `SESSION_COOKIE_SECURE`
- `REMEMBER_COOKIE_SAMESITE`
- `REMEMBER_COOKIE_SECURE`
- `DEBUG_ROOM=1`: 打开房间调试日志

## 运行前提

- 需要可用的 `LiveKit` 服务端，否则 `/room/<room_id>` 会返回 `503`
- 若要使用录屏转 MP4，服务端需要安装 `ffmpeg`
- 默认运行使用 SQLite；如果后续迁移到 MySQL/PostgreSQL，可通过 `DATABASE_URL` 切换

## 建议检查

- `python check_i18n.py`
- 手工验证登录、注册、创建房间、加入房间、退出房间
- 手工验证摄像头、麦克风、扬声器、屏幕共享、聊天与附件
- 手工验证中英文界面
- 至少做一次双端联调：桌面端和移动端互相进房，确认首进房即可收发远端媒体

## 文档

- `docs/README.md`: 文档导航
- `docs/STABILITY_AUDIT.md`: 当前 LiveKit 架构下的稳定性审计与后续建议
- `docs/答辩讲解文档.md`: 面向答辩场景的项目讲解稿，已补充“为什么不用 C 语言”
