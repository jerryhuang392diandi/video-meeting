# Deployment and Update Guide

[中文](DEPLOYMENT_GUIDE.md) | [English](DEPLOYMENT_GUIDE.en.md)

This guide is for deploying, updating, and troubleshooting the current `Flask + Flask-SocketIO + LiveKit` meeting system. Replace example paths and service names with the actual values on your server.

## Prerequisites

| Item | Example |
| --- | --- |
| Project directory | `/opt/video-meeting` |
| Virtual environment | `/opt/video-meeting/venv` |
| systemd service name | `video-meeting` |
| Default branch | `main` |
| Python dependencies | `requirements.txt` |

Confirm before deployment:

- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` are configured.
- `SECRET_KEY` is stable and does not change on every restart.
- `PUBLIC_HOST` and `PUBLIC_SCHEME` match the real public access address.
- `ffmpeg` is installed if MP4 recording export is required.
- Online room state is mainly single-process memory, so do not treat the default setup as horizontally scalable.

## Local Commit Flow

```bash
git status
git pull --rebase origin main
git add .
git commit -m "Improve documentation"
git push origin main
```

Before committing:

- Do not commit `instance/`, databases, uploads, temporary recordings, or the local virtual environment.
- Use a clear commit message even for documentation-only changes.
- If template text changed, run `python check_i18n.py`.

## Standard Server Update

```bash
cd /opt/video-meeting
git status
git pull origin main
source /opt/video-meeting/venv/bin/activate
pip install -r requirements.txt
systemctl restart video-meeting
systemctl status video-meeting
```

Notes:

- Skip `pip install -r requirements.txt` if dependencies did not change.
- Do not run `git clean -fd` by default; it deletes untracked files and can remove runtime data.
- Check `systemctl status` after restart, then continue with logs if needed.

## Code-Only Update

```bash
cd /opt/video-meeting
git pull origin main
source /opt/video-meeting/venv/bin/activate
systemctl restart video-meeting
systemctl status video-meeting
```

## Dependency Update

```bash
cd /opt/video-meeting
git pull origin main
source /opt/video-meeting/venv/bin/activate
pip install -r requirements.txt
systemctl restart video-meeting
systemctl status video-meeting
```

After dependency changes, verify:

- LiveKit tokens can be generated.
- Room pages do not hit the LiveKit-missing `503` path.
- Recording export still works on servers with `ffmpeg`.

## After Changing systemd Configuration

```bash
systemctl daemon-reload
systemctl restart video-meeting
systemctl status video-meeting
```

## Logs and Status

```bash
systemctl status video-meeting
journalctl -u video-meeting -n 100 --no-pager
journalctl -u video-meeting -f
```

Suggested troubleshooting order:

1. Check whether the service started successfully.
2. Read the latest 100 log lines.
3. Reproduce the issue while following logs with `journalctl -f`.
4. For room media issues, check application logs, the browser console, and LiveKit service status together.

## Minimum Post-Update Verification

After each production update, check at least:

- Home, login, and registration pages are reachable.
- A normal user can log in, create a room, and enter it.
- Two devices can join the same room and see remote media on first join.
- Camera, microphone, and screen sharing can start and stop.
- Chat, attachment upload, attachment preview, and download permissions work.
- Admin dashboard `/admin` opens and common actions work.
- Chinese and English UI text is not obviously missing.

If the change touches screen sharing, also verify:

- Refreshing during screen share does not leave stale sharer state.
- Layout recovers on remote clients after sharing stops.
- Mobile clients can at least watch remote screen share reliably.

## Common Issues

### Room Returns 503

Check first:

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- Token generation errors in application logs

### Page Opens but Media Is Missing

Check first:

- Whether the browser allowed camera and microphone access.
- Whether the LiveKit service is reachable.
- Whether `PUBLIC_HOST` / `PUBLIC_SCHEME` causes a wrong frontend connection address.
- Whether the issue affects only one device or both sides.

### Attachment Upload or Download Fails

Check first:

- Upload directory permissions under `instance/`.
- Whether the attachment is view-only.
- Whether the browser can preview the file type.

### Recording Export Fails

Check first:

- Whether `ffmpeg` is installed on the server.
- Whether logs show remux failures.
- Whether the browser's raw output format is `webm`.

## Operations to Avoid

- Do not habitually run `git clean -fd` in production directories.
- Do not repeatedly restart the service without reading logs.
- Do not mix runtime databases/uploads with repository-managed files.
- Do not only test page load; room media requires a two-client check.
