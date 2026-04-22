# 部署与更新手册

[中文](DEPLOYMENT_GUIDE.md) | [English](DEPLOYMENT_GUIDE.en.md)

这份文档按第一次上线的真实顺序写：先准备账号和服务器，再登录服务器，接着部署 Flask 应用、systemd、Nginx、HTTPS，最后配置 LiveKit。示例默认使用 Ubuntu 22.04 / 24.04、Nginx、systemd、Gunicorn + eventlet、SQLite 和 LiveKit Cloud 或自建 LiveKit。

## 先给零基础读者的结论

最稳妥的部署顺序是：

1. 本地先用 `python app.py` 跑通注册、登录、创建会议等基础页面。
2. 购买一台 Ubuntu 云服务器，确认域名、备案、DNS 和安全组。
3. 用 Windows CMD/PowerShell、macOS Terminal，或 FinalShell 通过 SSH 登录服务器。
4. 在服务器部署 Flask 应用、`.env`、systemd、Nginx 和 HTTPS。
5. LiveKit 先用 LiveKit Cloud，把 `LIVEKIT_URL`、`LIVEKIT_API_KEY`、`LIVEKIT_API_SECRET` 写入 `.env`。
6. 两台设备测试会议。如果必须自建媒体服务，再按本文的自建 LiveKit 章节单独部署。

Nginx 代理的是本项目网站；LiveKit 承担摄像头、麦克风、屏幕共享媒体传输。使用 LiveKit Cloud 时，不需要让 Nginx 代理 LiveKit。

## 常见名词先说明白

| 名词 | 在本项目里是什么意思 | 出问题时常见现象 |
| --- | --- | --- |
| Flask 应用 | `app.py` 运行出来的网站和接口 | 页面打不开、登录失败、接口 500 |
| Gunicorn | Linux 服务器上启动 Flask 的生产进程 | `systemctl status video-meeting` 报错 |
| Socket.IO | 聊天、成员列表、主持人操作、房间 UI 状态 | 页面能打开但聊天/成员不同步 |
| WebSocket | Socket.IO 常用长连接 | 浏览器控制台出现 socket 连接失败 |
| Nginx | 公网入口，负责反向代理、HTTPS、上传限制、WebSocket 头 | 502、上传失败、WebSocket 断开 |
| HTTPS 证书 | 浏览器信任网站所需证书 | 页面提示不安全，摄像头权限异常 |
| LiveKit | 音视频和屏幕共享媒体服务器 | 房间页 503，或进房后没有远端音视频 |
| TURN | 防火墙/弱网环境下帮助 WebRTC 连通的中继服务 | 同网络能用，换网络或手机流量失败 |

## 0. 如何阅读命令块

除非特别说明，本文命令都在服务器 Linux shell 中执行。示例占位值如下：

| 占位值 | 含义 | 你需要替换成 |
| --- | --- | --- |
| `meeting.example.com` | 会议系统域名 | 你自己的域名或子域名 |
| `livekit.example.com` | 自建 LiveKit 域名 | 如果自建 LiveKit，换成你的媒体服务域名 |
| `your_server_ip` | 云服务器公网 IP | 云厂商控制台显示的公网 IP |
| `/opt/video-meeting` | 项目部署目录 | 可保留，也可换成自己的目录 |
| `deploy` | Linux 运行用户 | 可保留，也可换成自己的用户名 |
| `video-meeting` | systemd 服务名 | 可保留，也可换成自己的服务名 |
| `main` | Git 默认分支 | 你的实际部署分支 |

本文尽量使用 `cat <<'EOF' | sudo tee ...` 的方式写配置文件。它比 `nano` 更适合复制粘贴，不会因为终端编辑器不熟导致文件没保存。确实要用 `nano` 时：`Ctrl+O` 保存，回车确认文件名，`Ctrl+X` 退出。

## 0.1 部署前先准备哪些账号

