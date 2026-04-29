<a id="deployment-guide-zh"></a>

# 部署与更新手册

[中文](#deployment-guide-zh) | [English](#deployment-guide-en)

这份文档按第一次上线的真实顺序写：先准备账号和服务器，再登录服务器，接着部署 Flask 应用、systemd、Nginx、HTTPS，最后配置 LiveKit。示例默认使用 Ubuntu 22.04 / 24.04、Nginx、systemd、Gunicorn threaded worker、SQLite 和 LiveKit Cloud 或自建 LiveKit。

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
| GitHub / Gitee | 托管代码，服务器 `git clone` / `git pull` | GitHub: https://github.com/jerryhuang392diandi/video-meeting；Gitee: https://gitee.com/jerryhqx/video-meeting |
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
  -> 127.0.0.1:8000 上的 Gunicorn threaded worker
  -> Flask + Flask-SocketIO 应用

用户浏览器
  -> wss://your-project.livekit.cloud 或 wss://livekit.example.com
  -> LiveKit SFU
```

当前应用的在线房间状态主要保存在单进程内存中，所以默认按单实例部署。不要简单启动多个 Gunicorn worker 或多台应用服务器，否则 `rooms`、`sid_to_user`、聊天历史和屏幕共享状态会不一致。

当前代码已经增加运行态锁和 `/api/healthz` 健康检查来降低单进程 `threading` 模式下的状态竞争，并为排障提供更直接入口；但这不改变单实例前提，只是让单实例更稳、更容易查问题。

建议把 `/api/healthz` 加入你的上线检查：

- 返回 `200` 且 `status` 为 `ok`：说明 Flask 主进程还活着。
- `livekit_enabled` 为 `false`：说明房间页 `503` 大概率不是前端问题，而是 LiveKit 环境变量未配置完整。
- `active_room_count`、`active_socket_count` 长时间异常不回落：优先检查是否有重连风暴、反向代理超时或客户端断开后未完成清理。

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

常用登录命令：

| 场景 | 命令 |
| --- | --- |
| Windows CMD | `ssh root@your_server_ip` |
| macOS Terminal | `ssh root@your_server_ip` |
| Linux shell | `ssh root@your_server_ip` |
| 用户名不是 `root` | `ssh ubuntu@your_server_ip` |

如果你是用私钥登录，三端可以直接按下面替换路径：

| 终端 | 私钥登录命令 |
| --- | --- |
| Windows CMD | `ssh -i C:\Users\yourname\.ssh\server.pem root@your_server_ip` |
| macOS Terminal | `ssh -i ~/.ssh/server.pem root@your_server_ip` |
| Linux shell | `ssh -i ~/.ssh/server.pem root@your_server_ip` |

如果你把 SSH 端口改成了 `2222`，三端写法也是一样的，只是多一个 `-p`：

| 终端 | 自定义端口命令 |
| --- | --- |
| Windows CMD | `ssh -p 2222 root@your_server_ip` |
| macOS Terminal | `ssh -p 2222 root@your_server_ip` |
| Linux shell | `ssh -p 2222 root@your_server_ip` |

第一次连接通常会问：

```text
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

这是 SSH 在确认服务器指纹。确认 IP 是你的服务器后输入 `yes` 回车。输入密码时，命令行通常不会显示星号，也不会显示光标变化；直接输入密码并回车即可。如果输错，会提示 `Permission denied`，重新输入或回云控制台重置密码。

FinalShell 可以用。它本质上也是 SSH 客户端，适合不熟悉命令行的人：

| 字段 | 填写内容 |
| --- | --- |
| 主机 | `your_server_ip` |
| 端口 | `22` |
| 用户名 | `root` / `ubuntu` / 云厂商给你的用户名 |
| 认证方式 | 密码或私钥 |

连接成功后，在 FinalShell 内置终端里继续执行本文命令。

CMD、PowerShell、macOS Terminal、Linux shell、FinalShell 都可以登录服务器。登录成功后看到的是服务器的 Linux shell，后续命令基本一致。

### 2.4 首次登录后的基础初始化

先以 root 或有 sudo 权限的用户执行：

```bash
apt update
apt upgrade -y
```

如果当前不是 root，就加 `sudo`：

```bash
sudo apt update
sudo apt upgrade -y
```

创建专用运行用户，避免长期用 root 跑应用：

```bash
adduser deploy
usermod -aG sudo deploy
su - deploy
```

如果提示输入新用户密码，按提示设置即可。密码输入时不显示字符是正常现象。

### 2.5 SSH 安全加固：先验证新登录，再收紧 SSH

第一次拿到新服务器时，很多云厂商默认给你的是 `root + 密码`，这适合“先登录进去”，但不适合长期公网运行。更稳妥的顺序是：

1. 先保留当前会话，不要急着关。
2. 新建一个普通用户，例如 `deploy`。
3. 给这个用户配置 SSH 公钥登录。
4. 先确认新用户能登录成功。
5. 再禁用 root 远程登录和密码登录。

推荐优先使用 `ed25519` 密钥。只有在旧系统、旧客户端或学校/单位现有规范明确要求 RSA 时，才改成 RSA 4096。不要把“SSH key 登录”和“必须用 RSA”混为一谈。

在你自己的电脑上生成密钥。三端命令基本一致：

| 终端 | `ed25519` 生成命令 |
| --- | --- |
| Windows CMD | `ssh-keygen -t ed25519 -C "deploy@meeting"` |
| macOS Terminal | `ssh-keygen -t ed25519 -C "deploy@meeting"` |
| Linux shell | `ssh-keygen -t ed25519 -C "deploy@meeting"` |

如果你确实需要 RSA：

| 终端 | RSA 4096 生成命令 |
| --- | --- |
| Windows CMD | `ssh-keygen -t rsa -b 4096 -C "deploy@meeting"` |
| macOS Terminal | `ssh-keygen -t rsa -b 4096 -C "deploy@meeting"` |
| Linux shell | `ssh-keygen -t rsa -b 4096 -C "deploy@meeting"` |

生成后你通常会得到：

- Windows CMD 私钥：`%USERPROFILE%\.ssh\id_ed25519` 或 `%USERPROFILE%\.ssh\id_rsa`
- Windows CMD 公钥：`%USERPROFILE%\.ssh\id_ed25519.pub` 或 `%USERPROFILE%\.ssh\id_rsa.pub`
- macOS / Linux 私钥：`~/.ssh/id_ed25519` 或 `~/.ssh/id_rsa`
- macOS / Linux 公钥：`~/.ssh/id_ed25519.pub` 或 `~/.ssh/id_rsa.pub`

把公钥内容复制出来：

| 终端 | 查看 `ed25519` 公钥 |
| --- | --- |
| Windows CMD | `type %USERPROFILE%\.ssh\id_ed25519.pub` |
| macOS Terminal | `cat ~/.ssh/id_ed25519.pub` |
| Linux shell | `cat ~/.ssh/id_ed25519.pub` |

如果你生成的是 RSA，就看：

| 终端 | 查看 RSA 公钥 |
| --- | --- |
| Windows CMD | `type %USERPROFILE%\.ssh\id_rsa.pub` |
| macOS Terminal | `cat ~/.ssh/id_rsa.pub` |
| Linux shell | `cat ~/.ssh/id_rsa.pub` |

如果你的本机已经有可用密钥，Ubuntu 官方也推荐优先直接复制公钥，而不是手动改很多 SSH 配置。最省事的方式是：

| 终端 | 复制公钥到服务器 |
| --- | --- |
| macOS Terminal | `ssh-copy-id deploy@your_server_ip` |
| Linux shell | `ssh-copy-id deploy@your_server_ip` |

Windows CMD 默认通常没有 `ssh-copy-id`。Windows 直接按后面的 `authorized_keys` 手动方式最稳，或者改用 Git Bash / WSL 再执行 `ssh-copy-id`。

如果你的环境没有 `ssh-copy-id`，再手动准备 `authorized_keys`：

```bash
sudo mkdir -p /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo tee /home/deploy/.ssh/authorized_keys > /dev/null <<'EOF'
把你本机的公钥整行粘贴到这里
EOF
sudo chown -R deploy:deploy /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

然后在你本机重新开一个终端，单独测试新用户登录。不要先关掉旧会话：

| 终端 | 测试新用户登录 |
| --- | --- |
| Windows CMD | `ssh deploy@your_server_ip` |
| macOS Terminal | `ssh deploy@your_server_ip` |
| Linux shell | `ssh deploy@your_server_ip` |

如果你改过 SSH 端口，例如改成 `2222`，测试命令是：

| 终端 | 测试新端口 |
| --- | --- |
| Windows CMD | `ssh -p 2222 deploy@your_server_ip` |
| macOS Terminal | `ssh -p 2222 deploy@your_server_ip` |
| Linux shell | `ssh -p 2222 deploy@your_server_ip` |

确认新用户可以稳定登录后，再改 SSH 服务配置。为了降低把主配置改坏的概率，推荐在 Ubuntu 上单独写一个 drop-in 文件，而不是上来就改完整的 `/etc/ssh/sshd_config`：

```bash
sudo install -d -m 755 /etc/ssh/sshd_config.d
cat <<'EOF' | sudo tee /etc/ssh/sshd_config.d/60-video-meeting.conf
PubkeyAuthentication yes
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
EOF
```

如果你暂时还没有完全切到 key 登录，就先不要写 `PasswordAuthentication no`；先只保留：

```text
PubkeyAuthentication yes
PermitRootLogin no
```

说明如下：

| 配置项 | 建议值 | 作用 |
| --- | --- | --- |
| `PermitRootLogin` | `no` | 禁止 root 直接远程登录 |
| `PubkeyAuthentication` | `yes` | 允许 SSH 公钥登录 |
| `PasswordAuthentication` | `no` | 禁止密码登录，减少撞库和爆破风险 |
| `KbdInteractiveAuthentication` | `no` | 关闭交互式认证，减少额外入口 |

第一次部署不建议一开始就改 SSH 端口。把登录方式、权限、`ufw`、Nginx、HTTPS 全跑通以后，如果你还想改端口，再单独处理。

如果你准备修改 SSH 端口，顺序一定要对：

1. 先在云安全组放行新端口。
2. 再在服务器 `ufw` 放行新端口。
3. 用新端口测试登录成功。
4. 最后再关闭旧的 `22/tcp`。

检查 SSH 配置是否有语法问题。Ubuntu 官方文档也建议先做这一步：

```bash
sudo sshd -t
```

如果没有报错，再重载服务：

```bash
sudo systemctl reload ssh
```

有些系统服务名也可能是 `sshd`，可以先查：

```bash
systemctl status ssh
systemctl status sshd
```

特别提醒：

- 在新用户 SSH key 登录没测通之前，不要先把 `PasswordAuthentication` 改成 `no`。
- 在新端口没测通之前，不要先删掉旧端口规则。
- 不要一边改 SSH 一边只保留一个终端窗口。至少留一个已经登录成功的会话备用。
- 如果改完 SSH 后真的进不去了，不要继续硬试密码把自己触发 `fail2ban`；直接用云厂商控制台自带的 VNC/远程终端登录，把 `/etc/ssh/sshd_config.d/60-video-meeting.conf` 改回去，再执行 `sudo sshd -t` 和 `sudo systemctl reload ssh`。

### 2.6 防火墙、自动封禁与恶意 IP 处理

公网部署至少要做两层入口控制：

1. 云厂商安全组
2. 服务器本机防火墙，例如 `ufw`

如果你仍然使用默认 SSH 端口 `22`：

```bash
sudo ufw allow OpenSSH
sudo ufw allow "Nginx Full"
sudo ufw enable
sudo ufw status
```

如果你把 SSH 端口改成了 `2222`，就不要再只写 `OpenSSH`，而要明确放行新端口：

```bash
sudo ufw allow 2222/tcp
sudo ufw allow "Nginx Full"
sudo ufw enable
sudo ufw status
```

确认新端口登录成功之后，如果你确实不再使用 `22`，再删除旧规则：

```bash
sudo ufw delete allow OpenSSH
```

或者：

```bash
sudo ufw delete allow 22/tcp
```

`ufw` 只是一层基础保护。要自动封禁 SSH 爆破 IP，最常见的是 `fail2ban`。比起“最小示例”，更建议直接上一个稍微完整但仍然容易维护的配置：

```bash
sudo apt update
sudo apt install -y fail2ban
```

新建建议配置：

```bash
sudo tee /etc/fail2ban/jail.local > /dev/null <<'EOF'
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5
ignoreip = 127.0.0.1/8 ::1 113.200.174.0/24

[sshd]
enabled = true
port = 22
backend = systemd
logpath = %(sshd_log)s
bantime = 1h
findtime = 10m
maxretry = 5

[recidive]
enabled = true
logpath = /var/log/fail2ban.log
banaction = %(banaction_allports)s
bantime = 1w
findtime = 1d
maxretry = 5
EOF
```

这份配置的含义：

| 配置项 | 建议值 | 作用 |
| --- | --- | --- |
| `ignoreip` | `127.0.0.1/8 ::1 你的固定公网IP/32` | 白名单，不会被 fail2ban 封 |
| `sshd` | 开启 | 处理短时间内的 SSH 登录失败 |
| `bantime = 1h` | 1 小时 | 普通爆破先封 1 小时 |
| `findtime = 10m` | 10 分钟 | 在 10 分钟窗口内统计失败次数 |
| `maxretry = 5` | 5 次 | 5 次失败后封禁 |
| `recidive` | 开启 | 针对反复触发封禁的来源做更长时间封禁 |
| `banaction_allports` | 使用 | 对复犯 IP 封所有端口，不只是 SSH |

如果你改了 SSH 端口，例如 `2222`，记得把 `[sshd]` 里的端口同步改成：

```text
port = 2222
```

如果你的出口 IP 是固定的，`ignoreip` 推荐写成：

```text
ignoreip = 127.0.0.1/8 ::1 198.51.100.24/32
```

如果你是公司、实验室或宿舍固定网段，也可以写 CIDR：

```text
ignoreip = 127.0.0.1/8 ::1 198.51.100.0/24
```

但不要随手把过大的网段加进去，例如整个运营商网段或 `0.0.0.0/0`，那等于把防爆破功能废掉。

### 2.6.1 如何避免把自己封掉

最稳妥的顺序是：

1. 先确认你已经能用 SSH key 稳定登录。
2. 先把你自己的固定公网 IP 加进 `ignoreip`。
3. 再启动 `fail2ban`。
4. 启动后立刻检查 `status`，确认 `sshd` jail 正常加载。

如果你本机公网 IP 是固定的，可以在你自己的电脑上先查出来再写进配置。常见命令：

```bash
curl https://ifconfig.me
```

或：

```bash
curl https://api.ipify.org
```

注意这必须是你真实的出口公网 IP，不是你电脑上的 `192.168.x.x`、`10.x.x.x` 或 `172.16-31.x.x` 局域网地址。

如果你经常切换网络，例如：

- 手机热点
- 宿舍 Wi-Fi
- 校园网
- 公司 VPN
- 家里宽带和手机流量来回切

那就不要依赖“固定把自己 IP 写进 `ignoreip`”这一招，因为你的出口 IP 可能经常变。此时更合适的做法是：

- 优先使用 SSH key 登录，不要反复试密码；
- 保留一个已登录的 SSH 会话再改配置；
- 先用较宽松的值，例如 `maxretry = 8`、`bantime = 30m`，确认无误后再收紧；
- 确保你知道如何使用云厂商控制台的网页终端/VNC 解封自己。

如果你刚把自己封了，可以直接在服务器控制台执行：

```bash
sudo fail2ban-client status sshd
sudo fail2ban-client set sshd unbanip 198.51.100.24
```

如果是 `recidive` 把你封了，再执行：

```bash
sudo fail2ban-client status recidive
sudo fail2ban-client set recidive unbanip 198.51.100.24
```

还可以直接查看当前被封的 IP：

```bash
sudo fail2ban-client status sshd
sudo fail2ban-client status recidive
```

启动并查看状态：

```bash
sudo systemctl enable fail2ban
sudo systemctl restart fail2ban
sudo systemctl status fail2ban
sudo fail2ban-client status
sudo fail2ban-client status sshd
sudo fail2ban-client status recidive
```

它的作用是：

- `sshd` 处理短时间爆破；
- `recidive` 处理“被封后又持续重来”的来源；
- `ignoreip` 保证你自己的固定管理 IP 不会被误封。

关于“封禁脏 IP”这件事，建议按下面的优先级处理：

1. 先把 `root` 登录禁掉，改成普通用户 + SSH key。
2. 开 `ufw`。
3. 开 `fail2ban` 自动封禁 SSH 爆破，并给自己的固定管理 IP 配 `ignoreip`。
4. 如果你使用 Cloudflare，再开启 WAF、Bot Fight Mode 或托管规则。
5. 只有当你已经观察到明确的恶意来源 IP 段时，再手动加封禁规则。

不建议小白一上来就导入来源不明的大型“黑名单 IP 库”，原因是：

- 很容易误伤正常用户或学校/公司共享出口 IP。
- 规则太多会增加维护负担。
- 很多网上流传的列表并不新，也不一定可信。

如果你确实想手动封禁某个已经确认异常的 IP，可以用：

```bash
sudo ufw deny from 203.0.113.10
```

如果你后面已经在 GitHub Actions 或自己维护的服务器脚本里接入了 [stamparm/ipsum](https://github.com/stamparm/ipsum) 这类公开恶意来源 IP 列表，也要把它当成“额外加固”，不要当成第一道安全线。更稳妥的做法是：

1. 先完成 SSH key、禁用 root 远程登录、`ufw`、`fail2ban`。
2. 再只取 `ipsum` 里你看得懂、能解释来源的高置信度条目，不要整库无脑导入。
3. 把规则放到你自己的 GitHub 仓库脚本或部署脚本里，保留注释，知道以后怎么更新和回滚。

例如，如果你只是想从 `ipsum` 拉一份高置信度来源，生成一个给 `ufw`/`ipset` 后续处理的文本文件，可以先在 Linux 服务器这样筛：

```bash
curl -fsSL https://raw.githubusercontent.com/stamparm/ipsum/master/levels/4.txt -o /tmp/ipsum-level4.txt
```

如果你想进一步只保留前面是真正 IP、后面是命中次数的行，再过滤一次：

```bash
awk '/^[0-9]/{print $1}' /tmp/ipsum-level4.txt > /tmp/ipsum-level4-ips.txt
```

这一步先停住，自己抽样看几条，再决定要不要批量导入防火墙。不要在没审过列表的情况下直接自动 `ufw deny` 几千条，否则很容易把正常出口 IP 一起封掉。

查看当前规则：

```bash
sudo ufw status numbered
```

删除规则时先看编号，再删除对应项：

```bash
sudo ufw delete 3
```

零基础部署时，优先级最高的不是“收集很多坏 IP”，而是先把这四件事做好：

- 用普通用户登录
- 只允许 SSH key 登录
- 禁止 root 远程登录
- 用 `fail2ban` 自动挡住爆破
- 知道如何用 `unbanip` 把自己解封

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
git clone https://gitee.com/jerryhqx/video-meeting.git .
# 按网络环境或代码托管平台按需选择 GitHub：
# git clone https://github.com/jerryhuang392diandi/video-meeting.git .
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

私有仓库需要先配置 SSH key 或 token。

## 5. 配置环境变量

先把最容易混淆的三个“用户”区分开：

| 名称 | 典型值 | 作用 | 应该写到哪里 |
| --- | --- | --- | --- |
| Linux 登录用户 | `root`、`ubuntu`、`deploy` | 你通过 SSH 登录服务器时使用的系统账号 | 云厂商控制台、`/etc/passwd`、SSH 配置 |
| systemd 运行用户 | `deploy` | `video-meeting.service` 以哪个 Linux 用户身份启动 Gunicorn | `/etc/systemd/system/video-meeting.service` 的 `User=` / `Group=` |
| 应用管理员用户名 | `meetingadmin` | 登录 `/admin` 的网站管理员账号 | `/opt/video-meeting/.env` 的 `ADMIN_USERNAME` |

这三者不是一回事：

- `ssh root@server` 里的 `root` 是 Linux 系统账号，不等于网站管理员。
- `.env` 里的 `ADMIN_USERNAME=root` 只是应用登录名，不会让 Gunicorn 以 root 身份运行。
- `.service` 里的 `User=deploy` 只决定进程权限，不会修改网站管理员用户名。

推荐长期固定成下面这种分层方式：

| 配置文件 | 推荐位置 | 负责内容 | 不要放什么 |
| --- | --- | --- | --- |
| 应用环境变量文件 | `/opt/video-meeting/.env` | `SECRET_KEY`、`PUBLIC_HOST`、`LIVEKIT_*`、`ADMIN_*`、Turnstile、Cookie、安全开关 | 不要放 `User=`、`ExecStart=` |
| systemd 服务文件 | `/etc/systemd/system/video-meeting.service` | `User=`、`Group=`、`WorkingDirectory=`、`EnvironmentFile=`、`ExecStart=`、重启策略 | 不要长期写一堆业务 `Environment=...` |
| Nginx 站点配置 | `/etc/nginx/sites-available/video-meeting` | 域名、反向代理、上传限制、HTTPS、WebSocket 头 | 不要放 `LIVEKIT_API_SECRET`、`ADMIN_PASSWORD` |

一句话判断：

- 改网站行为和密钥，改 `.env`
- 改进程身份和启动方式，改 `.service`
- 改公网入口和 HTTPS，改 Nginx

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

ADMIN_USERNAME=meetingadmin
ADMIN_PASSWORD=replace-with-strong-admin-password
ADMIN_EMAIL=admin@example.com
ADMIN_LOGIN_PATH=/manage-choose-a-long-random-path
ADMIN_SECURITY_RECOVERY_CODE=replace-with-a-long-recovery-code
PUBLIC_REGISTRATION_ENABLED=0
EMAIL_AUTH_ENABLED=1
EMAIL_SMTP_HOST=smtp.resend.com
EMAIL_SMTP_PORT=465
EMAIL_SMTP_USERNAME=resend
EMAIL_SMTP_PASSWORD=replace-with-resend-api-key
EMAIL_SMTP_USE_TLS=0
EMAIL_SMTP_USE_SSL=1
EMAIL_FROM_ADDRESS=noreply@meeting.example.com
EMAIL_FROM_NAME=Video Meeting

ADMIN_ALERT_EMAIL=admin@example.com
ADMIN_EMAIL_NOTIFY_ENABLED=1
ADMIN_NOTIFY_ON_USER_REGISTER=1
ADMIN_NOTIFY_ON_ROOM_JOIN=1
ADMIN_NOTIFY_ON_DANGEROUS_ACTIONS=1
ADMIN_ROOM_JOIN_NOTIFY_COOLDOWN_SECONDS=300

STRICT_SECURITY_CHECKS=1
TURNSTILE_SITE_KEY=replace-with-turnstile-site-key
TURNSTILE_SECRET_KEY=replace-with-turnstile-secret-key

SESSION_COOKIE_SECURE=1
REMEMBER_COOKIE_SECURE=1
SESSION_COOKIE_SAMESITE=Lax
REMEMBER_COOKIE_SAMESITE=Lax
EOF

chmod 600 /opt/video-meeting/.env
```

如果你当前是用 `root` 登录，或者目录 owner 还不是 `deploy`，更稳妥的写法是：

```bash
sudo tee /opt/video-meeting/.env > /dev/null <<'EOF'
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=sqlite:////opt/video-meeting/instance/app.db

PUBLIC_SCHEME=https
PUBLIC_HOST=meeting.example.com

LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=replace-with-livekit-api-key
LIVEKIT_API_SECRET=replace-with-livekit-api-secret

ADMIN_USERNAME=meetingadmin
ADMIN_PASSWORD=replace-with-strong-admin-password
ADMIN_EMAIL=admin@example.com
ADMIN_LOGIN_PATH=/manage-choose-a-long-random-path
ADMIN_SECURITY_RECOVERY_CODE=replace-with-a-long-recovery-code
PUBLIC_REGISTRATION_ENABLED=0
EMAIL_AUTH_ENABLED=1
EMAIL_SMTP_HOST=smtp.resend.com
EMAIL_SMTP_PORT=465
EMAIL_SMTP_USERNAME=resend
EMAIL_SMTP_PASSWORD=replace-with-resend-api-key
EMAIL_SMTP_USE_TLS=0
EMAIL_SMTP_USE_SSL=1
EMAIL_FROM_ADDRESS=noreply@meeting.example.com
EMAIL_FROM_NAME=Video Meeting

ADMIN_ALERT_EMAIL=admin@example.com
ADMIN_EMAIL_NOTIFY_ENABLED=1
ADMIN_NOTIFY_ON_USER_REGISTER=1
ADMIN_NOTIFY_ON_ROOM_JOIN=1
ADMIN_NOTIFY_ON_DANGEROUS_ACTIONS=1
ADMIN_ROOM_JOIN_NOTIFY_COOLDOWN_SECONDS=300

STRICT_SECURITY_CHECKS=1
TURNSTILE_SITE_KEY=replace-with-turnstile-site-key
TURNSTILE_SECRET_KEY=replace-with-turnstile-secret-key

SESSION_COOKIE_SECURE=1
REMEMBER_COOKIE_SECURE=1
SESSION_COOKIE_SAMESITE=Lax
REMEMBER_COOKIE_SAMESITE=Lax
EOF

sudo chown deploy:deploy /opt/video-meeting/.env
sudo chmod 600 /opt/video-meeting/.env
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
| `ADMIN_EMAIL` | 管理员账号邮箱；可用于独立管理员登录页登录；未设置时默认复用 `ADMIN_ALERT_EMAIL` | 推荐 |
| `ADMIN_LOGIN_PATH` | 独立管理员登录入口路径，例如 `/manage-choose-a-long-random-path`；普通登录页会拒绝管理员账号 | 公网推荐 |
| `ADMIN_SECURITY_RECOVERY_CODE` | 安全锁定后的恢复码；建议显式设置，避免只依赖服务器本地生成文件 | 强烈推荐 |
| `PUBLIC_REGISTRATION_ENABLED` | 是否允许任何人自助注册；公网建议关闭 | 推荐 |
| `EMAIL_AUTH_ENABLED` | 是否启用“用户名/邮箱 + 密码 + 邮箱验证码”注册登录链路 | 按需 |
| `EMAIL_SMTP_HOST` / `EMAIL_SMTP_PORT` | SMTP 服务器地址和端口 | 启用邮箱验证时必填 |
| `EMAIL_SMTP_USERNAME` / `EMAIL_SMTP_PASSWORD` | SMTP 用户名和密码；很多服务商这里用 API Key | 启用邮箱验证时通常必填 |
| `EMAIL_SMTP_USE_TLS` / `EMAIL_SMTP_USE_SSL` | SMTP 加密方式；常见是 `587 + TLS` 或 `465 + SSL` 二选一 | 启用邮箱验证时推荐 |
| `EMAIL_FROM_ADDRESS` / `EMAIL_FROM_NAME` | 验证邮件发件地址和显示名称 | 启用邮箱验证时必填 |
| `EMAIL_VERIFY_CODE_TTL_MINUTES` | 邮箱验证码有效期，默认 `10` 分钟 | 可选 |
| `EMAIL_CODE_SEND_LIMIT` | 单个页面窗口内允许发送验证码的最大次数，默认 `2` | 可选 |
| `EMAIL_CODE_SEND_WINDOW_SECONDS` | 验证码重发次数统计窗口，默认跟随验证码有效期 | 可选 |
| `ADMIN_ALERT_EMAIL` | 管理员接收提醒的邮箱；只写在服务器 `.env`，不要提交到 Git；如果未单独设置 `ADMIN_EMAIL`，也会作为管理员账号邮箱 | 开启提醒时必填 |
| `ADMIN_EMAIL_NOTIFY_ENABLED` | 是否启用管理员邮箱提醒；依赖同一套 SMTP 发信配置 | 可选 |
| `ADMIN_NOTIFY_ON_USER_REGISTER` | 新用户注册成功时是否通知管理员，默认 `1` | 可选 |
| `ADMIN_NOTIFY_ON_ROOM_JOIN` | 用户进入会议房间时是否通知管理员，默认 `1` | 可选 |
| `ADMIN_NOTIFY_ON_DANGEROUS_ACTIONS` | 管理员执行踢人、删用户、重置密码、停用/启用账号、处理重置申请、结束/删除会议等高危操作时是否通知，默认 `1` | 可选 |
| `ADMIN_ROOM_JOIN_NOTIFY_COOLDOWN_SECONDS` | 同一用户在同一房间重复进入的提醒冷却时间，默认 `300` 秒，避免刷屏 | 可选 |
| `STRICT_SECURITY_CHECKS` | 启动时拒绝弱 `SECRET_KEY` / `ADMIN_*` 配置 | 公网推荐 |
| `TURNSTILE_SITE_KEY` / `TURNSTILE_SECRET_KEY` | 登录/注册/找回密码的人机验证 | 可选 |
| `TURN_PUBLIC_HOST` | 自动生成 TURN/STUN 地址时使用的公网主机名 | 可选 |
| `TURN_URLS` | 自定义 TURN/STUN URL，多个地址用逗号分隔 | 可选 |
| `TURN_USERNAME` / `TURN_PASSWORD` | TURN 中继账号和密码；设置 `TURN_URLS` 时通常需要 | 可选 |
| `SESSION_COOKIE_SECURE` / `REMEMBER_COOKIE_SECURE` | Cookie 仅 HTTPS 发送 | HTTPS 推荐 |

注意：

- `.env` 不要提交到 Git。
- `.env` 推荐权限为 `600`，文件所有者建议就是运行服务的 Linux 用户，例如 `deploy`。
- 公网部署建议设置 `PUBLIC_REGISTRATION_ENABLED=0`，避免任何人直接创建账号。
- 公网部署建议设置 `STRICT_SECURITY_CHECKS=1`，避免弱 `SECRET_KEY`、弱管理员密码或默认 `root` 管理员名直接带到线上。
- 管理员和普通用户现在是分开的：普通用户继续访问 `/login`；管理员访问 `.env` 中的 `ADMIN_LOGIN_PATH`。这个路径不要写进 README 首页、页面导航或提交到公开仓库。
- 不要因为你是用 `root` 登录服务器，就顺手把 `ADMIN_USERNAME` 也设成 `root`。这是两个完全不同的概念。
- 如果开启 `EMAIL_AUTH_ENABLED=1`，请确保 SMTP 发信配置正确；注册验证码和密码重置验证码都会直接发到用户邮箱。
- 管理员提醒复用同一套 SMTP 配置：设置 `ADMIN_EMAIL_NOTIFY_ENABLED=1` 和 `ADMIN_ALERT_EMAIL=你的管理员邮箱` 后，新用户注册、用户进入会议房间以及高危管理操作都会按开关发送提醒。`ADMIN_ALERT_EMAIL` 是收提醒的邮箱；`ADMIN_EMAIL` 是管理员账号邮箱，默认复用 `ADMIN_ALERT_EMAIL`，所以也可以在独立管理员登录页用这个邮箱 + `ADMIN_PASSWORD` 登录。管理员邮箱只放服务器 `.env`，不要提交到 GitHub。
- 如果同时配置了管理员邮箱和 SMTP，系统现在还支持管理员安全告警：普通入口触发管理员凭据尝试、普通邮箱验证码入口触发管理员邮箱尝试、以及管理员成功登录时，都会发送带“一键锁定链接”和“忽略本次告警链接”的安全邮件。锁定后可通过 `/admin/security/unlock` + 恢复码恢复服务。
- 线上 systemd 不要直接运行 `python app.py`。那会启动 Werkzeug 开发服务器；如果你在 `systemctl status video-meeting` 里看到 `Werkzeug appears to be used in a production deployment` 或 `This is a development server`，说明当前运行方式不对。
- 如果你不熟悉终端编辑器，可以直接保留 EOF 写法；最后那个单独一行的 `EOF` 表示写入结束。
- `TURNSTILE_SECRET_KEY` 不能自己随便生成，必须和 `TURNSTILE_SITE_KEY` 一起从同一个 Cloudflare Turnstile 站点页面复制。
- 如果主要服务中国大陆用户，开启 Turnstile 前先在真实大陆网络环境下验证 `challenges.cloudflare.com` 是否可稳定访问。
- 修改 `.env` 后必须重启服务，后面 `systemd` 章节会执行这一步。
- LiveKit 三项缺失时，房间页返回 `503` 是正常保护逻辑。
- SQLite 数据库、上传文件、生成的管理员密码等运行时文件在 `instance/`，备份时不要漏掉。
- 如果没有设置 `ADMIN_SECURITY_RECOVERY_CODE`，应用会在首次启动后生成 `instance/security_recovery_code.txt`。生产环境建议立刻把恢复码抄到密码管理器里。

### 5.2 管理员安全锁定与恢复

适合新手的理解方式：

- “锁定”是指服务故意返回 `503 Security Lockdown`，并断开当前在线连接，防止继续被人操作。
- “恢复码”是只有你自己知道的一段字符串，用来从锁定模式恢复服务。
- “一键锁定链接”会出现在管理员安全告警邮件里，默认会长期有效，直到你点击锁定，或者点击同一封邮件里的“忽略本次告警链接”使其失效。

推荐配置：

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

把输出内容填进：

```env
ADMIN_SECURITY_RECOVERY_CODE=替换成你自己生成的恢复码
```

修改后重启服务：

```bash
sudo systemctl restart video-meeting
sudo systemctl status video-meeting --no-pager
```

如果你没有手动设置恢复码，第一次启动后可以在服务器上查看自动生成的文件：

```bash
cd /opt/video-meeting
ls -l instance
cat instance/security_recovery_code.txt
```

看到安全告警邮件后的新手操作建议：

1. 先确认邮件中的登录时间、IP、User-Agent 是否是你本人。
2. 如果不是你本人，先点邮件里的“一键锁定链接”。
3. 如果确认只是误报，可以点同一封邮件里的“忽略本次告警链接”，这样该邮件内的锁定链接会立即失效。
4. 锁定后浏览器访问：
   `https://你的域名/admin/security/unlock`
5. 输入恢复码恢复服务。
6. 立刻修改 `.env` 里的 `ADMIN_PASSWORD`，必要时也轮换 `SECRET_KEY`。
7. 修改完后重启服务。

Linux 常用命令：

```bash
cd /opt/video-meeting
sudo systemctl restart video-meeting
sudo systemctl status video-meeting --no-pager
sudo journalctl -u video-meeting -n 100 --no-pager
grep -n "ADMIN_PASSWORD" /opt/video-meeting/.env
grep -n "ADMIN_SECURITY_RECOVERY_CODE" /opt/video-meeting/.env
cat /opt/video-meeting/instance/security_recovery_code.txt
```

如果你决定直接改 `.env` 里的管理员密码：

```bash
sudo nano /opt/video-meeting/.env
```

把这一行改掉：

```env
ADMIN_PASSWORD=替换成新的强密码
```

保存退出后执行：

```bash
sudo systemctl restart video-meeting
```

再访问健康检查确认：

```bash
curl -s https://你的域名/api/healthz
```

你应该重点看这些字段：

- `status`
- `livekit_enabled`
- `security_lockdown_active`
- `security_lockdown_reason`

### 5.1 邮箱验证注册 / 登录接入

当前代码支持可选的邮箱验证码流程：

- 注册页填写 `用户名 + 邮箱 + 密码`
- 先通过人机验证，再发送 6 位邮箱验证码
- 单个页面窗口内，邮箱验证码最多发送 2 次；第一次发送后按钮会切换成“重发验证码”
- 只有邮箱验证码校验通过后，账号才会正式创建
- 已存在但未验证的旧账号，可直接在登录页使用“邮箱登录”
- 找回密码页继续复用同一套 SMTP 配置发送密码重置验证码

最省事的接法通常是 SMTP。你可以接自己域名邮箱，也可以接第三方发信服务的 SMTP。

如果你准备用 Resend 的 SMTP，大致顺序是：

1. 注册 Resend 并验证你的发件域名，准备好 `noreply@your-domain`。
2. 在 DNS 里按 Resend 后台要求添加 SPF / DKIM 记录。
3. 在 Resend 后台创建 API Key。
4. 把 `.env` 里这几项填好：

```env
EMAIL_AUTH_ENABLED=1
EMAIL_SMTP_HOST=smtp.resend.com
EMAIL_SMTP_PORT=465
EMAIL_SMTP_USERNAME=resend
EMAIL_SMTP_PASSWORD=re_xxxxxxxxx
EMAIL_SMTP_USE_TLS=0
EMAIL_SMTP_USE_SSL=1
EMAIL_FROM_ADDRESS=noreply@meeting.example.com
EMAIL_FROM_NAME=Video Meeting

ADMIN_ALERT_EMAIL=admin@example.com
ADMIN_EMAIL_NOTIFY_ENABLED=1
ADMIN_NOTIFY_ON_USER_REGISTER=1
ADMIN_NOTIFY_ON_ROOM_JOIN=1
ADMIN_NOTIFY_ON_DANGEROUS_ACTIONS=1
ADMIN_ROOM_JOIN_NOTIFY_COOLDOWN_SECONDS=300
EMAIL_VERIFY_CODE_TTL_MINUTES=10

ADMIN_ALERT_EMAIL=admin@example.com
ADMIN_EMAIL_NOTIFY_ENABLED=1
ADMIN_NOTIFY_ON_USER_REGISTER=1
ADMIN_NOTIFY_ON_ROOM_JOIN=1
ADMIN_NOTIFY_ON_DANGEROUS_ACTIONS=1
ADMIN_ROOM_JOIN_NOTIFY_COOLDOWN_SECONDS=300
```

如果你用 Brevo、企业邮箱或其他 SMTP 服务，只需要把主机、端口、用户名、密码和加密方式换成对方给你的值。常见组合是：

- `465 + SSL`
- `587 + TLS`

不要同时把 `EMAIL_SMTP_USE_TLS=1` 和 `EMAIL_SMTP_USE_SSL=1` 都开成主模式。通常只保留一种。

接入完成后，最少手测这几步：

1. 重启服务：`sudo systemctl restart video-meeting`
2. 用新邮箱注册一个普通账号
3. 确认收件箱或垃圾邮件箱收到验证码邮件
4. 输入邮件里的 6 位验证码，确认注册完成并能直接登录
5. 用用户名登录一次，再用邮箱登录一次
6. 在“找回密码”页提交一次，确认能收到密码重置验证码并成功设置新密码
7. 给一个未验证旧账号直接使用“邮箱登录”，确认可完成登录并补齐邮箱验证状态

如果收不到邮件，优先检查：

- `.env` 里的 `EMAIL_FROM_ADDRESS` 是否已经在服务商后台验证过
- `PUBLIC_HOST` 是否正确，不然邮件里的链接可能回到错误域名
- 服务商后台的 DNS 验证是否完成
- `journalctl -u video-meeting -n 100 --no-pager` 里是否有 SMTP 认证失败或连接失败

### 5.2 谁负责哪个文件

建议长期保持下面这套边界，不要混写：

| 你要修改的内容 | 正确文件 | 常见错误 |
| --- | --- | --- |
| 改域名或端口对应的对外访问地址 | `/opt/video-meeting/.env` 里的 `PUBLIC_HOST` / `PUBLIC_SCHEME` | 跑去改 `User=` 或只改 Nginx 不改应用配置 |
| 更换 LiveKit API key / secret | `/opt/video-meeting/.env` | 写进 Nginx 配置或硬编码到 `.service` |
| 更换网站管理员用户名/密码 | `/opt/video-meeting/.env` | 误以为 Linux 登录用户名也要一起改 |
| 修改 Gunicorn 监听地址或启动命令 | `/etc/systemd/system/video-meeting.service` 的 `ExecStart=` | 只改 `.env` 但忘了同步 Nginx `proxy_pass` |
| 修改 Gunicorn 运行身份 | `/etc/systemd/system/video-meeting.service` 的 `User=` / `Group=` | 在 `.env` 里乱加 `USER=deploy` 期待生效 |
| 修改 HTTPS、证书、反向代理 | Nginx 配置 | 写到 `.env` 后期待 Nginx 自动读取 |

如果你怀疑当前已经写乱了，先把三层都看一遍：

```bash
sudo systemctl cat video-meeting
sudo sed -n '1,120p' /opt/video-meeting/.env
sudo nginx -T | sed -n '1,220p'
```

然后按这个原则收敛：

- `.env` 只保留应用配置和密钥
- `.service` 只保留进程启动和身份配置
- Nginx 只保留公网入口配置

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
ExecStart=/opt/video-meeting/venv/bin/gunicorn --worker-class gthread --workers 1 --threads 100 --bind 127.0.0.1:8000 app:app
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
- `User=deploy` / `Group=deploy` 说的是 Linux 进程身份，不是网站管理员账号。
- 当前代码固定 `SocketIO(async_mode="threading")`，配合 `simple-websocket` 和 Gunicorn threaded worker 更一致，不要再照着旧文档装 `eventlet`。
- `--workers 1` 不要随便调大，因为当前房间在线态在单进程内存中。
- `--threads 100` 是 Flask-SocketIO 官方文档里 threaded worker 的常见写法；演示环境通常够用。
- `--bind 127.0.0.1:8000` 必须和 Nginx `proxy_pass` 一致。
- 如果你把 `User=` 改成了别的 Linux 用户，后面的“如何设置权限”要一起照着改。

### 6.1 如何设置权限

先记住一条最重要的规则：

- `root` 负责装软件、改 systemd、改 Nginx。
- Web 应用本身尽量用普通 Linux 用户运行，例如 `deploy`。

为什么示例里写 `deploy`：

- 它只是文档里约定的普通运行用户名字，不是固定要求。
- 用单独普通用户运行 Gunicorn，更容易控制项目目录、数据库、上传目录和 `.env` 的权限。
- 就算你平时是 `root` 或 `ubuntu` 登录服务器，也可以让服务本身用 `deploy` 运行。

如果你想继续用别的普通用户，例如 `ubuntu`、`ec2-user`、`meetingapp`，也可以，原则只有两条：

1. `User=` / `Group=` 改成那个真实存在的用户名。
2. `/opt/video-meeting`、`venv/`、`.env`、`instance/` 都要让这个用户可读写。

不推荐把服务长期写成 `User=root`。它虽然可能跑得起来，但上传文件、SQLite、运行时目录都会变成 root 权限，后面最容易遇到 owner 混乱和权限报错。

最推荐的做法是新建一个运行用户，然后把项目目录交给它：

```bash
sudo adduser deploy
sudo chown -R deploy:deploy /opt/video-meeting
sudo chmod 755 /opt/video-meeting
sudo chmod 755 /opt/video-meeting/venv
sudo chmod 700 /opt/video-meeting/instance
sudo chmod 600 /opt/video-meeting/.env
```

然后在 service 文件里保持：

```ini
User=deploy
Group=deploy
```

如果你不想新建用户，准备直接用现有登录用户 `ubuntu`，就把用户名整体替换掉：

```bash
sudo chown -R ubuntu:ubuntu /opt/video-meeting
sudo chmod 755 /opt/video-meeting
sudo chmod 755 /opt/video-meeting/venv
sudo chmod 700 /opt/video-meeting/instance
sudo chmod 600 /opt/video-meeting/.env
```

```ini
User=ubuntu
Group=ubuntu
```

这几条权限分别表示：

- `/opt/video-meeting` 用 `755`：运行用户可写，系统里其他用户可进入目录读取普通代码文件。
- `venv/` 用 `755`：服务可以执行虚拟环境里的 `gunicorn`。
- `instance/` 用 `700`：只让运行用户自己读写数据库、上传文件等运行数据。
- `.env` 用 `600`：只让运行用户自己读写密钥。

设置完以后，至少检查这四项：

```bash
sudo systemctl cat video-meeting
ps -o user,group,pid,cmd -C gunicorn
ls -ld /opt/video-meeting /opt/video-meeting/venv /opt/video-meeting/instance
ls -l /opt/video-meeting/.env
```

你应该看到：

- service 里的 `User=` 和 `Group=` 是同一个普通用户
- `gunicorn` 进程也是这个用户在运行
- `/opt/video-meeting`、`instance/`、`.env` 的 owner 跟这个用户一致

如果服务起不来，最常见的权限错误只有两种：

- `.env` 还是 `root root` 且权限是 `600`，导致 Gunicorn 读不到环境变量。
- `instance/` 还是 `root root`，导致 SQLite 或上传目录写不进去。

### 6.2 重新加载并检查服务

```bash
sudo systemctl daemon-reload
sudo systemctl enable video-meeting
sudo systemctl restart video-meeting
sudo systemctl status video-meeting --no-pager -l
```

查看日志：

```bash
journalctl -u video-meeting -n 100 --no-pager
journalctl -u video-meeting -f
```

如果你在线上看到 `python app.py`、`This is a development server`、或 `Werkzeug appears to be used in a production deployment`，说明当前不是正确的生产运行方式，应回到这里的 `gunicorn + threads + systemd` 结构。

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

如果你是自建 LiveKit，先把这三个值的来源分清：

- `LIVEKIT_URL` 是你自己给 LiveKit 准备的公网访问地址，通常写成 `wss://livekit.example.com`
- `LIVEKIT_API_KEY` 和 `LIVEKIT_API_SECRET` 来自你自建 LiveKit 服务端配置，不是 Cloudflare 的 key，也不是 Flask 的 `SECRET_KEY`
- Flask `.env` 里的 `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` 必须和 LiveKit 实际启动时加载的配置完全一致

不要把下面几类值混在一起：

- `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET`：Flask 后端签发 LiveKit token 时使用
- `TURNSTILE_SITE_KEY` / `TURNSTILE_SECRET_KEY`：Cloudflare Turnstile 人机验证使用
- Flask `SECRET_KEY`：这个 Web 应用自己的 session 和签名使用

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

写 LiveKit 配置。先生成一组 key/secret，示例里为了易读写成固定占位值，实际必须替换。

这里的 `keys:` 就是你后面要填进 Flask `.env` 的 `LIVEKIT_API_KEY` 和 `LIVEKIT_API_SECRET` 来源。不是去 gunicorn 拿，也不是去 Cloudflare 拿。

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

也就是要和 `/opt/livekit/livekit.yaml` 里的 `keys:` 保持一一对应。

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
python -m py_compile app.py translations.py i18n/translations.py scripts/check_i18n.py
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
pip install gunicorn
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
| `Permission denied (publickey)` | 说明服务器已要求公钥登录，但目标用户的 `~/.ssh/authorized_keys`、目录权限或本机私钥不对；优先回滚 SSH 配置，不要盲目继续试 |
| `Connection timed out` | 公网 IP、22 端口、安全组、本机网络防火墙有问题 |
| `Connection refused` | SSH 服务没起来、端口改错，或 `ufw` / 安全组没放行当前端口 |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | 服务器重装或 IP 复用后常见，确认安全后清理本机 `known_hosts` 对应记录 |

## 17. 参考依据

本文部署命令结合项目当前代码和以下官方/可信文档整理。优先依据官方文档；如果你想找一份更适合跟着敲的实操教程，最推荐 DigitalOcean 那两篇：

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
| Ubuntu UFW | [Ubuntu Uncomplicated Firewall](https://documentation.ubuntu.com/server/how-to/security/firewalls/) |
| Fail2ban | [Fail2ban Documentation](https://fail2ban.readthedocs.io/en/latest/) |
| DigitalOcean 服务器初始化 | [Initial Server Setup on Ubuntu](https://www.digitalocean.com/community/tutorials/initial-server-setup-with-ubuntu) |
| DigitalOcean Flask + Gunicorn + Nginx | [How To Serve Flask Applications with Gunicorn and Nginx on Ubuntu](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-22-04) |
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


---

<a id="deployment-guide-en"></a>

# Deployment and Update Guide

[中文](#deployment-guide-zh) | [English](#deployment-guide-en)

This guide follows the real first-deployment order: prepare accounts and a server, connect to the server, deploy the Flask app, systemd, Nginx, HTTPS, and then configure LiveKit. Examples assume Ubuntu 22.04 / 24.04, Nginx, systemd, Gunicorn threaded workers, SQLite, and either LiveKit Cloud or self-hosted LiveKit.

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
  -> Gunicorn threaded worker on 127.0.0.1:8000
  -> Flask + Flask-SocketIO app

User browser
  -> wss://your-project.livekit.cloud or wss://livekit.example.com
  -> LiveKit SFU
```

The current app keeps online room state mainly in single-process memory, so deploy it as one application instance by default. Do not simply start multiple Gunicorn workers or multiple app servers, or `rooms`, `sid_to_user`, chat history, and screen-share state can diverge.

The code now adds a runtime lock and `/api/healthz` to reduce state races in single-process `threading` mode and to provide a more direct troubleshooting entry point. This improves single-instance robustness, but it does not change the single-instance requirement.

Add `/api/healthz` to your rollout checklist:

- `200` with `status: ok` means the Flask process is still alive.
- `livekit_enabled: false` usually means room-page `503` errors are caused by incomplete LiveKit environment variables rather than the frontend.
- If `active_room_count` or `active_socket_count` stays abnormally high, check for reconnect storms, reverse-proxy timeouts, or cleanup paths that did not complete after disconnect.

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
| Windows CMD | `ssh root@your_server_ip` |
| macOS Terminal | `ssh root@your_server_ip` |
| Linux shell | `ssh root@your_server_ip` |
| Username is not `root` | `ssh ubuntu@your_server_ip` |

If you use a private key, replace the path like this:

| Terminal | Private-key login command |
| --- | --- |
| Windows CMD | `ssh -i C:\Users\yourname\.ssh\server.pem root@your_server_ip` |
| macOS Terminal | `ssh -i ~/.ssh/server.pem root@your_server_ip` |
| Linux shell | `ssh -i ~/.ssh/server.pem root@your_server_ip` |

If you changed the SSH port to `2222`, all three terminals just add `-p`:

| Terminal | Custom-port command |
| --- | --- |
| Windows CMD | `ssh -p 2222 root@your_server_ip` |
| macOS Terminal | `ssh -p 2222 root@your_server_ip` |
| Linux shell | `ssh -p 2222 root@your_server_ip` |

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

### 2.5 SSH Hardening: Move to a Normal User and SSH Keys

Many new cloud servers start with `root + password` access. That is acceptable for the very first login, but it is not the right long-term public setup. A safer order is:

1. Keep the current session open.
2. Create a normal user such as `deploy`.
3. Configure SSH public-key login for that user.
4. Confirm the new user can log in successfully.
5. Only then disable root remote login and password login.

Prefer `ed25519` keys by default. Only switch to RSA 4096 if you must support an older system, older SSH client, or an existing policy that explicitly requires RSA. Do not treat "SSH key login" and "must use RSA" as the same thing.

Generate a key on your own computer. The command is the same on all three terminals:

| Terminal | `ed25519` key generation |
| --- | --- |
| Windows CMD | `ssh-keygen -t ed25519 -C "deploy@meeting"` |
| macOS Terminal | `ssh-keygen -t ed25519 -C "deploy@meeting"` |
| Linux shell | `ssh-keygen -t ed25519 -C "deploy@meeting"` |

If you specifically need RSA:

| Terminal | RSA 4096 key generation |
| --- | --- |
| Windows CMD | `ssh-keygen -t rsa -b 4096 -C "deploy@meeting"` |
| macOS Terminal | `ssh-keygen -t rsa -b 4096 -C "deploy@meeting"` |
| Linux shell | `ssh-keygen -t rsa -b 4096 -C "deploy@meeting"` |

This usually creates:

- Windows CMD private key: `%USERPROFILE%\.ssh\id_ed25519` or `%USERPROFILE%\.ssh\id_rsa`
- Windows CMD public key: `%USERPROFILE%\.ssh\id_ed25519.pub` or `%USERPROFILE%\.ssh\id_rsa.pub`
- macOS / Linux private key: `~/.ssh/id_ed25519` or `~/.ssh/id_rsa`
- macOS / Linux public key: `~/.ssh/id_ed25519.pub` or `~/.ssh/id_rsa.pub`

Print the public key:

| Terminal | Show `ed25519` public key |
| --- | --- |
| Windows CMD | `type %USERPROFILE%\.ssh\id_ed25519.pub` |
| macOS Terminal | `cat ~/.ssh/id_ed25519.pub` |
| Linux shell | `cat ~/.ssh/id_ed25519.pub` |

If you created an RSA key instead:

| Terminal | Show RSA public key |
| --- | --- |
| Windows CMD | `type %USERPROFILE%\.ssh\id_rsa.pub` |
| macOS Terminal | `cat ~/.ssh/id_rsa.pub` |
| Linux shell | `cat ~/.ssh/id_rsa.pub` |

If your local machine already has a usable key, Ubuntu documentation also recommends copying the public key directly before you edit more SSH settings:

| Terminal | Copy public key to server |
| --- | --- |
| macOS Terminal | `ssh-copy-id deploy@your_server_ip` |
| Linux shell | `ssh-copy-id deploy@your_server_ip` |

Windows CMD usually does not include `ssh-copy-id` by default. On Windows, the safest default is the manual `authorized_keys` method below, or use Git Bash / WSL if you specifically want `ssh-copy-id`.

If `ssh-copy-id` is not available in your environment, prepare `authorized_keys` manually on the server:

```bash
sudo mkdir -p /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo tee /home/deploy/.ssh/authorized_keys > /dev/null <<'EOF'
paste-your-public-key-here-on-one-line
EOF
sudo chown -R deploy:deploy /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

Then open a second terminal on your own computer and test the new login before closing the old session:

| Terminal | Test new user login |
| --- | --- |
| Windows CMD | `ssh deploy@your_server_ip` |
| macOS Terminal | `ssh deploy@your_server_ip` |
| Linux shell | `ssh deploy@your_server_ip` |

If you changed the SSH port, for example to `2222`, test with:

| Terminal | Test new SSH port |
| --- | --- |
| Windows CMD | `ssh -p 2222 deploy@your_server_ip` |
| macOS Terminal | `ssh -p 2222 deploy@your_server_ip` |
| Linux shell | `ssh -p 2222 deploy@your_server_ip` |

After the new user login works reliably, edit the SSH server config. On Ubuntu, a safer pattern is to add a small drop-in file instead of rewriting the whole `/etc/ssh/sshd_config` immediately:

```bash
sudo install -d -m 755 /etc/ssh/sshd_config.d
cat <<'EOF' | sudo tee /etc/ssh/sshd_config.d/60-video-meeting.conf
PubkeyAuthentication yes
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
EOF
```

If you have not fully switched to key-based login yet, do not set `PasswordAuthentication no` yet. Start with:

```text
PubkeyAuthentication yes
PermitRootLogin no
```

Meaning:

| Setting | Recommended value | Purpose |
| --- | --- | --- |
| `PermitRootLogin` | `no` | Disables direct root remote login |
| `PubkeyAuthentication` | `yes` | Allows SSH public-key login |
| `PasswordAuthentication` | `no` | Disables password login to reduce brute-force risk |
| `KbdInteractiveAuthentication` | `no` | Closes an extra interactive auth path |

For a first deployment, do not change the SSH port on day one unless you already know why you want it. Get login, `ufw`, Nginx, and HTTPS working first, then change the port later if you still want to.

If you want to change the SSH port, do it in the correct order:

1. Open the new port in the cloud security group first.
2. Open the new port in `ufw`.
3. Test login through the new port successfully.
4. Only then close `22/tcp` if you no longer need it.

Check the SSH config before reload. Ubuntu documentation also recommends validating the config first:

```bash
sudo sshd -t
```

If there is no error, reload the service:

```bash
sudo systemctl reload ssh
```

Some systems use the service name `sshd`, so you can check both:

```bash
systemctl status ssh
systemctl status sshd
```

Important:

- Do not set `PasswordAuthentication no` before your new user key login is confirmed.
- Do not remove the old port rule before the new port works.
- Do not edit SSH while keeping only one terminal session open. Keep at least one known-good session alive.
- If you do lock yourself out, stop guessing passwords. Use the cloud provider browser console or VNC console, revert `/etc/ssh/sshd_config.d/60-video-meeting.conf`, then run `sudo sshd -t` and `sudo systemctl reload ssh`.

### 2.6 Firewall, Automatic Banning, and Bad IP Handling

For a public deployment, you need at least two layers of access control:

1. The cloud provider security group
2. The server firewall such as `ufw`

If you still use the default SSH port `22`:

```bash
sudo ufw allow OpenSSH
sudo ufw allow "Nginx Full"
sudo ufw enable
sudo ufw status
```

If you changed SSH to `2222`, do not rely on `OpenSSH`; allow the actual port explicitly:

```bash
sudo ufw allow 2222/tcp
sudo ufw allow "Nginx Full"
sudo ufw enable
sudo ufw status
```

After you confirm the new SSH port works, and only if you no longer need `22`, remove the old rule:

```bash
sudo ufw delete allow OpenSSH
```

or:

```bash
sudo ufw delete allow 22/tcp
```

`ufw` is only the basic layer. The most common automatic SSH brute-force protection is `fail2ban`. Instead of the smallest possible example, use a slightly fuller config that is still easy to maintain:

```bash
sudo apt update
sudo apt install -y fail2ban
```

Create a recommended config:

```bash
sudo tee /etc/fail2ban/jail.local > /dev/null <<'EOF'
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5
ignoreip = 127.0.0.1/8 ::1 198.51.100.24/32

[sshd]
enabled = true
port = 22
backend = systemd
logpath = %(sshd_log)s
bantime = 1h
findtime = 10m
maxretry = 5

[recidive]
enabled = true
logpath = /var/log/fail2ban.log
banaction = %(banaction_allports)s
bantime = 1w
findtime = 1d
maxretry = 5
EOF
```

What this config does:

| Setting | Recommended value | Purpose |
| --- | --- | --- |
| `ignoreip` | `127.0.0.1/8 ::1 your-fixed-public-ip/32` | Whitelist that fail2ban should never ban |
| `sshd` | enabled | Handles short-window SSH login failures |
| `bantime = 1h` | 1 hour | First-level ban for ordinary brute-force attempts |
| `findtime = 10m` | 10 minutes | Count failures within a 10-minute window |
| `maxretry = 5` | 5 tries | Ban after 5 failed attempts |
| `recidive` | enabled | Applies a much longer ban to repeat offenders |
| `banaction_allports` | enabled for recidive | Blocks all ports for repeat offenders, not just SSH |

If your SSH port is `2222`, change the `[sshd]` port to:

```text
port = 2222
```

If your public admin IP is fixed, `ignoreip` should look like:

```text
ignoreip = 127.0.0.1/8 ::1 198.51.100.24/32
```

If you manage the server from a fixed office/lab/dorm network range, you can also use CIDR:

```text
ignoreip = 127.0.0.1/8 ::1 198.51.100.0/24
```

Do not add overly broad ranges such as an entire ISP block or `0.0.0.0/0`, because that would effectively disable brute-force protection.

### 2.6.1 How to avoid banning yourself

The safest order is:

1. Confirm SSH key login already works reliably.
2. Add your own fixed public IP to `ignoreip`.
3. Only then start `fail2ban`.
4. Immediately inspect status and confirm the `sshd` jail loaded correctly.

If your public IP is fixed, get it from your own computer first and then place it in `ignoreip`. Common commands:

```bash
curl https://ifconfig.me
```

or:

```bash
curl https://api.ipify.org
```

This must be your real public egress IP, not a local address such as `192.168.x.x`, `10.x.x.x`, or `172.16-31.x.x`.

If you switch networks often, for example:

- mobile hotspot
- dorm Wi-Fi
- campus network
- company VPN
- home broadband and phone data

then do not rely too much on permanently whitelisting your own IP, because your public egress IP may change often. In that case:

- prefer SSH keys and avoid repeated password guesses;
- keep one known-good SSH session open while editing;
- start with slightly looser values such as `maxretry = 8` and `bantime = 30m`, then tighten later;
- make sure you know how to use the cloud provider browser console or VNC console to recover access.

If you already banned yourself, run this from the cloud console or another still-open session:

```bash
sudo fail2ban-client status sshd
sudo fail2ban-client set sshd unbanip 198.51.100.24
```

If `recidive` banned you, also run:

```bash
sudo fail2ban-client status recidive
sudo fail2ban-client set recidive unbanip 198.51.100.24
```

To inspect the current banned IP list:

```bash
sudo fail2ban-client status sshd
sudo fail2ban-client status recidive
```

Start it and inspect status:

```bash
sudo systemctl enable fail2ban
sudo systemctl restart fail2ban
sudo systemctl status fail2ban
sudo fail2ban-client status
sudo fail2ban-client status sshd
sudo fail2ban-client status recidive
```

What it does:

- `sshd` handles short-window brute-force attempts;
- `recidive` handles sources that keep coming back after bans;
- `ignoreip` prevents your own fixed admin IP from being banned by mistake.

For "dirty IP" handling, use this priority:

1. Disable root login and move to a normal user with SSH keys.
2. Enable `ufw`.
3. Enable `fail2ban` for SSH brute-force blocking, and whitelist your own fixed admin IP with `ignoreip`.
4. If you use Cloudflare, enable WAF, Bot Fight Mode, or managed rules.
5. Only add manual deny rules for IPs or ranges you have actually observed as malicious.

Do not start by importing a huge random internet blacklist if you are new to server ops, because:

- it can block legitimate users behind school or company shared exit IPs;
- too many rules create extra maintenance cost;
- many public lists are outdated or low-quality.

If you need to block a confirmed malicious source manually:

```bash
sudo ufw deny from 203.0.113.10
```

If you later add an IP blacklist workflow from GitHub or your own deployment scripts and use a public feed such as [stamparm/ipsum](https://github.com/stamparm/ipsum), treat it as an extra layer, not your primary defense. A safer order is:

1. finish SSH keys, disable remote root login, enable `ufw`, and enable `fail2ban` first;
2. only pull the higher-confidence `ipsum` entries you understand and can justify, instead of importing the whole project blindly;
3. keep that logic in your own GitHub repo or deployment script with comments so you can update or roll it back later.

For example, if you only want to fetch a higher-confidence `ipsum` list first and review it before deciding what to block, you can do this on the Linux server:

```bash
curl -fsSL https://raw.githubusercontent.com/stamparm/ipsum/master/levels/4.txt -o /tmp/ipsum-level4.txt
```

If you want to keep only the IP column for later `ufw` or `ipset` handling:

```bash
awk '/^[0-9]/{print $1}' /tmp/ipsum-level4.txt > /tmp/ipsum-level4-ips.txt
```

Stop there first and sample the file before mass-importing it into your firewall. Do not automate thousands of `ufw deny` rules from an unreviewed list, or you can easily block legitimate shared exit IPs.

Check current rules:

```bash
sudo ufw status numbered
```

Delete by rule number after checking the list:

```bash
sudo ufw delete 3
```

For a beginner deployment, the main goal is not collecting lots of bad IPs. The main goal is to get these four things right:

- use a normal login user;
- allow SSH key login only;
- disable root remote login;
- let `fail2ban` absorb repeated brute-force attempts;
- know how to use `unbanip` if you accidentally ban yourself.

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
pip install gunicorn
```

Private repositories need SSH key or token setup.

## 5. Configure Environment Variables

First separate the three different "users" that often get mixed together:

| Name | Typical value | What it does | Where it belongs |
| --- | --- | --- | --- |
| Linux login user | `root`, `ubuntu`, `deploy` | The system account used for SSH login | Cloud console, `/etc/passwd`, SSH config |
| systemd runtime user | `deploy` | The Linux user that runs Gunicorn | `User=` / `Group=` in `/etc/systemd/system/video-meeting.service` |
| App admin username | `meetingadmin` | The website administrator account for `/admin` | `ADMIN_USERNAME` in `/opt/video-meeting/.env` |

These are different identities:

- `ssh root@server` uses the Linux system account, not the website admin account.
- `ADMIN_USERNAME=root` in `.env` only defines the web admin login name; it does not make Gunicorn run as root.
- `User=deploy` in `.service` only controls process permissions; it does not rename the web admin.

Keep the layers split like this:

| Config file | Recommended path | Owns this | Do not put this there |
| --- | --- | --- | --- |
| App environment file | `/opt/video-meeting/.env` | `SECRET_KEY`, `PUBLIC_HOST`, `LIVEKIT_*`, `ADMIN_*`, Turnstile, cookies, security flags | Do not put `User=` or `ExecStart=` here |
| systemd service file | `/etc/systemd/system/video-meeting.service` | `User=`, `Group=`, `WorkingDirectory=`, `EnvironmentFile=`, `ExecStart=`, restart policy | Do not keep business config as many `Environment=...` lines |
| Nginx site config | `/etc/nginx/sites-available/video-meeting` | domain, reverse proxy, upload limits, HTTPS, WebSocket headers | Do not put `LIVEKIT_API_SECRET` or `ADMIN_PASSWORD` |

Quick rule:

- Change `.env` for app behavior and secrets
- Change `.service` for process identity and startup
- Change Nginx for public entry and HTTPS

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

ADMIN_USERNAME=meetingadmin
ADMIN_PASSWORD=replace-with-strong-admin-password
ADMIN_EMAIL=admin@example.com
ADMIN_LOGIN_PATH=/manage-choose-a-long-random-path
PUBLIC_REGISTRATION_ENABLED=0
EMAIL_AUTH_ENABLED=1
EMAIL_SMTP_HOST=smtp.resend.com
EMAIL_SMTP_PORT=465
EMAIL_SMTP_USERNAME=resend
EMAIL_SMTP_PASSWORD=replace-with-resend-api-key
EMAIL_SMTP_USE_TLS=0
EMAIL_SMTP_USE_SSL=1
EMAIL_FROM_ADDRESS=noreply@meeting.example.com
EMAIL_FROM_NAME=Video Meeting

ADMIN_ALERT_EMAIL=admin@example.com
ADMIN_EMAIL_NOTIFY_ENABLED=1
ADMIN_NOTIFY_ON_USER_REGISTER=1
ADMIN_NOTIFY_ON_ROOM_JOIN=1
ADMIN_NOTIFY_ON_DANGEROUS_ACTIONS=1
ADMIN_ROOM_JOIN_NOTIFY_COOLDOWN_SECONDS=300

STRICT_SECURITY_CHECKS=1
TURNSTILE_SITE_KEY=replace-with-turnstile-site-key
TURNSTILE_SECRET_KEY=replace-with-turnstile-secret-key

SESSION_COOKIE_SECURE=1
REMEMBER_COOKIE_SECURE=1
SESSION_COOKIE_SAMESITE=Lax
REMEMBER_COOKIE_SAMESITE=Lax
EOF

chmod 600 /opt/video-meeting/.env
```

If you are logged in as `root`, or the directory is not yet owned by `deploy`, the safer version is:

```bash
sudo tee /opt/video-meeting/.env > /dev/null <<'EOF'
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=sqlite:////opt/video-meeting/instance/app.db

PUBLIC_SCHEME=https
PUBLIC_HOST=meeting.example.com

LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=replace-with-livekit-api-key
LIVEKIT_API_SECRET=replace-with-livekit-api-secret

ADMIN_USERNAME=meetingadmin
ADMIN_PASSWORD=replace-with-strong-admin-password
ADMIN_EMAIL=admin@example.com
ADMIN_LOGIN_PATH=/manage-choose-a-long-random-path
PUBLIC_REGISTRATION_ENABLED=0
EMAIL_AUTH_ENABLED=1
EMAIL_SMTP_HOST=smtp.resend.com
EMAIL_SMTP_PORT=465
EMAIL_SMTP_USERNAME=resend
EMAIL_SMTP_PASSWORD=replace-with-resend-api-key
EMAIL_SMTP_USE_TLS=0
EMAIL_SMTP_USE_SSL=1
EMAIL_FROM_ADDRESS=noreply@meeting.example.com
EMAIL_FROM_NAME=Video Meeting

ADMIN_ALERT_EMAIL=admin@example.com
ADMIN_EMAIL_NOTIFY_ENABLED=1
ADMIN_NOTIFY_ON_USER_REGISTER=1
ADMIN_NOTIFY_ON_ROOM_JOIN=1
ADMIN_NOTIFY_ON_DANGEROUS_ACTIONS=1
ADMIN_ROOM_JOIN_NOTIFY_COOLDOWN_SECONDS=300

STRICT_SECURITY_CHECKS=1
TURNSTILE_SITE_KEY=replace-with-turnstile-site-key
TURNSTILE_SECRET_KEY=replace-with-turnstile-secret-key

SESSION_COOKIE_SECURE=1
REMEMBER_COOKIE_SECURE=1
SESSION_COOKIE_SAMESITE=Lax
REMEMBER_COOKIE_SAMESITE=Lax
EOF

sudo chown deploy:deploy /opt/video-meeting/.env
sudo chmod 600 /opt/video-meeting/.env
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
| `ADMIN_EMAIL` | Admin account email; can be used on the separate admin login page; defaults to `ADMIN_ALERT_EMAIL` if omitted | Recommended |
| `ADMIN_LOGIN_PATH` | Separate admin login path, for example `/manage-choose-a-long-random-path`; the normal login page rejects admin accounts | Recommended online |
| `PUBLIC_REGISTRATION_ENABLED` | Whether anyone can self-register; disable it for public deployments | Recommended |
| `EMAIL_AUTH_ENABLED` | Enable the username/email + password + email-code verification auth flow | Optional |
| `EMAIL_SMTP_HOST` / `EMAIL_SMTP_PORT` | SMTP host and port | Required when email verification is enabled |
| `EMAIL_SMTP_USERNAME` / `EMAIL_SMTP_PASSWORD` | SMTP username and password; many providers use an API key here | Usually required when email verification is enabled |
| `EMAIL_SMTP_USE_TLS` / `EMAIL_SMTP_USE_SSL` | SMTP transport mode; common choices are `587 + TLS` or `465 + SSL` | Recommended when email verification is enabled |
| `EMAIL_FROM_ADDRESS` / `EMAIL_FROM_NAME` | Sender address and display name for verification emails | Required when email verification is enabled |
| `EMAIL_VERIFY_CODE_TTL_MINUTES` | Email-code lifetime, default `10` minutes | Optional |
| `EMAIL_CODE_SEND_LIMIT` | Max email-code sends allowed in one page window, default `2` | Optional |
| `EMAIL_CODE_SEND_WINDOW_SECONDS` | Time window used for resend counting; defaults to the code lifetime window | Optional |
| `ADMIN_ALERT_EMAIL` | Email inbox that receives admin alerts; keep it only in server-side `.env`, never commit it to Git; also becomes the admin account email if `ADMIN_EMAIL` is omitted | Required when alerts are enabled |
| `ADMIN_EMAIL_NOTIFY_ENABLED` | Enable admin email alerts; uses the same SMTP delivery settings | Optional |
| `ADMIN_NOTIFY_ON_USER_REGISTER` | Notify the admin when a new user registers successfully, default `1` | Optional |
| `ADMIN_NOTIFY_ON_ROOM_JOIN` | Notify the admin when a user joins a meeting room, default `1` | Optional |
| `ADMIN_NOTIFY_ON_DANGEROUS_ACTIONS` | Notify the admin when high-risk admin actions occur, such as kicking/deleting users, password resets, disabling/enabling accounts, password-reset request updates, and ending/deleting meetings | Optional |
| `ADMIN_ROOM_JOIN_NOTIFY_COOLDOWN_SECONDS` | Cooldown for duplicate room-join alerts from the same user in the same room, default `300` seconds | Optional |
| `ADMIN_SECURITY_LINK_TTL_MINUTES` | Lifetime of the admin security lockdown / ignore links, default about `5 years`; the intended flow is to keep them valid until used or ignored | Optional |
| `STRICT_SECURITY_CHECKS` | Refuse weak `SECRET_KEY` / `ADMIN_*` settings at startup | Recommended online |
| `TURNSTILE_SITE_KEY` / `TURNSTILE_SECRET_KEY` | Human verification for login/register/password reset | Optional |
| `TURN_PUBLIC_HOST` | Public host used when generating TURN/STUN addresses | Optional |
| `TURN_URLS` | Custom TURN/STUN URLs, comma-separated | Optional |
| `TURN_USERNAME` / `TURN_PASSWORD` | TURN relay credentials; usually required when `TURN_URLS` is set | Optional |
| `SESSION_COOKIE_SECURE` / `REMEMBER_COOKIE_SECURE` | Send cookies over HTTPS only | Recommended for HTTPS |

Notes:

- Do not commit `.env`.
- Keep `.env` at permission `600`, ideally owned by the runtime Linux user such as `deploy`.
- For public deployments, set `PUBLIC_REGISTRATION_ENABLED=0` so anyone cannot create accounts directly.
- For public deployments, set `STRICT_SECURITY_CHECKS=1` so weak `SECRET_KEY`, weak admin passwords, and the default `root` admin name are rejected at startup.
- Admin and normal-user login are now separated: normal users use `/login`; administrators use the `ADMIN_LOGIN_PATH` from `.env`. Do not publish that path in README home pages, navigation, or public commits.
- Do not reuse the Linux login name just because you SSH as `root`; that is unrelated to `ADMIN_USERNAME`.
- If you enable `EMAIL_AUTH_ENABLED=1`, make sure SMTP delivery is configured correctly; registration codes and password-reset codes are sent directly by email.
- Admin alerts reuse the same SMTP settings: set `ADMIN_EMAIL_NOTIFY_ENABLED=1` and `ADMIN_ALERT_EMAIL=your-admin@example.com` to receive alerts for new registrations, room joins, and high-risk admin actions. `ADMIN_ALERT_EMAIL` is the alert inbox; `ADMIN_EMAIL` is the admin account email and defaults to `ADMIN_ALERT_EMAIL`, so you can sign in on the separate admin login page with that email + `ADMIN_PASSWORD`. Keep the admin inbox only in the server `.env`; do not commit it to GitHub.
- If your users are mainly in mainland China, test `challenges.cloudflare.com` from a real mainland network before enforcing Turnstile.
- Restart the service after changing `.env`; the `systemd` section below will do that.
- If LiveKit values are missing, room pages intentionally return `503`.
- Runtime data lives under `instance/`; include it in backups.

### 5.1 Email Verification Registration / Login

The current code now supports an optional email-code verification flow:

- the register page collects `username + email + password`
- after the human check passes, the app sends a 6-digit email code
- each page window allows at most two sends; after the first send, the button changes to `Resend code`
- the account is created only after the email code is verified
- legacy unverified accounts can sign in directly with `bound email + code`
- the forgot-password page still reuses the same SMTP setup to send password-reset codes

The easiest setup is SMTP. You can point it at your own domain mailbox or a provider SMTP endpoint.

If you want a low-friction Resend setup, the rough order is:

1. Create a Resend account and verify your sender domain, such as `noreply@your-domain`.
2. Add the SPF / DKIM DNS records shown in the Resend dashboard.
3. Create an API key in Resend.
4. Fill these values in `.env`:

```env
EMAIL_AUTH_ENABLED=1
EMAIL_SMTP_HOST=smtp.resend.com
EMAIL_SMTP_PORT=465
EMAIL_SMTP_USERNAME=resend
EMAIL_SMTP_PASSWORD=re_xxxxxxxxx
EMAIL_SMTP_USE_TLS=0
EMAIL_SMTP_USE_SSL=1
EMAIL_FROM_ADDRESS=noreply@meeting.example.com
EMAIL_FROM_NAME=Video Meeting

ADMIN_ALERT_EMAIL=admin@example.com
ADMIN_EMAIL_NOTIFY_ENABLED=1
ADMIN_NOTIFY_ON_USER_REGISTER=1
ADMIN_NOTIFY_ON_ROOM_JOIN=1
ADMIN_NOTIFY_ON_DANGEROUS_ACTIONS=1
ADMIN_ROOM_JOIN_NOTIFY_COOLDOWN_SECONDS=300
EMAIL_VERIFY_CODE_TTL_MINUTES=10

ADMIN_ALERT_EMAIL=admin@example.com
ADMIN_EMAIL_NOTIFY_ENABLED=1
ADMIN_NOTIFY_ON_USER_REGISTER=1
ADMIN_NOTIFY_ON_ROOM_JOIN=1
ADMIN_NOTIFY_ON_DANGEROUS_ACTIONS=1
ADMIN_ROOM_JOIN_NOTIFY_COOLDOWN_SECONDS=300
```

If you use Brevo, a company mailbox, or another SMTP provider, replace the host, port, username, password, and transport mode with that provider's values. The two common combinations are:

- `465 + SSL`
- `587 + TLS`

Do not try to run both `EMAIL_SMTP_USE_TLS=1` and `EMAIL_SMTP_USE_SSL=1` as the primary mode at the same time. In most cases, pick one.

Minimum manual test after setup:

1. Restart the service: `sudo systemctl restart video-meeting`
2. Register a new normal account with a real email
3. Confirm the verification-code email arrives in inbox or spam
4. Enter the 6-digit code from the email and confirm registration finishes successfully
5. Sign in once with the username, then once with the email
6. Submit one forgot-password request, confirm the reset code email arrives, and set a new password successfully
7. Sign in with one legacy unverified account through `bound email + code` and confirm the email verification state is completed during login

If mail does not arrive, check these first:

- whether `EMAIL_FROM_ADDRESS` has already been verified by the provider
- whether SMTP delivery is working and whether `EMAIL_FROM_ADDRESS` is accepted by the provider
- whether the provider DNS verification is complete
- whether `journalctl -u video-meeting -n 100 --no-pager` shows SMTP authentication or connection errors

### 5.2 Which file owns which setting

Keep these boundaries stable:

| What you want to change | Correct file | Common mistake |
| --- | --- | --- |
| Change the public domain or public scheme | `PUBLIC_HOST` / `PUBLIC_SCHEME` in `/opt/video-meeting/.env` | Editing `User=` or changing only Nginx but not app config |
| Rotate LiveKit API key / secret | `/opt/video-meeting/.env` | Putting them in Nginx or hardcoding them in `.service` |
| Change the web admin username/password | `/opt/video-meeting/.env` | Assuming the Linux username must change too |
| Change Gunicorn bind address or startup command | `ExecStart=` in `.service` | Editing only `.env` and forgetting Nginx `proxy_pass` |
| Change which Linux user runs Gunicorn | `User=` / `Group=` in `.service` | Adding `USER=deploy` to `.env` and expecting it to work |
| Change HTTPS and reverse proxy behavior | Nginx config | Editing `.env` and expecting Nginx to read it |

If the server is already messy, inspect all three layers first:

```bash
sudo systemctl cat video-meeting
sudo sed -n '1,120p' /opt/video-meeting/.env
sudo nginx -T | sed -n '1,220p'
```

Then normalize them with this rule:

- `.env` holds app config and secrets
- `.service` holds process startup and identity
- Nginx holds public edge config

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
ExecStart=/opt/video-meeting/venv/bin/gunicorn --worker-class gthread --workers 1 --threads 100 --bind 127.0.0.1:8000 app:app
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
- `User=deploy` / `Group=deploy` refer to the Linux process identity, not the website admin account.
- The current code hardcodes `SocketIO(async_mode="threading")`, so Gunicorn threaded workers plus `simple-websocket` are a better match than the older `eventlet` wording.
- Keep `--workers 1`; current online room state is in process memory.
- `--threads 100` follows the common threaded-worker example in the Flask-SocketIO deployment docs and is usually enough for a class demo or a small showcase.
- `--bind 127.0.0.1:8000` must match Nginx `proxy_pass`.
- If you change `User=`, follow the "How to set permissions" section below at the same time.

### 6.1 How to set permissions

Keep one simple rule in mind:

- `root` handles package install, systemd, and Nginx.
- The web app itself should run as a normal Linux user such as `deploy`.

Why the example uses `deploy`:

- It is only the example name for the runtime Linux user, not a systemd requirement.
- Running Gunicorn as a dedicated normal user makes it easier to control permissions for the project directory, database, uploads, and `.env`.
- Even if you usually log in as `root` or `ubuntu`, the service itself can still run as `deploy`.

If you prefer another normal user such as `ubuntu`, `ec2-user`, or `meetingapp`, that is also fine. Only follow these two rules:

1. Change `User=` / `Group=` to that real username.
2. Make `/opt/video-meeting`, `venv/`, `.env`, and `instance/` readable and writable by that user.

Do not keep the service running as `root` unless you have a very specific reason. It may start, but uploads, SQLite files, and runtime directories will become root-owned, which is the most common cause of later permission problems.

The recommended setup is to create one runtime user and give the project directory to it:

```bash
sudo adduser deploy
sudo chown -R deploy:deploy /opt/video-meeting
sudo chmod 755 /opt/video-meeting
sudo chmod 755 /opt/video-meeting/venv
sudo chmod 700 /opt/video-meeting/instance
sudo chmod 600 /opt/video-meeting/.env
```

Then keep these lines in the service file:

```ini
User=deploy
Group=deploy
```

If you do not want a separate user and want to use your existing login user `ubuntu`, replace the username consistently:

```bash
sudo chown -R ubuntu:ubuntu /opt/video-meeting
sudo chmod 755 /opt/video-meeting
sudo chmod 755 /opt/video-meeting/venv
sudo chmod 700 /opt/video-meeting/instance
sudo chmod 600 /opt/video-meeting/.env
```

```ini
User=ubuntu
Group=ubuntu
```

What these permissions mean:

- `/opt/video-meeting` with `755`: the runtime user can write, while other system users can enter the directory and read normal code files.
- `venv/` with `755`: the service can execute `gunicorn` inside the virtualenv.
- `instance/` with `700`: only the runtime user can read and write the database, uploads, and other runtime data.
- `.env` with `600`: only the runtime user can read and write secrets.

After setting permissions, check at least these four things:

```bash
sudo systemctl cat video-meeting
ps -o user,group,pid,cmd -C gunicorn
ls -ld /opt/video-meeting /opt/video-meeting/venv /opt/video-meeting/instance
ls -l /opt/video-meeting/.env
```

You should see:

- the same normal user in `User=` and `Group=`
- the `gunicorn` process running as that user
- `/opt/video-meeting`, `instance/`, and `.env` owned by that user

The two most common permission mistakes are:

- `.env` is still `root root` with mode `600`, so Gunicorn cannot read environment variables.
- `instance/` is still `root root`, so SQLite or uploads cannot write files.

### 6.2 Reload and verify the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable video-meeting
sudo systemctl restart video-meeting
sudo systemctl status video-meeting --no-pager -l
```

Logs:

```bash
journalctl -u video-meeting -n 100 --no-pager
journalctl -u video-meeting -f
```

If `systemctl status video-meeting` shows `python app.py`, `This is a development server`, or `Werkzeug appears to be used in a production deployment`, the server is not using the correct production shape yet. Return to the `gunicorn + threads + systemd` setup above.

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
python -m py_compile app.py translations.py i18n/translations.py scripts/check_i18n.py
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
pip install gunicorn
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
| `Permission denied (publickey)` | The server is already enforcing key login, but the target user's `~/.ssh/authorized_keys`, permissions, or your local private key does not match; revert the SSH hardening first instead of retrying blindly |
| `Connection timed out` | Check public IP, port 22, security group, and local network firewall |
| `Connection refused` | SSH is not listening on that port, or `ufw` / the security group does not allow the port you are trying |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | Common after reinstalling a server or reusing an IP; verify safety, then remove the old `known_hosts` entry |

## 17. References

This guide combines the current project code with these official or reliable documents. Official docs remain the source of truth. If you also want a practical tutorial to follow line by line, the two DigitalOcean guides below are the most useful supplements:

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
| Ubuntu UFW | [Ubuntu Uncomplicated Firewall](https://documentation.ubuntu.com/server/how-to/security/firewalls/) |
| Fail2ban | [Fail2ban Documentation](https://fail2ban.readthedocs.io/en/latest/) |
| DigitalOcean initial server setup | [Initial Server Setup on Ubuntu](https://www.digitalocean.com/community/tutorials/initial-server-setup-with-ubuntu) |
| DigitalOcean Flask + Gunicorn + Nginx | [How To Serve Flask Applications with Gunicorn and Nginx on Ubuntu](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-22-04) |
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
