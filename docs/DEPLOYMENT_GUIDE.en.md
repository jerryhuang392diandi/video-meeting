# Deployment and Update Guide

[中文](DEPLOYMENT_GUIDE.md) | [English](DEPLOYMENT_GUIDE.en.md)

This guide follows the real first-deployment order: prepare accounts and a server, connect to the server, deploy the Flask app, systemd, Nginx, HTTPS, and then configure LiveKit. Examples assume Ubuntu 22.04 / 24.04, Nginx, systemd, Gunicorn + eventlet, SQLite, and either LiveKit Cloud or self-hosted LiveKit.

## Beginner Path

Use this order for the lowest-risk first deployment:

1. Run locally with `python app.py` and verify registration, login, and meeting creation pages.
2. Buy one Ubuntu cloud server and confirm domain, ICP filing if needed, DNS, and security group rules.
3. Connect through SSH from Windows CMD/PowerShell, macOS Terminal, Linux shell, or FinalShell.
4. Deploy the Flask app, `.env`, systemd, Nginx, and HTTPS.
5. Use LiveKit Cloud first. Put `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` into `.env`.
6. Test with two real devices. Self-host LiveKit only if you really need to operate your own media service.

Nginx proxies this Flask website. LiveKit carries camera, microphone, and screen-share media. With LiveKit Cloud, Nginx does not proxy LiveKit.

## 0. How to Read Command Blocks

Unless stated otherwise, commands run in a Linux shell on the server. Placeholders:

| Placeholder | Meaning | Replace with |
| --- | --- | --- |
| `meeting.example.com` | Meeting app domain | Your own domain or subdomain |
| `livekit.example.com` | Self-hosted LiveKit domain | Your media service domain if self-hosting |
| `your_server_ip` | Cloud server public IP | Public IP from the cloud console |
| `/opt/video-meeting` | Project deployment directory | Keep it or use your own directory |
| `deploy` | Linux runtime user | Keep it or use your own username |
| `video-meeting` | systemd service name | Keep it or rename it consistently |
| `main` | Git default branch | Your real deployment branch |

This guide often writes files with `cat <<'EOF' | sudo tee ...`. That is easier to copy and less error-prone than editing with `nano`. If you use `nano`, save with `Ctrl+O`, press Enter to confirm, and exit with `Ctrl+X`.

## 0.1 Accounts and Websites to Prepare

| Type | Purpose | Entry |
| --- | --- | --- |
| Cloud server | Runs Flask, Nginx, and systemd | Alibaba Cloud ECS, Tencent Cloud CVM, Huawei Cloud ECS, AWS EC2, Azure VM, DigitalOcean, Vultr |
| Domain | Lets users open `meeting.example.com` | Alibaba Cloud Domains, Tencent DNSPod, Cloudflare Registrar, Namecheap, or another registrar |
| ICP filing | Usually required for public domain access on mainland China servers | MIIT filing system or cloud provider filing console |
| GitHub / Gitee | Code hosting for `git clone` / `git pull` | GitHub: https://github.com/jerryhuang392diandi/video-meeting; Gitee: https://gitee.com/jerryhqx/video-meeting |
| Cloudflare | Optional DNS hosting, proxy, and SSL/TLS settings | https://www.cloudflare.com/ |
| LiveKit Cloud | Easiest hosted LiveKit media service | https://cloud.livekit.io/ |
| Let's Encrypt / Certbot | Free HTTPS certificates | https://letsencrypt.org/ / https://certbot.eff.org/ |

Official references are collected at the end. Follow this guide first; use the official docs when your provider or version differs.

## 1. Recommended Architecture

```text
User browser
  -> https://meeting.example.com
  -> DNS or Cloudflare
  -> Nginx on 443/80
  -> Gunicorn + eventlet on 127.0.0.1:8000
  -> Flask + Flask-SocketIO app

User browser
  -> wss://your-project.livekit.cloud or wss://livekit.example.com
  -> LiveKit SFU
```

The current app keeps online room state mainly in single-process memory, so deploy it as one application instance by default. Do not simply start multiple Gunicorn workers or multiple app servers, or `rooms`, `sid_to_user`, chat history, and screen-share state can diverge.

## 2. Buying a Server, ICP Filing, and SSH Login

### 2.1 Buy a Server

