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

## Commit & Pull Request Guidelines
Recent history favors concise, imperative commit subjects (for example: “Fix ...”, “Improve ...”, “Tune ...”).

- Keep commit titles specific and action-first.
- Scope PRs to one functional change area.
- PR description should include: problem, solution summary, manual test steps, and screenshots/GIFs for UI changes.
- Link related issues and call out config/env var changes explicitly (`PUBLIC_HOST`, `PUBLIC_SCHEME`, admin credentials).
