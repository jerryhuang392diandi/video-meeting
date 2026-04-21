# Deployment and Update Guide

[中文](DEPLOYMENT_GUIDE.md) | [English](DEPLOYMENT_GUIDE.en.md)

This guide covers the full path from buying a Linux cloud server to running the app online. Examples assume Ubuntu 22.04 / 24.04, Nginx, systemd, Gunicorn + eventlet, SQLite, and an external LiveKit service. Replace paths, domains, and service names as needed.

## 0. How to Read Command Blocks

Commands in this guide run in a Linux shell on the server unless stated otherwise. After important command blocks, the guide explains:

- What each line does.
- Which values must be replaced with your real values.
- Which parameters can be customized for your server or project.

The examples use these placeholders:

| Placeholder | Meaning | Replace with |
| --- | --- | --- |
| `meeting.example.com` | Meeting system domain | Your own domain or subdomain |
| `your_server_ip` | Cloud server public IP | The public IP shown in your cloud console |
| `/opt/video-meeting` | Project deployment directory | Keep it or use your own directory |
| `deploy` | Linux runtime user | Keep it or use your own username |
| `video-meeting` | systemd service name | Keep it or use a shorter service name |
| `main` | Git default branch | Your actual deployment branch |

For a course demo, keeping the example directory, username, and service name reduces troubleshooting variables.

## 1. Recommended Architecture

```text
User browser
  -> https://meeting.example.com
  -> Cloudflare DNS or plain DNS
  -> Nginx reverse proxy for HTTPS and WebSocket forwarding
  -> Gunicorn + eventlet on 127.0.0.1:8000
  -> Flask + Flask-SocketIO application
  -> LiveKit Cloud or self-hosted LiveKit SFU
```

The current app keeps online room state mainly in single-process memory, so deploy it as one application instance by default. Do not simply start multiple Gunicorn workers or multiple app servers, or `rooms`, `sid_to_user`, chat history, and screen share state can diverge.

## 2. Buying a Server and Base Setup

Cloud providers can include Alibaba Cloud, Tencent Cloud, Huawei Cloud, AWS, Azure, DigitalOcean, Vultr, and similar vendors. For course demos or small demos:

| Item | Recommendation |
| --- | --- |
| OS | Ubuntu 22.04 LTS or 24.04 LTS |
| CPU / RAM | Start with 2 vCPU / 2 GB; use 4 GB for larger demos |
| Disk | Start with 30 GB; expand if uploads and recordings grow |
| Inbound ports | `22`, `80`, `443` |
| Domain | A subdomain such as `meeting.example.com` |
| Python production runtime | `requirements.txt` plus server-side `gunicorn eventlet` |

In the cloud console:

1. Allow `80/tcp` and `443/tcp` in the security group or firewall.
2. Restrict SSH to your own public IP if possible; otherwise use a strong password or SSH key.

First login:

```bash
ssh root@your_server_ip
apt update
apt upgrade -y
timedatectl set-timezone Asia/Shanghai
```

Command explanation:

| Command | Meaning | Customizable |
| --- | --- | --- |
| `ssh root@your_server_ip` | Log in to the new server as root | Replace `your_server_ip`; replace `root` if your provider uses another username |
| `apt update` | Refresh package indexes | Usually keep it |
| `apt upgrade -y` | Upgrade installed packages; `-y` auto-confirms | Remove `-y` if you want manual confirmation |
| `timedatectl set-timezone Asia/Shanghai` | Set server timezone to Shanghai | Use `UTC` or another timezone if appropriate |

Create a dedicated runtime user:

```bash
adduser deploy
usermod -aG sudo deploy
su - deploy
```

Command explanation:

| Command | Meaning | Customizable |
| --- | --- | --- |
| `adduser deploy` | Create a normal Linux user named `deploy` | Replace `deploy` with another username |
| `usermod -aG sudo deploy` | Allow `deploy` to run admin commands through `sudo` | In stricter production setups, omit sudo and let an admin run privileged commands |
| `su - deploy` | Switch to the `deploy` user | Must match the user above |

