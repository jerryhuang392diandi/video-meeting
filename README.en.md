# Video Meeting System

[中文](README.md) | [English](README.en.md)

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

The detailed LiveKit Cloud flow, the reason Nginx does not proxy LiveKit, and the self-hosted LiveKit port checklist are covered in [LiveKit Options](docs/DEPLOYMENT_GUIDE.en.md#7-livekit-options). The full production environment variable table is in [Configure Environment Variables](docs/DEPLOYMENT_GUIDE.en.md#5-configure-environment-variables).

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
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Initial admin login | Simple values are fine locally; use a strong password in production |

The three LiveKit values must come from the same LiveKit project. Flask only checks meeting permission and issues a token; the browser connects directly to `LIVEKIT_URL`, so that URL must be reachable from your browser.

If rooms return `503`, `.env` changes do not apply, or users can join but cannot see each other, start with [Common Issues](docs/DEPLOYMENT_GUIDE.en.md#16-common-issues). Local development usually only needs restarting `python app.py`; production systemd services must be restarted after `.env` changes.

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
| `pip install` is slow | Try a PyPI mirror or check the network; server setup details are in [Prepare Project Directory](docs/DEPLOYMENT_GUIDE.en.md#4-prepare-project-directory) |
| `/room/<room_id>` returns `503` | `.env` is missing `LIVEKIT_URL`, `LIVEKIT_API_KEY`, or `LIVEKIT_API_SECRET`; see [Common Issues](docs/DEPLOYMENT_GUIDE.en.md#16-common-issues) |
| MP4 recording remux fails | Confirm FFmpeg is installed and `ffmpeg -version` prints a version |
| Virtual background fails to start | Turn the camera on first; after toggling the camera, wait for local video to recover before enabling it; this feature also depends on the browser loading the MediaPipe model |

## Cloud Server Deployment Overview

For production or course demonstrations, use this deployment shape:

```text
Browser
  -> Domain / Cloudflare DNS
  -> Nginx reverse proxy and HTTPS
  -> Gunicorn + eventlet running Flask-SocketIO
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

See [docs/DEPLOYMENT_GUIDE.en.md](docs/DEPLOYMENT_GUIDE.en.md) for the full Linux cloud server procedure. It now follows the first-deployment order: server purchase, ICP filing notes for mainland China servers, Windows/macOS/FinalShell SSH login, project config, systemd, LiveKit, Nginx, and HTTPS.

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
| `DEBUG_ROOM=1` | Enables room debug logging |

Optional settings include `TURN_PUBLIC_HOST`, `SESSION_COOKIE_SAMESITE`, `SESSION_COOKIE_SECURE`, `REMEMBER_COOKIE_SAMESITE`, and `REMEMBER_COOKIE_SECURE`.

## Runtime Limits

- Online room state is primarily kept in single-process memory, so treat the default deployment as single-instance.
- LiveKit is external media infrastructure and must be configured correctly.
- MP4 recording export depends on server-side `ffmpeg`; without it, only the browser's raw recording output is kept.
- Virtual background depends on a live local camera track, the browser-side MediaPipe model, and canvas processing. Screen sharing and recording are also resource-heavy; on weak devices, meeting stability should come first.
- Current refactor direction is tracked in [docs/REFACTOR_AUDIT.en.md](docs/REFACTOR_AUDIT.en.md): keep room state consistency first, then split the room script and `app.py` gradually.

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

Deployment and runtime configuration mainly follow these official documents. See the "References" section in [docs/DEPLOYMENT_GUIDE.en.md](docs/DEPLOYMENT_GUIDE.en.md) for the detailed deployment context.

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

- [docs/README.md](docs/README.md) / [English](docs/README.en.md): documentation map

- [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) / [English](docs/DEPLOYMENT_GUIDE.en.md): deployment, update, and troubleshooting

- [docs/STABILITY_AUDIT.md](docs/STABILITY_AUDIT.md) / [English](docs/STABILITY_AUDIT.en.md): stability risks and evolution plan

- [docs/REFACTOR_AUDIT.md](docs/REFACTOR_AUDIT.md) / [English](docs/REFACTOR_AUDIT.en.md): current refactor audit, priorities, and recommended split order

- [docs/项目说明与代码索引.md](docs/%E9%A1%B9%E7%9B%AE%E8%AF%B4%E6%98%8E%E4%B8%8E%E4%BB%A3%E7%A0%81%E7%B4%A2%E5%BC%95.md) / [English](docs/PROJECT_GUIDE.en.md): project logic, core flows, code index, and presentation notes

	
