# Video Meeting Replace

Flask + Flask-SocketIO video meeting app with bilingual UI, account/admin flows, room chat attachments, and LiveKit-based media delivery.

## Structure

- `app.py`: main Flask app, Socket.IO events, models, and runtime configuration.
- `templates/`: Jinja templates, with room UI split into `_room_layout.html` and `_room_scripts.html`.
- `static/`: page styles and room-side JavaScript helpers.
- `translations.py`: Chinese/English translation table used by `t(...)`.
- `check_i18n.py`: scans templates for hardcoded Chinese text.
- `docs/`: non-runtime engineering and presentation documents.

## Run Locally

Windows:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Environment

- `PUBLIC_HOST`
- `PUBLIC_SCHEME`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`

## Checks

- `python check_i18n.py`
- Manual smoke test for login, room join/leave, media controls, chat, and attachment upload
- Verify both `zh` and `en` flows after template changes