Common cloud server providers:

| Provider | Entry | Notes |
| --- | --- | --- |
| Alibaba Cloud ECS | https://www.aliyun.com/product/ecs | Chinese console, good for mainland China users |
| Tencent Cloud CVM | https://cloud.tencent.com/product/cvm | Chinese console |
| Huawei Cloud ECS | https://www.huaweicloud.com/product/ecs.html | Chinese console |
| AWS EC2 | https://aws.amazon.com/ec2/ | International cloud provider |
| Azure Virtual Machines | https://azure.microsoft.com/products/virtual-machines/ | International cloud provider |
| DigitalOcean Droplets | https://www.digitalocean.com/products/droplets | Simple English dashboard |
| Vultr Cloud Compute | https://www.vultr.com/products/cloud-compute/ | Simple English dashboard |

For course demos or small deployments:

| Item | Recommendation |
| --- | --- |
| OS | Ubuntu 22.04 LTS or 24.04 LTS |
| CPU / RAM | Start with 2 vCPU / 2 GB; use 4 GB for larger demos |
| Disk | Start with 30 GB; expand later for uploads and recordings |
| Inbound ports | `22/tcp`, `80/tcp`, `443/tcp` |
| Domain | A subdomain such as `meeting.example.com` |

Buying notes:

- Choose a region close to your users.
- Beginners should choose Ubuntu LTS instead of CentOS, minimal Debian images, or custom images.
- Do not buy load balancers, managed databases, or object storage at the start. Get the single-server app working first.
- Open `22/tcp`, `80/tcp`, and `443/tcp` in the cloud security group. Self-hosted LiveKit needs additional media ports.

### 2.2 Mainland China Servers and ICP Filing

If the server is in mainland China and you want to serve a public website through a domain, ICP filing is usually required. Without filing, cloud providers may block domain binding or public access.

Simplified rule:

| Situation | ICP filing usually needed? |
| --- | --- |
| Mainland China server + public domain | Yes |
| Mainland China server + public IP only for temporary testing | Usually no domain filing, but not suitable for a public demo |
| Hong Kong, Singapore, US, or other non-mainland server | Usually no mainland China ICP filing, but network quality may differ |

ICP filing requirements change. Use MIIT and cloud provider documentation as the source of truth.

### 2.3 Login from Windows, macOS, Linux, or FinalShell

The cloud provider usually gives you a public IP, username, and either a password or SSH private key. Ubuntu usernames are often `root`, `ubuntu`, or a user created in the console.

Common login commands:

| Scenario | Command |
| --- | --- |
| Windows PowerShell / CMD | `ssh root@your_server_ip` |
| macOS Terminal / Linux shell | `ssh root@your_server_ip` |
| Username is not `root` | `ssh ubuntu@your_server_ip` |
| macOS / Linux private key | `ssh -i /path/to/your-key.pem root@your_server_ip` |
| Windows private key | `ssh -i C:\Users\yourname\.ssh\server.pem root@your_server_ip` |

First connection often asks:

```text
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

If the IP is your server, type `yes` and press Enter. When typing a password, the terminal usually shows no stars and no cursor movement. Type the password and press Enter. If it fails with `Permission denied`, check the username, password, SSH key, or reset the password in the cloud console.

FinalShell is fine. It is an SSH client with a graphical connection manager:

| Field | Value |
| --- | --- |
| Host | `your_server_ip` |
| Port | `22` |
| Username | `root`, `ubuntu`, or the provider username |
| Authentication | Password or private key |

After connecting, run the same Linux commands in the FinalShell terminal.

CMD, PowerShell, macOS Terminal, Linux shell, and FinalShell all connect to the same server-side Linux shell, so the later commands are the same.

### 2.4 First Server Initialization

As root or a sudo-capable user:

```bash
apt update
apt upgrade -y
```

If you are not root:

```bash
sudo apt update
sudo apt upgrade -y
```

Create a dedicated runtime user:

```bash
adduser deploy
usermod -aG sudo deploy
su - deploy
```

If prompted for a new password, set one. Password input not echoing is normal.

## 3. Install System Dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git nginx ffmpeg curl ufw ca-certificates gnupg
```

Enable a basic firewall:

```bash
sudo ufw allow OpenSSH
sudo ufw allow "Nginx Full"
sudo ufw enable
sudo ufw status
```

Confirm SSH is allowed before `sudo ufw enable`, otherwise you can lock yourself out.

## 4. Prepare the Project Directory

Example path:

```bash
sudo mkdir -p /opt/video-meeting
sudo chown deploy:deploy /opt/video-meeting
cd /opt/video-meeting
```

Deploy from Git:

```bash
git clone https://gitee.com/jerryhqx/video-meeting.git .
# Choose GitHub if needed based on network access or hosting preference:
# git clone https://github.com/jerryhuang392diandi/video-meeting.git .
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn eventlet
```

Private repositories need SSH key or token setup.

## 5. Configure Environment Variables

Write `/opt/video-meeting/.env` with EOF:

```bash
cat <<'EOF' > /opt/video-meeting/.env
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=sqlite:////opt/video-meeting/instance/app.db

PUBLIC_SCHEME=https
PUBLIC_HOST=meeting.example.com

LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=replace-with-livekit-api-key
LIVEKIT_API_SECRET=replace-with-livekit-api-secret

ADMIN_USERNAME=root
ADMIN_PASSWORD=replace-with-strong-admin-password

SESSION_COOKIE_SECURE=1
REMEMBER_COOKIE_SECURE=1
SESSION_COOKIE_SAMESITE=Lax
REMEMBER_COOKIE_SAMESITE=Lax
EOF

chmod 600 /opt/video-meeting/.env
```

Generate a `SECRET_KEY`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Configuration:

| Setting | Meaning | Required |
| --- | --- | --- |
| `SECRET_KEY` | Flask session signing secret; keep it stable | Yes |
| `DATABASE_URL` | SQLAlchemy database URL; SQLite by default | No |
| `PUBLIC_SCHEME` | Public scheme; use `https` online | Yes |
| `PUBLIC_HOST` | Public hostname without `https://` | Yes |
| `LIVEKIT_URL` | Browser-facing LiveKit `wss://...` URL | Yes |
| `LIVEKIT_API_KEY` | Backend key for signing LiveKit tokens | Yes |
| `LIVEKIT_API_SECRET` | Backend secret for signing LiveKit tokens | Yes |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Initial admin account | Recommended |
| `SESSION_COOKIE_SECURE` / `REMEMBER_COOKIE_SECURE` | Send cookies over HTTPS only | Recommended for HTTPS |

Notes:

- Do not commit `.env`.
- Restart `video-meeting` after changing `.env`.
- If LiveKit values are missing, room pages intentionally return `503`.
- Runtime data lives under `instance/`; include it in backups.

## 6. systemd Service

Write the service file:

```bash
cat <<'EOF' | sudo tee /etc/systemd/system/video-meeting.service
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
EOF
```

Start and enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable video-meeting
sudo systemctl start video-meeting
sudo systemctl status video-meeting
```

Key points:

- `EnvironmentFile=/opt/video-meeting/.env` loads production variables.
- `--worker-class eventlet` supports Flask-SocketIO long connections.
- Keep `--workers 1`; current online room state is in process memory.
- `--bind 127.0.0.1:8000` must match Nginx `proxy_pass`.

Logs:

```bash
journalctl -u video-meeting -n 100 --no-pager
journalctl -u video-meeting -f
```

After editing `.service`:

```bash
sudo systemctl daemon-reload
sudo systemctl restart video-meeting
```

After editing only `.env`, restart the service; `daemon-reload` is not needed.

Confirm the local app responds:

```bash
curl -I http://127.0.0.1:8000
```

## 7. LiveKit Options

This app uses LiveKit for media. Flask validates meeting permission and issues a token; the browser connects directly to `LIVEKIT_URL`.

### 7.1 LiveKit Cloud

Best for first deployment:

1. Open https://cloud.livekit.io/ and create a project.
2. Copy the Server URL, usually `wss://xxx.livekit.cloud`.
3. Create an API key and API secret.
4. Put them into `/opt/video-meeting/.env`.
5. Restart the app:

```bash
sudo systemctl restart video-meeting
sudo systemctl status video-meeting
```

Connection shape:

```text
Browser -> https://meeting.example.com -> Nginx -> Flask
Browser -> wss://your-project.livekit.cloud -> LiveKit Cloud
```

