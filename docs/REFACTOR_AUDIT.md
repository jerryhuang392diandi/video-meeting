<a id="refactor-audit-zh"></a>

# 重构巡检

[中文](#refactor-audit-zh) | [English](#refactor-audit-en)

这份文档记录 2026-04-26 对当前项目结构的巡检结论。它不是马上大拆代码的清单，而是给后续改动排序：先处理会影响会议稳定性的状态边界，再处理文件体积和可维护性。

## 当前结论

项目已经从早期浏览器直连思路收敛到 `Flask + Socket.IO + LiveKit SFU` 架构。最值得重构的地方不是媒体协议本身，而是房间页脚本和 `app.py` 中多个业务域仍然挤在一起，导致屏幕共享、背景虚化、录屏、聊天和管理员逻辑的影响范围不够清晰。

本次低风险整理已经完成这些同步：

- 删除 `docs/` 中编码异常且与正式文档重复的副本文件，避免后续继续在错误文件名上修改。
- 将 `participant_snapshot` 也带上 `active_sharer_*` 状态，让房间快照可以修正漏掉的共享事件和刷新后的旧焦点。
- 把屏幕共享状态更新收口到更少的 helper，减少同一状态在后端多处直接赋值。
- 把入会自动拉起媒体、摄像头/麦克风/共享/虚化按钮动作收成命名函数，减少房间启动和媒体控制入口里的内联分支。
- 把房间页最后的 socket 监听、按钮绑定和启动编排抽到 `static/room_bootstrap.js`，让 `_room_scripts.html` 更接近“状态 + 核心函数”。
- 把录屏和虚化重逻辑进一步抽到 `static/room_recording.js` 与 `static/room_virtual_background.js`，减少增强功能继续挤占房间主链路。
- 把注册页和邮箱验证码登录页的表单 intent 切换脚本抽到共享静态文件，避免认证页面继续复制同一段逻辑。
- 把认证页顶部栏和 action card 抽成模板局部，减少登录/注册/找回密码/管理员登录页面的重复结构。
- 给后端运行态补上 `runtime_state_lock` 和 `/api/healthz`，先把单进程内存状态的关键并发路径和排障入口收紧。
- 将重构优先级写入文档，避免后续维护只依赖口头记忆。

## 优先级

| 优先级 | 范围 | 现状 | 建议 |
| --- | --- | --- | --- |
| P0 | 房间状态一致性 | Socket.IO 维护在线成员、聊天和共享焦点；LiveKit 维护媒体轨道；两者需要靠前端和后端事件顺序协调 | 任何房间改动都先画清状态入口，再做代码变更 |
| P0 | 屏幕共享 | 后端有 `active_sharer_*`，前端有焦点、布局、LiveKit 发布和刷新恢复；当前已补上快照兜底同步 | 继续抽出共享状态协调层，统一开始、停止、拒绝、刷新恢复 |
| P1 | `templates/_room_scripts.html` | 仍承担房间启动、媒体按钮、录屏、背景虚化、聊天事件绑定、清理逻辑 | 逐步拆成 `room_bootstrap.js`、`room_media_controls.js`、`room_recording.js`、`room_virtual_background.js` |
| P1 | `app.py` | 约两千多行，包含模型、认证、房间、聊天上传、录屏转封装、后台管理 | 按蓝图或模块拆分，但保持路由行为不变 |
| P1 | 聊天附件 | 上传校验、压缩、存储限制、权限校验和视图分发在同一区域 | 先抽出附件服务函数，再考虑独立模块 |
| P2 | 可观测性 | 依赖调试日志和手工复现 | 补充健康检查、结构化房间事件日志和更明确的 LiveKit 配置错误 |

## 推荐拆分顺序

1. 房间前端脚本先拆非媒体逻辑：录屏、背景虚化、聊天绑定可以比 LiveKit 连接更安全地迁移。
2. 后端先抽纯函数和服务层：上传校验、录屏转封装、系统统计可以先离开 `app.py`。
3. 最后再动房间在线态和 Socket.IO 事件，因为它们直接影响双端入会、刷新恢复和主持人操作。

## 改动前检查

做任何非平凡重构前，先确认这些入口是否会改同一份状态：

- `/room/<room_id>` 初始渲染
- Socket.IO `join_room`、`join_ok`、`participant_snapshot`
- LiveKit token 获取和连接完成
- 本地摄像头、麦克风、屏幕共享发布
- 远端 track 发布和取消发布
- 刷新恢复、主动离会、断线清理
- 管理员踢人、禁用用户、结束会议

## 不建议现在做

- 不要一次性把 `app.py` 全量拆成多个蓝图。当前没有自动化测试覆盖，风险大于收益。
- 不要把 Socket.IO 在线态直接理解成 LiveKit 在线态。两者生命周期不同。
- 不要在没有 Redis 或共享状态设计前写多实例部署承诺。


---

<a id="refactor-audit-en"></a>

# Refactor Audit

[中文](#refactor-audit-zh) | [English](#refactor-audit-en)

This document records the project structure audit from 2026-04-22. It is not a request to rewrite the code immediately. It ranks future work so stability-sensitive boundaries are handled before file size and cosmetic maintainability.

## Current Conclusion

The project has converged from the early browser-direct idea to a `Flask + Socket.IO + LiveKit SFU` architecture. The main refactor target is not the media protocol itself. The bigger issue is that the room page script and `app.py` still combine several domains, so screen sharing, background blur, recording, chat, and admin changes have a broad impact surface.

This pass only makes low-risk synchronization changes:

- Add `active_sharer_*` state to `participant_snapshot` so room snapshots can repair missed share events and stale focus after refresh.
- Reduce direct screen-share state writes by routing more updates through shared helpers.
- Move final room-page socket listeners and bootstrap orchestration into `static/room_bootstrap.js`.
- Move recording and virtual-background heavy logic into `static/room_recording.js` and `static/room_virtual_background.js`.
- Add `runtime_state_lock` plus `/api/healthz` so the single-process runtime has tighter critical sections and a first-line troubleshooting endpoint.

## Priorities

| Priority | Scope | Current state | Recommendation |
| --- | --- | --- | --- |
| P0 | Room state consistency | Socket.IO owns online members, chat, and share focus; LiveKit owns media tracks; frontend/backend event ordering keeps them aligned | Map state entry points before changing room code |
| P0 | Screen sharing | Backend `active_sharer_*`, frontend focus/layout, LiveKit publication, and refresh recovery all interact | Extract a share-state coordination layer for start, stop, deny, and refresh recovery |
| P1 | `templates/_room_scripts.html` | Still owns room bootstrap, media buttons, recording, background blur, chat binding, and cleanup | Gradually split into `room_bootstrap.js`, `room_media_controls.js`, `room_recording.js`, and `room_virtual_background.js` |
| P1 | `app.py` | Over two thousand lines covering models, auth, rooms, chat uploads, recording remux, and admin management | Split by blueprint or module while preserving route behavior |
| P1 | Chat attachments | Upload validation, compression, storage limits, permission checks, and response handling live together | Extract attachment service functions first, then consider a separate module |
| P2 | Observability | Debugging depends on logs and manual reproduction | Add health checks, structured room event logs, and clearer LiveKit configuration errors |

## Recommended Order

1. Split lower-risk room frontend logic first. Recording, background blur, and chat binding are safer to move than the LiveKit connection path.
2. Extract pure backend helpers and services next. Upload validation, recording remux, and system stats can leave `app.py` before the core room events.
3. Move room online state and Socket.IO events last because they directly affect two-client joining, refresh recovery, and host actions.

## Pre-Change Checks

Before any non-trivial refactor, verify whether these entry points mutate the same state:

- Initial `/room/<room_id>` render
- Socket.IO `join_room`, `join_ok`, and `participant_snapshot`
- LiveKit token fetch and connection completion
- Local camera, microphone, and screen share publication
- Remote track publish and unpublish
- Refresh recovery, explicit leave, and disconnect cleanup
- Admin kick, user disable, and meeting end

## Not Recommended Now

- Do not split all of `app.py` into blueprints in one pass. Without automated coverage, the risk is larger than the payoff.
- Do not treat Socket.IO online state as LiveKit online state. Their lifecycles differ.
- Do not promise multi-instance deployment before Redis or another shared-state design exists.