| 类型 | 用途 | 官方入口 |
| --- | --- | --- |
| 云服务器 | 运行 Flask、Nginx、systemd | 阿里云 ECS、腾讯云 CVM、华为云 ECS、AWS EC2、Azure VM、DigitalOcean、Vultr |
| 域名 | 让用户访问 `meeting.example.com` | 阿里云域名、腾讯云 DNSPod、Cloudflare Registrar、Namecheap 等 |
| 备案入口 | 中国大陆服务器绑定域名时通常需要 ICP 备案 | 工信部备案系统、云厂商备案控制台 |
| GitHub / Gitee | 托管代码，服务器 `git clone` / `git pull` | https://github.com/ / https://gitee.com/ |
| Cloudflare | 可选 DNS 托管、代理、SSL/TLS 设置 | https://www.cloudflare.com/ |
| LiveKit Cloud | 最省事的托管 LiveKit 媒体服务 | https://cloud.livekit.io/ |
| Let's Encrypt / Certbot | 免费 HTTPS 证书 | https://letsencrypt.org/ / https://certbot.eff.org/ |

可信参考链接集中放在文末“参考依据”。如果你是第一次部署，先看本文步骤；遇到细节差异时再打开官方文档核对。

## 1. 推荐部署架构

```text
用户浏览器
  -> https://meeting.example.com
  -> DNS 或 Cloudflare
  -> Nginx 443/80
  -> 127.0.0.1:8000 上的 Gunicorn + eventlet
  -> Flask + Flask-SocketIO 应用

用户浏览器
  -> wss://your-project.livekit.cloud 或 wss://livekit.example.com
  -> LiveKit SFU
```

当前应用的在线房间状态主要保存在单进程内存中，所以默认按单实例部署。不要简单启动多个 Gunicorn worker 或多台应用服务器，否则 `rooms`、`sid_to_user`、聊天历史和屏幕共享状态会不一致。

## 2. 购买服务器、备案与登录准备

### 2.1 购买服务器

常见云服务器入口：

| 厂商 | 官方入口 | 备注 |
| --- | --- | --- |
| 阿里云 ECS | https://www.aliyun.com/product/ecs | 国内访问方便，控制台中文 |
| 腾讯云 CVM | https://cloud.tencent.com/product/cvm | 国内访问方便，控制台中文 |
| 华为云 ECS | https://www.huaweicloud.com/product/ecs.html | 国内访问方便，控制台中文 |
| AWS EC2 | https://aws.amazon.com/ec2/ | 国际云厂商 |
| Azure Virtual Machines | https://azure.microsoft.com/products/virtual-machines/ | 国际云厂商 |
| DigitalOcean Droplets | https://www.digitalocean.com/products/droplets | 面板简单，英文界面 |
| Vultr Cloud Compute | https://www.vultr.com/products/cloud-compute/ | 面板简单，英文界面 |

课程展示或小规模演示推荐：

| 项 | 建议 |
| --- | --- |
| 系统 | Ubuntu 22.04 LTS 或 24.04 LTS |
| CPU / 内存 | 2 vCPU / 2 GB 起步，演示人数较多建议 4 GB |
| 磁盘 | 30 GB 起步，附件和录屏多时再扩容 |
| 入站端口 | `22/tcp`、`80/tcp`、`443/tcp` |
| 域名 | `meeting.example.com` 这类子域名 |

购买时注意：

- 中国大陆用户访问优先选国内或香港/新加坡机房；海外用户选离用户近的区域。
- 新手优先选 Ubuntu LTS，不建议一开始选 CentOS、Debian minimal 或自定义镜像。
- 不要一开始就买负载均衡、云数据库、对象存储等附加产品；先让单机跑通。
- 安全组先放行 `22/tcp`、`80/tcp`、`443/tcp`。如果后续自建 LiveKit，还要额外放行媒体端口。

### 2.2 中国大陆服务器和备案

如果服务器在中国大陆，并且你要用域名公开访问网站，通常需要先完成 ICP 备案。没有备案时，云厂商可能不允许域名绑定大陆服务器的 Web 服务，或访问会被拦截。

简化判断：

| 情况 | 通常是否需要备案 |
| --- | --- |
| 中国大陆服务器 + 域名公开访问 | 需要 ICP 备案 |
| 中国大陆服务器 + 只用公网 IP 临时调试 | 通常不涉及域名备案，但不适合正式展示 |
| 香港、新加坡、美国等非中国大陆服务器 | 通常不需要中国大陆 ICP 备案，但国内访问质量可能不同 |