So Nginx does not need a `livekit.cloud` config when using LiveKit Cloud.

### 7.2 Self-Hosted LiveKit: When to Use It

Self-host LiveKit only when you need:

- No hosted LiveKit Cloud.
- Private or intranet deployment.
- Full control over media region, ports, logs, and cost.

It is more operational work. Get the app working with LiveKit Cloud first, then replace the media service.

### 7.3 Self-Hosted LiveKit: Domains and Ports

Use separate domains:

| Domain | Purpose | Points to |
| --- | --- | --- |
| `meeting.example.com` | Flask website | Flask/Nginx server |
| `livekit.example.com` | LiveKit signaling and WSS | LiveKit server |

For a small demo both domains can point to one server. For production, separate servers are often cleaner. Consider these ports:

| Port | Protocol | Purpose |
| --- | --- | --- |
| `443` | TCP | LiveKit WSS / HTTPS entry |
| `7881` | TCP | WebRTC TCP fallback, depending on LiveKit config |
| `50000-60000` | UDP | WebRTC UDP media range, depending on LiveKit config |
| `3478` | UDP/TCP | TURN/STUN if TURN is enabled |
| `5349` | TCP | TURN TLS if TURN TLS is enabled |

Use your actual LiveKit config and official docs as the final source. Open ports in both the cloud security group and `ufw`.

### 7.4 Self-Hosted LiveKit: Docker Compose Example

Install Docker:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker deploy
newgrp docker
docker --version
```

Prepare the directory:

```bash
sudo mkdir -p /opt/livekit
sudo chown deploy:deploy /opt/livekit
cd /opt/livekit
```

Write LiveKit config. Replace the key and secret:

```bash
cat <<'EOF' > /opt/livekit/livekit.yaml
port: 7880
bind_addresses:
  - ""
rtc:
  tcp_port: 7881
  port_range_start: 50000
  port_range_end: 60000
  use_external_ip: true
keys:
  replace-livekit-api-key: replace-livekit-api-secret
logging:
  level: info