## 3. Install System Dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git nginx ffmpeg curl ufw
```

Command and dependency explanation:

| Item | Meaning | Customizable |
| --- | --- | --- |
| `sudo apt update` | Refresh package indexes | Do not skip |
| `python3` | Python runtime | Ubuntu 22.04 / 24.04 built-in versions are usually enough |
| `python3-venv` | Creates the project virtual environment | Required |
| `python3-pip` | Installs Python packages | Required |
| `git` | Pulls code from Git | Optional if deploying by archive, but Git is recommended |
| `nginx` | Public entry, HTTPS, WebSocket reverse proxy | Can be replaced by Caddy/Apache, but this guide uses Nginx |
| `ffmpeg` | WebM recording remux to MP4 | Optional if MP4 export is not needed |
| `curl` | Command-line HTTP testing | Recommended |
| `ufw` | Ubuntu firewall tool | Can be supplemented by cloud security groups |

Enable a basic firewall:

```bash
sudo ufw allow OpenSSH
sudo ufw allow "Nginx Full"
sudo ufw enable
sudo ufw status
```

Command explanation:

| Command | Meaning | Customizable |
| --- | --- | --- |
| `sudo ufw allow OpenSSH` | Allows SSH so you do not lock yourself out | If SSH uses a custom port, allow that port |
| `sudo ufw allow "Nginx Full"` | Allows Nginx HTTP `80` and HTTPS `443` | If not using Nginx, allow `80/tcp` and `443/tcp` manually |
| `sudo ufw enable` | Enables the firewall | Confirm SSH is allowed first |
| `sudo ufw status` | Shows active firewall rules | Use it to verify rules |

## 4. Prepare the Project Directory

Example path: `/opt/video-meeting`.

```bash
sudo mkdir -p /opt/video-meeting
sudo chown deploy:deploy /opt/video-meeting
cd /opt/video-meeting
```

Deploy from Git:

```bash
git clone https://github.com/your-name/video-meeting-replace.git .
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn eventlet
```

If you upload a project archive instead, extract it into `/opt/video-meeting`, then create the virtual environment and install dependencies.

`gunicorn` and `eventlet` are for Linux production runtime only; Windows local development still uses `python app.py` as shown in the root README.

Command explanation:

| Command | Meaning | Customizable |
| --- | --- | --- |
| `sudo mkdir -p /opt/video-meeting` | Creates the project directory, including parents | Replace with `/srv/video-meeting` or another path if desired |
| `sudo chown deploy:deploy /opt/video-meeting` | Gives ownership to the `deploy` user | Must match your runtime user |
| `git clone ... .` | Clones the repository into the current directory; trailing `.` avoids creating another subdirectory | Replace URL; private repos need SSH key or token setup |
| `python3 -m venv venv` | Creates the `venv` virtual environment | Directory name can change, but systemd must match |
| `source venv/bin/activate` | Activates the virtual environment | Run it before manual dependency installs |
| `pip install --upgrade pip` | Upgrades pip | Optional but recommended |
| `pip install -r requirements.txt` | Installs project dependencies | Re-run after requirements changes |
| `pip install gunicorn eventlet` | Installs Linux production runtime dependencies | Can move to a dedicated production requirements file later |

## 5. Configure Environment Variables

Use `/opt/video-meeting/.env` for production config and load it from systemd:

```bash
nano /opt/video-meeting/.env
```

Example:

```env
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=sqlite:////opt/video-meeting/instance/app.db

PUBLIC_SCHEME=https
PUBLIC_HOST=meeting.example.com

LIVEKIT_URL=wss://your-livekit-host
LIVEKIT_API_KEY=replace-with-livekit-api-key
LIVEKIT_API_SECRET=replace-with-livekit-api-secret

ADMIN_USERNAME=root
ADMIN_PASSWORD=replace-with-strong-admin-password

