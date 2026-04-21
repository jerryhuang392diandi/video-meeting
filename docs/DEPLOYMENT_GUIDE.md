# 部署与更新手册

[中文](DEPLOYMENT_GUIDE.md) | [English](DEPLOYMENT_GUIDE.en.md)

这份文档给出从购买 Linux 云服务器到上线运行的完整路径。示例默认使用 Ubuntu 22.04 / 24.04、Nginx、systemd、Gunicorn + eventlet、SQLite 和外部 LiveKit 服务。路径、域名和服务名可以按实际情况替换。

## 0. 如何阅读命令块

本文里的命令默认在服务器 Linux shell 中执行，除非特别说明。命令块下面会解释：

- 每一行在做什么。
- 哪些值必须替换成你的真实值。
- 哪些参数可以按服务器规格或项目需求自定义。

示例里统一使用这些占位值：

| 占位值 | 含义 | 你需要替换成 |
| --- | --- | --- |
| `meeting.example.com` | 会议系统域名 | 你自己的域名或子域名 |
| `your_server_ip` | 云服务器公网 IP | 云厂商控制台显示的公网 IP |
| `/opt/video-meeting` | 项目部署目录 | 可保留，也可换成自己的目录 |
| `deploy` | Linux 运行用户 | 可保留，也可换成自己的用户名 |
| `video-meeting` | systemd 服务名 | 可保留，也可换成更短的服务名 |
| `main` | Git 默认分支 | 你的实际部署分支 |

如果只是课程展示，建议尽量保持示例里的目录、用户名和服务名，减少排障变量。

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

命令解释：

| 命令 | 含义 | 可自定义项 |
| --- | --- | --- |
| `ssh root@your_server_ip` | 用 root 登录新服务器 | 把 `your_server_ip` 换成公网 IP；如果云厂商提供其他用户名，也要替换 `root` |
| `apt update` | 更新软件包索引 | 不建议改 |
| `apt upgrade -y` | 升级已安装软件包，`-y` 表示自动确认 | 如果想逐项确认，可以去掉 `-y` |
| `timedatectl set-timezone Asia/Shanghai` | 设置服务器时区为中国上海 | 如果服务器面向其他地区，可换成 `UTC` 或其他时区 |

创建专用运行用户，避免长期用 root 跑应用：

```bash
adduser deploy
usermod -aG sudo deploy
su - deploy
```

命令解释：

| 命令 | 含义 | 可自定义项 |
| --- | --- | --- |
| `adduser deploy` | 创建普通用户 `deploy` | `deploy` 可以换成任意 Linux 用户名 |
| `usermod -aG sudo deploy` | 允许 `deploy` 使用 `sudo` 执行管理员命令 | 如果生产环境权限更严格，可不给 sudo，但后续命令要由管理员执行 |
| `su - deploy` | 切换到 `deploy` 用户 | 用户名要和前两行一致 |

