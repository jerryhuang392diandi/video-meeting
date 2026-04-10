# 文档导航 / Documentation Hub

这个目录存放项目当前版本的配套说明文档。除课程报告 `.docx` 外，其余文档已按当前代码状态重新整理，尽量采用中文主叙述，并补充英文说明，方便在 GitHub 上直接阅读。

This directory contains the supporting documentation for the current project state. Except for the course report `.docx`, the other documents have been rewritten around the current codebase, with Chinese as the primary language and English added for GitHub readability.

## 文档列表 / Documents

### [../README.md](../README.md)

- 中文：仓库主页文档，适合第一次打开项目时快速了解功能、架构、运行方式和环境变量。
- English: The repository landing page for a quick understanding of features, architecture, setup, and environment variables.

### [STABILITY_AUDIT.md](STABILITY_AUDIT.md)

- 中文：围绕当前 `Flask + Socket.IO + LiveKit` 架构整理的稳定性审计，重点关注单进程在线态、Socket.IO 与 LiveKit 的一致性、屏幕共享、虚拟背景、录屏和后续演进风险。
- English: A stability audit for the current `Flask + Socket.IO + LiveKit` architecture, focusing on single-process runtime state, Socket.IO and LiveKit consistency, screen sharing, virtual background, recording, and future evolution risks.

### [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

- 中文：把原来的纯文本更新清单改写为 Markdown 部署手册，覆盖本地提交流程、服务器更新流程、依赖更新、systemd 管理与日志排查。
- English: A Markdown deployment guide that replaces the old plain-text checklist, covering local Git workflow, server updates, dependency refresh, systemd management, and log troubleshooting.

### [答辩讲解文档.md](%E7%AD%94%E8%BE%A9%E8%AE%B2%E8%A7%A3%E6%96%87%E6%A1%A3.md)

- 中文：面向课程答辩的讲解稿，按“项目是什么、为什么这样做、代码怎么分工、局限在哪里”组织，也保留了“为什么不用 C 语言”的回答素材。
- English: Defense notes for a course presentation, organized around what the project is, why it was built this way, how the code is split, what the limitations are, and why C was not chosen.

### `视觉媒体通信期末大作业实践报告.docx`

- 中文：课程报告 Word 原稿，本次不改写，只保留归档。
- English: The original course report in Word format. It is intentionally preserved and not rewritten in this pass.

## 阅读建议 / Recommended Reading Order

1. 先看根目录 `README.md`
2. 再看 `STABILITY_AUDIT.md`
3. 如果要部署或更新服务器，再看 `DEPLOYMENT_GUIDE.md`
4. 如果要准备答辩，再看 `答辩讲解文档.md`

Suggested order:

1. Start with the root `README.md`
2. Then read `STABILITY_AUDIT.md`
3. Use `DEPLOYMENT_GUIDE.md` for deployment and update work
4. Use `答辩讲解文档.md` when preparing for a presentation or defense
