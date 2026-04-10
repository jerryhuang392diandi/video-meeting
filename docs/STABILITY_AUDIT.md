# 稳定性审计 / Stability Audit

## 结论摘要 / Executive Summary

中文：

当前项目已经不再以浏览器 Mesh/P2P 作为主媒体路径，而是采用 `Flask + Socket.IO + LiveKit SFU` 的分层架构。稳定性重点因此发生了变化：主要风险不再是旧版 WebRTC 自协商冲突，而是运行时在线态仍在单进程内存中、Socket.IO 与 LiveKit 两套状态源之间的一致性、以及屏幕共享/虚拟背景/录屏带来的资源压力。

English:

The project no longer relies on browser mesh/P2P as the primary media path. It now uses a layered `Flask + Socket.IO + LiveKit SFU` architecture. The main stability risks have therefore shifted away from legacy WebRTC self-negotiation conflicts toward single-process runtime room state, consistency between Socket.IO and LiveKit, and the resource cost of screen sharing, virtual background, and recording.

## 当前系统边界 / Current System Boundaries

### 业务层 / Business Layer

- `app.py` 负责登录注册、会议创建与加入、会议历史、管理员后台、聊天附件、录屏转封装、LiveKit token 下发。
- SQLAlchemy 负责持久化用户、会议、参会记录、密码找回请求等数据。

### 状态同步层 / State Sync Layer

- Socket.IO 负责成员加入/离开、聊天广播、主持人动作、共享焦点状态、界面级事件同步。
- 房间在线态主要保存在内存结构中，例如 `rooms`、`sid_to_user`、`user_active_sids`。

### 媒体层 / Media Layer

- LiveKit 负责摄像头、麦克风、屏幕共享、远端轨道订阅与 SFU 分发。
- `static/room_livekit.js` 和房间脚本负责媒体连接、发布、恢复与前端控制。

### 展示层 / Presentation Layer

- `templates/_room_layout.html` 负责房间结构。
- `templates/_room_scripts.html` 负责房间初始化和主交互编排。
- `static/room_ui.js`、`static/room_chat.js`、`static/room_diagnostics.js` 分别负责布局、聊天、诊断展示。

## 已有优点 / Existing Strengths

### 1. 媒体层已经迁移到 SFU / Media Already Runs on SFU

中文：当前多人会议的扩展性明显优于传统浏览器 Mesh。每个用户不需要和所有其他成员分别建链，复杂度和带宽压力更可控。

English: Multi-party scalability is much better than browser mesh. Each participant no longer needs a direct peer connection to every other participant.

### 2. 业务与媒体职责已有边界 / Clearer Separation of Concerns

中文：Flask/Socket.IO 管业务和房间状态，LiveKit 管媒体轨道。这比把所有逻辑都堆在一套自写 WebRTC 信令里更稳定，也更便于后续维护。

English: Flask/Socket.IO owns business and room state, while LiveKit owns media tracks. This is more maintainable than keeping everything in a custom WebRTC signaling flow.

### 3. 已有基础诊断能力 / Basic Diagnostics Already Exist

中文：房间页已经有 RTC/LiveKit 诊断面板，排查码率、RTT、丢包、帧率时比纯黑盒系统更容易。

English: The room page already exposes RTC/LiveKit diagnostics, which makes bitrate, RTT, packet loss, and frame-rate troubleshooting much easier.

## 主要风险 / Main Risks

### A. 在线态仍是单进程内存 / Runtime Presence Is Still Single-Process Memory

中文：

- 服务重启后在线态会丢失
- 默认不适合多实例横向扩展
- Socket 连接态和持久化数据之间没有真正的分布式一致性

English:

- Online room presence is lost on restart
- Horizontal scaling is not safe by default
- There is no true distributed consistency between sockets and persisted data

建议 / Recommendation:

- 短期保持单实例部署
- 明确在文档中写出这一限制
- 中期考虑将在线态迁移到 Redis

### B. Socket.IO 与 LiveKit 是两套状态源 / Socket.IO and LiveKit Are Two Sources of Truth