## 3. 安装系统依赖

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git nginx ffmpeg curl ufw
```

命令和依赖解释：

| 项 | 含义 | 可自定义项 |
| --- | --- | --- |
| `sudo apt update` | 更新软件包索引 | 不建议省略 |
| `python3` | Python 运行环境 | Ubuntu 22.04 / 24.04 自带版本通常够用 |
| `python3-venv` | 创建项目虚拟环境 | 必装 |
| `python3-pip` | 安装 Python 包 | 必装 |
| `git` | 从 Git 仓库拉取代码 | 如果用压缩包上传，可以不装，但不推荐 |
| `nginx` | 公网入口、HTTPS、WebSocket 反向代理 | 可换成 Caddy/Apache，但本文只写 Nginx |
| `ffmpeg` | 录屏 WebM 转 MP4 | 不需要录屏导出时可不装 |
| `curl` | 命令行测试 HTTP 服务 | 建议安装 |
| `ufw` | Ubuntu 防火墙管理工具 | 可用云厂商安全组替代，但服务器本机防火墙仍建议开启 |

启用基础防火墙：

```bash
sudo ufw allow OpenSSH
sudo ufw allow "Nginx Full"
sudo ufw enable
sudo ufw status
```

命令解释：

| 命令 | 含义 | 可自定义项 |
| --- | --- | --- |
| `sudo ufw allow OpenSSH` | 放行 SSH，避免启用防火墙后把自己锁在外面 | 如果改了 SSH 端口，要改成对应端口 |
| `sudo ufw allow "Nginx Full"` | 放行 Nginx 的 HTTP `80` 和 HTTPS `443` | 如果不用 Nginx，可改为手动放行 `80/tcp`、`443/tcp` |
| `sudo ufw enable` | 启用防火墙 | 执行前必须确认 SSH 已放行 |
| `sudo ufw status` | 查看防火墙状态 | 用于确认规则生效 |

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

命令解释：

| 命令 | 含义 | 可自定义项 |
| --- | --- | --- |
| `sudo mkdir -p /opt/video-meeting` | 创建项目目录，`-p` 表示父目录不存在也一并创建 | 可把 `/opt/video-meeting` 换成 `/srv/video-meeting` 等目录 |
| `sudo chown deploy:deploy /opt/video-meeting` | 把目录所有者改成 `deploy` 用户 | 用户名要和前面创建的运行用户一致 |
| `git clone ... .` | 把仓库内容克隆到当前目录，末尾 `.` 表示不额外创建子目录 | URL 换成你的仓库地址；私有仓库要先配置 SSH key 或 token |
| `python3 -m venv venv` | 在项目目录创建 `venv` 虚拟环境 | 虚拟环境目录名可换，但 systemd 里要同步 |
| `source venv/bin/activate` | 激活虚拟环境 | 每次手动安装依赖前都要执行 |
| `pip install --upgrade pip` | 升级 pip | 可省略，但建议执行 |
| `pip install -r requirements.txt` | 安装项目通用依赖 | requirements 变更后要重新执行 |
| `pip install gunicorn eventlet` | 安装 Linux 生产运行依赖 | 如果后续写入专门的生产依赖文件，可改为安装该文件 |

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

配置项解释：

| 配置 | 含义 | 必填 | 可自定义项 |
| --- | --- | --- | --- |
| `SECRET_KEY` | Flask 会话签名密钥 | 是 | 换成随机长字符串；不要提交到 Git |
| `DATABASE_URL` | SQLAlchemy 数据库连接串 | 否 | SQLite 可保留；生产扩展可换 PostgreSQL/MySQL |
| `PUBLIC_SCHEME` | 对外访问协议 | 是 | HTTPS 上线填 `https`；本地 HTTP 才填 `http` |
| `PUBLIC_HOST` | 对外域名或主机名 | 是 | 填 `meeting.example.com`，不要带 `https://` |
| `LIVEKIT_URL` | 浏览器连接 LiveKit 的 URL | 是 | LiveKit Cloud 通常是 `wss://...livekit.cloud` |
| `LIVEKIT_API_KEY` | LiveKit 后端签发 token 用的 key | 是 | 从 LiveKit 控制台复制 |
| `LIVEKIT_API_SECRET` | LiveKit 后端签发 token 用的 secret | 是 | 从 LiveKit 控制台复制，不能泄露 |
| `ADMIN_USERNAME` | 初始管理员用户名 | 否 | 默认 `root`，建议生产明确设置 |
| `ADMIN_PASSWORD` | 初始管理员密码 | 否 | 强烈建议设置强密码；不设置会生成到 `instance/admin_password.txt` |
| `SESSION_COOKIE_SECURE` | 会话 cookie 仅 HTTPS 发送 | HTTPS 推荐 | HTTPS 部署填 `1` |
| `REMEMBER_COOKIE_SECURE` | 记住登录 cookie 仅 HTTPS 发送 | HTTPS 推荐 | HTTPS 部署填 `1` |
| `SESSION_COOKIE_SAMESITE` | 会话 cookie 跨站策略 | 推荐 | 常规同站部署用 `Lax` |
| `REMEMBER_COOKIE_SAMESITE` | 记住登录 cookie 跨站策略 | 推荐 | 常规同站部署用 `Lax` |

生成 `SECRET_KEY` 的一种方式：

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

命令解释：

| 部分 | 含义 | 可自定义项 |
| --- | --- | --- |
| `python3 -c "..."` | 执行一段 Python 单行代码 | 不需要改 |
| `secrets.token_urlsafe(48)` | 生成适合 URL/cookie 使用的随机密钥 | `48` 可以调大；不要调得太小 |

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

Socket.IO 需要 WebSocket 或长轮询。Nginx 官方 WebSocket 代理示例建议根据请求是否带 `Upgrade` 头来设置 `Connection`，所以这里先创建一个全局 map。

创建 WebSocket map：

```bash
sudo nano /etc/nginx/conf.d/websocket-map.conf
```

