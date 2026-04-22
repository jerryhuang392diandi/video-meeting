# Project Guide and Code Index

[中文](%E9%A1%B9%E7%9B%AE%E8%AF%B4%E6%98%8E%E4%B8%8E%E4%BB%A3%E7%A0%81%E7%B4%A2%E5%BC%95.md) | [English](PROJECT_GUIDE.en.md)

This document explains the project logic, core code locations, and presentation talking points. It combines system layering, communication methods, core flows, feature implementation, code index, and common Q&A in one place.

## 1. One-Sentence Overview

This is an online meeting system built with `Flask + Flask-SocketIO + LiveKit`, covering accounts, room creation and joining, multi-party audio/video, screen sharing, chat attachments, meeting history, admin management, and basic diagnostics.

A more engineering-oriented summary:

> Templates render pages, JavaScript handles interaction, Flask owns business logic, Socket.IO syncs real-time room state, and LiveKit transports audio/video media.

## 2. What Problem the Project Solves

This is not just a "camera can display" demo. It connects the common workflow of a meeting product:

- User registration, login, logout, and session control
- Meeting creation, meeting join, and meeting history
- Camera, microphone, and screen sharing inside the room
- Chat, emoji, @ mentions, image/video/document attachments
- Host actions, admin dashboard, and password reset requests
- Chinese/English UI, RTC/LiveKit diagnostics, recording, and virtual background

For presentation, emphasize that it is a complete web application, not a single WebRTC experiment page.

## 3. Main Page Entry Points

| Path | Page | Code location |
| --- | --- | --- |
| `/` | Home / create meeting / join meeting | `templates/index.html`, `index()` |
| `/login` | Login | `templates/login.html`, `login()` |
| `/register` | Registration | `templates/register.html`, `register()` |
| `/forgot-password` | Password reset request | `templates/forgot_password.html`, `forgot_password_page()` |
| `/quickstart` | Quickstart | `templates/quickstart.html`, `quickstart_page()` |
| `/help` | User Guide | `templates/help.html`, `help_page()` |
| `/support` | Support | `templates/support.html`, `support_page()` |
| `/account` | Account and preferences | `templates/account.html`, `account_page()` |
| `/history` | Meeting history | `templates/history.html`, `history()` |
| `/room/<room_id>` | Meeting room | `templates/room.html`, `room_page()` |
| `/admin` | Admin dashboard | `templates/admin.html`, `admin_dashboard()` |

These entries match the "User-Facing Pages" table in the root README.

## 4. Technical Architecture

| Layer | Main technology / file | Responsibility |
| --- | --- | --- |
| Template layer | `templates/*.html` | Page skeletons for login, home, room, history, account, admin, and other pages |
| Frontend interaction layer | `static/*.js` | Button events, API calls, Socket.IO and LiveKit connection, chat/video rendering |
| Flask backend layer | `app.py` | Accounts, meetings, permissions, uploads, admin, translation, Socket.IO events, LiveKit token generation |
| Real-time state layer | Flask-SocketIO + in-memory state | Member join/leave, chat, screen share state, host ending meetings |
| Media layer | LiveKit SFU | Camera, microphone, screen sharing, and remote media tracks |
| Persistence layer | SQLite / SQLAlchemy | Users, meetings, participation records, password reset requests |

The current refactor audit is in [REFACTOR_AUDIT.en.md](REFACTOR_AUDIT.en.md). Maintenance should keep room state consistency first, then gradually split `app.py` and the room frontend script.

## 4.1 i18n and Mobile/Desktop Adaptation

i18n:

- `translations.py` is the main translation table, and the `zh` and `en` key sets currently match.
- Templates prefer `t('key')`; some in-room runtime and browser-capability prompts use explicit Chinese/English branches.
- `check_i18n.py` checks templates for missed hardcoded Chinese and should be run before submitting.
- Users can change the page language through the language switch or the default language preference in `/account`.

Mobile and desktop:

- The home page has mobile QR join on phones, while desktop keeps room ID, password, and invite-link copy workflows.
- The room page uses a meeting grid plus right chat column on desktop; on phones, chat reflows into a bottom panel with touch scrolling and input visibility handling.
- `room_livekit.js` selects different media publishing settings for mobile and desktop, with more conservative settings on phones.
- `_room_scripts.html` handles mobile fullscreen, iOS video fullscreen, landscape orientation lock, touch playback recovery, and screen-share viewing.
- `style.css` and `room.css` keep responsive layout rules for general pages and the meeting room.

## 5. Why LiveKit Instead of Browser Mesh

If every browser directly connects to every other browser, connection count and each user's upload bandwidth grow quickly as the room gets larger. In a five-person meeting, each browser must maintain several connections, which increases browser load, network pressure, and debugging complexity.

This project uses LiveKit SFU: each user sends media to LiveKit, and LiveKit forwards it to the other users. This is more suitable for multi-party meetings and makes remote tracks, reconnection, and unstable networks easier to handle.

Presentation wording:

> I use LiveKit for media transport so the project can focus on meeting business logic, permission control, and system integration instead of implementing a multi-party media server from scratch.

## 6. How Frontend and Backend Communicate

The project uses four communication paths.

### 6.1 HTML Form Submission

Suitable for account and admin pages.

| Feature | Frontend template | Backend entry |
| --- | --- | --- |
| Register | `templates/register.html` | `/register`, `register()` |
| Login | `templates/login.html` | `/login`, `login()` |
| Account settings | `templates/account.html` | `/account`, `account_page()` |
| Admin actions | `templates/admin.html` | Multiple `/admin/...` routes |

Forms use `method="post"`, Flask reads `request.form`, and the server returns a new page or redirect.

### 6.2 `fetch` Calls to Flask APIs

Suitable for room creation, join validation, LiveKit token retrieval, uploads, translation, and recording remux.

| Feature | Backend API |
| --- | --- |
| Create room | `/api/create_room` |
| Validate room join | `/api/join_room` |
| Get LiveKit token | `/api/livekit/token` |
| Upload media attachment | `/api/chat_upload_media` |
| Upload document attachment | `/api/chat_upload_doc` |
| Remux recording to MP4 | `/api/remux-recording` |
| Translate chat message | `/api/translate_message`, `/api/translate_to_english` |

### 6.3 Socket.IO Real-Time Events

Suitable for room actions that should not refresh the page.

| Feature | Socket event |
| --- | --- |
| Actually join the room | `join_room` |
| Update display name | `update_profile` |
| Send chat | `meeting_chat_send` |
| Clear chat | `meeting_chat_clear` |
| Retract chat | `meeting_chat_retract` |
| Sync screen share state | `room_ui_event` |
| Host ends meeting | `host_end_meeting` |
| Leave room | `leave_room` |

Socket.IO owns membership, chat, host actions, and UI-level room state.

### 6.4 LiveKit Media Connection

Camera, microphone, and screen sharing media are not forwarded by the Flask application.

| Media feature | Implementation |
| --- | --- |
| Camera | `static/room_livekit.js` |
| Microphone | `static/room_livekit.js` |
| Screen share video | `static/room_livekit.js` |
| Screen share audio | `static/room_livekit.js` |

Flask authenticates the user and issues a LiveKit token. The browser then connects directly to the LiveKit service.

## 7. Key File Index

### Backend Core

| File | Description |
| --- | --- |
| `app.py` | Backend core: routes, models, admin logic, chat, attachments, translation, Socket.IO events, LiveKit token generation |
| `translations.py` | Chinese/English UI text |
| `check_i18n.py` | Checks templates for untranslated Chinese text |

### Templates

| File | Description |
| --- | --- |
| `templates/login.html` | Login page |
| `templates/register.html` | Registration page |
| `templates/index.html` | Home page for creating, joining, and QR joining meetings |
| `templates/room.html` | Meeting page entry |
| `templates/_room_layout.html` | Meeting page layout skeleton |
| `templates/_room_scripts.html` | Main room script entry for Socket.IO events, button binding, and room orchestration |
| `templates/account.html` | User preferences and account settings |
| `templates/admin.html` | Admin dashboard |
| `templates/history.html` | Meeting history |
| `templates/attachment_view.html` | Chat attachment view page |
| `templates/help.html`, `templates/support.html` | Help and support pages |