中文：

当前设计本身合理，但必须持续处理“成员状态”和“媒体状态”不同步的问题。用户加入成功，不代表媒体一定已就绪；Socket 离开，也不代表媒体轨道已瞬时清理。

English:

The design is reasonable, but it requires continuous care to prevent drift between room membership state and media state. A successful room join does not mean media is ready yet, and a socket leaving does not guarantee that media tracks have been cleaned up instantly.

重点关注 / Focus areas:

- `join_ok`
- `participant_snapshot`
- 刷新恢复与重连
- 同账号多端在线
- 屏幕共享开始与停止后的 UI 状态恢复

### C. 屏幕共享是联动最多的高风险功能 / Screen Share Is a High-Risk Cross-Cutting Feature

中文：

屏幕共享会同时触及 LiveKit 发布状态、房间布局、共享者焦点、扬声器体验和移动端浏览器限制。只要其中一个恢复顺序错位，就容易表现为“UI 还以为在共享，但媒体已经停了”或相反。

English:

Screen sharing touches LiveKit publication state, room layout, share focus, speaker behavior, and mobile browser limitations all at once. Any mismatch in cleanup or restoration order can leave the UI and media transport out of sync.

建议 / Recommendation:

- 共享逻辑改动时，必须同时检查服务端 `active_sharer_*` 清理和前端焦点恢复
- 对移动端优先保证“能看到共享内容”，其次再追求复杂交互
- 刷新、异常退出、重新加入都要回归测试

### D. 虚拟背景和录屏都在抢资源 / Virtual Background and Recording Compete for Resources

中文：

虚拟背景依赖浏览器端分割与 Canvas 合成；录屏依赖浏览器编码，必要时还要走服务端 `ffmpeg`。在低性能设备上，这两类功能与摄像头、屏幕共享并行时容易掉帧、发热、卡顿。

English:

Virtual background depends on browser-side segmentation and compositing. Recording depends on browser encoding and may additionally rely on server-side `ffmpeg`. On weaker devices, these features easily compete with camera and screen sharing for CPU/GPU resources.

建议 / Recommendation:

- 把它们视为增强功能，而不是稳定性基线
- 文档和演示中明确说明资源占用事实
- 弱设备优先保证可用性，而不是画质或特效

### E. 单体 `app.py` 的维护压力会继续增长 / The Monolithic `app.py` Will Keep Growing

中文：当前单体后端结构在课程项目阶段是可接受的，但随着功能增加，认证、房间、聊天、后台、录屏相关逻辑继续堆叠，会降低可读性与修改安全性。

English: A monolithic backend is acceptable at this stage, but ongoing feature growth will reduce readability and make changes riskier across authentication, room, chat, admin, and recording logic.

## 当前优先级建议 / Recommended Priority Order

### P0

- 文档中明确单实例部署前提
- 所有房间相关改动都复查 Socket.IO 与 LiveKit 的一致性
- 屏幕共享改动必须覆盖刷新、重连、移动端回归

### P1

- 在线态迁移到 Redis
- 梳理更清晰的房间恢复与同账号多端状态机
- 为录屏转 MP4 补充更明确的部署与失败提示

### P2

- 按业务域拆分 `app.py`
- 视部署规模引入任务队列和更完整的监控

## 不建议的误判 / Misdiagnoses to Avoid

- 不要继续把当前稳定性问题简单归因到旧的 Mesh `createOffer` 冲突
- 不要混淆“Socket 房间状态问题”和“LiveKit 媒体问题”
- 不要把虚拟背景和录屏当作零成本能力

Do not:

- blame everything on legacy mesh offer collisions
- mix room-state bugs with media-transport bugs
- treat virtual background and recording as free features

## 一句话结论 / One-Line Conclusion

中文：当前项目的核心稳定性问题，已经从“如何把浏览器 P2P 协商写对”转向“如何把业务状态、媒体状态和高负载功能的退化路径管理好”。

English: The core stability challenge has shifted from “making browser P2P negotiation work” to “keeping business state, media state, and high-cost feature degradation paths under control.”
