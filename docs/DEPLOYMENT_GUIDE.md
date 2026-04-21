# 部署与更新手册

这份文档用于部署、更新和排查当前 `Flask + Flask-SocketIO + LiveKit` 会议系统。示例路径和服务名可以按你的服务器实际情况替换。

## 部署前提

| 项 | 示例 |
| --- | --- |
| 项目目录 | `/opt/video-meeting` |
| 虚拟环境 | `/opt/video-meeting/venv` |
| systemd 服务名 | `video-meeting` |
| 默认分支 | `main` |
| Python 依赖 | `requirements.txt` |

必须确认：

- `LIVEKIT_URL`、`LIVEKIT_API_KEY`、`LIVEKIT_API_SECRET` 已配置。
- `SECRET_KEY` 已配置为稳定值，不要每次重启变化。
- `PUBLIC_HOST` 和 `PUBLIC_SCHEME` 与真实访问地址一致。
- 如果需要 MP4 导出，服务器已安装 `ffmpeg`。
- 当前在线态主要在单进程内存中，默认不要按多实例横向扩展部署。

## 本地提交流程

```bash
git status
git pull --rebase origin main
git add .
git commit -m "Improve documentation"
git push origin main
```

提交前检查：

- 不要提交 `instance/`、数据库、上传文件、临时录屏或本地虚拟环境。
- 只改文档也要写清楚提交信息。
- 如果改了模板文案，运行 `python check_i18n.py`。

## 服务器标准更新

```bash
cd /opt/video-meeting
git status
git pull origin main
source /opt/video-meeting/venv/bin/activate
pip install -r requirements.txt
systemctl restart video-meeting
systemctl status video-meeting
```

说明：

- 没有依赖变化时可以跳过 `pip install -r requirements.txt`。
- 不要默认执行 `git clean -fd`，它会删除未跟踪文件，容易误删运行时内容。
- 重启后先看 `systemctl status`，再根据日志继续排查。

## 只更新代码

```bash
cd /opt/video-meeting
git pull origin main
source /opt/video-meeting/venv/bin/activate
systemctl restart video-meeting
systemctl status video-meeting
```

## 更新依赖

```bash
cd /opt/video-meeting
git pull origin main
source /opt/video-meeting/venv/bin/activate
pip install -r requirements.txt
systemctl restart video-meeting
systemctl status video-meeting
```

依赖变化后重点验证：

- LiveKit token 能正常生成。
- 房间页不会走 LiveKit 未配置的 `503` 路径。
- 录屏导出相关功能在有 `ffmpeg` 的服务器上仍可用。

## 修改 systemd 配置后

```bash
systemctl daemon-reload
systemctl restart video-meeting
systemctl status video-meeting
```

## 日志与状态

```bash
systemctl status video-meeting
journalctl -u video-meeting -n 100 --no-pager
journalctl -u video-meeting -f
```

排查顺序建议：

1. 先看服务是否启动成功。
2. 再看最近 100 行日志。
3. 复现问题时用 `journalctl -f` 实时追踪。
4. 房间媒体问题要同时看应用日志、浏览器控制台和 LiveKit 服务状态。

## 更新后最小验证

每次线上更新后至少检查：

- 首页、登录页、注册页可访问。
- 普通用户能登录、创建房间并进入房间。
- 两个设备能互相进房，首次加入即可看到远端媒体。
- 摄像头、麦克风、屏幕共享开始和停止可用。
- 聊天、附件上传、附件预览或下载权限正常。
- 管理员后台 `/admin` 可打开，常用操作正常。
- 中英文界面没有明显缺失文案。

如果本次改动涉及屏幕共享，还要额外验证：

- 共享中刷新页面不会留下错误的共享者状态。
- 共享停止后远端布局能恢复。
- 移动端至少能稳定看到远端共享内容。

## 常见问题

### 房间返回 503

优先检查：

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- 应用日志里的 token 生成异常

### 页面能打开但没有媒体

优先检查：

- 浏览器是否允许摄像头和麦克风。
- LiveKit 服务是否可达。
- `PUBLIC_HOST` / `PUBLIC_SCHEME` 是否导致前端连接地址错误。
- 是否只有单端设备异常，还是双端都失败。

### 附件上传或下载异常

优先检查：

- `instance/` 下上传目录权限。
- 附件是否被设置为仅查看。
- 文件类型是否支持浏览器预览。

### 录屏导出失败

优先检查：

- 服务器是否安装 `ffmpeg`。
- 日志是否出现 remux 失败。
- 浏览器原始输出格式是否为 `webm`。

## 不建议的操作

- 不要在生产目录里习惯性执行 `git clean -fd`。
- 不要反复重启服务但不看日志。
- 不要把运行时数据库、上传文件和仓库文件混在一起管理。
- 不要只测页面加载，房间媒体必须做双端验证。