SESSION_COOKIE_SECURE=1
REMEMBER_COOKIE_SECURE=1
SESSION_COOKIE_SAMESITE=Lax
REMEMBER_COOKIE_SAMESITE=Lax
```

Configuration explanation:

| Setting | Meaning | Required | Customizable |
| --- | --- | --- | --- |
| `SECRET_KEY` | Flask session signing secret | Yes | Use a long random value; never commit it |
| `DATABASE_URL` | SQLAlchemy database URL | No | Keep SQLite or switch to PostgreSQL/MySQL later |
| `PUBLIC_SCHEME` | Public access scheme | Yes | Use `https` online; use `http` only for local HTTP |
| `PUBLIC_HOST` | Public hostname | Yes | Use `meeting.example.com` without `https://` |
| `LIVEKIT_URL` | Browser-facing LiveKit URL | Yes | LiveKit Cloud usually gives `wss://...livekit.cloud` |
| `LIVEKIT_API_KEY` | LiveKit key for backend token signing | Yes | Copy from LiveKit console |
| `LIVEKIT_API_SECRET` | LiveKit secret for backend token signing | Yes | Copy from LiveKit console and keep private |
| `ADMIN_USERNAME` | Initial admin username | No | Defaults to `root`; set explicitly in production |
| `ADMIN_PASSWORD` | Initial admin password | No | Strongly recommended; otherwise generated into `instance/admin_password.txt` |
| `SESSION_COOKIE_SECURE` | Sends session cookie over HTTPS only | Recommended for HTTPS | Set to `1` online |
| `REMEMBER_COOKIE_SECURE` | Sends remember cookie over HTTPS only | Recommended for HTTPS | Set to `1` online |
| `SESSION_COOKIE_SAMESITE` | SameSite policy for session cookie | Recommended | Use `Lax` for normal same-site deployment |
| `REMEMBER_COOKIE_SAMESITE` | SameSite policy for remember cookie | Recommended | Use `Lax` for normal same-site deployment |

Generate a `SECRET_KEY`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Command explanation:

| Part | Meaning | Customizable |
| --- | --- | --- |
| `python3 -c "..."` | Runs a one-line Python snippet | Keep it |
| `secrets.token_urlsafe(48)` | Generates a random secret suitable for URLs/cookies | `48` can be increased; do not make it small |

Important:

- `SECRET_KEY` must stay stable across restarts, or user sessions are invalidated.
- `PUBLIC_HOST` is the hostname without scheme, for example `meeting.example.com`.
- Use `PUBLIC_SCHEME=https` when HTTPS is enabled.
- If LiveKit config is missing, room pages intentionally return `503`; that is a configuration problem.
- SQLite data and uploads live under `instance/`, so production backups must include that directory.

## 6. LiveKit Options

### 6.1 LiveKit Cloud

The simplest path is LiveKit Cloud:

1. Create a LiveKit Cloud project.
2. Copy the server URL, usually `wss://...livekit.cloud`.
3. Create an API key and API secret.
4. Put them into `.env` as `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET`.

The Flask app only issues tokens. Browsers connect directly to LiveKit, so Nginx does not proxy LiveKit Cloud.

### 6.2 Self-Hosted LiveKit

Self-hosting LiveKit gives more control but adds operational work. You must handle:

- LiveKit process or container deployment.
- LiveKit's own HTTPS / WSS endpoint.
- UDP media ports, TCP fallback, and TURN/ICE reachability.
- Cloud security group and OS firewall rules for LiveKit ports.
- Matching LiveKit API key / secret values in Flask `.env`.

For a course demo, use LiveKit Cloud first, then consider self-hosting after the core flow works.

## 7. Domain, Cloudflare, and DNS

### 7.1 Plain DNS

Add an A record at your DNS provider:

```text
Type: A
Name: meeting
Value: your_server_ip
TTL: Auto or 600
```

Check propagation:

```bash
dig meeting.example.com
```

### 7.2 Cloudflare

If the domain is on Cloudflare:

1. Add an `A` record, name `meeting`, IPv4 address set to the server public IP.
2. Start with DNS only, then enable Proxied after the server works.
3. Use SSL/TLS mode `Full (strict)` with a valid server-side certificate.
4. If Cloudflare proxy is enabled, confirm WebSocket is not blocked; this app needs stable Socket.IO WebSocket or polling.

Stable demo path:

1. Run DNS only + Nginx + Let's Encrypt first.
2. Enable Cloudflare Proxied afterward.
3. Re-test login, room join, chat, and two-device media.

## 8. Nginx Reverse Proxy

Socket.IO needs WebSocket or long polling. The official Nginx WebSocket proxy pattern maps the client `Upgrade` header to a connection variable, so create this map first.

Create the WebSocket map:

```bash
sudo nano /etc/nginx/conf.d/websocket-map.conf
```

