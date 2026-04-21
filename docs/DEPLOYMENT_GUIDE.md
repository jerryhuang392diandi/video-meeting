# 部署与更新手册

[中文](DEPLOYMENT_GUIDE.md) | [English](DEPLOYMENT_GUIDE.en.md)

这份文档给出从购买 Linux 云服务器到上线运行的完整路径。示例默认使用 Ubuntu 22.04 / 24.04、Nginx、systemd、Gunicorn + eventlet、SQLite 和外部 LiveKit 服务。路径、域名和服务名可以按实际情况替换。

## 1. 推荐部署架构

```text
用户浏览器
  -> https://meeting.example.com
  -> Cloudflare DNS 或普通 DNS
  -> Nginx 反向代理，负责 HTTPS、静态连接和 WebSocket 转发
  -> 127.0.0.1:8000 上的 Gunicorn + eventlet
  -> Flask + Flask-SocketIO 应用
  -> LiveKit Cloud 或自建 LiveKit SFU
```

当前应用的在线房间状态主要保存在单进程内存中，所以默认按单实例部署。不要简单启动多个 Gunicorn worker 或多台应用服务器来横向扩展，否则 `rooms`、`sid_to_user`、聊天历史和屏幕共享状态会不一致。

## 2. 购买服务器与基础准备

云厂商可以选择阿里云、腾讯云、华为云、AWS、Azure、DigitalOcean、Vultr 等。课程展示或小规模演示推荐：

| 项 | 建议 |
| --- | --- |
| 系统 | Ubuntu 22.04 LTS 或 24.04 LTS |
| CPU / 内存 | 2 vCPU / 2 GB 起步，演示人数较多建议 4 GB |
| 磁盘 | 30 GB 起步，附件和录屏多时单独扩容 |
| 入站端口 | `22`、`80`、`443` |
| 域名 | `meeting.example.com` 这类子域名 |
| Python 生产运行依赖 | `requirements.txt` 加服务器侧 `gunicorn eventlet` |

云厂商控制台里要做两件事：

1. 在安全组或防火墙中放行 `80/tcp` 和 `443/tcp`。
2. SSH 端口只对自己的公网 IP 开放更安全；如果做不到，至少使用强密码或 SSH key。

首次登录服务器：

```bash
ssh root@your_server_ip
apt update
apt upgrade -y
timedatectl set-timezone Asia/Shanghai
```

创建专用运行用户，避免长期用 root 跑应用：

```bash
adduser deploy
usermod -aG sudo deploy
su - deploy
```

## 3. 安装系统依赖

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git nginx ffmpeg curl ufw
```

说明：

- `python3-venv` 用于创建虚拟环境。
- `nginx` 负责公网入口、HTTPS 和 WebSocket 反向代理。
- `ffmpeg` 用于把浏览器录制出的 WebM 转封装为 MP4；不需要录屏导出时可以不装。
- `ufw` 是 Ubuntu 常用防火墙工具。

启用基础防火墙：

```bash
sudo ufw allow OpenSSH
sudo ufw allow "Nginx Full"
sudo ufw enable
sudo ufw status
```

## 4. 准备项目目录

示例把项目放在 `/opt/video-meeting`：

```bash
sudo mkdir -p /opt/video-meeting
sudo chown deploy:deploy /opt/video-meeting
cd /opt/video-meeting
```

从 Git 仓库部署：

```bash
git clone https://github.com/your-name/video-meeting-replace.git .
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn eventlet
```

如果你是把项目压缩包上传到服务器，先解压到 `/opt/video-meeting`，再执行虚拟环境和依赖安装命令。

`gunicorn` 和 `eventlet` 只用于 Linux 服务器上的生产运行；Windows 本地开发仍按根 README 使用 `python app.py`。

## 5. 配置环境变量

建议用 `/opt/video-meeting/.env` 保存生产配置，并在 systemd 服务里加载。先创建文件：

```bash
nano /opt/video-meeting/.env
```

示例内容：

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

生成 `SECRET_KEY` 的一种方式：

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

注意：

- `SECRET_KEY` 必须稳定，不能每次重启都变化，否则用户登录态会失效。
- `PUBLIC_HOST` 必须是不带协议的域名，例如 `meeting.example.com`。
- `PUBLIC_SCHEME` 使用 HTTPS 时填 `https`。
- LiveKit 缺失时，房间页会按设计返回 `503`，这是配置问题，不是模板问题。
- SQLite 文件和上传文件在 `instance/` 下，生产环境备份时必须包含这个目录。

## 6. LiveKit 配置选择

### 6.1 使用 LiveKit Cloud

最省事的方式是使用 LiveKit Cloud：

1. 创建 LiveKit Cloud 项目。
2. 获取 server URL，通常是 `wss://...livekit.cloud`。
3. 创建 API key 和 API secret。
4. 把三项写入 `.env`：`LIVEKIT_URL`、`LIVEKIT_API_KEY`、`LIVEKIT_API_SECRET`。

