<a id="readme-zh"></a>

# 视频会议系统

[中文](#readme-zh) | [English](#readme-en)

基于 `Flask + Flask-SocketIO + LiveKit` 的在线视频会议系统。当前版本使用 LiveKit SFU 作为音视频主链路，Socket.IO 负责房间成员、聊天、主持人操作和界面状态同步。

## 你可以用它做什么

- 注册、登录、退出，以及基础会话控制
- 创建会议、加入会议、查看历史会议
- 摄像头、麦克风、扬声器和屏幕共享
- 房间聊天、@ 提及、图片/视频/文档附件
- 附件查看权限与下载权限控制
- 背景虚化和浏览器端录屏
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

## 中英文和双端适配状态

当前界面按中英文双语维护：

- `translations.py` 同时包含 `zh` 和 `en` 两套翻译表，当前两边 key 数一致。
- 模板优先使用 `t('key')`，少量运行时提示使用 `lang == 'zh'` 的中英文分支。
- `python check_i18n.py` 当前可通过，用来检查模板里遗漏的硬编码中文。
- `/set-language/<lang>`、页面右上角语言切换、`/account` 默认语言偏好和会话语言会共同决定页面语言。

移动端和桌面端都已有独立适配，不是单纯缩放桌面页面：

- 首页在移动端显示“扫码入会”，通过浏览器 `BarcodeDetector` 和后置摄像头扫描会议二维码；桌面端保留会议号、密码、复制邀请链接等主流程。
- 房间页使用 `viewport-fit=cover`，桌面端是会议网格 + 右侧聊天栏；移动端聊天会重排为可拖动/可滚动的底部区域，避免遮挡视频和发送按钮。
- `static/room_livekit.js` 根据 `matchMedia('(max-width: 768px)')` 和移动设备 UA 选择更保守的摄像头、麦克风和屏幕共享发布参数，降低手机发热、耗电和弱网压力。
- `templates/_room_scripts.html` 对移动端全屏、iOS Safari 原生视频全屏、横屏锁定、触摸播放恢复和共享屏幕观看做了单独处理。
- `static/style.css` 和 `static/room.css` 保留桌面分页网格、桌面聊天栏、移动端聊天底部面板、移动端屏幕共享全屏等规则。

提交前建议同时验证：中文和英文页面、桌面浏览器和手机浏览器、同一账号双设备、手机扫码入会、移动端观看远端屏幕共享。

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
| FFmpeg | 录屏导出 MP4 时使用；不装也能启动项目 | https://ffmpeg.org/download.html |
| VS Code | 编辑代码，可选 | https://code.visualstudio.com/ |

如果 Windows 的 `winget` 可用，也可以在 PowerShell 里安装：

```powershell
winget install -e --id Python.Python.3.12
winget install -e --id Git.Git
winget install -e --id Gyan.FFmpeg
winget install -e --id Microsoft.VisualStudioCode
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

项目仓库地址：

| 平台 | 地址 |
| --- | --- |
| GitHub | https://github.com/jerryhuang392diandi/video-meeting |
| Gitee | https://gitee.com/jerryhqx/video-meeting |

下面示例默认使用 Gitee。用户也可以按网络环境或代码托管平台选择 GitHub。

Windows PowerShell 示例：

```powershell
mkdir D:\projects
cd D:\projects
git clone https://gitee.com/jerryhqx/video-meeting.git
# 按需选择 GitHub：
# git clone https://github.com/jerryhuang392diandi/video-meeting.git
cd video-meeting
```

Windows CMD 示例：

```bat
mkdir D:\projects
cd /d D:\projects
git clone https://gitee.com/jerryhqx/video-meeting.git
REM 按需选择 GitHub：
REM git clone https://github.com/jerryhuang392diandi/video-meeting.git
cd video-meeting
```

macOS / Linux 示例：

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://gitee.com/jerryhqx/video-meeting.git
# 按需选择 GitHub：
# git clone https://github.com/jerryhuang392diandi/video-meeting.git
cd video-meeting
```

如果你没有 Git 仓库，也可以把压缩包解压到一个固定目录，然后在终端 `cd` 进入项目目录。

命令解释：

| 命令 | 含义 | 可自定义项 |
| --- | --- | --- |
| `mkdir D:\projects` / `mkdir -p ~/projects` | 创建一个专门放代码的父目录 | 可以换成你自己的路径 |
| `cd D:\projects` / `cd ~/projects` | 进入父目录，后续 clone 会把项目放在这里 | Windows CMD 跨盘符要用 `cd /d` |
| `git clone https://gitee.com/jerryhqx/video-meeting.git` | 从 Gitee 下载代码；默认会创建 `video-meeting` 文件夹 | 也可按需换成 GitHub：`https://github.com/jerryhuang392diandi/video-meeting.git` |
| `cd video-meeting` | 进入刚下载的项目目录 | 如果 clone 时指定了目录名，例如 `git clone ... my-folder`，这里也要改成 `cd my-folder` |

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

命令解释：

| 命令 | 含义 | 可自定义项 |
| --- | --- | --- |
| `python -m venv venv` / `python3 -m venv venv` | 在项目目录创建独立 Python 环境，避免污染系统 Python | `venv` 名字可以换，但后续激活命令要同步 |
| `venv\Scripts\activate` / `source venv/bin/activate` | 激活虚拟环境；激活后安装的包只进当前项目 | Windows CMD 使用 `activate.bat` |
| `python -m pip install --upgrade pip` | 升级包管理器 pip，减少安装依赖时的兼容问题 | 如果网络慢可以先跳过，但推荐执行 |
| `pip install -r requirements.txt` | 按项目清单安装 Flask、Socket.IO、SQLAlchemy、LiveKit API、Pillow、psutil 等依赖 | 如果很慢，可以临时加镜像参数，例如 `-i https://pypi.tuna.tsinghua.edu.cn/simple` |

### 4. 配置本地 `.env`

如果只想看登录、注册、首页、帮助页，可以先不写 LiveKit 配置；但进入会议房间会返回 `503`，这是正常的保护逻辑。

如果要本地测试会议音视频，建议先用 LiveKit Cloud。最短步骤是：

1. 打开 [LiveKit Cloud](https://cloud.livekit.io/) 并创建一个 project。
2. 在项目设置里复制 server URL、API key、API secret。
3. 在项目根目录新建 `.env`，把三项 LiveKit 配置和本地基础配置写进去。

更细的 LiveKit Cloud 操作、为什么 Nginx 不代理 LiveKit、自建 LiveKit 的域名/端口/Docker Compose 示例，已经写在 [docs/DEPLOYMENT_GUIDE.md 的 LiveKit 配置选择](docs/DEPLOYMENT_GUIDE.md#7-livekit-配置选择) 里。生产环境变量的完整说明见 [docs/DEPLOYMENT_GUIDE.md 的配置环境变量](docs/DEPLOYMENT_GUIDE.md#5-配置环境变量)。

```env
SECRET_KEY=local-dev-secret-change-me
PUBLIC_SCHEME=http
PUBLIC_HOST=127.0.0.1:5000

LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=replace-with-livekit-api-key
LIVEKIT_API_SECRET=replace-with-livekit-api-secret

ADMIN_USERNAME=localadmin
ADMIN_PASSWORD=root1234
PUBLIC_REGISTRATION_ENABLED=1
STRICT_SECURITY_CHECKS=0
TURNSTILE_SITE_KEY=
TURNSTILE_SECRET_KEY=
```

`.env` 不要提交到 Git。

配置项说明：

| 配置项 | 用途 | 本地建议 |
| --- | --- | --- |
| `SECRET_KEY` | Flask 会话和安全签名密钥 | 本地可以用示例值，部署时必须换成长随机字符串 |
| `PUBLIC_SCHEME` | 浏览器访问应用时使用的协议 | 本地通常是 `http`，线上 HTTPS 是 `https` |
| `PUBLIC_HOST` | 浏览器访问应用时使用的主机和端口 | 本地默认 `127.0.0.1:5000` |
| `LIVEKIT_URL` | 浏览器直接连接的 LiveKit 服务地址 | LiveKit Cloud 项目页提供，通常是 `wss://...livekit.cloud` |
| `LIVEKIT_API_KEY` | 后端签发 LiveKit token 使用的 API key | 从 LiveKit Cloud 项目设置复制 |
| `LIVEKIT_API_SECRET` | 后端签发 LiveKit token 使用的 API secret | 从 LiveKit Cloud 项目设置复制，不要公开 |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | 管理后台初始登录账号 | 本地可用简单值，但不要和 Linux 的 `root` / `ubuntu` 登录用户混为一谈；线上必须改强密码 |
| `PUBLIC_REGISTRATION_ENABLED` | 是否允许任何人直接注册 | 本地演示可开，公网建议设为 `0` |
| `STRICT_SECURITY_CHECKS` | 是否在启动时拒绝弱 `SECRET_KEY` / `ADMIN_*` 配置 | 公网建议设为 `1` |
| `TURNSTILE_SITE_KEY` / `TURNSTILE_SECRET_KEY` | Cloudflare Turnstile 站点 key 和服务端 secret | 大陆用户需先实测可用性 |

LiveKit 的三项配置必须来自同一个 LiveKit 项目。Flask 只负责校验用户并签发 token，浏览器拿到 token 后会直接连 `LIVEKIT_URL`；所以这个地址必须能被你的浏览器访问。

这里的 `ADMIN_USERNAME` 是网站管理员登录名，不是你的 Linux/macOS/Windows 系统用户名，也不是服务器 SSH 登录用户。线上如果是 `systemd` 部署，应用配置写 `.env`，进程运行用户写在 service 文件的 `User=`。

如果房间返回 `503`、修改 `.env` 后不生效、或进入房间但看不到对方，先看 [docs/DEPLOYMENT_GUIDE.md 的常见问题](docs/DEPLOYMENT_GUIDE.md#16-常见问题)。本地运行通常重启 `python app.py` 即可重新读取 `.env`；线上 systemd 服务还需要重启服务。

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
| `pip install` 很慢 | 可以换国内 PyPI 镜像，或先确认网络；服务器安装说明见 [部署指南准备项目目录](docs/DEPLOYMENT_GUIDE.md#4-准备项目目录) |
| `/room/<会议号>` 返回 `503` | `.env` 里缺少 `LIVEKIT_URL`、`LIVEKIT_API_KEY`、`LIVEKIT_API_SECRET`；排查步骤见 [部署指南常见问题](docs/DEPLOYMENT_GUIDE.md#16-常见问题) |
| 录屏转 MP4 失败 | 是否安装 FFmpeg，并且 `ffmpeg -version` 能输出版本 |
| 背景虚化启动失败 | 先确认摄像头已开启；如果刚关闭/重开过摄像头，等待本地画面恢复后再启用；该功能依赖浏览器加载 MediaPipe 模型 |

## 云服务器部署概览

生产或课程展示部署建议采用：

```text
浏览器
  -> 域名 / Cloudflare DNS
  -> Nginx 反向代理和 HTTPS
  -> Gunicorn threaded worker 运行 Flask-SocketIO
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
| GitHub 项目仓库 | 代码托管与版本管理 | https://github.com/jerryhuang392diandi/video-meeting |
| Gitee 项目仓库 | 国内访问较快的项目镜像 | https://gitee.com/jerryhqx/video-meeting |

完整 Linux 云服务器操作步骤见 [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)。这份部署手册已经按零基础顺序整理了购买服务器、国内备案、Windows/macOS/FinalShell 登录服务器、项目配置、systemd、LiveKit、Nginx 和 HTTPS，建议第一次部署时照着它从前往后做，不要直接跳到配置片段。

里面包括：

- 购买服务器后的备案判断、SSH 登录、密码输入说明、安全组、防火墙、系统用户和目录准备。
- Cloudflare 或普通 DNS 解析配置。
- Python 虚拟环境、依赖安装和 EOF 方式写 `.env` 配置。
- Nginx 为什么需要反向代理、WebSocket 头、上传体积限制，以及可直接使用的 HTTPS 配置。
- EOF 方式写 systemd 服务文件、开机自启、日志查看和线上更新。
- LiveKit Cloud 的最短接入步骤，以及自建 LiveKit 的域名、证书、Docker Compose、媒体端口、TURN/ICE 检查清单。
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
| `PUBLIC_REGISTRATION_ENABLED` | 是否允许公开注册，默认开启 |
| `STRICT_SECURITY_CHECKS` | 严格安全启动检查，开启后要求显式强 `SECRET_KEY`、强 `ADMIN_PASSWORD`，且不允许 `ADMIN_USERNAME=root` |
| `TURNSTILE_SITE_KEY` | Cloudflare Turnstile site key，留空则关闭 |
| `TURNSTILE_SECRET_KEY` | Cloudflare Turnstile secret key，留空则关闭 |
| `DEBUG_ROOM=1` | 输出房间相关调试日志 |

可选项包括 `TURN_PUBLIC_HOST`、`TURN_URLS`、`TURN_USERNAME`、`TURN_PASSWORD`、`SESSION_COOKIE_SAMESITE`、`SESSION_COOKIE_SECURE`、`REMEMBER_COOKIE_SAMESITE`、`REMEMBER_COOKIE_SECURE`、`LOGIN_RATE_LIMIT_PER_IP`、`LOGIN_RATE_LIMIT_PER_USER`、`PUBLIC_REGISTRATION_ENABLED`、`STRICT_SECURITY_CHECKS`、`TURNSTILE_SITE_KEY`、`TURNSTILE_SECRET_KEY`。

## 运行限制

- 当前在线态主要保存在单进程内存中，默认应按单实例部署理解。
- LiveKit 是外部媒体基础设施，必须正确配置后房间媒体才可用。
- 录屏转 MP4 依赖服务端 `ffmpeg`；未安装时只能保留浏览器原始录制结果。
- 背景虚化依赖本地摄像头 live track、浏览器端 MediaPipe 模型和 canvas 处理；屏幕共享和录屏也比较消耗资源，弱设备上应优先保证会议可用性。
- 当前主要重构方向见 [docs/REFACTOR_AUDIT.md](docs/REFACTOR_AUDIT.md)：优先保持房间状态一致性，再逐步拆分房间脚本和 `app.py`。

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
| Nginx HTTPS 配置 | [Configuring HTTPS servers](https://nginx.org/en/docs/http/configuring_https_servers.html) |
| Certbot / Let's Encrypt | [Certbot install guide](https://eff-certbot.readthedocs.io/en/stable/install.html) |
| Let's Encrypt | [Let's Encrypt](https://letsencrypt.org/) |
| Cloudflare 入口 | [Cloudflare](https://www.cloudflare.com/) / [Dashboard](https://dash.cloudflare.com/) |
| Cloudflare DNS 记录 | [Create DNS records](https://developers.cloudflare.com/dns/manage-dns-records/how-to/create-dns-records/) |
| Cloudflare SSL 模式 | [Cloudflare Full (strict)](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/) |
| 域名注册商示例 | [阿里云域名](https://wanwang.aliyun.com/) / [腾讯云 DNSPod](https://dnspod.cloud.tencent.com/) / [Cloudflare Registrar](https://www.cloudflare.com/products/registrar/) / [Namecheap](https://www.namecheap.com/) |
| systemd 环境变量 | [systemd.exec EnvironmentFile](https://www.freedesktop.org/software/systemd/man/systemd.exec.html) |
| LiveKit | [LiveKit Docs](https://docs.livekit.io/) / [LiveKit Cloud](https://cloud.livekit.io/) |
| SSH 登录 | [Microsoft OpenSSH](https://learn.microsoft.com/windows-server/administration/openssh/openssh_install_firstuse) / [Ubuntu OpenSSH](https://documentation.ubuntu.com/server/how-to/security/openssh-server/) |
| 中国大陆备案 | [工信部备案系统](https://beian.miit.gov.cn/) / [阿里云备案](https://help.aliyun.com/zh/icp-filing/) / [腾讯云备案](https://cloud.tencent.com/document/product/243) |
| GitHub / Gitee | [GitHub](https://github.com/) / [Gitee](https://gitee.com/) |
| 本地工具 | [Python](https://www.python.org/downloads/) / [Git](https://git-scm.com/downloads) / [FFmpeg](https://ffmpeg.org/download.html) / [VS Code](https://code.visualstudio.com/) / [Homebrew](https://brew.sh/) / [winget](https://learn.microsoft.com/windows/package-manager/winget/) |

## 文档

| 文档 | 用途 |
| --- | --- |
| [docs/README.md](docs/README.md) / [English](docs/README.md#documentation-map) | 文档地图 |
| [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) / [English](docs/DEPLOYMENT_GUIDE.md#deployment-and-update-guide) | 部署、更新和排障 |
| [docs/STABILITY_AUDIT.md](docs/STABILITY_AUDIT.md) / [English](docs/STABILITY_AUDIT.md#stability-audit) | 稳定性风险和后续演进建议 |
| [docs/REFACTOR_AUDIT.md](docs/REFACTOR_AUDIT.md) / [English](docs/REFACTOR_AUDIT.md#refactor-audit) | 当前重构巡检结论、优先级和推荐拆分顺序 |
| [docs/项目说明与代码索引.md](docs/%E9%A1%B9%E7%9B%AE%E8%AF%B4%E6%98%8E%E4%B8%8E%E4%BB%A3%E7%A0%81%E7%B4%A2%E5%BC%95.md) / [English](docs/%E9%A1%B9%E7%9B%AE%E8%AF%B4%E6%98%8E%E4%B8%8E%E4%BB%A3%E7%A0%81%E7%B4%A2%E5%BC%95.md#project-guide-and-code-index) | 项目逻辑、核心流程、代码索引和展示讲解口径 |


---

<a id="readme-en"></a>

# Video Meeting System

[中文](#readme-zh) | [English](#readme-en)

An online meeting system built with `Flask + Flask-SocketIO + LiveKit`. The current version uses LiveKit SFU as the primary media path, while Socket.IO handles room membership, chat, host operations, and UI-level room state.

## What It Does

- User registration, login, logout, and basic session control
- Meeting creation, meeting join, and meeting history
- Camera, microphone, speaker, and screen sharing controls
- Room chat, @ mentions, image/video/document attachments
- Attachment view and download permission control
- Virtual background and browser-side screen recording
- Host controls for ending meetings, clearing chat, and managing room behavior
- Admin dashboard for users, meetings, password reset requests, and system stats
- Chinese/English UI and a lightweight i18n checker
- Bilingual Quickstart page for international guests
- Full User Guide covering account preferences, join-time devices, chat attachments, screen sharing, and host actions
- RTC/LiveKit diagnostics inside the meeting room

## User-Facing Pages

| Path | Page | Audience |
| --- | --- | --- |
| `/` | Home / create meeting / join meeting | Signed-in users |
| `/login` | Login | Existing users |
| `/register` | Registration | First-time users |
| `/forgot-password` | Password reset request | Users who forgot passwords |
| `/quickstart` | Quickstart | First-time meeting users |
| `/help` | User Guide | Users who need account, device, chat, screen share, or host guidance |
| `/support` | Support | Login, device permission, meeting entry, or upload issues |
| `/account` | Account and preferences | Name, language, timezone, attachment permission, and default device settings |
| `/history` | Meeting history | Meetings created or joined by the current user |
| `/room/<room_id>` | Meeting room | Actual in-meeting page, usually opened from an invite link |
| `/admin` | Admin dashboard | Root/admin users managing users, meetings, reset requests, and stats |

Time display rules:

- `/history` uses the current user's timezone preference from `/account`.
- `/admin` uses the current admin account's timezone preference for registration times and meeting records.

## Architecture

| Layer | Technology | Responsibility |
| --- | --- | --- |
| Web backend | Flask | Routes, auth, database models, admin dashboard, uploads, LiveKit tokens |
| Real-time state | Flask-SocketIO | Join/leave, chat broadcast, host actions, room UI state |
| Media transport | LiveKit SFU | Camera, microphone, screen share, remote track subscription |
| Storage | SQLite by default, override with `DATABASE_URL` | Users, meetings, history, password reset requests |
| Frontend | Jinja2 + vanilla JavaScript | Page rendering, room interactions, media controls, diagnostics |

## i18n and Device Adaptation Status

The UI is maintained in both Chinese and English:

- `translations.py` contains both `zh` and `en` translation tables, and the two key sets currently match.
- Templates prefer `t('key')`; a small number of runtime prompts use explicit `lang == 'zh'` Chinese/English branches.
- `python check_i18n.py` currently passes and checks templates for missed hardcoded Chinese text.
- `/set-language/<lang>`, the page language switch, `/account` language preference, and session language together control the rendered language.

Mobile and desktop have separate adaptations instead of only scaling the desktop page:

- The home page shows mobile QR join on phones through browser `BarcodeDetector` and the rear camera; desktop keeps room ID, password, and invite-link workflows.
- The room page uses `viewport-fit=cover`. Desktop uses the meeting grid plus a right chat column; mobile reflows chat into a draggable/scrollable bottom area so it does not cover video or the send button.
- `static/room_livekit.js` uses `matchMedia('(max-width: 768px)')` and mobile user-agent detection to choose more conservative camera, microphone, and screen-share publish settings for heat, battery, and weak networks.
- `templates/_room_scripts.html` has separate handling for mobile fullscreen, iOS Safari native video fullscreen, landscape orientation lock, touch playback recovery, and screen-share viewing.
- `static/style.css` and `static/room.css` keep rules for desktop paged grids, desktop chat column, mobile chat bottom panel, and mobile screen-share fullscreen.

Before submitting, verify Chinese and English pages, desktop and phone browsers, same-account two-device join, mobile QR join, and mobile viewing of remote screen share.

## Project Structure

```text
.
├── app.py                    # Flask routes, Socket.IO events, models, runtime config
├── templates/                # Jinja2 page templates
├── static/                   # Room JS, styles, frontend assets
├── translations.py           # Chinese/English translation table
├── check_i18n.py             # Hardcoded Chinese checker for templates
├── requirements.txt          # Python dependencies
├── docs/                     # Deployment, stability, and presentation docs
└── instance/                 # Runtime directory, generated and ignored
```

Room frontend files:

- `static/room_livekit.js`: LiveKit connection, local publishing, remote track handling
- `static/room_ui.js`: participant cards, layout, focus state, screen share view
- `static/room_chat.js`: chat messages and attachment rendering
- `static/room_diagnostics.js`: RTC/LiveKit diagnostic summary
- `static/room_utils.js`: shared helpers

## Quick Start

These steps are written for first-time local setup. They are for editing code and testing before a course demo; public access still needs cloud deployment.

Open a command line first:

| System | Recommended terminal | Notes |
| --- | --- | --- |
| Windows | PowerShell or CMD | Search `PowerShell` or `cmd` in the Start menu; PowerShell is used first below, with CMD differences noted |
| macOS | Terminal | The default shell is usually `zsh`, and the bash-style commands below work |
| Linux | Terminal | Most distributions include `bash`; minimal systems may need `bash`, `python3`, and `git` installed first |

### 1. Install Basic Tools

Windows:

| Tool | Purpose | Source |
| --- | --- | --- |
| Python 3.10+ | Runs the Flask app | https://www.python.org/downloads/ |
| Git | Downloads code and manages versions | https://git-scm.com/downloads |
| FFmpeg | MP4 recording export; optional for basic startup | https://ffmpeg.org/download.html or `winget install Gyan.FFmpeg` |
| VS Code | Code editor, optional | https://code.visualstudio.com/ |

If `winget` is available on Windows, you can install from PowerShell:

```powershell
winget install -e --id Python.Python.3.12
winget install -e --id Git.Git
winget install -e --id Gyan.FFmpeg
winget install -e --id Microsoft.VisualStudioCode
```

macOS:

| Tool | Purpose | Source |
| --- | --- | --- |
| Homebrew | Installs command-line tools | https://brew.sh/ |
| Python 3.10+ | Runs the Flask app | `brew install python` |
| Git | Downloads code and manages versions | `brew install git` |
| FFmpeg | MP4 recording export; optional for basic startup | `brew install ffmpeg` |
| VS Code | Code editor, optional | https://code.visualstudio.com/ |

Linux Ubuntu / Debian:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git ffmpeg bash
```

Check versions:

Windows PowerShell / CMD:

```powershell
python --version
git --version
ffmpeg -version
```

macOS / Linux:

```bash
python3 --version
git --version
ffmpeg -version
```

### 2. Create a Project Folder

Project repositories:

| Platform | URL |
| --- | --- |
| GitHub | https://github.com/jerryhuang392diandi/video-meeting |
| Gitee | https://gitee.com/jerryhqx/video-meeting |

The examples below use Gitee by default. Users can choose GitHub instead based on network access or hosting preference.

Windows PowerShell:

```powershell
mkdir D:\projects
cd D:\projects
git clone https://gitee.com/jerryhqx/video-meeting.git
# Choose GitHub if needed:
# git clone https://github.com/jerryhuang392diandi/video-meeting.git
cd video-meeting
```

Windows CMD:

```bat
mkdir D:\projects
cd /d D:\projects
git clone https://gitee.com/jerryhqx/video-meeting.git
REM Choose GitHub if needed:
REM git clone https://github.com/jerryhuang392diandi/video-meeting.git
cd video-meeting
```

macOS / Linux:

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://gitee.com/jerryhqx/video-meeting.git
# Choose GitHub if needed:
# git clone https://github.com/jerryhuang392diandi/video-meeting.git
cd video-meeting
```

Command explanation:

| Command | Meaning | Customizable |
| --- | --- | --- |
| `mkdir D:\projects` / `mkdir -p ~/projects` | Creates a parent folder for source code | Replace it with your preferred path |
| `cd D:\projects` / `cd ~/projects` | Enters the parent folder so the clone lands there | Windows CMD needs `cd /d` when switching drives |
| `git clone https://gitee.com/jerryhqx/video-meeting.git` | Downloads the Gitee repository and creates a `video-meeting` folder | You can use GitHub instead: `https://github.com/jerryhuang392diandi/video-meeting.git` |
| `cd video-meeting` | Enters the cloned project folder | If you clone into another folder name, use that name here |

### 3. Create a Virtual Environment

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

Command explanation:

| Command | Meaning | Customizable |
| --- | --- | --- |
| `python -m venv venv` / `python3 -m venv venv` | Creates an isolated Python environment inside the project | The folder name can change, but activation commands must match |
| `venv\Scripts\activate` / `source venv/bin/activate` | Activates the virtual environment so packages install into this project | Windows CMD uses `activate.bat` |
| `python -m pip install --upgrade pip` | Upgrades pip to reduce dependency installation issues | Optional, but recommended |
| `pip install -r requirements.txt` | Installs Flask, Socket.IO, SQLAlchemy, LiveKit API, Pillow, psutil, and other project dependencies | If it is slow, use a PyPI mirror such as `-i https://pypi.tuna.tsinghua.edu.cn/simple` |

### 4. Configure Local `.env`

Without LiveKit settings, login and normal pages can work, but meeting rooms return `503`. To test audio/video locally, use LiveKit Cloud first. The shortest path is:

1. Open [LiveKit Cloud](https://cloud.livekit.io/) and create a project.
2. Copy the server URL, API key, and API secret from that project.
3. Create `.env` in the project root and paste the LiveKit values plus the local app settings.

The detailed LiveKit Cloud flow, the reason Nginx does not proxy LiveKit, and the self-hosted LiveKit port checklist are covered in [LiveKit Options](docs/DEPLOYMENT_GUIDE.md#7-livekit-options). The full production environment variable table is in [Configure Environment Variables](docs/DEPLOYMENT_GUIDE.md#5-configure-environment-variables).

```env
SECRET_KEY=local-dev-secret-change-me
PUBLIC_SCHEME=http
PUBLIC_HOST=127.0.0.1:5000

LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=replace-with-livekit-api-key
LIVEKIT_API_SECRET=replace-with-livekit-api-secret

ADMIN_USERNAME=localadmin
ADMIN_PASSWORD=root1234
PUBLIC_REGISTRATION_ENABLED=1
STRICT_SECURITY_CHECKS=0
TURNSTILE_SITE_KEY=
TURNSTILE_SECRET_KEY=
```

Do not commit `.env`.

Configuration explanation:

| Variable | Purpose | Local recommendation |
| --- | --- | --- |
| `SECRET_KEY` | Flask session and signing secret | The sample is fine locally; use a long random value in production |
| `PUBLIC_SCHEME` | Browser-facing scheme for the app | Usually `http` locally and `https` in production |
| `PUBLIC_HOST` | Browser-facing host and port | Default local value is `127.0.0.1:5000` |
| `LIVEKIT_URL` | Browser-reachable LiveKit service URL | Copy it from LiveKit Cloud; usually `wss://...livekit.cloud` |
| `LIVEKIT_API_KEY` | API key used by the backend to sign LiveKit tokens | Copy from the same LiveKit project |
| `LIVEKIT_API_SECRET` | API secret used by the backend to sign LiveKit tokens | Copy from the same LiveKit project and keep private |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Initial admin login | Simple values are fine locally, but this is not the Linux SSH user such as `root` or `ubuntu`; use a strong password in production |
| `PUBLIC_REGISTRATION_ENABLED` | Whether anyone can self-register | Fine for local demos; set `0` on public deployments |
| `STRICT_SECURITY_CHECKS` | Refuse weak `SECRET_KEY` / `ADMIN_*` settings at startup | Set `1` on public deployments |
| `TURNSTILE_SITE_KEY` / `TURNSTILE_SECRET_KEY` | Cloudflare Turnstile site key and server secret | Test availability first for mainland users |

The three LiveKit values must come from the same LiveKit project. Flask only checks meeting permission and issues a token; the browser connects directly to `LIVEKIT_URL`, so that URL must be reachable from your browser.

`ADMIN_USERNAME` is the website admin login name, not your operating system account and not the SSH user on the server. In production with `systemd`, app settings belong in `.env`, while the process user belongs in the service file `User=`.

If rooms return `503`, `.env` changes do not apply, or users can join but cannot see each other, start with [Common Issues](docs/DEPLOYMENT_GUIDE.md#16-common-issues). Local development usually only needs restarting `python app.py`; production systemd services must be restarted after `.env` changes.

### 5. Start the App

After activating the virtual environment:

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

By default the app uses `instance/app.db` as the SQLite database. On first run, if no admin password is configured, the app generates one and writes it to `instance/admin_password.txt`.

Meeting history timestamps use the current user's region/timezone preference from `/account`. The admin dashboard uses the current admin account's timezone preference for user registration times and meeting records.

### 6. Local Common Issues

| Symptom | Check first |
| --- | --- |
| `python` command is missing | Confirm Python is installed; on Windows, confirm Add Python to PATH was selected |
| `git` command is missing | Confirm Git is installed, then reopen the terminal |
| `pip install` is slow | Try a PyPI mirror or check the network; server setup details are in [Prepare Project Directory](docs/DEPLOYMENT_GUIDE.md#4-prepare-the-project-directory) |
| `/room/<room_id>` returns `503` | `.env` is missing `LIVEKIT_URL`, `LIVEKIT_API_KEY`, or `LIVEKIT_API_SECRET`; see [Common Issues](docs/DEPLOYMENT_GUIDE.md#16-common-issues) |
| MP4 recording remux fails | Confirm FFmpeg is installed and `ffmpeg -version` prints a version |
| Virtual background fails to start | Turn the camera on first; after toggling the camera, wait for local video to recover before enabling it; this feature also depends on the browser loading the MediaPipe model |

## Cloud Server Deployment Overview

For production or course demonstrations, use this deployment shape:

```text
Browser
  -> Domain / Cloudflare DNS
  -> Nginx reverse proxy and HTTPS
  -> Gunicorn threaded worker running Flask-SocketIO
  -> Flask application
  -> LiveKit Cloud or self-hosted LiveKit for media transport
```

Minimum server recommendation:

- Ubuntu 22.04 / 24.04 LTS.
- Start with 2 vCPU and 2 GB RAM; use 4 GB RAM for larger demos, recording remux, or heavier admin usage.
- Open ports `80` and `443`; configure SSH in the cloud provider security group.
- Prepare a domain such as `meeting.example.com`.
- Prefer LiveKit Cloud for the media service. If self-hosting LiveKit, also prepare LiveKit service deployment, TLS, UDP/TCP reachability, and TURN/ICE settings.

Common cloud server entry points:

| Provider | Link |
| --- | --- |
| Alibaba Cloud ECS | https://www.aliyun.com/product/ecs |
| Tencent Cloud CVM | https://cloud.tencent.com/product/cvm |
| Huawei Cloud ECS | https://www.huaweicloud.com/product/ecs.html |
| AWS EC2 | https://aws.amazon.com/ec2/ |
| Azure Virtual Machines | https://azure.microsoft.com/products/virtual-machines/ |
| DigitalOcean Droplets | https://www.digitalocean.com/products/droplets |
| Vultr Cloud Compute | https://www.vultr.com/products/cloud-compute/ |

Common companion platform entry points:

| Platform | Purpose | Link |
| --- | --- | --- |
| Cloudflare | DNS hosting, optional CDN/proxy, SSL/TLS settings | https://www.cloudflare.com/ |
| Cloudflare Dashboard | Add DNS records, switch DNS only / Proxied | https://dash.cloudflare.com/ |
| LiveKit Cloud | Hosted LiveKit media service; copy `LIVEKIT_URL`, API key, and API secret | https://cloud.livekit.io/ |
| GitHub | Code hosting and version control | https://github.com/ |
| Gitee | Optional code hosting platform in China | https://gitee.com/ |

See [docs/DEPLOYMENT_GUIDE.md#deployment-and-update-guide](docs/DEPLOYMENT_GUIDE.md#deployment-and-update-guide) for the full Linux cloud server procedure. It now follows the first-deployment order: server purchase, ICP filing notes for mainland China servers, Windows/macOS/FinalShell SSH login, project config, systemd, LiveKit, Nginx, and HTTPS.

It includes:

- ICP filing checks, SSH login, password input behavior, security groups, firewall, server users, and project directories after buying a server.
- Cloudflare or plain DNS records.
- Python virtual environment, dependency installation, and EOF-based `.env` configuration.
- Nginx reverse proxy for WebSocket headers, upload size, and a direct HTTPS config.
- EOF-based systemd service files, auto-start, log inspection, and production updates.
- LiveKit Cloud configuration and self-hosted LiveKit domains, Docker Compose, TLS, ports, TURN/ICE, and API keys.
- Troubleshooting for missing LiveKit config, WebSocket failures, upload issues, and MP4 recording remux.

## Key Configuration

LiveKit configuration is required. If it is missing, room media is unavailable and `/room/<room_id>` returns `503`.

| Environment variable | Description |
| --- | --- |
| `SECRET_KEY` | Flask session secret |
| `LIVEKIT_URL` | LiveKit server URL |
| `LIVEKIT_API_KEY` | LiveKit API key |
| `LIVEKIT_API_SECRET` | LiveKit API secret |
| `DATABASE_URL` | Database URL, defaults to `instance/app.db` |
| `PUBLIC_HOST` | Public hostname |
| `PUBLIC_SCHEME` | Public scheme, usually `http` or `https` |
| `ADMIN_USERNAME` | Initial admin username, defaults to `root` |
| `ADMIN_PASSWORD` | Initial admin password; generated if not set |
| `PUBLIC_REGISTRATION_ENABLED` | Whether public self-registration is enabled, defaults to on |
| `STRICT_SECURITY_CHECKS` | Strict startup guard; requires explicit strong `SECRET_KEY`, strong `ADMIN_PASSWORD`, and non-`root` `ADMIN_USERNAME` |
| `TURNSTILE_SITE_KEY` | Cloudflare Turnstile site key; leave empty to disable |
| `TURNSTILE_SECRET_KEY` | Cloudflare Turnstile secret key; leave empty to disable |
| `DEBUG_ROOM=1` | Enables room debug logging |

Optional settings include `TURN_PUBLIC_HOST`, `TURN_URLS`, `TURN_USERNAME`, `TURN_PASSWORD`, `SESSION_COOKIE_SAMESITE`, `SESSION_COOKIE_SECURE`, `REMEMBER_COOKIE_SAMESITE`, `REMEMBER_COOKIE_SECURE`, `LOGIN_RATE_LIMIT_PER_IP`, `LOGIN_RATE_LIMIT_PER_USER`, `PUBLIC_REGISTRATION_ENABLED`, `STRICT_SECURITY_CHECKS`, `TURNSTILE_SITE_KEY`, and `TURNSTILE_SECRET_KEY`.

## Runtime Limits

- Online room state is primarily kept in single-process memory, so treat the default deployment as single-instance.
- LiveKit is external media infrastructure and must be configured correctly.
- MP4 recording export depends on server-side `ffmpeg`; without it, only the browser's raw recording output is kept.
- Virtual background depends on a live local camera track, the browser-side MediaPipe model, and canvas processing. Screen sharing and recording are also resource-heavy; on weak devices, meeting stability should come first.
- Current refactor direction is tracked in [docs/REFACTOR_AUDIT.md#refactor-audit](docs/REFACTOR_AUDIT.md#refactor-audit): keep room state consistency first, then split the room script and `app.py` gradually.

## Pre-Submission Checks

```bash
python check_i18n.py
```

Recommended manual smoke tests:

- Login, registration, room creation, room join, and room leave
- Desktop and mobile two-client join flow; the first join should show remote media without refresh
- Camera, microphone, and screen sharing start/stop
- Chat, attachment upload, attachment view/download permissions
- Chinese/English UI switching
- Common admin dashboard actions

## References

Deployment and runtime configuration mainly follow these official documents. See the "References" section in [docs/DEPLOYMENT_GUIDE.md#deployment-and-update-guide](docs/DEPLOYMENT_GUIDE.md#deployment-and-update-guide) for the detailed deployment context.

| Topic | Official documentation |
| --- | --- |
| Flask-SocketIO deployment | [Flask-SocketIO Deployment](https://flask-socketio.readthedocs.io/en/latest/deployment.html) |
| Gunicorn settings | [Gunicorn Settings](https://docs.gunicorn.org/en/stable/settings.html) |
| Nginx WebSocket proxying | [Nginx WebSocket proxying](https://nginx.org/en/docs/http/websocket.html) |
| Nginx HTTPS configuration | [Configuring HTTPS servers](https://nginx.org/en/docs/http/configuring_https_servers.html) |
| Certbot / Let's Encrypt | [Certbot install guide](https://eff-certbot.readthedocs.io/en/stable/install.html) |
| Let's Encrypt | [Let's Encrypt](https://letsencrypt.org/) |
| Cloudflare entry | [Cloudflare](https://www.cloudflare.com/) / [Dashboard](https://dash.cloudflare.com/) |
| Cloudflare DNS records | [Create DNS records](https://developers.cloudflare.com/dns/manage-dns-records/how-to/create-dns-records/) |
| Cloudflare SSL mode | [Cloudflare Full (strict)](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/) |
| Domain registrar examples | [Alibaba Cloud Domains](https://wanwang.aliyun.com/) / [Tencent Cloud DNSPod](https://dnspod.cloud.tencent.com/) / [Cloudflare Registrar](https://www.cloudflare.com/products/registrar/) / [Namecheap](https://www.namecheap.com/) |
| systemd environment variables | [systemd.exec EnvironmentFile](https://www.freedesktop.org/software/systemd/man/systemd.exec.html) |
| LiveKit | [LiveKit Docs](https://docs.livekit.io/) / [LiveKit Cloud](https://cloud.livekit.io/) |
| SSH login | [Microsoft OpenSSH](https://learn.microsoft.com/windows-server/administration/openssh/openssh_install_firstuse) / [Ubuntu OpenSSH](https://documentation.ubuntu.com/server/how-to/security/openssh-server/) |
| Mainland China ICP filing | [MIIT filing system](https://beian.miit.gov.cn/) / [Alibaba Cloud ICP filing](https://help.aliyun.com/zh/icp-filing/) / [Tencent Cloud ICP filing](https://cloud.tencent.com/document/product/243) |
| GitHub / Gitee | [GitHub](https://github.com/) / [Gitee](https://gitee.com/) |
| Local tools | [Python](https://www.python.org/downloads/) / [Git](https://git-scm.com/downloads) / [FFmpeg](https://ffmpeg.org/download.html) / [VS Code](https://code.visualstudio.com/) / [Homebrew](https://brew.sh/) / [winget](https://learn.microsoft.com/windows/package-manager/winget/) |

## Documentation

- [docs/README.md](docs/README.md) / [English](docs/README.md#documentation-map): documentation map

- [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) / [English](docs/DEPLOYMENT_GUIDE.md#deployment-and-update-guide): deployment, update, and troubleshooting

- [docs/STABILITY_AUDIT.md](docs/STABILITY_AUDIT.md) / [English](docs/STABILITY_AUDIT.md#stability-audit): stability risks and evolution plan

- [docs/REFACTOR_AUDIT.md](docs/REFACTOR_AUDIT.md) / [English](docs/REFACTOR_AUDIT.md#refactor-audit): current refactor audit, priorities, and recommended split order

- [docs/项目说明与代码索引.md](docs/%E9%A1%B9%E7%9B%AE%E8%AF%B4%E6%98%8E%E4%B8%8E%E4%BB%A3%E7%A0%81%E7%B4%A2%E5%BC%95.md) / [English](docs/%E9%A1%B9%E7%9B%AE%E8%AF%B4%E6%98%8E%E4%B8%8E%E4%BB%A3%E7%A0%81%E7%B4%A2%E5%BC%95.md#project-guide-and-code-index): project logic, core flows, code index, and presentation notes
