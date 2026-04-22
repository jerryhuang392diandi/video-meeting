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
- 面向外国友人的中英双语 Quickstart 快速开始页
- 更完整的用户指南，覆盖账户偏好、入会设备、聊天附件、屏幕共享和主持人操作
- 房间内 RTC/LiveKit 诊断面板

## 使用入口

| 路径 | 页面 | 适合谁看 |
| --- | --- | --- |
| `/` | 首页 / 创建会议 / 加入会议 | 登录后的普通用户 |
| `/login` | 登录页 | 已有账号的用户 |
| `/register` | 注册页 | 第一次使用的用户 |
| `/forgot-password` | 找回密码申请页 | 忘记密码的用户 |
| `/quickstart` | 快速开始页 | 第一次开会的人，中英双语最短流程 |
| `/help` | 用户指南 | 想了解账户偏好、设备、聊天附件、屏幕共享、主持人操作的人 |
| `/support` | 支持页 | 登录、入会、设备权限、文件上传异常时查看 |
| `/account` | 个人账户与偏好 | 修改昵称、语言、地区/时区、附件权限、默认设备开关 |
| `/history` | 历史会议 | 查看自己创建或参加过的会议 |
| `/room/<会议号>` | 会议房间 | 参会者实际开会页面，通常通过邀请链接进入 |
| `/admin` | 管理员后台 | root / 管理员处理用户、会议、密码重置、系统统计 |

时间显示规则：

- 普通用户查看 `/history` 时，会议时间按该用户在 `/account` 保存的地区/时区显示。
- 管理员查看 `/admin` 时，用户注册时间、当前会议和历史会议时间按当前管理员账号的地区/时区显示。

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

## 快速开始

下面写的是零基础本地运行步骤，适合改代码和课堂演示前自测；真正让别人从公网访问，仍然要看后面的云服务器部署。

你需要先会打开命令行：

| 系统 | 推荐打开方式 | 说明 |
| --- | --- | --- |
| Windows | PowerShell 或 CMD | 开始菜单搜索 `PowerShell` 或 `cmd`；下面优先写 PowerShell，也补充 CMD 差异 |
| macOS | Terminal 终端 | 默认 shell 通常是 `zsh`，可以直接执行本文的 bash 风格命令 |
| Linux | Terminal 终端 | 通常自带 `bash`；如果是极简系统，先安装 `bash`、`python3`、`git` |

### 1. 先安装基础软件

Windows 建议安装：

| 软件 | 用途 | 获取方式 |
| --- | --- | --- |
| Python 3.10+ | 运行 Flask 项目 | https://www.python.org/downloads/ |
| Git | 下载代码、版本管理 | https://git-scm.com/downloads |
| FFmpeg | 录屏导出 MP4 时使用；不装也能启动项目 | https://ffmpeg.org/download.html 或 `winget install Gyan.FFmpeg` |
| VS Code | 编辑代码，可选 | https://code.visualstudio.com/ |

如果 Windows 的 `winget` 可用，也可以在 PowerShell 里安装：

```powershell
winget install Python.Python.3.12
winget install Git.Git
winget install Gyan.FFmpeg
winget install Microsoft.VisualStudioCode
```

macOS 建议安装：

| 软件 | 用途 | 获取方式 |
| --- | --- | --- |
| Homebrew | 安装命令行工具 | https://brew.sh/ |
| Python 3.10+ | 运行 Flask 项目 | `brew install python` |
| Git | 下载代码、版本管理 | `brew install git` |
| FFmpeg | 录屏导出 MP4 时使用；不装也能启动项目 | `brew install ffmpeg` |
| VS Code | 编辑代码，可选 | https://code.visualstudio.com/ |

Linux Ubuntu / Debian 建议安装：

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git ffmpeg bash
```

安装后检查版本：

Windows PowerShell / CMD：

```powershell
python --version
git --version
ffmpeg -version
```

macOS / Linux：

```bash
python3 --version
git --version
ffmpeg -version
```

### 2. 创建本地项目文件夹

Windows PowerShell 示例：

```powershell
mkdir D:\projects
cd D:\projects
git clone https://github.com/jerryhuangqingxuan/video-meeting-replace.git
cd video-meeting-replace
```

Windows CMD 示例：

```bat
mkdir D:\projects
cd /d D:\projects
git clone https://github.com/jerryhuangqingxuan/video-meeting-replace.git
cd video-meeting-replace
```

macOS / Linux 示例：

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/jerryhuangqingxuan/video-meeting-replace.git
cd video-meeting-replace
```