应用只负责签发 token，浏览器会直接连接 LiveKit。Nginx 不需要代理 LiveKit Cloud。

### 6.2 自建 LiveKit

自建 LiveKit 适合需要完全控制媒体服务的场景，但复杂度更高。至少要处理：

- LiveKit 服务进程或容器部署。
- LiveKit 自己的 HTTPS / WSS 入口。
- UDP 媒体端口、TCP fallback、TURN/ICE 可达性。
- 云厂商安全组和系统防火墙放行 LiveKit 所需端口。
- LiveKit API key / secret 与 Flask `.env` 保持一致。

如果课程展示时间有限，建议先用 LiveKit Cloud 跑通主流程，再考虑自建。

## 7. 域名、Cloudflare 与 DNS

### 7.1 普通 DNS

在域名服务商添加 A 记录：

```text
类型: A
主机记录: meeting
值: your_server_ip
TTL: 自动或 600
```

等待解析生效：

```bash
dig meeting.example.com
```

### 7.2 使用 Cloudflare

如果域名托管在 Cloudflare：

1. 添加 `A` 记录，名称填 `meeting`，IPv4 地址填服务器公网 IP。
2. 代理状态可以先设为 DNS only，确认服务器部署正常后再打开 Proxied。
3. SSL/TLS 模式建议使用 `Full (strict)`，并在服务器上安装有效证书。
4. 如果先用 Cloudflare 代理，确认 WebSocket 没有被拦截；本项目 Socket.IO 需要 WebSocket 或轮询连接稳定可用。

课程演示最稳妥路径：

1. 先 DNS only + Nginx + Let's Encrypt 跑通。
2. 再打开 Cloudflare Proxied。
3. 打开后重新测试登录、入房、聊天和双端媒体。

## 8. Nginx 反向代理

创建站点配置：

```bash
sudo nano /etc/nginx/sites-available/video-meeting
```

先使用 HTTP 配置，拿到证书后再自动升级到 HTTPS：

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
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600;
        proxy_send_timeout 3600;
    }
}
```

启用站点：

```bash
sudo ln -s /etc/nginx/sites-available/video-meeting /etc/nginx/sites-enabled/video-meeting
sudo nginx -t
sudo systemctl reload nginx
```

`client_max_body_size 150m` 要大于视频附件限制。当前项目视频附件上限是 120 MB，所以这里给 150 MB。

## 9. HTTPS 证书

使用 Let's Encrypt：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d meeting.example.com
```

验证自动续期：

```bash
sudo certbot renew --dry-run
```

拿到证书后确认 `.env` 使用：

```env
PUBLIC_SCHEME=https
SESSION_COOKIE_SECURE=1
REMEMBER_COOKIE_SECURE=1
```

如果使用 Cloudflare `Full (strict)`，服务器侧仍然需要有效证书，Let's Encrypt 即可。

## 10. systemd 服务

安装依赖后，创建服务文件：

```bash
sudo nano /etc/systemd/system/video-meeting.service
```

推荐配置：

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

关键点：

- `--worker-class eventlet` 用于配合 Flask-SocketIO。
- `--workers 1` 是有意的，当前内存房间状态不适合多 worker。
- 只绑定 `127.0.0.1:8000`，公网入口交给 Nginx。

启动并设置开机自启：

```bash
sudo systemctl daemon-reload
sudo systemctl enable video-meeting
sudo systemctl start video-meeting
sudo systemctl status video-meeting
```

查看日志：

```bash
journalctl -u video-meeting -n 100 --no-pager
journalctl -u video-meeting -f
```

## 11. 首次上线验证

先检查本机服务：

```bash
curl -I http://127.0.0.1:8000
curl -I http://meeting.example.com
curl -I https://meeting.example.com
```

浏览器验证：

- 首页、登录页、注册页可访问。
- 管理员账号可以登录。
- 普通用户可以注册、登录、创建会议。
- 房间页不会因为缺少 LiveKit 配置返回 `503`。
- 两个设备加入同一会议，首次加入即可看到远端媒体。
- 聊天、附件上传、附件预览和下载权限可用。
- 摄像头、麦克风、屏幕共享开始和停止可用。
- `/admin` 能打开，常用管理动作正常。

