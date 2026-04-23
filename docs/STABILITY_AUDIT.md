<a id="stability-audit-zh"></a>

# 稳定性审计

[中文](#stability-audit-zh) | [English](#stability-audit-en)

当前项目已经迁移到 `Flask + Socket.IO + LiveKit SFU` 的分层架构。主要风险不再是浏览器 Mesh/P2P 自协商，而是业务状态、Socket.IO 房间状态、LiveKit 媒体状态之间的一致性，以及屏幕共享、虚拟背景、录屏带来的资源压力。

## 系统边界

| 层级 | 所有者 | 主要状态 |
| --- | --- | --- |
| 业务层 | `app.py` / Flask / SQLAlchemy | 用户、会议、参会记录、密码重置、附件记录 |
| 房间状态层 | Socket.IO + 后端内存结构 | 在线成员、主持人操作、聊天广播、共享焦点 |
| 媒体层 | LiveKit + `static/room_livekit.js` | 摄像头、麦克风、屏幕共享、远端轨道 |
| 展示层 | templates + `static/room_ui.js` | 卡片布局、焦点视图、按钮状态、诊断面板 |

关键事实：

- Socket.IO 不是媒体传输层。
- LiveKit 不负责业务权限和会议历史。
- 在线态目前主要在单进程内存中。
- 屏幕共享和录屏横跨多个层级，改动时最容易引入状态错位。

## 已有优势

- 多人媒体已经由 LiveKit SFU 承担，比浏览器 Mesh 更适合多人会议。
- 业务状态和媒体状态已经分层，后续排查可以按职责定位。
- 房间内有 RTC/LiveKit 诊断面板，便于观察码率、RTT、丢包和帧率。
- 管理员后台、历史记录、附件权限和密码重置让项目更接近完整应用，而不是单一音视频 Demo。

## 风险登记表

| 优先级 | 风险 | 影响 | 建议 |
| --- | --- | --- | --- |
| P0 | 在线态仍在单进程内存中 | 重启丢失在线态，多实例部署不安全 | 短期明确单实例部署；中期迁移到 Redis |
| P0 | Socket.IO 与 LiveKit 状态不同步 | 用户已进房但媒体未就绪，或媒体已断但 UI 未恢复 | 保持清晰的加入、快照、重连、离开顺序 |
| P0 | 屏幕共享状态清理不完整 | 刷新或异常退出后出现错误焦点、旧共享者、远端看不到共享 | 每次改动都验证开始、停止、刷新、重连和移动端 |
| P1 | 虚拟背景和录屏资源占用高 | 弱设备卡顿、掉帧、发热，影响基础会议体验 | 把它们视为增强功能，必要时降级 |
| P1 | `app.py` 继续膨胀 | 认证、房间、聊天、后台、录屏逻辑互相影响 | 后续按业务域拆分 |
| P2 | 部署可观测性有限 | 线上问题定位依赖人工日志排查 | 补充结构化日志、健康检查和监控 |

## 房间逻辑改动检查清单

改动 `app.py`、`templates/_room_scripts.html`、`static/room_livekit.js`、`static/room_ui.js` 时，至少检查这些入口是否会改同一份状态：

- 首次进入房间
- Socket.IO `join_ok`
- `participant_snapshot`
- LiveKit 连接成功
- 远端 track 发布和取消发布
- 页面刷新恢复
- Socket 断开和后端清理
- 同账号多设备在线
- 主持人结束会议

同时确认桌面端和移动端没有走出两套互相冲突的状态：

- 桌面端会议网格、分页、右侧聊天栏和聊天折叠状态。
- 移动端扫码入会、聊天底部面板、触摸滚动、输入框可见性和屏幕共享全屏。
- 手机端默认媒体参数更保守，不应被桌面端高码率配置覆盖。

原则：

- 一个状态域尽量只有一个权威更新路径。
- UI 焦点状态不要和 LiveKit 媒体发布状态混为一谈。
- 后端房间在线态、Socket.IO 广播、LiveKit participant 生命周期要一起验证。

## 屏幕共享回归重点

屏幕共享同时影响媒体、布局、主持/共享状态和移动端体验。改动相关逻辑后必须验证：

- A 开始共享后，B 首次进房能看到共享内容。
- A 停止共享后，A 和 B 的布局都恢复。
- A 共享中刷新页面，不会留下旧的 `active_sharer_*` 状态。
- B 重新加入后不会看到过期共享焦点。
- 移动端至少能稳定观看远端共享内容。
- 同账号双设备不会因为误判旧 socket 而互相挤掉。

## 录屏与虚拟背景回归重点

这两项都属于增强功能，不应影响基础会议链路。

需要确认：

- 摄像头开关正常。
- 麦克风开关正常。
- 开启虚拟背景后仍能发布本地视频。
- 摄像头关闭后再开启，虚拟背景不会复用已经 ended 的旧摄像头 track。
- 虚拟背景启动失败后会回退到原始摄像头，并清理未成功的 canvas 处理流。
- 屏幕共享和虚拟背景不会争用同一条本地视频替换路径。
- 浏览器录屏能生成原始结果。
- 有 `ffmpeg` 的服务器能继续转封装为 MP4。

## 演进建议

短期：

- 文档中保持单实例部署前提。
- 部署文档必须继续明确区分 Nginx 代理的是 Flask 网站，LiveKit 承担的是媒体传输；不要把两者写成同一个服务。
- 所有房间改动都做双端手动验证。
- 屏幕共享改动必须覆盖刷新和重连。

中期：

- 将在线态、socket 映射和房间运行态迁移到 Redis。
- 把 `app.py` 按认证、房间、聊天、录屏、后台逐步拆分。
- 补充更明确的 LiveKit 配置检查和错误提示。

长期：

- 引入更完整的自动化测试和端到端测试。
- 补充部署健康检查、结构化日志和监控。
- 根据实际规模决定是否引入任务队列处理重任务。

## 重构关联

当前代码巡检的具体拆分建议单独记录在 [REFACTOR_AUDIT.md](REFACTOR_AUDIT.md)。稳定性优先级高于文件拆分本身：先保证房间状态、屏幕共享和 LiveKit 媒体生命周期一致，再逐步拆分 `templates/_room_scripts.html` 和 `app.py`。

## 不要误判

- 不要把当前所有稳定性问题继续归因到旧版 Mesh/P2P。
- 不要把 Socket.IO 房间状态问题误判成 LiveKit 媒体问题。
- 不要把 LiveKit track 生命周期当作业务房间成员生命周期。
- 不要把虚拟背景和录屏当成零成本能力。


---

<a id="stability-audit-en"></a>

# Stability Audit

[中文](#stability-audit-zh) | [English](#stability-audit-en)

The project has moved to a layered `Flask + Socket.IO + LiveKit SFU` architecture. The main risks are no longer browser Mesh/P2P negotiation. They are consistency between business state, Socket.IO room state, and LiveKit media state, plus the resource pressure introduced by screen sharing, virtual background, and recording.

## System Boundaries

| Layer | Owner | Main State |
| --- | --- | --- |
| Business layer | `app.py` / Flask / SQLAlchemy | Users, meetings, participation records, password resets, attachment records |
| Room state layer | Socket.IO + backend memory structures | Online members, host actions, chat broadcast, shared focus |
| Media layer | LiveKit + `static/room_livekit.js` | Camera, microphone, screen share, remote tracks |
| Presentation layer | templates + `static/room_ui.js` | Card layout, focus view, button state, diagnostic panel |

Key facts:

- Socket.IO is not the media transport layer.
- LiveKit does not own business permissions or meeting history.
- Online state is currently kept mainly in single-process memory.
- Screen sharing and recording cross several layers, so they are the easiest places to introduce state mismatch.

## Existing Strengths

- Multi-party media is handled by LiveKit SFU, which is more suitable than browser Mesh for multi-user meetings.
- Business state and media state are separated, making troubleshooting easier by responsibility.
- The room contains an RTC/LiveKit diagnostics panel for bitrate, RTT, packet loss, and frame rate.
- Admin dashboard, meeting history, attachment permissions, and password reset make the project closer to a complete app than a single media demo.

## Risk Register

| Priority | Risk | Impact | Recommendation |
| --- | --- | --- | --- |
| P0 | Online state is still in single-process memory | Online state is lost on restart; multi-instance deployment is unsafe | Keep single-instance deployment short term; migrate to Redis later |
| P0 | Socket.IO and LiveKit state can diverge | User is in room but media is not ready, or media disconnects while UI stays stale | Keep join, snapshot, reconnect, and leave ordering clear |
| P0 | Screen share cleanup can be incomplete | Refresh or abnormal exit can leave wrong focus, stale sharer state, or invisible share | Verify start, stop, refresh, reconnect, and mobile every time |
| P1 | Virtual background and recording are expensive | Weak devices may stutter, drop frames, overheat, or hurt baseline meeting quality | Treat them as enhancements and degrade when needed |
| P1 | `app.py` keeps growing | Auth, room, chat, admin, and recording logic can interfere with each other | Split by domain over time |
| P2 | Limited deployment observability | Production debugging relies on manual log inspection | Add structured logs, health checks, and monitoring |

## Room Logic Change Checklist

When changing `app.py`, `templates/_room_scripts.html`, `static/room_livekit.js`, or `static/room_ui.js`, check whether these entry points mutate the same state:

- First room entry
- Socket.IO `join_ok`
- `participant_snapshot`
- LiveKit connection success
- Remote track publish and unpublish
- Page refresh recovery
- Socket disconnect and backend cleanup
- Same account online on multiple devices
- Host ending the meeting

Also confirm desktop and mobile paths do not drift into conflicting state flows:

- Desktop meeting grid, pagination, right chat column, and chat collapsed state.
- Mobile QR join, chat bottom panel, touch scrolling, input visibility, and screen-share fullscreen.
- Phone media defaults should remain more conservative and should not be overwritten by desktop high-bitrate settings.

Principles:

- Prefer one authoritative update path for each state domain.
- Do not mix UI focus state with LiveKit media publication state.
- Validate backend online state, Socket.IO broadcasts, and LiveKit participant lifecycle together.

## Screen Share Regression Focus

Screen sharing affects media, layout, host/share state, and mobile behavior. After related changes, verify:

- User B can see user A's share when B joins after A starts sharing.
- Layout recovers for both A and B after A stops sharing.
- Refreshing while sharing does not leave stale `active_sharer_*` state.
- Rejoining does not show stale share focus.
- Mobile can at least watch remote screen share reliably.
- Same-account dual-device sessions do not evict each other due to stale socket detection.

## Recording and Virtual Background Regression Focus

Both are enhancement features and should not break the baseline meeting path.

Confirm:

- Camera toggling still works.
- Microphone toggling still works.
- Local video can still publish after virtual background is enabled.
- After the camera is turned off and on again, virtual background does not reuse an ended old camera track.
- If virtual background startup fails, it falls back to the raw camera and cleans up the failed canvas processing stream.
- Screen sharing and virtual background do not fight over the same local video replacement path.
- Browser recording can generate the raw result.
- Servers with `ffmpeg` can still remux to MP4.

## Evolution Recommendations

Short term:

- Keep single-instance deployment stated clearly in documentation.
- Keep deployment docs explicit that Nginx proxies the Flask website while LiveKit carries media transport; do not describe them as one service.
- Run two-client manual verification for every room change.
- Cover refresh and reconnect for every screen share change.

Medium term:

- Move online state, socket mappings, and runtime room state to Redis.
- Split `app.py` gradually by auth, room, chat, recording, and admin domains.
- Add clearer LiveKit configuration checks and error messages.

Long term:

- Add fuller automated and end-to-end tests.
- Add deployment health checks, structured logs, and monitoring.
- Introduce a task queue for heavy jobs if real usage requires it.

## Refactor Link

Concrete split recommendations from the current code audit are tracked in [REFACTOR_AUDIT.md#refactor-audit](REFACTOR_AUDIT.md#refactor-audit). Stability has higher priority than file splitting itself: keep room state, screen sharing, and LiveKit media lifecycle consistent first, then gradually split `templates/_room_scripts.html` and `app.py`.

## Avoid Wrong Conclusions

- Do not keep attributing current stability issues to the old Mesh/P2P path.
- Do not mistake Socket.IO room state issues for LiveKit media issues.
- Do not treat LiveKit track lifecycle as the business room membership lifecycle.
- Do not treat virtual background and recording as zero-cost features.