备案要按云厂商流程准备身份证明、域名实名、服务器实例、网站信息等材料。具体政策会更新，以工信部和云厂商官方文档为准。本文只提醒部署前必须考虑这个前置条件。

### 2.3 Windows、macOS 和 FinalShell 怎么登录服务器

云厂商通常会给你三类信息：公网 IP、登录用户名、密码或 SSH key。Ubuntu 常见用户名可能是 `root`、`ubuntu` 或你在控制台创建的用户。

Windows 可以用 PowerShell 或 CMD：

```powershell
ssh root@your_server_ip
```

macOS 用 Terminal：

```bash
ssh root@your_server_ip
```

如果用户名不是 `root`：

```bash
ssh ubuntu@your_server_ip
```

如果云厂商给的是私钥文件：

```bash
ssh -i /path/to/your-key.pem root@your_server_ip
```

Windows 私钥路径示例：

```powershell
ssh -i C:\Users\yourname\.ssh\server.pem root@your_server_ip
```

第一次连接通常会问：

```text
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

这是 SSH 在确认服务器指纹。确认 IP 是你的服务器后输入 `yes` 回车。输入密码时，命令行通常不会显示星号，也不会显示光标变化；直接输入密码并回车即可。如果输错，会提示 `Permission denied`，重新输入或回云控制台重置密码。

FinalShell 可以用。它本质上也是 SSH 客户端，适合不熟悉命令行的人：

1. 安装 FinalShell。
2. 新建 SSH 连接。
3. 主机填 `your_server_ip`，端口填 `22`。
4. 用户名填 `root` / `ubuntu` / 云厂商给你的用户名。
5. 认证方式选择密码或私钥。
6. 连接成功后，在内置终端里继续执行本文命令。

CMD、PowerShell、macOS Terminal、Linux shell、FinalShell 都可以登录服务器。登录成功后看到的是服务器的 Linux shell，后续命令基本一致。

### 2.4 首次登录后的基础初始化

先以 root 或有 sudo 权限的用户执行：

```bash
apt update
apt upgrade -y
timedatectl set-timezone Asia/Shanghai
```

如果当前不是 root，就加 `sudo`：

```bash
sudo apt update
sudo apt upgrade -y
sudo timedatectl set-timezone Asia/Shanghai
```

创建专用运行用户，避免长期用 root 跑应用：

```bash
adduser deploy
usermod -aG sudo deploy
su - deploy
```

如果提示输入新用户密码，按提示设置即可。密码输入时不显示字符是正常现象。

## 3. 安装系统依赖

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git nginx ffmpeg curl ufw ca-certificates gnupg
```

依赖说明：

| 项 | 含义 |
| --- | --- |
| `python3 python3-venv python3-pip` | Python 运行环境、虚拟环境和包管理 |
| `git` | 从 GitHub / Gitee 拉代码 |
| `nginx` | 公网入口、反向代理、HTTPS、WebSocket 转发 |
| `ffmpeg` | 录屏 WebM 转 MP4 |
| `curl` | 命令行测试 HTTP/HTTPS |
| `ufw` | Ubuntu 本机防火墙 |
| `ca-certificates gnupg` | 安装 Docker/仓库签名时常用 |

启用基础防火墙：

```bash
sudo ufw allow OpenSSH
sudo ufw allow "Nginx Full"
sudo ufw enable
sudo ufw status
```

执行 `sudo ufw enable` 前必须确认 SSH 已放行，否则可能把自己锁在服务器外。

## 4. 准备项目目录

示例把项目放在 `/opt/video-meeting`：

```bash
sudo mkdir -p /opt/video-meeting
sudo chown deploy:deploy /opt/video-meeting
cd /opt/video-meeting
```

从 Git 仓库部署：

```bash
git clone https://github.com/jerryhuang392diandi/video-meeting.git .
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn eventlet
```

如果你的仓库在 Gitee 或私有 GitHub，替换 `git clone` URL。私有仓库需要先配置 SSH key 或 token。

## 5. 配置环境变量

建议用 EOF 直接写 `/opt/video-meeting/.env`：

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