### Frontend Scripts and Styles

| File | Description |
| --- | --- |
| `static/room_livekit.js` | LiveKit connection, camera, microphone, screen share, media track sync |
| `static/room_chat.js` | Chat rendering, @ mentions, emoji panel, attachment rendering |
| `static/room_ui.js` | Meeting UI rendering, layout scheduling, participant card updates |
| `static/room_utils.js` | Copying text, HTML escaping, media track helpers |
| `static/room_diagnostics.js` | RTC / LiveKit diagnostics display |
| `static/room.css` | Meeting page styles |
| `static/style.css` | Shared page styles |

## 8. Data Storage

### Database Storage

Database models are concentrated in `app.py`.

| Model | Purpose |
| --- | --- |
| `User` | Account, password hash, admin flag, enabled state, display name, language, default join preferences |
| `Meeting` | Room ID, room password, host, meeting status, creation time, end time |
| `MeetingParticipant` | Participation records: who joined, when they joined, when they left |
| `PasswordResetRequest` | Password reset requests for admin handling |

### Runtime Memory State

The database stores persistent data. Real-time room state during meetings is mainly in memory.

| Variable | Purpose |
| --- | --- |
| `rooms` | Per-room online members, chat history, screen share state, host presence |
| `sid_to_user` | Maps Socket.IO `request.sid` to the current user and room |
| `user_active_sids` | Tracks active sockets for a user, used for session control and kicking users |

This means the current project is best treated as single-instance. Multi-instance deployment requires moving runtime state to Redis or another shared store.

## 9. Core Flows

### 9.1 Registration and Login

Registration:

1. `register.html` submits username and password with a normal form.
2. Flask `/register` reads the form.
3. The backend checks empty values and duplicate username.
4. `user.set_password(password)` stores the password hash.
5. The user is saved and logged in with `login_user(user)`.
6. `session["session_version"]` is written and the user is redirected home.

Login:

1. `login.html` submits to `/login`.
2. The backend queries `User` by username.
3. `user.check_password(password)` verifies the hash.
4. Disabled accounts are rejected.
5. `session_version` is refreshed.
6. `login_user(user)` establishes the session.
7. `disconnect_user_sockets(...)` cleans old sockets.

Presentation wording:

> Registration and login do not let the frontend modify the database directly. Flask validates input, passwords are stored as hashes, Flask-Login maintains the login state, and `session_version` invalidates old sessions.

### 9.2 Creating a Meeting

1. The user clicks "Create meeting" on the home page.
2. The frontend calls `POST /api/create_room`.
3. `api_create_room()` generates a room ID and password.
4. A `Meeting` database record is created.
5. `rooms[room_id]` runtime state is initialized.
6. The backend returns `room_id`, `password`, and `join_url`.
7. The frontend displays the meeting ID, password, and invite link.

Key point: `Meeting` is persistent; `rooms[room_id]` is runtime state.

### 9.3 Joining a Meeting

Joining has three steps.

First, HTTP validation on the home page:

1. The user enters room ID and password.
2. The frontend calls `POST /api/join_room`.
3. The backend checks existence, expiration, and password.
4. On success, the frontend redirects to `/room/<room_id>?pwd=...`.

Second, the room page joins the Socket.IO room:

1. `_room_scripts.html` loads.
2. The frontend creates a Socket.IO connection with `const socket = io()`.
3. It emits `join_room` with `room_id`, `password`, and `user_name`.
4. `on_join_room(data)` validates login, room state, and password again.
5. The backend records `request.sid` in `rooms[room_id]["participants"]`.
6. The backend records `sid_to_user`.
7. Socket.IO joins the room.
8. A `MeetingParticipant` record is written.
9. `join_ok` returns participants, chat history, and share state.
10. `participant_joined` is broadcast to other members.

Third, the frontend gets a LiveKit token and connects media:

1. The frontend receives `self_sid` from `join_ok`.
2. The frontend calls `POST /api/livekit/token`.
3. The request includes `room_id`, `password`, `participant_sid`, and `name`.
4. `api_livekit_token()` verifies the room, password, sid registration, and current user.
5. The backend signs a LiveKit JWT token.
6. `room_livekit.js` connects to LiveKit.

