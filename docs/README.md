<a id="docs-readme-zh"></a>

# 文档地图

[中文](#docs-readme-zh) | [English](#docs-readme-en)

这里放项目说明、部署手册、稳定性审计和课程答辩材料。根目录 [README.md](../README.md) 是项目入口；本文件只负责告诉你该读哪一份文档。

## 推荐阅读顺序

1. [../README.md](../README.md): 先了解项目功能、完整使用入口、零基础快速开始步骤和关键配置。
2. [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) / [English](DEPLOYMENT_GUIDE.md#deployment-and-update-guide): 准备购买云服务器、首次部署、更新服务器、使用 Git 管理三端代码或排查线上问题时阅读。包含云厂商入口、国内备案提醒、Windows/macOS/FinalShell 登录、Nginx、HTTPS、systemd、LiveKit Cloud 和自建 LiveKit 说明。
3. [STABILITY_AUDIT.md](STABILITY_AUDIT.md) / [English](STABILITY_AUDIT.md#stability-audit): 改房间、媒体、屏幕共享、录屏或部署架构前阅读。
4. [REFACTOR_AUDIT.md](REFACTOR_AUDIT.md) / [English](REFACTOR_AUDIT.md#refactor-audit): 准备拆分 `app.py`、房间脚本或共享状态逻辑前阅读。
5. [项目说明与代码索引.md](%E9%A1%B9%E7%9B%AE%E8%AF%B4%E6%98%8E%E4%B8%8E%E4%BB%A3%E7%A0%81%E7%B4%A2%E5%BC%95.md) / [English](%E9%A1%B9%E7%9B%AE%E8%AF%B4%E6%98%8E%E4%B8%8E%E4%BB%A3%E7%A0%81%E7%B4%A2%E5%BC%95.md#project-guide-and-code-index): 准备课程展示、口头讲解或代码跟读时阅读。

## 文档职责

| 文档 | 用途 | 适合读者 |
| --- | --- | --- |
| [../README.md](../README.md) / [English](../README.md#video-meeting-system) | 项目总览、完整页面入口、中英文和移动/桌面适配状态、快速开始、本地依赖安装、本地启动、配置和基本检查 | 第一次打开项目的人 |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) / [English](DEPLOYMENT_GUIDE.md#deployment-and-update-guide) | 云服务器购买入口、备案、SSH/FinalShell 登录、DNS/Cloudflare、Nginx、WebSocket、HTTPS、LiveKit Cloud、自建 LiveKit、systemd、Git 三端协作、服务更新、日志排查和官方参考资料 | 部署和维护项目的人，尤其是第一次部署的人 |
| [STABILITY_AUDIT.md](STABILITY_AUDIT.md) / [English](STABILITY_AUDIT.md#stability-audit) | 当前架构边界、风险、回归重点和演进方向 | 修改核心逻辑的人 |
| [REFACTOR_AUDIT.md](REFACTOR_AUDIT.md) / [English](REFACTOR_AUDIT.md#refactor-audit) | 当前重构巡检结论、优先级、推荐拆分顺序和改动前检查 | 准备重构或长期维护的人 |
| [项目说明与代码索引.md](%E9%A1%B9%E7%9B%AE%E8%AF%B4%E6%98%8E%E4%B8%8E%E4%BB%A3%E7%A0%81%E7%B4%A2%E5%BC%95.md) / [English](%E9%A1%B9%E7%9B%AE%E8%AF%B4%E6%98%8E%E4%B8%8E%E4%BB%A3%E7%A0%81%E7%B4%A2%E5%BC%95.md#project-guide-and-code-index) | 项目逻辑、核心流程、代码索引和常见问题回答 | 准备展示或维护代码的人 |
| `视觉媒体通信期末大作业实践报告.docx` | 课程报告原稿归档 | 需要提交课程材料的人 |

## 维护规则

- 行为变化优先更新根 README。
- 部署命令、环境变量或服务管理方式变化时更新 `DEPLOYMENT_GUIDE.md`。
- 房间状态、LiveKit、屏幕共享、录屏、虚拟背景相关变化时更新 `STABILITY_AUDIT.md`。
- 中英文文案、移动端扫码、移动端聊天布局、桌面端会议网格或设备默认策略变化时，同步更新根 README 和项目说明文档。
- 重构优先级、拆分顺序或模块边界变化时更新 `REFACTOR_AUDIT.md`。
- 课程展示口径、核心流程或代码索引变化时更新 `项目说明与代码索引.md`。
- `.docx` 报告是归档材料，除非明确需要重新出报告，否则不要把它当作代码文档同步更新。


---

<a id="docs-readme-en"></a>

# Documentation Map

[中文](#docs-readme-zh) | [English](#docs-readme-en)

This folder contains the project overview, deployment guide, stability audit, and course presentation notes. The root [README](../README.md#video-meeting-system) is the project entry point; this file only explains which document to read.

## Recommended Reading Order

1. [../README.md#video-meeting-system](../README.md#video-meeting-system): project features, complete page entry points, beginner Quick Start, and key configuration.
2. [DEPLOYMENT_GUIDE.md#deployment-and-update-guide](DEPLOYMENT_GUIDE.md#deployment-and-update-guide): read before buying a cloud server, first deployment, Git-based three-side code updates, server updates, or production troubleshooting. It covers cloud providers, ICP filing notes, Windows/macOS/FinalShell SSH login, Nginx, HTTPS, systemd, LiveKit Cloud, and self-hosted LiveKit.
3. [STABILITY_AUDIT.md#stability-audit](STABILITY_AUDIT.md#stability-audit): read before changing room logic, media logic, screen sharing, recording, or deployment architecture.
4. [REFACTOR_AUDIT.md#refactor-audit](REFACTOR_AUDIT.md#refactor-audit): read before splitting `app.py`, the room script, or shared state logic.
5. [Project Guide and Code Index](%E9%A1%B9%E7%9B%AE%E8%AF%B4%E6%98%8E%E4%B8%8E%E4%BB%A3%E7%A0%81%E7%B4%A2%E5%BC%95.md#project-guide-and-code-index): read before course presentation, oral explanation, or code walkthrough.

## Document Responsibilities

| Document | Purpose | Audience |
| --- | --- | --- |
| [../README.md](../README.md) / [English](../README.md#video-meeting-system) | Project overview, complete page entry points, i18n and mobile/desktop adaptation status, Quick Start, local tool installation, local startup, configuration, and basic checks | First-time readers |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) / [English](DEPLOYMENT_GUIDE.md#deployment-and-update-guide) | Cloud provider entry points, ICP filing notes, SSH/FinalShell login, DNS/Cloudflare, Nginx, WebSocket, HTTPS, LiveKit Cloud, self-hosted LiveKit, systemd, Git three-side workflow, service updates, log troubleshooting, and official references | Deployers and maintainers, especially first-time deployers |
| [STABILITY_AUDIT.md](STABILITY_AUDIT.md) / [English](STABILITY_AUDIT.md#stability-audit) | Architecture boundaries, risks, regression focus, and future direction | People changing core logic |
| [REFACTOR_AUDIT.md](REFACTOR_AUDIT.md) / [English](REFACTOR_AUDIT.md#refactor-audit) | Current refactor audit, priorities, recommended split order, and pre-change checks | People planning refactors or long-term maintenance |
| [项目说明与代码索引.md](%E9%A1%B9%E7%9B%AE%E8%AF%B4%E6%98%8E%E4%B8%8E%E4%BB%A3%E7%A0%81%E7%B4%A2%E5%BC%95.md) / [English](%E9%A1%B9%E7%9B%AE%E8%AF%B4%E6%98%8E%E4%B8%8E%E4%BB%A3%E7%A0%81%E7%B4%A2%E5%BC%95.md#project-guide-and-code-index) | Project logic, core flows, code index, and common Q&A | Presenters and maintainers |
| `视觉媒体通信期末大作业实践报告.docx` | Archived course report source | Course submission readers |

## Maintenance Rules

- Update the root README first when project behavior changes.
- Update `DEPLOYMENT_GUIDE.md` when deployment commands, environment variables, or service management changes.
- Update `STABILITY_AUDIT.md` when room state, LiveKit, screen sharing, recording, or virtual background behavior changes.
- Update the root README and project guide when UI text, mobile QR join, mobile chat layout, desktop meeting grid, or default device behavior changes.
- Update `REFACTOR_AUDIT.md` when refactor priorities, split order, or module boundaries change.
- Update `项目说明与代码索引.md` when presentation wording, core flows, or code index changes.
- The `.docx` report is archived material; do not treat it as live code documentation unless a new report is explicitly required.