生成 `SECRET_KEY`：

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

配置项解释：

| 配置 | 含义 | 必填 |
| --- | --- | --- |
| `SECRET_KEY` | Flask 会话签名密钥，必须稳定保存 | 是 |
| `DATABASE_URL` | SQLAlchemy 数据库连接串，默认 SQLite | 否 |
| `PUBLIC_SCHEME` | 对外访问协议，线上填 `https` | 是 |
| `PUBLIC_HOST` | 对外域名，不带 `https://` | 是 |
| `LIVEKIT_URL` | 浏览器连接 LiveKit 的 `wss://...` URL | 是 |
| `LIVEKIT_API_KEY` | Flask 后端签发 LiveKit token 用的 key | 是 |
| `LIVEKIT_API_SECRET` | Flask 后端签发 LiveKit token 用的 secret | 是 |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | 初始管理员账号和密码 | 推荐 |
| `SESSION_COOKIE_SECURE` / `REMEMBER_COOKIE_SECURE` | Cookie 仅 HTTPS 发送 | HTTPS 推荐 |

注意：

- `.env` 不要提交到 Git。
- 修改 `.env` 后必须 `sudo systemctl restart video-meeting`。
- LiveKit 三项缺失时，房间页返回 `503` 是正常保护逻辑。
- SQLite 数据库、上传文件、生成的管理员密码等运行时文件在 `instance/`，备份时不要漏掉。

## 6. systemd 服务

用 EOF 写服务文件：

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

启动并设置开机自启：

```bash
sudo systemctl daemon-reload
sudo systemctl enable video-meeting
sudo systemctl start video-meeting
sudo systemctl status video-meeting
```

关键点：

- `EnvironmentFile=/opt/video-meeting/.env` 让 systemd 加载生产环境变量。
- `--worker-class eventlet` 用于 Flask-SocketIO 长连接。
- `--workers 1` 不要随便调大，因为当前房间在线态在单进程内存中。
- `--bind 127.0.0.1:8000` 必须和 Nginx `proxy_pass` 一致。

查看日志：

```bash
journalctl -u video-meeting -n 100 --no-pager
journalctl -u video-meeting -f
```

修改 `.service` 后执行：

```bash
sudo systemctl daemon-reload
sudo systemctl restart video-meeting
```

只修改 `.env` 时不需要 `daemon-reload`，但必须重启服务。

此时先确认本机应用能响应：

```bash
curl -I http://127.0.0.1:8000
```

## 7. LiveKit 配置选择

本项目使用 LiveKit 传输音视频。Flask 只负责校验用户并签发 token；浏览器拿到 token 后直接连 `LIVEKIT_URL`。

### 7.1 使用 LiveKit Cloud

这是最适合课程展示和第一次部署的方案：

1. 打开 https://cloud.livekit.io/ 并创建 project。
2. 在项目页面复制 Server URL，通常类似 `wss://xxx.livekit.cloud`。
3. 创建 API key 和 API secret。
4. 写入服务器 `/opt/video-meeting/.env`。
5. 重启应用：

```bash
sudo systemctl restart video-meeting
sudo systemctl status video-meeting
```

连接形态是：

```text
浏览器 -> https://meeting.example.com -> Nginx -> Flask
浏览器 -> wss://your-project.livekit.cloud -> LiveKit Cloud
```

所以使用 LiveKit Cloud 时，Nginx 配置里不需要 `livekit.cloud`。

### 7.2 自建 LiveKit：什么时候需要

自建 LiveKit 适合这些情况：

- 不想使用托管 LiveKit Cloud。
- 要内网或私有化部署。
- 要自己控制媒体服务区域、端口、日志和成本。

它比 LiveKit Cloud 麻烦很多。建议先用 LiveKit Cloud 跑通本项目，再单独替换为自建 LiveKit。

### 7.3 自建 LiveKit：域名和端口规划

建议网站和 LiveKit 分开域名：

| 域名 | 用途 | 指向 |
| --- | --- | --- |
| `meeting.example.com` | Flask 网站 | Flask/Nginx 服务器 |
| `livekit.example.com` | LiveKit 信令和 WSS | LiveKit 服务器 |

