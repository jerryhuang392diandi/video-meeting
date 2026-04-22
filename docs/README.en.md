# Documentation Map

[中文](README.md) | [English](README.en.md)

This folder contains the project overview, deployment guide, stability audit, and course presentation notes. The root [README.en.md](../README.en.md) is the project entry point; this file only explains which document to read.

## Recommended Reading Order

1. [../README.en.md](../README.en.md): project features, complete page entry points, beginner Quick Start, and key configuration.
2. [DEPLOYMENT_GUIDE.en.md](DEPLOYMENT_GUIDE.en.md): read before buying a cloud server, first deployment, Git-based three-side code updates, server updates, or production troubleshooting. It covers cloud providers, ICP filing notes, Windows/macOS/FinalShell SSH login, Nginx, HTTPS, systemd, LiveKit Cloud, and self-hosted LiveKit.
3. [STABILITY_AUDIT.en.md](STABILITY_AUDIT.en.md): read before changing room logic, media logic, screen sharing, recording, or deployment architecture.
4. [REFACTOR_AUDIT.en.md](REFACTOR_AUDIT.en.md): read before splitting `app.py`, the room script, or shared state logic.
5. [PROJECT_GUIDE.en.md](PROJECT_GUIDE.en.md): read before course presentation, oral explanation, or code walkthrough.

## Document Responsibilities

| Document | Purpose | Audience |
| --- | --- | --- |
| [../README.md](../README.md) / [English](../README.en.md) | Project overview, complete page entry points, i18n and mobile/desktop adaptation status, Quick Start, local tool installation, local startup, configuration, and basic checks | First-time readers |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) / [English](DEPLOYMENT_GUIDE.en.md) | Cloud provider entry points, ICP filing notes, SSH/FinalShell login, DNS/Cloudflare, Nginx, WebSocket, HTTPS, LiveKit Cloud, self-hosted LiveKit, systemd, Git three-side workflow, service updates, log troubleshooting, and official references | Deployers and maintainers, especially first-time deployers |
| [STABILITY_AUDIT.md](STABILITY_AUDIT.md) / [English](STABILITY_AUDIT.en.md) | Architecture boundaries, risks, regression focus, and future direction | People changing core logic |
| [REFACTOR_AUDIT.md](REFACTOR_AUDIT.md) / [English](REFACTOR_AUDIT.en.md) | Current refactor audit, priorities, recommended split order, and pre-change checks | People planning refactors or long-term maintenance |
| [项目说明与代码索引.md](%E9%A1%B9%E7%9B%AE%E8%AF%B4%E6%98%8E%E4%B8%8E%E4%BB%A3%E7%A0%81%E7%B4%A2%E5%BC%95.md) / [English](PROJECT_GUIDE.en.md) | Project logic, core flows, code index, and common Q&A | Presenters and maintainers |
| `视觉媒体通信期末大作业实践报告.docx` | Archived course report source | Course submission readers |

## Maintenance Rules

- Update the root README first when project behavior changes.
- Update `DEPLOYMENT_GUIDE.md` and `DEPLOYMENT_GUIDE.en.md` when deployment commands, environment variables, or service management changes.
- Update `STABILITY_AUDIT.md` and `STABILITY_AUDIT.en.md` when room state, LiveKit, screen sharing, recording, or virtual background behavior changes.
- Update the root README and project guide when UI text, mobile QR join, mobile chat layout, desktop meeting grid, or default device behavior changes.
- Update `REFACTOR_AUDIT.md` and `REFACTOR_AUDIT.en.md` when refactor priorities, split order, or module boundaries change.
- Update `项目说明与代码索引.md` and `PROJECT_GUIDE.en.md` when presentation wording, core flows, or code index changes.
- The `.docx` report is archived material; do not treat it as live code documentation unless a new report is explicitly required.