Presentation wording:

> Entering a meeting is not a single step. HTTP validates the room password, Socket.IO joins the real-time room, and only then does the client receive a LiveKit token for media.

## 10. Audio/Video and Meeting Features

### Camera and Microphone

Users can save default join preferences in `account.html`. `/account` stores them in `User.auto_enable_camera`, `User.auto_enable_microphone`, and `User.auto_enable_speaker`. Room scripts use those preferences after page load.

`room_livekit.js` controls actual media tracks:

| Function | Purpose |
| --- | --- |
| `buildRoomOptions()` | Camera/microphone capture and publishing parameters |
| `setCameraEnabled(nextEnabled)` | Controls camera through the LiveKit local participant |
| `setMicrophoneEnabled(nextEnabled)` | Controls microphone through the LiveKit local participant |

Mobile devices use more conservative capture settings to reduce power, heat, and network pressure.

### Screen Sharing

Frontend flow:

1. The user clicks the screen share button.
2. `_room_scripts.html` handles options such as system audio and microphone behavior.
3. The frontend calls `controller.setScreenShareEnabled(...)`.
4. `room_livekit.js` uses LiveKit screen sharing APIs.

Backend rule control:

1. The frontend reports `screen_share_started` or `screen_share_stopped` through `room_ui_event`.
2. The backend checks whether another sharer already exists.
3. If another user is sharing, it emits `screen_share_denied`.
4. If allowed, the backend writes `room["active_sharer_sid"]` and `room["active_sharer_user_id"]`.
5. On stop, the backend clears sharer state and broadcasts the update.

Presentation wording:

> LiveKit carries the screen media, while Flask maintains meeting rules such as only allowing one active screen sharer.

### Recording

Recording is driven by `toggleScreenRecording()` in `_room_scripts.html`.

1. The browser calls `navigator.mediaDevices.getDisplayMedia(...)`.
2. A `MediaRecorder` is created.
3. `ondataavailable` collects recording chunks.
4. On stop, chunks are merged into a `Blob`.

If the browser records MP4 directly, the frontend downloads it. If it records WebM, the frontend uploads it to `/api/remux-recording`; the backend calls `ffmpeg` to remux it to MP4.

### Virtual Background

Virtual background is an enhancement feature, not a requirement for baseline meeting stability. It depends on browser-side video processing and may increase CPU usage, heat, and delay on weak devices.

The room page sends the raw camera stream into MediaPipe Selfie Segmentation, draws the segmented output to a canvas, and replaces the LiveKit camera track with the canvas output track. To reduce startup failures, the code only uses camera tracks that are still `live`; on failure it falls back to the raw camera and cleans up the failed processing stream. Common causes include a camera that was just turned off or restarted, local preview not being ready yet, model asset loading failure, and weak device performance.

## 11. Chat, Attachments, Emoji, and @ Mentions

Attachments are not sent as Socket.IO binary payloads. The flow is:

1. Upload the file over HTTP.
2. The backend stores the file and returns attachment metadata.
3. The frontend sends chat text and metadata through Socket.IO.
4. The backend broadcasts metadata, not file bytes.

Upload APIs:

| Type | API |
| --- | --- |
| Media attachments | `/api/chat_upload_media` |
| Document attachments | `/api/chat_upload_doc` |

Size limits:

| Type | Limit |
| --- | --- |
| Image | 25 MB |
| Video | 120 MB |
| Document / archive | 25 MB |

Attachment access uses tokenized URLs:

| API | Purpose |
| --- | --- |
| `/chat_attachment/<room_id>/<token>` | Attachment view page |
| `/chat_attachment/<room_id>/<token>/raw` | Raw preview for embeddable files |
| `/chat_attachment/<room_id>/<token>/download` | Download endpoint when permission allows it |

Presentation wording:

> Large files are uploaded by HTTP first. The real-time chat channel only broadcasts text and attachment metadata, which keeps Socket.IO responsive and allows permission checks.

## 12. Admin Dashboard