EOF
```

Write Docker Compose:

```bash
cat <<'EOF' > /opt/livekit/docker-compose.yml
services:
  livekit:
    image: livekit/livekit-server:latest
    command: --config /etc/livekit.yaml
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./livekit.yaml:/etc/livekit.yaml:ro
EOF
```

Start it:

```bash
docker compose up -d
docker compose logs -f livekit
```

Open LiveKit media ports:

```bash
sudo ufw allow 7881/tcp
sudo ufw allow 50000:60000/udp
sudo ufw status
```

If the same Nginx proxies LiveKit WSS, create a separate `livekit.example.com` site. This only proxies signaling; UDP/TCP media ports still need direct access.

```bash
cat <<'EOF' | sudo tee /etc/nginx/sites-available/livekit
server {
    listen 80;
    server_name livekit.example.com;

    location / {
        proxy_pass http://127.0.0.1:7880;
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
EOF

sudo ln -s /etc/nginx/sites-available/livekit /etc/nginx/sites-enabled/livekit
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d livekit.example.com
```

Then update Flask `.env`:

```env
LIVEKIT_URL=wss://livekit.example.com
LIVEKIT_API_KEY=replace-livekit-api-key
LIVEKIT_API_SECRET=replace-livekit-api-secret
```

Restart:

```bash
sudo systemctl restart video-meeting
```

### 7.5 Self-Hosted LiveKit Checklist

| Check | Expected |
| --- | --- |
| DNS | `livekit.example.com` points to the LiveKit server public IP |
| HTTPS/WSS | `https://livekit.example.com` has a trusted certificate |
| `LIVEKIT_URL` | `wss://livekit.example.com`, not `http://` |
| API key / secret | Exactly match LiveKit config and Flask `.env` |
| Cloud security group | Allows `443/tcp`, LiveKit TCP fallback, and UDP media ports |
| `ufw` | Allows the same ports as the cloud security group |
| NAT/public IP | LiveKit can discover or is told its public address |
| TURN | Add TURN when campus, corporate, or mobile networks fail |

## 8. Domain, Cloudflare, and DNS

A public deployment needs a domain users can open, such as `meeting.example.com`.

### 8.1 Plain DNS

Add an A record:

```text
Type: A
Name: meeting
Value: your_server_ip
TTL: Auto or 600
```

Check it:

```bash
getent hosts meeting.example.com
```

If self-hosting LiveKit, add another record:

```text
Type: A
Name: livekit
Value: livekit_server_ip
TTL: Auto or 600
```

### 8.2 Cloudflare

Dashboard: https://dash.cloudflare.com/

Recommended flow:

1. Add the site to Cloudflare.
2. Change nameservers at the domain registrar as instructed.
3. Add an `A` record: `meeting -> your_server_ip`.
4. Start with `DNS only`.
5. After Nginx and HTTPS work, consider enabling `Proxied`.
6. Use SSL/TLS mode `Full (strict)`; the origin server still needs a valid certificate.

If LiveKit Cloud uses `*.livekit.cloud`, do not configure it in Cloudflare. Browsers connect directly to LiveKit Cloud.

If self-hosting `livekit.example.com`, start with DNS only. Normal Cloudflare HTTP proxy does not proxy WebRTC UDP media ports.

## 9. Nginx Reverse Proxy

Nginx listens on public `80/443` and forwards to Gunicorn on `127.0.0.1:8000`. It must preserve WebSocket headers for Socket.IO.

### 9.1 WebSocket Map

Create the Nginx WebSocket map:

```bash
cat <<'EOF' | sudo tee /etc/nginx/conf.d/websocket-map.conf
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}
EOF
```

### 9.2 Create the Site Config

Start with HTTP so Certbot can validate the domain:

```bash
cat <<'EOF' | sudo tee /etc/nginx/sites-available/video-meeting
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
EOF
```

Enable it:

```bash
sudo ln -s /etc/nginx/sites-available/video-meeting /etc/nginx/sites-enabled/video-meeting
sudo nginx -t
sudo systemctl reload nginx
```

If the symlink already exists, it was enabled before. Inspect before changing it.

### 9.3 Enable and Check Syntax

Common checks:

```bash
sudo nginx -t
sudo systemctl reload nginx
curl -I http://meeting.example.com
```

`client_max_body_size 150m` is intentionally larger than the current 120 MB video attachment limit.

### 9.4 How to Tell Whether Nginx Works

```bash
curl -I http://127.0.0.1:8000
curl -I http://meeting.example.com
sudo tail -n 80 /var/log/nginx/error.log
```

Order of diagnosis:

- If `127.0.0.1:8000` fails, check systemd/Gunicorn/Flask.
- If `127.0.0.1:8000` works but the domain fails, check Nginx, DNS, security group, and firewall.
- If pages open but Socket.IO fails, check `Upgrade` and `Connection` proxy headers.

### 9.5 Nginx and LiveKit

With LiveKit Cloud:

```text
meeting.example.com -> Nginx -> Flask
your-project.livekit.cloud -> LiveKit Cloud
```

With self-hosted LiveKit:

```text
meeting.example.com -> Nginx -> Flask
livekit.example.com -> LiveKit WSS entry
LiveKit UDP/TCP media ports -> direct access to LiveKit
```

Proxying `livekit.example.com` HTTPS is not enough for WebRTC. Media UDP/TCP ports still need to be open.

## 10. HTTPS Certificate

Certbot recommends snap installation for Ubuntu + Nginx:

```bash
sudo snap install core
sudo snap refresh core
sudo apt remove -y certbot
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
```

If the last line says the file exists, `certbot` is already available.

### 10.1 Let Certbot Edit Nginx Automatically

Simplest path:

```bash
sudo certbot --nginx -d meeting.example.com
sudo certbot renew --dry-run
```

Then check:

```bash
curl -I https://meeting.example.com
```

### 10.2 Manual HTTPS Nginx Config

If you prefer to write Nginx yourself, first request the certificate:

```bash
sudo certbot certonly --nginx -d meeting.example.com
```

Then write a complete HTTPS config:

```bash
cat <<'EOF' | sudo tee /etc/nginx/sites-available/video-meeting
server {
    listen 80;
    server_name meeting.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name meeting.example.com;

    ssl_certificate /etc/letsencrypt/live/meeting.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/meeting.example.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    client_max_body_size 150m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_read_timeout 3600;
        proxy_send_timeout 3600;
    }
}
EOF

sudo nginx -t
sudo systemctl reload nginx
sudo certbot renew --dry-run
```

Important points:

- Port `80` redirects to HTTPS.
- `443 ssl http2` serves real traffic.
- `X-Forwarded-Proto https` tells Flask the external scheme.
- WebSocket headers remain present.
- Certificate paths must match your domain.

After HTTPS is ready, keep `.env` aligned:

```env
PUBLIC_SCHEME=https
SESSION_COOKIE_SECURE=1
REMEMBER_COOKIE_SECURE=1
```

## 11. First Online Verification

Command-line checks:

```bash
curl -I http://127.0.0.1:8000
curl -I http://meeting.example.com
curl -I https://meeting.example.com
grep LIVEKIT /opt/video-meeting/.env
```

Browser checks:

- Home, login, and registration pages are reachable.
- The admin account can log in.
- Normal users can register, log in, and create meetings.
- Room pages do not return `503` because of missing LiveKit config.
- Two devices can join the same meeting and see remote media on first join.
- Chat, attachment upload, preview, and download permissions work.
- Camera, microphone, and screen sharing can start and stop.
- `/admin` opens and common admin actions work.

## 12. Three-Side Code Changes and Git Version Control

There are usually three sides:

| Side | Role |
| --- | --- |
| Local computer | Edit code, run `python app.py`, test locally |
| Git platform | Stores versions and acts as the sync center |
| Cloud server | Pulls confirmed code and restarts the service |

Recommended flow:

```text
Edit locally -> test locally -> git commit -> git push -> SSH to server -> git pull -> restart systemd
```

Local commit:

```bash
git status
python check_i18n.py
python -m py_compile app.py translations.py
git add .
git commit -m "Improve deployment documentation"
git push origin main
```

Server update:

```bash
ssh deploy@your_server_ip
cd /opt/video-meeting
git status
git pull origin main
source /opt/video-meeting/venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart video-meeting
sudo systemctl status video-meeting
```

If `git status` on the server shows local modifications, do not force `git pull`. Someone may have edited files directly on the server.

## 13. Standard Server Update

Normal update:

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

Code-only update:

```bash
cd /opt/video-meeting
git pull origin main
sudo systemctl restart video-meeting
sudo systemctl status video-meeting
```

After changing Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

After changing systemd:

```bash
sudo systemctl daemon-reload
sudo systemctl restart video-meeting
sudo systemctl status video-meeting
```

## 14. Backup and Migration

SQLite and uploads live under `instance/`:

```bash
cd /opt/video-meeting
tar -czf /tmp/video-meeting-instance-$(date +%F).tar.gz instance
cp /opt/video-meeting/.env /tmp/video-meeting-env-$(date +%F)
```

Migration:

1. Deploy code and dependencies on the new server.
2. Copy the old `instance/`.
3. Copy or recreate `.env`.
4. Point DNS to the new server IP.
5. Restart systemd and run a two-device room test.

## 15. Local Commit Quick Reference

```bash
git status
git pull --rebase origin main
python check_i18n.py
git add .
git commit -m "Improve deployment documentation"
git push origin main
```

Do not commit `venv/`, `instance/`, `.env`, databases, uploads, recordings, archives, or IDE caches.

## 16. Common Issues

### Room Returns 503

```bash
grep LIVEKIT /opt/video-meeting/.env
journalctl -u video-meeting -n 100 --no-pager
sudo systemctl restart video-meeting
```

Confirm:

- `LIVEKIT_URL` is a browser-reachable `wss://...` URL.
- `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` are correct.
- systemd loads `/opt/video-meeting/.env`.
- The service was restarted after `.env` changed.

### Page Opens but Socket.IO Fails

Check Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
grep -R "Upgrade\\|connection_upgrade" /etc/nginx/conf.d /etc/nginx/sites-available
journalctl -u video-meeting -f
```

Required directives:

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection $connection_upgrade;
proxy_read_timeout 3600;
```

### Page Opens but Remote Media Is Missing

Check first:

- Whether the browser allowed camera and microphone.
- Whether LiveKit Cloud or self-hosted LiveKit is reachable.
- Whether `PUBLIC_HOST` / `PUBLIC_SCHEME` match the real public address.
- If self-hosting LiveKit, whether cloud security group and `ufw` allow media ports.
- Whether only one network fails. If campus/corporate/mobile networks fail, consider TURN.

### Attachment Upload Fails

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

```bash
sudo systemctl status video-meeting
journalctl -u video-meeting -n 100 --no-pager
ss -lntp | grep 8000
sudo tail -n 80 /var/log/nginx/error.log
```

This usually means the app service is down, Gunicorn failed, or Nginx `proxy_pass` does not match systemd `--bind`.

### `.env` Changes Do Not Apply

```bash
sudo systemctl restart video-meeting
journalctl -u video-meeting -n 50 --no-pager
```

If `/etc/systemd/system/video-meeting.service` changed:

```bash
sudo systemctl daemon-reload
sudo systemctl restart video-meeting
```

### SSH Login Issues

| Symptom | Action |
| --- | --- |
| Password input shows nothing | Normal SSH behavior; type it and press Enter |
| `Permission denied` | Check username, password, key, or reset credentials in the cloud console |
| `Connection timed out` | Check public IP, port 22, security group, and local network firewall |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | Common after reinstalling a server or reusing an IP; verify safety, then remove the old `known_hosts` entry |

## 17. References

This guide combines the current project code with these official or reliable documents:

| Topic | Docs |
| --- | --- |
| Flask-SocketIO + Gunicorn | [Flask-SocketIO Deployment](https://flask-socketio.readthedocs.io/en/latest/deployment.html) |
| Gunicorn arguments | [Gunicorn Settings](https://docs.gunicorn.org/en/stable/settings.html) |
| Nginx WebSocket | [Nginx WebSocket proxying](https://nginx.org/en/docs/http/websocket.html) |
| Nginx HTTPS | [Configuring HTTPS servers](https://nginx.org/en/docs/http/configuring_https_servers.html) |
| Nginx basics | [Beginner's Guide](https://nginx.org/en/docs/beginners_guide.html) |
| Certbot / Nginx | [Certbot install guide](https://eff-certbot.readthedocs.io/en/stable/install.html) |
| Let's Encrypt | [Let's Encrypt Documentation](https://letsencrypt.org/docs/) |
| systemd environment | [systemd.exec EnvironmentFile](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html) |
| LiveKit self-hosting | [LiveKit self-hosting deployment](https://docs.livekit.io/home/self-hosting/deployment/) |
| LiveKit VM deployment | [LiveKit VM deployment](https://docs.livekit.io/home/self-hosting/vm/) |
| LiveKit Docker | [LiveKit Docker image](https://github.com/livekit/livekit) |
| LiveKit Cloud | [LiveKit Cloud](https://cloud.livekit.io/) |
| Cloudflare DNS | [Create DNS records](https://developers.cloudflare.com/dns/manage-dns-records/how-to/create-dns-records/) |
| Cloudflare SSL | [Full (strict) SSL mode](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/) |
| Windows OpenSSH | [Microsoft OpenSSH client](https://learn.microsoft.com/windows-server/administration/openssh/openssh_install_firstuse) |
| macOS SSH | [Apple remote login guide](https://support.apple.com/guide/mac-help/allow-a-remote-computer-to-access-your-mac-mchlp1066/mac) |
| Ubuntu SSH | [Ubuntu OpenSSH Server](https://documentation.ubuntu.com/server/how-to/security/openssh-server/) |
| Mainland China ICP filing | [MIIT ICP/IP/domain filing system](https://beian.miit.gov.cn/) |
| Alibaba Cloud ICP filing | [Alibaba Cloud ICP filing](https://help.aliyun.com/zh/icp-filing/) |
| Tencent Cloud ICP filing | [Tencent Cloud ICP filing](https://cloud.tencent.com/document/product/243) |
| Huawei Cloud ICP filing | [Huawei Cloud ICP filing](https://support.huaweicloud.com/icp/) |
| FinalShell | [FinalShell official site](https://www.hostbuf.com/) |

## 18. Operations to Avoid

- Do not run production with the Flask debug server.
- Do not start multiple Gunicorn workers to "improve performance" unless runtime room state has moved to shared storage.
- Do not habitually run `git clean -fd` in production directories.
- Do not repeatedly restart services without reading logs.
- Do not commit `.env`, databases, uploads, or recording files.
- Do not only test page load; room media requires a two-client check.
