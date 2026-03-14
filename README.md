# Video Meeting UI Upgrade

Features:
- bilingual Chinese/English UI
- single-device login
- admin dashboard
- HTTPS invite links via PUBLIC_HOST/PUBLIC_SCHEME
- explicit media permission button
- camera switch button
- screen share button
- virtual background placeholder button

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