如果你没有 Git 仓库，也可以把压缩包解压到一个固定目录，然后在终端 `cd` 进入项目目录。

### 3. 创建 Python 虚拟环境并安装依赖

Windows PowerShell:

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Windows CMD:

```bat
python -m venv venv
venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```

macOS / Linux:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

以后每次重新打开终端，都要先进入项目目录并激活虚拟环境。

### 4. 配置本地 `.env`

如果只想看登录、注册、首页、帮助页，可以先不写 LiveKit 配置；但进入会议房间会返回 `503`，这是正常的保护逻辑。

如果要本地测试会议音视频，建议先用 LiveKit Cloud，创建项目后把三项配置写入项目根目录 `.env`：

```env
SECRET_KEY=local-dev-secret-change-me
PUBLIC_SCHEME=http
PUBLIC_HOST=127.0.0.1:5000

LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=replace-with-livekit-api-key
LIVEKIT_API_SECRET=replace-with-livekit-api-secret

ADMIN_USERNAME=root
ADMIN_PASSWORD=root1234
```

`.env` 不要提交到 Git。

### 5. 启动项目

Windows / macOS / Linux 激活虚拟环境后都执行：

```bash
python app.py
```

浏览器打开：

```text
http://127.0.0.1:5000
```

默认会使用 `instance/app.db` 作为 SQLite 数据库。首次运行时如果没有设置管理员密码，应用会生成初始密码并写入 `instance/admin_password.txt`。

### 6. 本地常见问题

| 现象 | 优先检查 |
| --- | --- |
| `python` 命令不存在 | Python 是否安装；Windows 安装时是否勾选 Add Python to PATH |
| `git` 命令不存在 | Git 是否安装；重新打开终端 |
| `pip install` 很慢 | 可以换国内 PyPI 镜像，或先确认网络 |
| `/room/<会议号>` 返回 `503` | `.env` 里缺少 `LIVEKIT_URL`、`LIVEKIT_API_KEY`、`LIVEKIT_API_SECRET` |
| 录屏转 MP4 失败 | 是否安装 FFmpeg，并且 `ffmpeg -version` 能输出版本 |

## 云服务器部署概览

生产或课程展示部署建议采用：

```text
浏览器
  -> 域名 / Cloudflare DNS
  -> Nginx 反向代理和 HTTPS
  -> Gunicorn + eventlet 运行 Flask-SocketIO
  -> Flask 应用
  -> LiveKit Cloud 或自建 LiveKit 负责媒体传输
```

最小服务器建议：

- Ubuntu 22.04 / 24.04 LTS。
- 2 vCPU、2 GB 内存起步；多人演示、录屏转封装或后台任务较多时建议 4 GB 内存。
- 开放 `80`、`443` 端口；SSH 端口按云厂商安全组配置。
- 准备一个域名，例如 `meeting.example.com`。
- LiveKit 建议优先使用 LiveKit Cloud；如果自建 LiveKit，需要额外准备 LiveKit 服务、TLS、UDP/TCP 可达性和 TURN/ICE 配置。

常见云服务器入口：

| 厂商 | 链接 |
| --- | --- |
| 阿里云 ECS | https://www.aliyun.com/product/ecs |
| 腾讯云 CVM | https://cloud.tencent.com/product/cvm |
| 华为云 ECS | https://www.huaweicloud.com/product/ecs.html |
| AWS EC2 | https://aws.amazon.com/ec2/ |
| Azure Virtual Machines | https://azure.microsoft.com/products/virtual-machines/ |
| DigitalOcean Droplets | https://www.digitalocean.com/products/droplets |
| Vultr Cloud Compute | https://www.vultr.com/products/cloud-compute/ |

常见配套平台入口：

