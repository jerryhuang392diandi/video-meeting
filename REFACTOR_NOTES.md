# Refactor notes

- Moved the large `TRANSLATIONS` dictionary out of `app.py` into `translations.py`.
- Split `templates/room.html` into two includes: `_room_layout.html` and `_room_scripts.html`.
- Removed unused or generated clutter: `room.js`, backup templates, `__pycache__`, and swap files.
- Expanded `.gitignore` to keep cache, backup, and local DB artifacts out of commits.
- `debug_log()` now supports opt-in logging with `DEBUG_ROOM=1` without changing default behavior.
