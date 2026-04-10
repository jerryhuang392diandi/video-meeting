# 部署与更新手册 / Deployment and Update Guide

这份文档用于替代原来的 `git_server_update_checklist.txt`。目标不是保留一份危险的“一把梭命令”，而是把本地提交、服务器更新、依赖变更、服务重启和排障流程整理成更安全、适合 GitHub 阅读的 Markdown 版本。

This guide replaces the old `git_server_update_checklist.txt`. The goal is not to preserve a risky one-line command, but to document local Git workflow, server updates, dependency refresh, service restart, and troubleshooting in a safer Markdown format that reads well on GitHub.

## 1. 适用前提 / Assumptions

- 服务器项目目录示例：`/opt/video-meeting`
- Python 虚拟环境示例：`/opt/video-meeting/venv`
- 进程管理示例：`systemd` 服务名为 `video-meeting`
- 默认分支示例：`main`

Adjust these paths and names to your actual deployment environment.

## 2. 本地更新与推送 / Local Update and Push

### 推荐流程 / Recommended Flow

```bash
git status
git pull --rebase origin main
git add .
git commit -m "Describe the change"
git push origin main
```

中文说明：

- `git pull --rebase` 比直接 merge 更适合保持历史整洁
- 提交前先确认没有把运行时文件、临时录屏或数据库文件误加进去
- 如果只改了文档，也建议写清楚提交说明

English notes:

- `git pull --rebase` usually keeps history cleaner than a merge pull
- Check that runtime files, recordings, or database artifacts are not staged by mistake
- Use a meaningful commit message even for documentation changes

## 3. 服务器更新流程 / Server Update Flow

### 标准步骤 / Standard Steps

```bash
cd /opt/video-meeting
git status
git pull origin main
source /opt/video-meeting/venv/bin/activate
pip install -r requirements.txt
systemctl restart video-meeting
systemctl status video-meeting
```

中文说明：

- 不建议默认使用 `git clean -fd`，因为它会直接删除未跟踪文件，容易误删运行时内容或人工补充文件
- 如果确认这次没有依赖变化，可以跳过 `pip install -r requirements.txt`
- 重启后先看 `systemctl status`，再决定是否继续追日志

English notes:

- Do not default to `git clean -fd`; it can delete untracked runtime files or manual server-side additions
- If dependencies did not change, you may skip `pip install -r requirements.txt`
- Check `systemctl status` immediately after restart before deeper troubleshooting

## 4. 仅代码更新时 / When Only Application Code Changed

```bash
cd /opt/video-meeting
git pull origin main
source /opt/video-meeting/venv/bin/activate
systemctl restart video-meeting
systemctl status video-meeting
```

## 5. 依赖变更时 / When Dependencies Changed

```bash
cd /opt/video-meeting
git pull origin main
source /opt/video-meeting/venv/bin/activate
pip install -r requirements.txt
systemctl restart video-meeting
systemctl status video-meeting
```

如果这次改动涉及以下能力，更要确认服务器依赖齐全：

- `LIVEKIT_URL`、`LIVEKIT_API_KEY`、`LIVEKIT_API_SECRET`
- `ffmpeg`
- 正确的 `PUBLIC_HOST` / `PUBLIC_SCHEME`

If the change touches these areas, verify the related server prerequisites carefully:

- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
- `ffmpeg`
- correct `PUBLIC_HOST` / `PUBLIC_SCHEME`

## 6. 查看运行状态 / Inspect Service Health

### 服务状态 / Service Status

```bash
systemctl status video-meeting
```

### 最近日志 / Recent Logs

```bash
journalctl -u video-meeting -n 100 --no-pager
```

### 实时追踪日志 / Follow Logs

```bash
journalctl -u video-meeting -f
```

## 7. 修改了 systemd 配置时 / If systemd Config Changed

```bash
systemctl daemon-reload
systemctl restart video-meeting
systemctl status video-meeting
```

## 8. 线上更新后的最小验证 / Minimum Post-Deploy Verification

中文：

每次更新后，至少做下面这些检查，不要只看到服务重启成功就结束：

1. 打开首页，确认登录页与首页都能正常访问
2. 登录一个普通用户，创建房间并成功进入
3. 确认房间页没有出现 LiveKit 未配置的 `503` 提示
4. 两个设备互相进房，确认首次加入就能看到对方媒体
5. 测试聊天、附件上传、附件查看或下载
6. 如改动涉及共享或录屏，测试屏幕共享和录屏导出
7. 如改动涉及管理员功能，确认 `/admin` 可正常打开

English:

After each deployment, do not stop at “the service restarted.” At minimum:

1. Open the landing and login pages
2. Log in as a normal user and enter a room
3. Confirm the room page does not fail with the LiveKit `503` path
4. Join from two devices and verify media works on first join
5. Test chat, attachment upload, and attachment access
6. If the change touched sharing or recording, test those explicitly
7. If admin functionality changed, confirm `/admin` still works

## 9. 常用排障方向 / Common Troubleshooting Directions

### 房间打不开 / Room Fails to Open

- 检查 `LIVEKIT_URL`、`LIVEKIT_API_KEY`、`LIVEKIT_API_SECRET`
- 查看应用日志里是否出现 `503` 或 token 生成异常

### 有页面但没有媒体 / Page Loads but Media Fails

- 检查 LiveKit 是否可达
- 检查浏览器是否授予麦克风/摄像头权限
- 双端测试确认不是单端设备问题

### 录屏导出失败 / Recording Export Fails

- 检查服务器是否安装 `ffmpeg`
- 检查日志是否出现 remux 失败
- 注意浏览器可能先产出 `webm`，不是所有环境都能直接生成 `mp4`

### 附件相关问题 / Attachment Issues

- 检查 `instance/` 下上传目录权限
- 确认不是“仅查看”权限导致无法下载
- 检查文件类型是否属于浏览器可直接预览范围

## 10. 不建议保留的旧习惯 / Old Habits to Avoid

- 不要习惯性执行 `git clean -fd`
- 不要在不看日志的前提下反复重启服务
- 不要把生产目录里的运行时文件和仓库版本文件混为一谈
- 不要只测单端页面加载，不测双端进房和媒体链路

Avoid:

- running `git clean -fd` by reflex
- repeatedly restarting without reading logs
- mixing runtime artifacts with tracked repository files
- validating only page load without testing two-device media flow
