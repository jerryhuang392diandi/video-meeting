# Repository Guidelines

## Project Structure & Module Organization
This project is now a `Flask + Flask-SocketIO + LiveKit` online meeting app with a mostly monolithic backend in `app.py`. Keep feature changes grouped by concern inside that file, such as auth, room lifecycle, chat upload, recording, and admin management.

- `app.py`: routes, REST APIs, Socket.IO events, SQLAlchemy models, runtime config, LiveKit token handling.
- `templates/`: Jinja2 pages and room partials, especially `_room_layout.html` and `_room_scripts.html`.
- `static/`: room frontend logic (`room_livekit.js`, `room_ui.js`, `room_chat.js`, `room_diagnostics.js`, `room_utils.js`) and shared styles.
- `translations.py`: Chinese/English translation keys used by `t(...)` in templates and backend.
- `check_i18n.py`: lightweight i18n consistency checker for hardcoded Chinese in templates.
- `docs/`: project docs, deployment notes, stability audit, and defense notes.
- `instance/` (generated, ignored): SQLite DB, runtime uploads, generated admin password file.

## Build, Test, and Development Commands
- `python -m venv venv` then `venv\Scripts\activate` on Windows: create and activate local environment.
- `pip install -r requirements.txt`: install Flask, Socket.IO, and LiveKit-related dependencies.
- `python app.py`: run the local server.
- `python check_i18n.py`: scan templates for untranslated hardcoded Chinese text.

There is currently no formal CI test runner in this repo. Before shipping, rely on the manual checks listed below.

## Coding Style & Naming Conventions
Use Python 4-space indentation and keep naming consistent with the existing code:

- `snake_case` for functions and variables, such as `preferred_display_name` and `chat_upload_dir`.
- `UPPER_SNAKE_CASE` for constants.
- clear and short route/event names aligned with existing Flask and Socket.IO patterns.

For templates, prefer translation keys through `t('key')` instead of inline UI text. For static JS/CSS, keep changes modular by file responsibility:

- `room_livekit.js`: LiveKit room connection, local publish/unpublish, remote track handling.
- `room_ui.js`: room layout, focus state, participant card UI.
- `room_chat.js`: chat rendering and attachment rendering.
- `room_diagnostics.js`: RTC/LiveKit diagnostics summary.
- `room_utils.js`: shared helpers.

## Testing Guidelines
Before submitting:

- run `python check_i18n.py`;
- start the app and smoke test login, room join/leave, media controls, and chat attachment upload;
- verify both `zh` and `en` UI paths for any changed template;
- test a two-client room join flow, ideally desktop + mobile, and confirm first join works without refresh;
- verify that joining with local camera/mic still blocked or not yet granted can still receive remote media;
- if you changed admin logic, verify `/admin` and the main admin actions still work.

## LiveKit Regression Guard
The project’s primary media path is now LiveKit SFU. Do not reintroduce browser-mesh assumptions into the main room bootstrap path.

Minimum manual check after editing room media logic:

- User A enters a room, then User B joins from desktop or mobile.
- B should immediately see A without refresh.
- Both sides should remain visible after `join_ok`, `participant_snapshot`, and LiveKit room connection complete.
- Refresh while screen sharing must not leave stale server-side `active_sharer_*` state or stale client-side “self is sharer” layout.
- Joining with the same account on two devices must not evict the other active device unless the old socket is truly stale.
- Room load must fail cleanly if LiveKit config is missing, including the expected `503` path.

## Cross-Module Conflict Audit
Before editing any non-trivial logic, inspect adjacent modules and shared state first, then check whether the change creates duplicated or conflicting flows elsewhere.

Minimum review steps for every substantial code change:

- Identify every entry point that can mutate the same state, such as initial load, refresh recovery, snapshot sync, user-triggered action, background retry, and disconnect cleanup.
- Trace which files own that state and which files consume it, especially `app.py`, `templates/_room_scripts.html`, `static/room_livekit.js`, and UI helpers.
- Prefer one canonical update path per state domain. If the same state is updated in multiple handlers, refactor to a shared helper before adding more conditions.
- After refactoring, re-read all related handlers end-to-end and verify they still agree on ordering, ownership, and cleanup.

## Room State Consistency Notes
Important project-specific reality:

- Socket.IO owns room roster, chat, host permissions, and UI-level room state.
- LiveKit owns camera, microphone, screen share media transport, and remote track delivery.
- Runtime online state is still primarily stored in single-process memory on the Flask side.

That means every room change should be checked for consistency across:

- Flask runtime room state
- Socket.IO roster events
- LiveKit participant/media lifecycle
- front-end layout and focus state

## Screen Share Notes
Screen sharing is still one of the most failure-prone features because it spans backend room state, LiveKit publication state, participant focus, and mobile browser constraints.

When changing screen share behavior:

- verify server cleanup of `active_sharer_*` fields;
- verify client focus state reset after stop, refresh, and reconnect;
- treat UI focus state separately from media publication state;
- prioritize “remote users can still see the share” over polished secondary interactions on mobile or weak networks;
- re-check recording and virtual background interactions if they share the same local media path.

## Recording and Virtual Background Notes
Both features are resource-heavy and should be treated as enhancement features, not baseline stability guarantees.

- Recording may depend on browser output format and optional server-side `ffmpeg` remux.
- Virtual background depends on browser-side processing and can degrade weak devices.
- If a change touches local media replacement, verify camera, screen share, virtual background, and recording paths do not conflict.

## Deployment and Runtime Guard
Do not write docs or make deployment assumptions as if this app were already safely horizontally scalable.

Current runtime reality:

- room online state is still largely single-process memory;
- LiveKit is external infrastructure and must be configured correctly;
- `ffmpeg` is optional but required for some recording export paths;
- deployment docs must stay aligned with actual env vars such as `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `PUBLIC_HOST`, and `PUBLIC_SCHEME`.

## Documentation Maintenance
When project behavior changes, update the relevant docs in the same workstream whenever practical.

If a document has paired Chinese and English sections or counterpart files, keep them synchronized. Do not leave one language with materially newer steps, warnings, or conclusions than the other.

At minimum, check whether the change affects:

- `README.md`
- `docs/README.md`
- `docs/STABILITY_AUDIT.md`
- `docs/DEPLOYMENT_GUIDE.md`
- `docs/项目说明与代码索引.md`
- `docs/REFACTOR_AUDIT.md`
- `AGENTS.md`

Do not leave `AGENTS.md` describing old mesh/P2P behavior after the code and README have moved on.

## Commit & Pull Request Guidelines
Recent history favors concise, imperative commit subjects such as `Fix ...`, `Improve ...`, or `Tune ...`.

- Keep commit titles specific and action-first.
- Scope PRs to one functional change area.
- PR descriptions should include the problem, the solution summary, manual test steps, and screenshots/GIFs for UI changes where relevant.
- Link related issues and call out config/env var changes explicitly, especially `PUBLIC_HOST`, `PUBLIC_SCHEME`, admin credentials, and LiveKit-related settings.
