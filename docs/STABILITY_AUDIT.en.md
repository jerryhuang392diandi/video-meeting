# Stability Audit

[中文](STABILITY_AUDIT.md) | [English](STABILITY_AUDIT.en.md)

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

Concrete split recommendations from the current code audit are tracked in [REFACTOR_AUDIT.en.md](REFACTOR_AUDIT.en.md). Stability has higher priority than file splitting itself: keep room state, screen sharing, and LiveKit media lifecycle consistent first, then gradually split `templates/_room_scripts.html` and `app.py`.

## Avoid Wrong Conclusions

- Do not keep attributing current stability issues to the old Mesh/P2P path.
- Do not mistake Socket.IO room state issues for LiveKit media issues.
- Do not treat LiveKit track lifecycle as the business room membership lifecycle.
- Do not treat virtual background and recording as zero-cost features.
