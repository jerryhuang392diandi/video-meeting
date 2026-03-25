# Repository Guidelines

## Project Structure & Module Organization
This is a Flask + Flask-SocketIO app with a mostly monolithic backend in `app.py`. Keep feature changes grouped by concern inside that file (auth, room lifecycle, chat upload, admin).

- `app.py`: routes, Socket.IO events, SQLAlchemy models, runtime config.
- `templates/`: Jinja2 pages and room partials (for example `_room_layout.html`, `_room_scripts.html`).
- `static/`: room frontend logic (`room_rtc.js`, `room_ui.js`, `room_chat.js`, diagnostics) and shared styles.
- `translations.py`: Chinese/English translation keys used by `t(...)` in templates and backend.
- `check_i18n.py`: lightweight i18n consistency checker for hardcoded Chinese in templates.
- `instance/` (generated, ignored): SQLite DB and runtime uploads.

## Build, Test, and Development Commands
- `python -m venv venv` then `venv\Scripts\activate` (Windows): create and activate local environment.
- `pip install -r requirements.txt`: install Flask/SocketIO dependencies.
- `python app.py`: run local server.
- `python check_i18n.py`: scan templates for untranslated hardcoded Chinese text.

There is currently no formal CI test runner in this repo; use the checks below before opening a PR.

## Coding Style & Naming Conventions
Use Python 4-space indentation and keep naming consistent with existing code:
- `snake_case` for functions/variables (`preferred_display_name`, `chat_upload_dir`).
- `UPPER_SNAKE_CASE` for constants (`MAX_PARTICIPANTS`).
- clear, short event/route names aligned with existing Socket.IO and Flask patterns.

For templates, prefer translation keys (`t('key')`) over inline UI text. For static JS/CSS, keep changes modular by file responsibility (RTC logic in `room_rtc.js`, UI state in `room_ui.js`).

## Testing Guidelines
Before submitting:
- run `python check_i18n.py`;
- start the app and smoke test login, room join/leave, media controls, and chat attachment upload;
- verify both `zh` and `en` UI paths for any changed template.
- for RTC changes, explicitly test the `join_ok` path with two clients (desktop + mobile): after first join (without refresh), each side must see the other side's card/video.
- verify that joining with local camera/mic still blocked or not yet granted can still receive remote media (no "only self visible" regression).

## RTC Regression Guard
`templates/_room_scripts.html` has a recurring failure point around `join_ok` + `ensurePeer(...)`. Do not remove the base audio/video transceiver bootstrap unless replaced with an equivalent negotiation strategy.

Minimum manual check after editing this area:
- User A enters room, then User B enters from mobile Safari/Chrome.
- B should immediately see A (without page refresh).
- Both sides should receive `participant_snapshot` updates and keep remote cards visible.
- If sharer refreshes while screen sharing, server must clear stale `active_sharer_*` state; client must not stay stuck in "self is sharer" layout.
- After `join_ok` and `participant_snapshot`, ensure a renegotiation sweep still runs so late media readiness does not leave peers in "only self visible" state.
- Joining with the same account on two devices must not evict the other active device; only truly stale same-user sids may be pruned.

### Mandatory RTC Change Review
Before shipping any RTC/signaling change, do a full conflict audit across all offer paths, not only the function being edited.

Required checklist:
- Enumerate every `createOffer` call site and verify they all use the same initiator rule.
- Verify `callPeer`, media-sync renegotiation, ICE-failure recovery, and snapshot/join handlers cannot bypass that rule.
- Re-check server-side room state transitions (`join_room`, `participant_snapshot`, `active_sharer_*`) for stale-state conflicts after refresh/reconnect.
- Run desktop↔mobile first-join tests in both directions, then refresh-and-rejoin tests, before finalizing.

## Cross-Module Conflict Audit
Before editing any non-trivial logic, inspect adjacent modules and shared state first, then check whether the change creates duplicated or conflicting flows elsewhere.

Minimum review steps for every substantial code change:
- Identify every entry point that can mutate the same state (for example: initial load, refresh recovery, snapshot sync, user-triggered action, background retry).
- Trace which files own that state and which files consume it (`app.py`, `templates/_room_scripts.html`, `static/room_rtc.js`, UI helpers).
- Prefer one canonical update path per state domain; if the same state is updated in multiple handlers, refactor to a shared helper before adding more conditions.
- After refactoring, re-read all related handlers end-to-end and verify they still agree on ordering, ownership, and cleanup.

## Screen Share Notes
Important open documentation references:
- MDN Perfect Negotiation: use symmetric WebRTC negotiation patterns; do not mix ad-hoc host-only offer rules into browser P2P flows.
- MDN `MediaStreamTrack.contentHint`: screen sharing should prefer `detail` (or `text` when supported) for slides/text; camera video should prefer `motion`.
- Jitsi / mediasoup architecture docs: stable multi-party conferencing at distance is typically built on SFU routing, not browser mesh.

Project-specific guidance:
- This repository currently behaves like a mesh/P2P app, so long-distance performance is highly sensitive to RTT, packet loss, and TURN relay geography.
- If two far-apart users are relayed through a distant TURN server, latency is infrastructure-limited; codec tweaks alone will not fully fix it.
- For screen sharing, tune for one goal at a time: `detail` for text readability, `motion` for smoother cursor/video. Do not expect both at low bitrate.
- Screen share bitrate/FPS must be lower on mobile and under weak networks; prioritize stability before sharpness.
- When diagnosing poor remote screen-share FPS, check in this order: ICE path (direct vs relay), TURN region distance, RTT/loss stats, then sender bitrate/FPS constraints.
- If product requirements include reliable long-distance multi-party screen sharing, plan an SFU migration; repeated mesh-side patches are a stopgap, not a final architecture.

## SFU Migration Guard
When migrating RTC from mesh to LiveKit SFU, do not mix half-migrated media control paths. Keep one owner per responsibility.

Required review steps before each SFU change:
- Confirm which layer owns each action: Flask/Socket.IO for auth, room roster, chat, host permissions; LiveKit for camera, microphone, screen share, remote track delivery.
- Audit every button handler and lifecycle hook (`connect`, `join_ok`, `participant_snapshot`, leave/reload cleanup) so a LiveKit path cannot fall through into mesh renegotiation code.
- Keep participant identity mapping explicit. If Socket.IO still drives UI roster, LiveKit participant identity must match the same per-user/session key used by the room UI.
- Treat screen-share focus state separately from media transport. UI focus/banners may stay on Socket.IO events during migration, but media publication/subscription must come from LiveKit only.
- After each migration step, read the full room bootstrap path end-to-end and verify there is no duplicate media initialization, duplicate cleanup, or mixed publish/unpublish ownership.

## Commit & Pull Request Guidelines
Recent history favors concise, imperative commit subjects (for example: “Fix ...”, “Improve ...”, “Tune ...”).

- Keep commit titles specific and action-first.
- Scope PRs to one functional change area.
- PR description should include: problem, solution summary, manual test steps, and screenshots/GIFs for UI changes.
- Link related issues and call out config/env var changes explicitly (`PUBLIC_HOST`, `PUBLIC_SCHEME`, admin credentials).
