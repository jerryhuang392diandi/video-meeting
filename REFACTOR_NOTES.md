# Refactor notes

This pass focused on reducing duplication and keeping Git history usable without changing the runtime flow too aggressively.

## What changed
- Moved reusable helpers out of `app.py` into `core_utils.py`:
  - display-name helpers
  - password/room-id generators
  - traffic-cycle helpers
  - chat visibility helpers
  - TURN/base-url helpers
  - meeting-expiry helpers
- Kept route logic and Socket.IO handlers inside `app.py` to avoid a riskier behavioral rewrite.
- Removed generated or maintenance-only clutter:
  - `__pycache__/`
  - `check_i18n.py`
- Tightened `.gitignore` for a Git-based workflow:
  - ignore caches, swap files, backups
  - ignore runtime DB files and uploaded chat files
  - do **not** ignore the whole `instance/` directory anymore
- Added `instance/.gitkeep` so the runtime folder can stay in the repository without committing local DB artifacts.

## Current structure
- `app.py` keeps Flask routes, models, and Socket.IO events.
- `translations.py` keeps the translation dictionary.
- `core_utils.py` keeps reusable pure/helper logic.
- `templates/room.html` stays minimal and includes:
  - `_room_layout.html`
  - `_room_scripts.html`
