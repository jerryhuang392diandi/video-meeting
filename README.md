# 视频会议系统

[中文](README.md) | [English](README.en.md)

基于 `Flask + Flask-SocketIO + LiveKit` 的在线视频会议系统。当前版本使用 LiveKit SFU 作为音视频主链路，Socket.IO 负责房间成员、聊天、主持人操作和界面状态同步。

## 你可以用它做什么

- 注册、登录、退出，以及基础会话控制
- 创建会议、加入会议、查看历史会议
- 摄像头、麦克风、扬声器和屏幕共享
- 房间聊天、@ 提及、图片/视频/文档附件
- 附件查看权限与下载权限控制
- 虚拟背景和浏览器端录屏
- 主持人结束会议、清空聊天、控制房间行为
- 管理员后台：用户管理、会议管理、密码重置申请、系统统计
- 中英文界面和基础 i18n 检查
- 房间内 RTC/LiveKit 诊断面板

## 技术架构

| 层级 | 技术 | 职责 |
| --- | --- | --- |
| Web 后端 | Flask | 路由、认证、数据库模型、管理后台、文件上传、LiveKit token |
| 实时状态 | Flask-SocketIO | 成员进出、聊天广播、主持人动作、房间 UI 状态 |
| 媒体传输 | LiveKit SFU | 摄像头、麦克风、屏幕共享、远端轨道订阅 |
| 数据存储 | SQLite 默认，可用 `DATABASE_URL` 覆盖 | 用户、会议、历史记录、密码重置等持久化数据 |
| 前端 | Jinja2 + vanilla JavaScript | 页面渲染、房间交互、媒体控制、诊断展示 |

## 项目结构

```text
.
├── app.py                    # Flask 路由、Socket.IO 事件、模型、运行配置
├── templates/                # Jinja2 页面模板
├── static/                   # 房间 JS、样式和前端资源
├── translations.py           # 中英文翻译表
├── check_i18n.py             # 模板硬编码中文检查
├── requirements.txt          # Python 依赖
├── docs/                     # 部署、稳定性、答辩等文档
└── instance/                 # 运行时目录，生成后不纳入版本管理
```

房间相关前端文件分工：

- `static/room_livekit.js`: LiveKit 连接、本地媒体发布、远端轨道处理
- `static/room_ui.js`: 参会者卡片、布局、焦点和屏幕共享视图
- `static/room_chat.js`: 聊天消息和附件渲染
- `static/room_diagnostics.js`: RTC/LiveKit 诊断摘要
- `static/room_utils.js`: 共享工具函数

## 本地运行

Windows:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

macOS / Linux:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

默认会使用 `instance/app.db` 作为 SQLite 数据库。首次运行时如果没有设置管理员密码，应用会生成初始密码并写入 `instance/admin_password.txt`。

## 关键配置

最重要的是 LiveKit 配置。缺少这些配置时，房间媒体能力不可用，`/room/<room_id>` 会返回 `503`。

| 环境变量 | 说明 |
| --- | --- |
| `SECRET_KEY` | Flask 会话密钥 |
| `LIVEKIT_URL` | LiveKit 服务地址 |
| `LIVEKIT_API_KEY` | LiveKit API key |
| `LIVEKIT_API_SECRET` | LiveKit API secret |
| `DATABASE_URL` | 数据库连接串，默认使用 `instance/app.db` |
| `PUBLIC_HOST` | 对外访问域名或主机名 |
| `PUBLIC_SCHEME` | 对外访问协议，通常为 `http` 或 `https` |
| `ADMIN_USERNAME` | 初始管理员用户名，默认 `root` |
| `ADMIN_PASSWORD` | 初始管理员密码；未设置时自动生成 |
| `DEBUG_ROOM=1` | 输出房间相关调试日志 |

可选项包括 `TURN_PUBLIC_HOST`、`SESSION_COOKIE_SAMESITE`、`SESSION_COOKIE_SECURE`、`REMEMBER_COOKIE_SAMESITE`、`REMEMBER_COOKIE_SECURE`。

## 运行限制

- 当前在线态主要保存在单进程内存中，默认应按单实例部署理解。
- LiveKit 是外部媒体基础设施，必须正确配置后房间媒体才可用。
- 录屏转 MP4 依赖服务端 `ffmpeg`；未安装时只能保留浏览器原始录制结果。
- 虚拟背景、屏幕共享和录屏都比较消耗资源，弱设备上应优先保证会议可用性。

## 提交前检查

```bash
python check_i18n.py
```

建议再做一次手动烟测：

- 登录、注册、创建房间、加入房间、退出房间
- 桌面端和移动端双端进房，确认首次加入即可看到远端媒体
- 摄像头、麦克风、屏幕共享开始和停止
- 聊天、附件上传、附件查看/下载权限
- 中英文界面切换
- 管理员后台常用操作

## 文档

- [docs/README.md](docs/README.md) / [English](docs/README.en.md): 文档地图
- [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) / [English](docs/DEPLOYMENT_GUIDE.en.md): 部署、更新和排障
- [docs/STABILITY_AUDIT.md](docs/STABILITY_AUDIT.md) / [English](docs/STABILITY_AUDIT.en.md): 稳定性风险和后续演进建议
- [docs/项目说明与代码索引.md](docs/%E9%A1%B9%E7%9B%AE%E8%AF%B4%E6%98%8E%E4%B8%8E%E4%BB%A3%E7%A0%81%E7%B4%A2%E5%BC%95.md) / [English](docs/PROJECT_GUIDE.en.md): 项目逻辑、核心流程、代码索引和展示讲解口径
- `docs/视觉媒体通信期末大作业实践报告.docx`: 课程报告原稿
