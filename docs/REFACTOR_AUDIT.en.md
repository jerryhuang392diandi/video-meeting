# Refactor Audit

[中文](REFACTOR_AUDIT.md) | [English](REFACTOR_AUDIT.en.md)

This document records the project structure audit from 2026-04-22. It is not a request to rewrite the code immediately. It ranks future work so stability-sensitive boundaries are handled before file size and cosmetic maintainability.

## Current Conclusion

The project has converged from the early browser-direct idea to a `Flask + Socket.IO + LiveKit SFU` architecture. The main refactor target is not the media protocol itself. The bigger issue is that the room page script and `app.py` still combine several domains, so screen sharing, virtual background, recording, chat, and admin changes have a broad impact surface.

This pass only makes low-risk synchronization changes:

- Remove the stale room-script constant saying virtual background is not wired into LiveKit.
- Change the home-page technology chip to `LiveKit SFU` instead of the generic `WebRTC` label.
- Tighten virtual background camera-source checks so only `live` camera tracks are used, and clean up failed canvas processing streams after startup failure.
- Document refactor priorities so future maintenance does not rely on memory.

## Priorities

| Priority | Scope | Current state | Recommendation |
| --- | --- | --- | --- |
| P0 | Room state consistency | Socket.IO owns online members, chat, and share focus; LiveKit owns media tracks; frontend/backend event ordering keeps them aligned | Map state entry points before changing room code |
| P0 | Screen sharing | Backend `active_sharer_*`, frontend focus/layout, LiveKit publication, and refresh recovery all interact | Extract a share-state coordination layer for start, stop, deny, and refresh recovery |
| P1 | `templates/_room_scripts.html` | Still owns room bootstrap, media buttons, recording, virtual background, chat binding, and cleanup | Gradually split into `room_bootstrap.js`, `room_media_controls.js`, `room_recording.js`, and `room_virtual_background.js` |
| P1 | `app.py` | Over two thousand lines covering models, auth, rooms, chat uploads, recording remux, and admin management | Split by blueprint or module while preserving route behavior |
| P1 | Chat attachments | Upload validation, compression, storage limits, permission checks, and response handling live together | Extract attachment service functions first, then consider a separate module |
| P2 | Observability | Debugging depends on logs and manual reproduction | Add health checks, structured room event logs, and clearer LiveKit configuration errors |

## Recommended Order

1. Split lower-risk room frontend logic first. Recording, virtual background, and chat binding are safer to move than the LiveKit connection path.
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