单服务器演示可以让两个域名指向同一台机器；生产上可以分开机器。安全组和防火墙至少考虑：

| 端口 | 协议 | 用途 |
| --- | --- | --- |
| `443` | TCP | LiveKit WSS / HTTPS 入口 |
| `7881` | TCP | WebRTC TCP fallback，按 LiveKit 配置决定 |
| `50000-60000` | UDP | WebRTC UDP 媒体端口范围，按 LiveKit 配置决定 |
| `3478` | UDP/TCP | TURN/STUN，使用 TURN 时需要 |
| `5349` | TCP | TURN TLS，使用 TURN TLS 时需要 |

实际端口以你的 LiveKit 配置和官方文档为准。云厂商安全组和服务器 `ufw` 都要放行，二者缺一不可。

### 7.4 自建 LiveKit：Docker Compose 示例

安装 Docker：

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker deploy
newgrp docker
docker --version
```

准备目录：

```bash
sudo mkdir -p /opt/livekit
sudo chown deploy:deploy /opt/livekit
cd /opt/livekit
```

写 LiveKit 配置。先生成一组 key/secret，示例里为了易读写成固定占位值，实际必须替换：

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

写 Docker Compose：

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

启动：

```bash
docker compose up -d
docker compose logs -f livekit
```

放行 LiveKit 端口：

```bash
sudo ufw allow 7881/tcp
sudo ufw allow 50000:60000/udp
sudo ufw status
```

如果要在同一台 Nginx 上代理 LiveKit 的 WSS 入口，可以新建 `livekit.example.com` 的 Nginx 配置。媒体 UDP 端口不能靠这个 HTTP 反向代理解决，仍然要直通开放。

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

然后把 Flask `.env` 改成：

```bash
cat <<'EOF' >> /opt/video-meeting/.env
# 如果改用自建 LiveKit，确保旧值已被替换，不要重复保留多份 LIVEKIT_ 配置。
EOF
```

实际编辑时把三项改为：

```env
LIVEKIT_URL=wss://livekit.example.com
LIVEKIT_API_KEY=replace-livekit-api-key
LIVEKIT_API_SECRET=replace-livekit-api-secret
```

最后重启：

```bash
sudo systemctl restart video-meeting
```

### 7.5 自建 LiveKit 验证清单

| 检查项 | 应该是什么样 |
| --- | --- |
| DNS | `livekit.example.com` 指向 LiveKit 服务器公网 IP |
| HTTPS/WSS | `https://livekit.example.com` 证书可信 |
| `LIVEKIT_URL` | `wss://livekit.example.com`，不是 `http://` |
| API key / secret | LiveKit 配置和 Flask `.env` 完全一致 |
| 云安全组 | 放行 `443/tcp`、LiveKit TCP fallback、UDP 媒体端口 |
| `ufw` | 与云安全组放行同样端口 |
| NAT/公网 IP | LiveKit 能知道自己的公网出口，必要时配置外部 IP |
| TURN | 校园网、公司网、移动网络异常时再重点补 TURN |

## 8. 域名、Cloudflare 与 DNS

公网部署需要一个用户能打开的域名，例如 `meeting.example.com`。

### 8.1 普通 DNS

在 DNS 服务商添加 A 记录：

```text
Type: A
Name: meeting
Value: your_server_ip
TTL: Auto 或 600
```

检查解析：

```bash
getent hosts meeting.example.com
```

如果使用自建 LiveKit，再加一条：

```text
Type: A
Name: livekit
Value: livekit_server_ip
TTL: Auto 或 600
```

### 8.2 使用 Cloudflare

Cloudflare 控制台：https://dash.cloudflare.com/

推荐流程：

1. 在 Cloudflare 添加站点。
2. 按提示到域名注册商修改 nameserver。
3. DNS 页面添加 `A` 记录：`meeting -> your_server_ip`。
4. 第一次部署先用 `DNS only`。
5. Nginx 和 HTTPS 都正常后，再考虑开启 `Proxied`。
6. SSL/TLS 模式使用 `Full (strict)`，服务器侧仍然要有有效证书。