Add:

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}
```

Configuration explanation:

| Directive | Meaning | Customizable |
| --- | --- | --- |
| `map $http_upgrade $connection_upgrade` | Creates a variable based on whether the client requests protocol upgrade | Variable name can change, but the site config must match |
| `default upgrade;` | If `Upgrade` exists, upgrade the connection to WebSocket | Keep it |
| `'' close;` | If no `Upgrade` header exists, treat it as normal HTTP | Keep it |

Create the site config:

```bash
sudo nano /etc/nginx/sites-available/video-meeting
```

Start with HTTP; Certbot can later upgrade it to HTTPS:

```nginx
server {
    listen 80;
    server_name meeting.example.com;

    client_max_body_size 150m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_read_timeout 3600;
        proxy_send_timeout 3600;
    }
}
```

Configuration explanation:

| Directive | Meaning | Customizable |
| --- | --- | --- |
| `listen 80;` | Listens on HTTP; Certbot uses it to issue the certificate | Use default for public HTTPS setup |
| `server_name meeting.example.com;` | Domain served by this block | Must be your domain |
| `client_max_body_size 150m;` | Maximum upload request body | Current video attachment limit is 120 MB; increase if app limits increase |
| `proxy_pass http://127.0.0.1:8000;` | Forwards traffic to local Gunicorn | Port must match systemd `--bind` |
| `proxy_http_version 1.1;` | Required for WebSocket proxying | Keep it |
| `proxy_set_header Host $host;` | Passes original host to Flask | Keep it |
| `proxy_set_header X-Real-IP $remote_addr;` | Passes client IP | Behind Cloudflare, you can later add real IP handling |
| `proxy_set_header X-Forwarded-For ...` | Passes proxy chain IPs | Keep it |
| `proxy_set_header X-Forwarded-Proto $scheme;` | Passes external scheme | Used for HTTPS-aware behavior and secure cookies |
| `proxy_set_header Upgrade $http_upgrade;` | Passes WebSocket upgrade header | Required for Socket.IO WebSocket |
| `proxy_set_header Connection $connection_upgrade;` | Uses the map variable for upgrade/close | Must match the map above |
| `proxy_read_timeout 3600;` | Allows long-running upstream reads | Adjust if needed |
| `proxy_send_timeout 3600;` | Allows long-running upstream sends | Adjust if needed |

Enable it:

```bash
sudo ln -s /etc/nginx/sites-available/video-meeting /etc/nginx/sites-enabled/video-meeting
sudo nginx -t
sudo systemctl reload nginx
```

`client_max_body_size 150m` is larger than the current 120 MB video attachment limit.

## 9. HTTPS Certificate

Certbot officially recommends snap installation for Ubuntu + Nginx. Install the snap version first:

```bash
sudo snap install core
sudo snap refresh core
sudo apt remove -y certbot
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
```

Command explanation:

| Command | Meaning | Customizable |
| --- | --- | --- |
| `sudo snap install core` | Installs snap core runtime | If already installed, the command may say so |
| `sudo snap refresh core` | Updates snap core | Keep it |
| `sudo apt remove -y certbot` | Removes apt Certbot to avoid command conflicts | Can skip if apt Certbot was never installed |
| `sudo snap install --classic certbot` | Installs official snap Certbot | Keep it |
| `sudo ln -s /snap/bin/certbot /usr/bin/certbot` | Makes `certbot` available in the usual PATH | If it already exists, it has already been configured |

Issue the certificate and let Certbot update Nginx:

```bash
sudo certbot --nginx -d meeting.example.com
```

Command explanation:

| Argument | Meaning | Customizable |
| --- | --- | --- |
| `--nginx` | Lets Certbot read and edit Nginx config | Use `certonly --nginx` if you want to edit Nginx manually |
| `-d meeting.example.com` | Domain for the certificate | Must be your domain; use multiple `-d` flags for multiple domains |

Verify renewal:

```bash
sudo certbot renew --dry-run
```

Command explanation:

| Argument | Meaning | Customizable |
| --- | --- | --- |
| `renew` | Tests renewal flow | Keep it |
| `--dry-run` | Simulation only; does not replace the real certificate | Keep it for verification |

After HTTPS is ready, keep `.env` aligned:

```env
PUBLIC_SCHEME=https
SESSION_COOKIE_SECURE=1
REMEMBER_COOKIE_SECURE=1
```

If Cloudflare uses `Full (strict)`, the server still needs a valid certificate; Let's Encrypt is enough.

## 10. systemd Service

Create the service:

```bash
sudo nano /etc/systemd/system/video-meeting.service
```

Recommended config:

```ini
[Unit]
Description=Video Meeting Flask-SocketIO App
After=network.target

[Service]
User=deploy
Group=deploy
WorkingDirectory=/opt/video-meeting
EnvironmentFile=/opt/video-meeting/.env
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/video-meeting/venv/bin/gunicorn --worker-class eventlet --workers 1 --bind 127.0.0.1:8000 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Configuration explanation:

| Setting | Meaning | Customizable |
| --- | --- | --- |
| `Description` | Human-readable service description | Change to your project name |
| `After=network.target` | Starts after network is available | Usually keep it |
| `User=deploy` / `Group=deploy` | Runs the service as a normal user | Must match the runtime user |
| `WorkingDirectory=/opt/video-meeting` | Service working directory | Must match project directory |
| `EnvironmentFile=/opt/video-meeting/.env` | Loads environment variables from `.env` | Path can change if the file exists and permissions are correct |
| `Environment=PYTHONUNBUFFERED=1` | Sends Python logs to journal promptly | Recommended |
| `ExecStart=...gunicorn...` | Actual application start command | Adjust virtualenv path, port, or module if the project changes |
| `--worker-class eventlet` | Uses eventlet worker for Socket.IO long connections | Flask-SocketIO supports this; changing worker type requires re-testing |
| `--workers 1` | Starts exactly one worker | Required for current in-memory room state; do not casually increase |
| `--bind 127.0.0.1:8000` | Listens only on local port 8000 | Port can change, but Nginx `proxy_pass` must match |
| `app:app` | Flask app object `app` inside `app.py` | Change if the file/object is renamed |
| `Restart=always` | Restarts after crashes | Recommended |
| `RestartSec=5` | Waits 5 seconds before restart | Adjustable |
| `WantedBy=multi-user.target` | Enables normal boot auto-start | Keep it |

Start and enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable video-meeting
sudo systemctl start video-meeting
sudo systemctl status video-meeting
```

Command explanation:

| Command | Meaning | Customizable |
| --- | --- | --- |
| `sudo systemctl daemon-reload` | Reloads systemd unit files | Required after editing `.service` |
| `sudo systemctl enable video-meeting` | Enables auto-start on boot | Replace service name if changed |
| `sudo systemctl start video-meeting` | Starts the service | Use `restart` for restarts |
| `sudo systemctl status video-meeting` | Shows service status and recent logs | First troubleshooting step |

Logs:

```bash
journalctl -u video-meeting -n 100 --no-pager
journalctl -u video-meeting -f
```

Command explanation:

| Command | Meaning | Customizable |
| --- | --- | --- |
| `journalctl -u video-meeting -n 100 --no-pager` | Shows latest 100 log lines without pager | Change `100` as needed |
| `journalctl -u video-meeting -f` | Follows logs live | Use while reproducing an issue |

## 11. First Online Verification

Check the service:

```bash
curl -I http://127.0.0.1:8000
curl -I http://meeting.example.com
curl -I https://meeting.example.com
```

Browser checks:

- Home, login, and registration pages are reachable.
- The admin account can log in.
- A normal user can register, log in, and create a meeting.
- Room pages do not return `503` because of missing LiveKit config.
- Two devices can join the same meeting and see remote media on first join.
- Chat, attachment upload, preview, and download permissions work.
- Camera, microphone, and screen sharing can start and stop.
- `/admin` opens and common admin actions work.

## 12. Standard Server Update

```bash
cd /opt/video-meeting
git status
git pull origin main
source /opt/video-meeting/venv/bin/activate
pip install -r requirements.txt
pip install gunicorn eventlet
sudo systemctl restart video-meeting
sudo systemctl status video-meeting
```

Notes:

- Skip `pip install -r requirements.txt` if dependencies did not change.
- If `gunicorn eventlet` is already installed in the server virtual environment, normal code-only updates do not need to reinstall it.
- Do not run `git clean -fd` by default; it deletes untracked files and can remove runtime data.
- Check `systemctl status` after restart, then continue with logs if needed.

Code-only update:

```bash
cd /opt/video-meeting
git pull origin main
sudo systemctl restart video-meeting
sudo systemctl status video-meeting
```

After changing systemd:

```bash
sudo systemctl daemon-reload
sudo systemctl restart video-meeting
sudo systemctl status video-meeting
```

After changing Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 13. Backup and Migration

SQLite and uploads are under `instance/` by default. Back up at least:

```bash
cd /opt/video-meeting
tar -czf /tmp/video-meeting-instance-$(date +%F).tar.gz instance
```