| Item | Location |
| --- | --- |
| Page | `templates/admin.html` |
| Route | `/admin` |
| Backend function | `admin_dashboard()` |

The admin dashboard shows:

1. System status: CPU, memory, disk, online rooms, active sockets.
2. User list: admin state, disabled state, registration time.
3. Current and historical meetings: end meetings, delete records, bulk operations.
4. Password reset requests: mark resolved or rejected.

Time display rules:

- A regular user's meeting history uses that user's region/timezone preference from `/account`.
- The admin dashboard uses the current admin account's region/timezone preference for user registration times and meeting records.
- The page header shows the active display timezone to avoid confusion during cross-region troubleshooting.

Most admin actions are traditional POST forms.

Typical user management routes:

| Route | Purpose |
| --- | --- |
| `/admin/user/<id>/disable` | Disable user |
| `/admin/user/<id>/enable` | Enable user |
| `/admin/user/<id>/delete` | Delete user |
| `/admin/user/<id>/reset-password` | Reset password |
| `/admin/user/<id>/kick` | Kick user and disconnect sockets |

Typical meeting management routes:

| Route | Purpose |
| --- | --- |
| `/admin/meeting/<id>/end` | End one meeting |
| `/admin/meetings/bulk-end` | End meetings in bulk |
| `/admin/meeting/<id>/delete` | Delete one meeting record |
| `/admin/meetings/bulk-delete` | Delete meeting records in bulk |

Admin routes use both `@login_required` and `@admin_required`.

## 13. `app.py` Core Function Index

Line numbers may change; remember function names and responsibilities first.

| Function | Purpose |
| --- | --- |
| `account_page()` | Account profile, language, timezone, attachment permission defaults, media preferences, password change |
| `register()` | Registration, username/password validation, password hash, login state |
| `login()` | Login, password hash verification, account enabled check, `session_version` refresh |
| `api_create_room()` | Creates a meeting, writes `Meeting`, initializes runtime `rooms` |
| `api_join_room()` | HTTP validation before joining; does not join the real-time room |
| `room_page()` | Renders room page and injects room config, LiveKit URL, user preferences |
| `api_livekit_token()` | Verifies Socket identity and issues LiveKit token |
| `history()` | Queries current user's meeting history |
| `api_remux_recording()` | Receives recording and calls `ffmpeg` to remux MP4 |
| `admin_dashboard()` | Renders admin dashboard |
| `admin_delete_user()` | Deletes user and cleans related meetings, participation records, sockets |
| `admin_reset_user_password()` | Resets user password and disconnects old sessions |
| `admin_disable_user()` / `admin_enable_user()` | Disables or enables users |
| `admin_end_meeting()` / `admin_bulk_end_meetings()` | Ends one or many meetings |
| `admin_delete_meeting()` / `admin_bulk_delete_meetings()` | Deletes meeting records and runtime state |
| `on_join_room(data)` | Actually joins a user to a Socket.IO room |
| `_api_chat_upload_impl()` | Shared chat attachment upload implementation |
| `chat_attachment_view()` | Attachment view page |
| `chat_attachment_raw()` | Raw attachment preview |
| `chat_attachment_download()` | Attachment download |
| `api_translate_message()` / `api_translate_to_english()` | Chat message translation |
| `on_meeting_chat_send()` | Chat send and broadcast |
| `on_meeting_chat_clear()` | Clear chat |
| `on_meeting_chat_retract()` | Retract chat |
| `on_room_ui_event()` | Screen sharing and other room UI state rules |
| `on_host_end_meeting()` | Host ends meeting |
| `on_leave_room()` | User leaves meeting |

## 14. Code Walkthrough Pointers

### Create Meeting

Frontend `templates/index.html` calls:

```js
const res = await fetch('/api/create_room', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ host_name })
});
```

Backend `api_create_room()` creates a `Meeting` record and initializes `rooms[room_id]`.

### Validate Join Before Real Join

`/api/join_room` only checks whether the room can be joined. It does not write `rooms[room_id]["participants"]` and does not broadcast membership changes. The real join happens later through Socket.IO `join_room`.

### Room Page and Socket.IO Join

`templates/_room_scripts.html` creates the socket:

```js
const socket = io();
window.socket = socket;
```

Then it emits `join_room` with the room ID, password, and display name. The backend records `request.sid`, updates `sid_to_user`, calls Socket.IO `join_room(room_id)`, and returns `join_ok`.

### LiveKit Connects After `join_ok`

The frontend waits for `join_ok` because it needs `self_sid` before requesting a LiveKit token. `api_livekit_token()` verifies that the sid belongs to the current logged-in user and the current room before signing the token.

### Screen Share Has Two Layers

LiveKit publishes the actual screen media. Flask handles meeting rules through `room_ui_event`, including rejecting a second active sharer.

### Recording Is Frontend Capture plus Backend Remux

The browser records with `getDisplayMedia` and `MediaRecorder`. If the output is WebM, `/api/remux-recording` uses `ffmpeg` to convert or remux it to MP4.

### Chat Attachments Use HTTP Upload First

The frontend uploads the file, receives metadata, then sends that metadata with `meeting_chat_send`. `_api_chat_upload_impl()` stores files; `on_meeting_chat_send()` writes chat history and broadcasts the message.

## 15. Current Limits and Future Improvements

Current limits:

- Online state is mainly single-process memory, so restart loses online state and multi-instance deployment is unsafe.
- `app.py` is large and should eventually be split by domain.
- Virtual background depends on a live local camera track, browser-side model loading, and canvas processing. Screen sharing and recording are also resource-heavy.
- MP4 recording export depends on server-side `ffmpeg`.
- LiveKit must be correctly configured with `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET`.

Future improvements:

- Move `rooms`, `sid_to_user`, and other runtime state to Redis for multi-instance deployment.
- Split `app.py` into modules for auth, meetings, chat attachments, admin, and recording.
- Add automated tests for login, room creation, join validation, attachment upload, and admin actions.
- Add clearer frontend messages for LiveKit connection failure, mobile screen sharing limits, virtual background model loading failures, and recording remux failures.

## 16. Common Q&A

### Why Not Use C?

Direct answer:

> C is suitable for low-level high-performance components, but this project's main challenge is web application integration and meeting workflow, not implementing a media engine from scratch.

Reasons:

- The project focuses on accounts, rooms, permissions, database, templates, and admin, not pure low-level performance.
- Flask handles routes, sessions, templates, and database integration quickly.
- Heavy media transport is already delegated to LiveKit.
- C would increase memory management and security implementation cost for this course project.

### How Does a User Join a Meeting?

The home page first calls `/api/join_room` to validate room ID and password. Then it opens `/room/<room_id>`. The room page emits Socket.IO `join_room`, receives `join_ok`, requests `/api/livekit/token`, and finally connects to LiveKit.

### How Are Camera and Microphone Used?

The frontend reads user preferences, then `room_livekit.js` calls `setCameraEnabled` and `setMicrophoneEnabled` on the LiveKit local participant.

### How Is Screen Sharing Implemented?

The frontend calls LiveKit screen sharing APIs. The backend maintains the active sharer state through `room_ui_event` to prevent multiple users from sharing at the same time.

### How Are Documents Sent in a Meeting?

The frontend uploads the attachment over HTTP to `/api/chat_upload_media` or `/api/chat_upload_doc`. The backend stores it and returns metadata. Then the frontend broadcasts text plus metadata through `meeting_chat_send`.

### How Is the Admin Dashboard Implemented?

The admin visits `/admin`. The backend aggregates system status, users, meetings, and password reset requests, then renders `admin.html`. Operations are mostly POST forms protected by `@admin_required`.

## 17. Final Presentation Summary

Do not describe the project as only "a frontend video meeting page." A more accurate summary is:

- Flask handles accounts, meetings, permissions, uploads, admin management, and LiveKit token issuance.
- Socket.IO handles real-time state sync inside meetings.
- LiveKit handles actual camera, microphone, and screen sharing media transport.
- SQLite persists users, meetings, and participation records.
- Frontend templates and JavaScript handle interaction, rendering, and API calls.

If the presentation follows five lines, it will cover most questions: registration/login, join flow, audio/video, chat attachments, and admin dashboard.