如果 LiveKit Cloud 用 `*.livekit.cloud`，不要在 Cloudflare 配 LiveKit。浏览器会直接访问 LiveKit Cloud。

如果自建 `livekit.example.com`，建议先保持 DNS only，确认 WSS 和媒体端口都正常后再评估是否使用 Cloudflare。普通 Cloudflare HTTP 代理不代理 WebRTC UDP 媒体端口。

## 9. Nginx 反向代理

Nginx 监听公网 `80/443`，把请求转发到本机 `127.0.0.1:8000` 的 Gunicorn。它还要保留 WebSocket 头，否则 Socket.IO 可能断开。

### 9.1 为什么要写 WebSocket map

按 Nginx 官方 WebSocket 代理写法，先创建 `Connection` 映射：

```bash
cat <<'EOF' | sudo tee /etc/nginx/conf.d/websocket-map.conf
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}
EOF
```

### 9.2 创建网站反向代理配置

先写 HTTP 配置，方便 Certbot 验证域名：

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

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/video-meeting /etc/nginx/sites-enabled/video-meeting
sudo nginx -t
sudo systemctl reload nginx
```

如果提示 symlink 已存在，说明之前启用过，可忽略或先检查文件。

### 9.3 启用配置并检查语法

常用检查：

```bash
sudo nginx -t
sudo systemctl reload nginx
curl -I http://meeting.example.com
```

`client_max_body_size 150m` 要大于应用的视频附件限制。当前项目视频附件上限是 120 MB，所以这里给 150 MB。

### 9.4 Nginx 配好后怎么判断是否正常

```bash
curl -I http://127.0.0.1:8000
curl -I http://meeting.example.com
sudo tail -n 80 /var/log/nginx/error.log
```

判断顺序：

- `127.0.0.1:8000` 不通：先查 systemd/Gunicorn/Flask。
- `127.0.0.1:8000` 通但域名不通：查 Nginx、DNS、安全组、防火墙。
- 页面打开但 Socket.IO 失败：查 `Upgrade` 和 `Connection` 代理头。

### 9.5 Nginx 和 LiveKit 的关系

使用 LiveKit Cloud：

```text
meeting.example.com -> Nginx -> Flask
your-project.livekit.cloud -> LiveKit Cloud
```

自建 LiveKit：

```text
meeting.example.com -> Nginx -> Flask
livekit.example.com -> LiveKit WSS 入口
LiveKit UDP/TCP media ports -> 直通 LiveKit 服务
```

不要以为代理了 `livekit.example.com` 的 HTTPS 就完成了 WebRTC 部署；媒体 UDP/TCP 端口仍然要开放。

## 10. HTTPS 证书

Certbot 官方推荐 Ubuntu + Nginx 使用 snap 版：

```bash
sudo snap install core
sudo snap refresh core
sudo apt remove -y certbot
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
```

如果最后一行提示文件已存在，说明 `certbot` 命令已经可用。

### 10.1 自动让 Certbot 修改 Nginx

最简单方式：

```bash
sudo certbot --nginx -d meeting.example.com
sudo certbot renew --dry-run
```

Certbot 会读取 Nginx 配置、申请证书并写入 HTTPS 配置。完成后检查：

```bash
curl -I https://meeting.example.com
```

### 10.2 手动写一个直接可用的 HTTPS 配置

如果你不想让 Certbot 自动改 Nginx，可以先申请证书：

```bash
sudo certbot certonly --nginx -d meeting.example.com
```

然后直接写完整 HTTPS 配置：

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

这个配置的关键点：

- `80` 只做跳转到 HTTPS。
- `443 ssl http2` 承担真实访问。
- `X-Forwarded-Proto https` 明确告诉 Flask 外部是 HTTPS。
- WebSocket 仍然保留 `Upgrade` 和 `Connection`。
- 证书路径必须和你的域名一致。

HTTPS 完成后，`.env` 应保持：

```env
PUBLIC_SCHEME=https
SESSION_COOKIE_SECURE=1
REMEMBER_COOKIE_SECURE=1
```

## 11. 首次上线验证

命令行检查：

```bash
curl -I http://127.0.0.1:8000
curl -I http://meeting.example.com
curl -I https://meeting.example.com
grep LIVEKIT /opt/video-meeting/.env
```

浏览器检查：

- 首页、登录页、注册页可访问。
- 管理员账号可以登录。
- 普通用户可以注册、登录、创建会议。
- 房间页不会因为 LiveKit 缺失返回 `503`。
- 两个设备加入同一会议，首次加入即可看到远端媒体。
- 聊天、附件上传、附件预览和下载权限可用。
- 摄像头、麦克风、屏幕共享开始和停止可用。
- `/admin` 能打开，常用管理动作正常。

## 12. 三端改代码与 Git 版本管理

实际维护通常有三端：

| 端 | 作用 |
| --- | --- |
| 本地电脑 | 写代码、运行 `python app.py`、本地测试 |
| Git 平台 | 保存版本，作为同步中心 |
| 云服务器 | 只拉取确认过的代码并重启服务 |

推荐流程：

```text
本地改代码 -> 本地测试 -> git commit -> git push -> SSH 登录服务器 -> git pull -> 重启 systemd
```

本地提交：

```bash
git status
python check_i18n.py
python -m py_compile app.py translations.py
git add .
git commit -m "Improve deployment documentation"
git push origin main
```

云服务器更新：

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

如果服务器 `git status` 显示未提交改动，不要强行 `git pull`，先确认是不是有人直接在服务器改过文件。

## 13. 标准服务器更新

普通更新：

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

只改代码：

```bash
cd /opt/video-meeting
git pull origin main
sudo systemctl restart video-meeting
sudo systemctl status video-meeting
```

修改 Nginx：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

修改 systemd：

```bash
sudo systemctl daemon-reload
sudo systemctl restart video-meeting
sudo systemctl status video-meeting
```

## 14. 备份与迁移

SQLite 和上传文件默认在 `instance/`：

```bash
cd /opt/video-meeting
tar -czf /tmp/video-meeting-instance-$(date +%F).tar.gz instance
cp /opt/video-meeting/.env /tmp/video-meeting-env-$(date +%F)
```

迁移服务器：

1. 新服务器部署代码和依赖。
2. 拷贝旧服务器 `instance/`。
3. 拷贝或重建 `.env`。
4. 更新 DNS 到新服务器 IP。
5. 重启 systemd 并做双端入房验证。

## 15. 本地提交速查

```bash
git status
git pull --rebase origin main
python check_i18n.py
git add .
git commit -m "Improve deployment documentation"
git push origin main
```

不要提交 `venv/`、`instance/`、`.env`、数据库、上传文件、录屏文件、临时压缩包或 IDE 缓存。

## 16. 常见问题

### 房间返回 503

```bash
grep LIVEKIT /opt/video-meeting/.env
journalctl -u video-meeting -n 100 --no-pager
sudo systemctl restart video-meeting
```

确认：

- `LIVEKIT_URL` 是浏览器可访问的 `wss://...` 地址。
- `LIVEKIT_API_KEY` 和 `LIVEKIT_API_SECRET` 正确。
- systemd 服务加载了 `/opt/video-meeting/.env`。
- 修改 `.env` 后已经重启服务。