For server migration:

1. Deploy code and dependencies on the new server.
2. Copy the old server's `instance/` directory.
3. Copy `.env`, or recreate it while keeping `DATABASE_URL`, LiveKit, domain, and admin settings correct.
4. Point DNS to the new server IP.
5. Restart systemd and run a two-device room test.

## 14. Local Commit Flow

```bash
git status
git pull --rebase origin main
git add .
git commit -m "Improve deployment documentation"
git push origin main
```

Before committing:

- Do not commit `instance/`, databases, uploads, temporary recordings, or the local virtual environment.
- If template text changed, run `python check_i18n.py`.
- If deployment behavior changed, update the root README, deployment guide, and stability notes together.

## 15. Common Issues

### Room Returns 503

Check first:

```bash
grep LIVEKIT /opt/video-meeting/.env
journalctl -u video-meeting -n 100 --no-pager
```

Confirm:

- `LIVEKIT_URL` is a browser-reachable `wss://...` URL.
- `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` are correct.
- systemd loads `/opt/video-meeting/.env`.
- `video-meeting` was restarted after editing `.env`.

### Page Opens but Socket.IO Fails

Confirm Nginx preserves WebSocket headers:

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection $connection_upgrade;
proxy_read_timeout 3600;
```

Then check:

```bash
sudo nginx -t
sudo systemctl reload nginx
journalctl -u video-meeting -f
```

### Page Opens but Remote Media Is Missing

Check first:

- Whether the browser allowed camera and microphone.
- Whether LiveKit is reachable.
- Whether `PUBLIC_HOST` / `PUBLIC_SCHEME` match the real public address.
- Whether Cloudflare proxy affects WebSocket or LiveKit domain access.
- Whether only one device fails or both sides fail.

### Attachment Upload Fails

Check Nginx upload limits and directory permissions:

```bash
grep client_max_body_size /etc/nginx/sites-available/video-meeting
ls -ld /opt/video-meeting/instance
sudo chown -R deploy:deploy /opt/video-meeting/instance
```

### MP4 Recording Export Fails

```bash
which ffmpeg
ffmpeg -version
journalctl -u video-meeting -n 100 --no-pager
```

Without `ffmpeg`, the app can still keep the browser's raw recording output, but WebM-to-MP4 remux fails.

### 502 Bad Gateway

This usually means the app service is down or Nginx points to the wrong port:

```bash
sudo systemctl status video-meeting
journalctl -u video-meeting -n 100 --no-pager
ss -lntp | grep 8000
```

### `.env` Changes Do Not Apply

systemd does not automatically reload `.env`:

```bash
sudo systemctl restart video-meeting
```

If the service file changed:

```bash
sudo systemctl daemon-reload
sudo systemctl restart video-meeting
```

## 16. References

This guide combines the current project code with these official documents:

| Topic | Official docs | Adopted point |
| --- | --- | --- |
| Flask-SocketIO + Gunicorn | [Flask-SocketIO Deployment](https://flask-socketio.readthedocs.io/en/latest/deployment.html) | Use Gunicorn with `eventlet`, keeping `-w 1` / `--workers 1` |
| Gunicorn arguments | [Gunicorn Settings](https://docs.gunicorn.org/en/stable/settings.html) | Meaning of `--bind`, `--workers`, and `--worker-class` |
| Nginx WebSocket | [Nginx WebSocket proxying](https://nginx.org/en/docs/http/websocket.html) | Forward `Upgrade` explicitly and use `map` for `Connection` |
| Certbot | [Certbot install guide](https://eff-certbot.readthedocs.io/en/stable/install.html) | Use snap Certbot for Ubuntu/Nginx |
| Cloudflare SSL | [Cloudflare Full (strict)](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/) | Full (strict) requires a valid origin certificate |
| systemd environment | [systemd.exec EnvironmentFile](https://www.freedesktop.org/software/systemd/man/systemd.exec.html) | `EnvironmentFile=` loads variables from a file |

## 17. Operations to Avoid

- Do not run production service with the Flask debug server.
- Do not start multiple Gunicorn workers to "improve performance" unless runtime room state has moved to shared storage.
- Do not habitually run `git clean -fd` in production directories.
- Do not repeatedly restart the service without reading logs.
- Do not commit runtime databases, uploads, or generated files.
- Do not only test page load; room media requires a two-client check.