## 12. 标准服务器更新

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

说明：

- 没有依赖变化时可以跳过 `pip install -r requirements.txt`。
- 如果服务器虚拟环境里已经装过 `gunicorn eventlet`，后续普通代码更新不需要重复安装。
- 不要默认执行 `git clean -fd`，它会删除未跟踪文件，容易误删运行时内容。
- 重启后先看 `systemctl status`，再根据日志继续排查。

只更新代码：

```bash
cd /opt/video-meeting
git pull origin main
sudo systemctl restart video-meeting
sudo systemctl status video-meeting
```

修改 systemd 后：

```bash
sudo systemctl daemon-reload
sudo systemctl restart video-meeting
sudo systemctl status video-meeting
```

修改 Nginx 后：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 13. 备份与迁移

SQLite 和上传文件默认在 `instance/` 下，至少备份：

```bash
cd /opt/video-meeting
tar -czf /tmp/video-meeting-instance-$(date +%F).tar.gz instance
```

迁移服务器时：

1. 新服务器部署代码和依赖。
2. 拷贝旧服务器 `instance/`。
3. 拷贝 `.env`，或重新生成但保持 `DATABASE_URL`、LiveKit、域名和管理员配置正确。
4. 更新 DNS 到新服务器 IP。
5. 重启 systemd 服务并做双端入房验证。

## 14. 本地提交流程

```bash
git status
git pull --rebase origin main
git add .
git commit -m "Improve deployment documentation"
git push origin main
```

提交前检查：

- 不要提交 `instance/`、数据库、上传文件、临时录屏或本地虚拟环境。
- 如果改了模板文案，运行 `python check_i18n.py`。
- 如果改了部署行为，同步更新根 README、部署指南和稳定性说明。

## 15. 常见问题

### 房间返回 503

优先检查：

```bash
grep LIVEKIT /opt/video-meeting/.env
journalctl -u video-meeting -n 100 --no-pager
```

确认：

- `LIVEKIT_URL` 是浏览器可访问的 `wss://...` 地址。
- `LIVEKIT_API_KEY` 和 `LIVEKIT_API_SECRET` 正确。
- systemd 服务确实加载了 `/opt/video-meeting/.env`。
- 修改 `.env` 后已经重启 `video-meeting`。

### 页面能打开但 Socket.IO 连接失败

优先检查 Nginx 是否保留了 WebSocket 头：

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
proxy_read_timeout 3600;
```

然后检查：

```bash
sudo nginx -t
sudo systemctl reload nginx
journalctl -u video-meeting -f
```

### 页面能打开但没有远端媒体

优先检查：

- 浏览器是否允许摄像头和麦克风。
- LiveKit 服务是否可达。
- `PUBLIC_HOST` / `PUBLIC_SCHEME` 是否与真实访问地址一致。
- Cloudflare 代理打开后是否影响 WebSocket 或 LiveKit 域名访问。
- 是否只有单端设备异常，还是双端都失败。

### 附件上传失败

检查 Nginx 上传限制和目录权限：

```bash
grep client_max_body_size /etc/nginx/sites-available/video-meeting
ls -ld /opt/video-meeting/instance
sudo chown -R deploy:deploy /opt/video-meeting/instance
```

### 录屏导出 MP4 失败

```bash
which ffmpeg
ffmpeg -version
journalctl -u video-meeting -n 100 --no-pager
```

没有 `ffmpeg` 时，应用仍可保留浏览器原始录制结果，但 WebM 转 MP4 会失败。

### 502 Bad Gateway

通常是应用服务没启动或 Nginx 代理端口不一致：

```bash
sudo systemctl status video-meeting
journalctl -u video-meeting -n 100 --no-pager
ss -lntp | grep 8000
```

### 修改 .env 后不生效

systemd 不会自动重新读取 `.env`，需要：

```bash
sudo systemctl restart video-meeting
```

如果改了服务文件本身，还需要：

```bash
sudo systemctl daemon-reload
sudo systemctl restart video-meeting
```

## 16. 不建议的操作

- 不要把生产服务跑在 Flask debug server 上。
- 不要启动多个 Gunicorn worker 来“提升性能”，除非先把房间运行态迁移到共享存储。
- 不要在生产目录里习惯性执行 `git clean -fd`。
- 不要反复重启服务但不看日志。
- 不要把运行时数据库、上传文件和仓库文件混在一起提交。
- 不要只测页面加载，房间媒体必须做双端验证。
