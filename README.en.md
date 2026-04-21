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
- RTC/LiveKit diagnostics inside the meeting room

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

## Local Development

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

By default the app uses `instance/app.db` as the SQLite database. On first run, if no admin password is configured, the app generates one and writes it to `instance/admin_password.txt`.

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

See [docs/DEPLOYMENT_GUIDE.en.md](docs/DEPLOYMENT_GUIDE.en.md) for the full Linux cloud server procedure, including:

- Security groups, firewall, server users, and project directories after buying a server.
- Cloudflare or plain DNS records.
- Python virtual environment, dependency installation, and `.env` configuration.
- Nginx reverse proxy for WebSocket, upload size, and HTTPS.
- systemd service files, auto-start, log inspection, and production updates.
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
- Virtual background, screen sharing, and recording are resource-heavy; on weak devices, meeting stability should come first.

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

## Documentation

- [docs/README.md](docs/README.md) / [English](docs/README.en.md): documentation map
- [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) / [English](docs/DEPLOYMENT_GUIDE.en.md): deployment, update, and troubleshooting
- [docs/STABILITY_AUDIT.md](docs/STABILITY_AUDIT.md) / [English](docs/STABILITY_AUDIT.en.md): stability risks and evolution plan
- [docs/项目说明与代码索引.md](docs/%E9%A1%B9%E7%9B%AE%E8%AF%B4%E6%98%8E%E4%B8%8E%E4%BB%A3%E7%A0%81%E7%B4%A2%E5%BC%95.md) / [English](docs/PROJECT_GUIDE.en.md): project logic, core flows, code index, and presentation notes
- `docs/视觉媒体通信期末大作业实践报告.docx`: archived course report
