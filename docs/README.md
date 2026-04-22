# 文档地图

[中文](README.md) | [English](README.en.md)

这里放项目说明、部署手册、稳定性审计和课程答辩材料。根目录 [README.md](../README.md) 是项目入口；本文件只负责告诉你该读哪一份文档。

## 推荐阅读顺序

1. [../README.md](../README.md): 先了解项目功能、架构、本地运行和关键配置。
2. [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) / [English](DEPLOYMENT_GUIDE.en.md): 准备购买云服务器、首次部署、更新服务器或排查线上问题时阅读。中文版本包含面向零基础的 Nginx、HTTPS、LiveKit Cloud 和自建 LiveKit 说明。
3. [STABILITY_AUDIT.md](STABILITY_AUDIT.md) / [English](STABILITY_AUDIT.en.md): 改房间、媒体、屏幕共享、录屏或部署架构前阅读。
4. [项目说明与代码索引.md](%E9%A1%B9%E7%9B%AE%E8%AF%B4%E6%98%8E%E4%B8%8E%E4%BB%A3%E7%A0%81%E7%B4%A2%E5%BC%95.md) / [English](PROJECT_GUIDE.en.md): 准备课程展示、口头讲解或代码跟读时阅读。

## 文档职责

| 文档 | 用途 | 适合读者 |
| --- | --- | --- |
| [../README.md](../README.md) / [English](../README.en.md) | 项目总览、本地启动、配置和基本检查 | 第一次打开项目的人 |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) / [English](DEPLOYMENT_GUIDE.en.md) | 云服务器准备、DNS/Cloudflare、Nginx、WebSocket、HTTPS、LiveKit Cloud、自建 LiveKit、systemd、服务更新、日志排查和官方参考资料 | 部署和维护项目的人，尤其是第一次部署的人 |
| [STABILITY_AUDIT.md](STABILITY_AUDIT.md) / [English](STABILITY_AUDIT.en.md) | 当前架构边界、风险、回归重点和演进方向 | 修改核心逻辑的人 |
| [项目说明与代码索引.md](%E9%A1%B9%E7%9B%AE%E8%AF%B4%E6%98%8E%E4%B8%8E%E4%BB%A3%E7%A0%81%E7%B4%A2%E5%BC%95.md) / [English](PROJECT_GUIDE.en.md) | 项目逻辑、核心流程、代码索引和常见问题回答 | 准备展示或维护代码的人 |
| `视觉媒体通信期末大作业实践报告.docx` | 课程报告原稿归档 | 需要提交课程材料的人 |

## 维护规则

- 行为变化优先更新根 README。
- 部署命令、环境变量或服务管理方式变化时更新 `DEPLOYMENT_GUIDE.md`。
- 房间状态、LiveKit、屏幕共享、录屏、虚拟背景相关变化时更新 `STABILITY_AUDIT.md`。
- 课程展示口径、核心流程或代码索引变化时更新 `项目说明与代码索引.md`。
- `.docx` 报告是归档材料，除非明确需要重新出报告，否则不要把它当作代码文档同步更新。
