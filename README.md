# Video Meeting UI Upgrade

Features:
- bilingual Chinese/English UI
- single-device login
- admin dashboard
- HTTPS invite links via PUBLIC_HOST/PUBLIC_SCHEME
- explicit media permission button
- camera switch button
- screen share button
- virtual background image replacement for the local camera feed

Run locally:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Systemd env vars example:
- PUBLIC_HOST=peoplelovesai.xyz
- PUBLIC_SCHEME=https
- ADMIN_USERNAME=root
- ADMIN_PASSWORD=your-password

LiveKit env vars required for meeting rooms:
- LIVEKIT_URL=wss://your-livekit-host
- LIVEKIT_API_KEY=your-api-key
- LIVEKIT_API_SECRET=your-api-secret