| 平台 | 用途 | 链接 |
| --- | --- | --- |
| Cloudflare | DNS 托管、可选 CDN/代理、SSL/TLS 设置 | https://www.cloudflare.com/ |
| Cloudflare 控制台 | 添加 DNS 记录、切换 DNS only / Proxied | https://dash.cloudflare.com/ |
| LiveKit Cloud | 托管 LiveKit 媒体服务，复制 `LIVEKIT_URL`、API key、API secret | https://cloud.livekit.io/ |
| GitHub | 代码托管与版本管理 | https://github.com/ |
| Gitee | 国内可选代码托管平台 | https://gitee.com/ |

完整 Linux 云服务器操作步骤见 [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)。这份部署手册已经按零基础顺序重写了 Nginx 和 LiveKit 相关内容，建议第一次部署时照着它从前往后做，不要直接跳到配置片段。

里面包括：

- 购买服务器后的安全组、防火墙、系统用户和目录准备。
- Cloudflare 或普通 DNS 解析配置。
- Python 虚拟环境、依赖安装和 `.env` 配置。
- Nginx 为什么需要反向代理、WebSocket 头、上传体积限制和 HTTPS。
- systemd 服务文件、开机自启、日志查看和线上更新。
- LiveKit Cloud 的最短接入步骤，以及自建 LiveKit 时域名、证书、媒体端口、TURN/ICE 的检查清单。
- LiveKit 缺失、WebSocket 失败、附件上传、录屏转 MP4 等常见排障。

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

## 参考资料

部署和运行配置主要参考以下官方文档；更详细的逐步说明见 [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) 的“参考依据”章节。

| 主题 | 官方文档 |
| --- | --- |
| Flask-SocketIO 部署 | [Flask-SocketIO Deployment](https://flask-socketio.readthedocs.io/en/latest/deployment.html) |
| Gunicorn 参数 | [Gunicorn Settings](https://docs.gunicorn.org/en/stable/settings.html) |
| Nginx WebSocket 代理 | [Nginx WebSocket proxying](https://nginx.org/en/docs/http/websocket.html) |
| Certbot / Let's Encrypt | [Certbot install guide](https://eff-certbot.readthedocs.io/en/stable/install.html) |
| Let's Encrypt | [Let's Encrypt](https://letsencrypt.org/) |
| Cloudflare 入口 | [Cloudflare](https://www.cloudflare.com/) / [Dashboard](https://dash.cloudflare.com/) |
| Cloudflare DNS 记录 | [Create DNS records](https://developers.cloudflare.com/dns/manage-dns-records/how-to/create-dns-records/) |
| Cloudflare SSL 模式 | [Cloudflare Full (strict)](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/) |
| 域名注册商示例 | [阿里云域名](https://wanwang.aliyun.com/) / [腾讯云 DNSPod](https://dnspod.cloud.tencent.com/) / [Cloudflare Registrar](https://www.cloudflare.com/products/registrar/) / [Namecheap](https://www.namecheap.com/) |
| systemd 环境变量 | [systemd.exec EnvironmentFile](https://www.freedesktop.org/software/systemd/man/systemd.exec.html) |
| LiveKit | [LiveKit Docs](https://docs.livekit.io/) / [LiveKit Cloud](https://cloud.livekit.io/) |
| GitHub / Gitee | [GitHub](https://github.com/) / [Gitee](https://gitee.com/) |
| 本地工具 | [Python](https://www.python.org/downloads/) / [Git](https://git-scm.com/downloads) / [FFmpeg](https://ffmpeg.org/download.html) / [VS Code](https://code.visualstudio.com/) / [Homebrew](https://brew.sh/) / [winget](https://learn.microsoft.com/windows/package-manager/winget/) |

## 文档

| 文档 | 用途 |
| --- | --- |
| [docs/README.md](docs/README.md) / [English](docs/README.en.md) | 文档地图 |
| [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) / [English](docs/DEPLOYMENT_GUIDE.en.md) | 部署、更新和排障 |
| [docs/STABILITY_AUDIT.md](docs/STABILITY_AUDIT.md) / [English](docs/STABILITY_AUDIT.en.md) | 稳定性风险和后续演进建议 |
| [docs/项目说明与代码索引.md](docs/%E9%A1%B9%E7%9B%AE%E8%AF%B4%E6%98%8E%E4%B8%8E%E4%BB%A3%E7%A0%81%E7%B4%A2%E5%BC%95.md) / [English](docs/PROJECT_GUIDE.en.md) | 项目逻辑、核心流程、代码索引和展示讲解口径 |