写入：

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}
```

配置解释：

| 指令 | 含义 | 可自定义项 |
| --- | --- | --- |
| `map $http_upgrade $connection_upgrade` | 根据客户端是否请求协议升级，生成一个变量 | 变量名可改，但站点配置里要同步 |
| `default upgrade;` | 有 `Upgrade` 头时，把连接升级为 WebSocket | 不建议改 |
| `'' close;` | 没有 `Upgrade` 头时，普通 HTTP 请求使用关闭连接语义 | 不建议改 |

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
        proxy_set_header Connection $connection_upgrade;
        proxy_read_timeout 3600;
        proxy_send_timeout 3600;
    }
}
```

配置项解释：

| 指令 | 含义 | 可自定义项 |
| --- | --- | --- |
| `listen 80;` | 监听 HTTP 端口，Certbot 会基于它申请证书 | 如果只内网测试可改端口，公网 HTTPS 不建议改 |
| `server_name meeting.example.com;` | 当前站点绑定域名 | 必须改成你的域名 |
| `client_max_body_size 150m;` | 允许上传的最大请求体 | 当前视频附件 120 MB，建议至少 150 MB；如调大应用限制，也要同步调大 |
| `proxy_pass http://127.0.0.1:8000;` | 转发到本机 Gunicorn 服务 | 端口要和 systemd `--bind` 保持一致 |
| `proxy_http_version 1.1;` | WebSocket 代理需要 HTTP/1.1 | 不建议改 |
| `proxy_set_header Host $host;` | 把原始域名传给 Flask | 不建议删 |
| `proxy_set_header X-Real-IP $remote_addr;` | 传递用户真实 IP | Cloudflare 后面还可进一步配置真实 IP 模块 |
| `proxy_set_header X-Forwarded-For ...` | 传递代理链路 IP | 不建议删 |
| `proxy_set_header X-Forwarded-Proto $scheme;` | 告诉后端外部请求协议 | HTTPS 跳转和安全 cookie 判断会用到 |
| `proxy_set_header Upgrade $http_upgrade;` | 传递 WebSocket 升级头 | Socket.IO 需要 |
| `proxy_set_header Connection $connection_upgrade;` | 根据 map 设置连接升级状态 | 与前面的 map 配套 |
| `proxy_read_timeout 3600;` | 后端长连接 3600 秒无数据才超时 | 可按需要调大或调小 |
| `proxy_send_timeout 3600;` | 向后端发送数据的超时时间 | 可按网络情况调整 |

启用站点：

```bash
sudo ln -s /etc/nginx/sites-available/video-meeting /etc/nginx/sites-enabled/video-meeting
sudo nginx -t
sudo systemctl reload nginx
```

`client_max_body_size 150m` 要大于视频附件限制。当前项目视频附件上限是 120 MB，所以这里给 150 MB。

## 9. HTTPS 证书

Certbot 官方对 Ubuntu + Nginx 推荐 snap 安装方式。先安装 snap 版 Certbot：

```bash
sudo snap install core
sudo snap refresh core
sudo apt remove -y certbot
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
```

命令解释：

| 命令 | 含义 | 可自定义项 |
| --- | --- | --- |
| `sudo snap install core` | 安装 snap 的核心运行包 | 已安装时会提示存在，可继续 |
| `sudo snap refresh core` | 更新 snap core | 不建议省略 |
| `sudo apt remove -y certbot` | 移除 apt 版 certbot，避免命令冲突 | 如果确定没装过 apt 版，可省略 |
| `sudo snap install --classic certbot` | 安装官方推荐的 snap 版 Certbot | 不建议改 |
| `sudo ln -s /snap/bin/certbot /usr/bin/certbot` | 让 `certbot` 命令在常规 PATH 下可用 | 如果提示文件已存在，说明已经配置过 |

申请并自动写入 Nginx HTTPS 配置：

```bash
sudo certbot --nginx -d meeting.example.com
```

命令解释：

| 参数 | 含义 | 可自定义项 |
| --- | --- | --- |
| `--nginx` | 让 Certbot 读取并修改 Nginx 配置 | 如果想手动配置证书，可用 `certonly --nginx` |
| `-d meeting.example.com` | 要申请证书的域名 | 必须替换成你的域名；多个域名可写多个 `-d` |

验证自动续期：

```bash
sudo certbot renew --dry-run
```

命令解释：

| 参数 | 含义 | 可自定义项 |
| --- | --- | --- |
| `renew` | 测试续期流程 | 不需要改 |
| `--dry-run` | 只演练，不真正替换证书 | 不建议去掉，正式续期由系统 timer 自动处理 |

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

配置项解释：