### 页面能打开但 Socket.IO 连接失败

检查 Nginx：

```bash
sudo nginx -t
sudo systemctl reload nginx
grep -R "Upgrade\\|connection_upgrade" /etc/nginx/conf.d /etc/nginx/sites-available
journalctl -u video-meeting -f
```

必须包含：

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection $connection_upgrade;
proxy_read_timeout 3600;
```

### 页面能打开但没有远端媒体

优先检查：

- 浏览器是否允许摄像头和麦克风。
- LiveKit Cloud 或自建 LiveKit 是否可达。
- `PUBLIC_HOST` / `PUBLIC_SCHEME` 是否与真实访问地址一致。
- 如果自建 LiveKit，云安全组和 `ufw` 是否放行媒体端口。
- 是否只有单个网络失败；如果校园网/公司网失败，考虑 TURN。

### 附件上传失败

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

```bash
sudo systemctl status video-meeting
journalctl -u video-meeting -n 100 --no-pager
ss -lntp | grep 8000
sudo tail -n 80 /var/log/nginx/error.log
```

通常是应用服务没启动、Gunicorn 报错，或 Nginx 代理端口和 systemd `--bind` 不一致。

### 修改 .env 后不生效

```bash
sudo systemctl restart video-meeting
journalctl -u video-meeting -n 50 --no-pager
```

如果改的是 `/etc/systemd/system/video-meeting.service`：

```bash
sudo systemctl daemon-reload
sudo systemctl restart video-meeting
```

### SSH 登录问题

| 现象 | 处理 |
| --- | --- |
| 输入密码没有显示 | 正常，Linux/SSH 密码输入默认不回显 |
| `Permission denied` | 用户名、密码、密钥不对；回云控制台检查或重置 |
| `Connection timed out` | 公网 IP、22 端口、安全组、本机网络防火墙有问题 |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | 服务器重装或 IP 复用后常见，确认安全后清理本机 `known_hosts` 对应记录 |

## 17. 参考依据

本文部署命令结合项目当前代码和以下官方/可信文档整理：

| 主题 | 文档 |
| --- | --- |
| Flask-SocketIO + Gunicorn | [Flask-SocketIO Deployment](https://flask-socketio.readthedocs.io/en/latest/deployment.html) |
| Gunicorn 参数 | [Gunicorn Settings](https://docs.gunicorn.org/en/stable/settings.html) |
| Nginx WebSocket | [Nginx WebSocket proxying](https://nginx.org/en/docs/http/websocket.html) |
| Nginx HTTPS | [Configuring HTTPS servers](https://nginx.org/en/docs/http/configuring_https_servers.html) |
| Nginx 入门 | [Beginner's Guide](https://nginx.org/en/docs/beginners_guide.html) |
| Certbot / Nginx | [Certbot install guide](https://eff-certbot.readthedocs.io/en/stable/install.html) |
| Let's Encrypt | [Let's Encrypt Documentation](https://letsencrypt.org/docs/) |
| systemd 环境变量 | [systemd.exec EnvironmentFile](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html) |
| LiveKit 自建部署 | [LiveKit self-hosting deployment](https://docs.livekit.io/home/self-hosting/deployment/) |
| LiveKit VM 部署 | [LiveKit VM deployment](https://docs.livekit.io/home/self-hosting/vm/) |
| LiveKit Docker | [LiveKit Docker image](https://github.com/livekit/livekit) |
| LiveKit Cloud | [LiveKit Cloud](https://cloud.livekit.io/) |
| Cloudflare DNS | [Create DNS records](https://developers.cloudflare.com/dns/manage-dns-records/how-to/create-dns-records/) |
| Cloudflare SSL | [Full (strict) SSL mode](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/) |
| Windows OpenSSH | [Microsoft OpenSSH client](https://learn.microsoft.com/windows-server/administration/openssh/openssh_install_firstuse) |
| macOS SSH | [Apple: Allow a remote computer to access your Mac](https://support.apple.com/guide/mac-help/allow-a-remote-computer-to-access-your-mac-mchlp1066/mac) |
| Ubuntu SSH | [Ubuntu OpenSSH Server](https://documentation.ubuntu.com/server/how-to/security/openssh-server/) |
| 中国大陆备案 | [工信部 ICP/IP 地址/域名信息备案管理系统](https://beian.miit.gov.cn/) |
| 阿里云备案 | [阿里云 ICP 备案](https://help.aliyun.com/zh/icp-filing/) |
| 腾讯云备案 | [腾讯云 ICP 备案](https://cloud.tencent.com/document/product/243) |
| 华为云备案 | [华为云 ICP 备案](https://support.huaweicloud.com/icp/) |
| FinalShell | [FinalShell 官方网站](https://www.hostbuf.com/) |

## 18. 不建议的操作

- 不要把生产服务跑在 Flask debug server 上。
- 不要启动多个 Gunicorn worker 来“提升性能”，除非先把房间运行态迁移到共享存储。
- 不要在生产目录里习惯性执行 `git clean -fd`。
- 不要反复重启服务但不看日志。
- 不要把 `.env`、数据库、上传文件和录屏文件提交到 Git。
- 不要只测页面加载，房间媒体必须做双端验证。