| 配置 | 含义 | 可自定义项 |
| --- | --- | --- |
| `Description` | 服务描述 | 可改成自己的项目名 |
| `After=network.target` | 网络就绪后再启动 | 一般保留 |
| `User=deploy` / `Group=deploy` | 用普通用户运行服务 | 要和前面创建的用户一致 |
| `WorkingDirectory=/opt/video-meeting` | 服务启动目录 | 要和项目目录一致 |
| `EnvironmentFile=/opt/video-meeting/.env` | 从 `.env` 加载环境变量 | 路径可改，但要保证文件存在且权限正确 |
| `Environment=PYTHONUNBUFFERED=1` | 让 Python 日志更及时输出到 journal | 建议保留 |
| `ExecStart=...gunicorn...` | 真正启动应用的命令 | 虚拟环境路径、端口、模块名可按项目调整 |
| `--worker-class eventlet` | 使用 eventlet worker 支持 Socket.IO 长连接 | Flask-SocketIO 官方支持；若改 gevent/threading 要重新验证 |
| `--workers 1` | 只启动 1 个 worker | 当前内存房间状态必须保持 1；不要随意调大 |
| `--bind 127.0.0.1:8000` | 只监听本机 8000 端口 | 端口可改，但 Nginx `proxy_pass` 要同步 |
| `app:app` | `app.py` 文件里的 Flask 应用对象 `app` | 如果重构文件名或对象名，需要同步修改 |
| `Restart=always` | 崩溃后自动重启 | 生产建议保留 |
| `RestartSec=5` | 崩溃后 5 秒再重启 | 可按需要调整 |
| `WantedBy=multi-user.target` | 允许开机自启 | 保留 |

启动并设置开机自启：

```bash
sudo systemctl daemon-reload
sudo systemctl enable video-meeting
sudo systemctl start video-meeting
sudo systemctl status video-meeting
```

命令解释：

| 命令 | 含义 | 可自定义项 |
| --- | --- | --- |
| `sudo systemctl daemon-reload` | 重新加载 systemd 服务文件 | 每次改 `.service` 后必须执行 |
| `sudo systemctl enable video-meeting` | 设置开机自启 | 服务名如果改了，这里也要改 |
| `sudo systemctl start video-meeting` | 启动服务 | 可用 `restart` 重启 |
| `sudo systemctl status video-meeting` | 查看服务状态和最近日志 | 排障第一步 |

查看日志：

```bash
journalctl -u video-meeting -n 100 --no-pager
journalctl -u video-meeting -f
```

命令解释：

| 命令 | 含义 | 可自定义项 |
| --- | --- | --- |
| `journalctl -u video-meeting -n 100 --no-pager` | 查看最近 100 行日志，不进入分页器 | `100` 可调大 |
| `journalctl -u video-meeting -f` | 实时跟踪日志 | 复现问题时使用 |

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
proxy_set_header Connection $connection_upgrade;
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

## 16. 参考依据

本文部署命令结合了项目当前代码和以下官方文档整理：

| 主题 | 官方文档 | 本文采用的要点 |
| --- | --- | --- |
| Flask-SocketIO + Gunicorn | [Flask-SocketIO Deployment](https://flask-socketio.readthedocs.io/en/latest/deployment.html) | Gunicorn 使用 `eventlet` worker，并保持 `-w 1` / `--workers 1` |
| Gunicorn 参数 | [Gunicorn Settings](https://docs.gunicorn.org/en/stable/settings.html) | `--bind`、`--workers`、`--worker-class` 的含义 |
| Nginx WebSocket | [Nginx WebSocket proxying](https://nginx.org/en/docs/http/websocket.html) | 显式转发 `Upgrade`，并使用 `map` 设置 `Connection` |
| Certbot | [Certbot install guide](https://eff-certbot.readthedocs.io/en/stable/install.html) | Ubuntu/Nginx 推荐使用 snap 版 Certbot |
| Cloudflare SSL | [Cloudflare Full (strict)](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/) | 使用 Full (strict) 时源站需要有效证书 |
| systemd 环境变量 | [systemd.exec EnvironmentFile](https://www.freedesktop.org/software/systemd/man/systemd.exec.html) | systemd 可通过 `EnvironmentFile=` 从文件加载环境变量 |

## 17. 不建议的操作

- 不要把生产服务跑在 Flask debug server 上。
- 不要启动多个 Gunicorn worker 来“提升性能”，除非先把房间运行态迁移到共享存储。
- 不要在生产目录里习惯性执行 `git clean -fd`。
- 不要反复重启服务但不看日志。
- 不要把运行时数据库、上传文件和仓库文件混在一起提交。
- 不要只测页面加载，房间媒体必须做双端验证。
