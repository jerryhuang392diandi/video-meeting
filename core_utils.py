import os
import secrets
import string
from datetime import datetime, timedelta
from pathlib import Path

TRAFFIC_RESET_DAYS = 30


def preferred_display_name(user):
    if not user:
        return "Guest"
    return (getattr(user, "display_name", None) or getattr(user, "username", None) or "Guest").strip()[:32] or "Guest"


def utc_iso(dt):
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_password(pwd: str) -> str:
    return (pwd or "").strip().upper()


def generate_room_id(exists_fn):
    while True:
        room_id = "".join(secrets.choice(string.digits) for _ in range(6))
        if not exists_fn(room_id):
            return room_id


def generate_password(length=6):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def get_base_url(request_obj):
    scheme = (os.environ.get("PUBLIC_SCHEME") or request_obj.headers.get("X-Forwarded-Proto") or "https").strip()
    host = (os.environ.get("PUBLIC_HOST") or request_obj.host or "").strip()
    return f"{scheme}://{host}"


def cycle_anchor_for_user(user):
    anchor = getattr(user, "traffic_cycle_start_at", None)
    if anchor:
        return anchor
    anchor = getattr(user, "created_at", None) or datetime.utcnow()
    user.traffic_cycle_start_at = anchor
    return anchor


def refresh_user_traffic_cycle(user, now=None):
    now = now or datetime.utcnow()
    anchor = cycle_anchor_for_user(user)
    changed = False
    while anchor + timedelta(days=TRAFFIC_RESET_DAYS) <= now:
        anchor = anchor + timedelta(days=TRAFFIC_RESET_DAYS)
        user.used_traffic_mb = 0.0
        changed = True
    if user.traffic_cycle_start_at != anchor:
        user.traffic_cycle_start_at = anchor
        changed = True
    if user.monthly_quota_mb is None:
        user.monthly_quota_mb = 3072.0
        changed = True
    if user.used_traffic_mb is None:
        user.used_traffic_mb = 0.0
        changed = True
    return changed


def user_remaining_quota_mb(user):
    refresh_user_traffic_cycle(user)
    return max(0.0, float(user.monthly_quota_mb or 0.0) - float(user.used_traffic_mb or 0.0))


def user_quota_exceeded(user):
    return user_remaining_quota_mb(user) <= 0.0001


def format_mb(mb_value):
    value = float(mb_value or 0.0)
    if value >= 1024:
        return f"{value / 1024:.2f} GB"
    return f"{value:.0f} MB"


def bool_from_form(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "on", "yes"}


def room_user_marker_key(user_id, sid=None):
    return f"user:{user_id}" if user_id else f"sid:{sid or ''}"


def visible_chat_history_for_user(room, user_id, sid, is_room_host=False):
    history = list(room.get("chat_history", []))
    marker_key = room_user_marker_key(user_id, sid)
    clear_index = int((room.get("chat_clear_markers") or {}).get(marker_key, 0) or 0)
    visible = []
    for idx, item in enumerate(history):
        if idx < clear_index and not is_room_host:
            continue
        if item.get("mode") == "all":
            visible.append(item)
        elif is_room_host or item.get("senderUserId") == user_id or item.get("from") == sid:
            visible.append(item)
    return visible


def detect_traffic_interface():
    forced = (os.environ.get("TURN_TRAFFIC_INTERFACE") or os.environ.get("TRAFFIC_NET_IFACE") or "").strip()
    if forced:
        return forced
    try:
        with open("/proc/net/route", "r", encoding="utf-8") as fh:
            next(fh, None)
            for line in fh:
                parts = line.strip().split()
                if len(parts) >= 4 and parts[1] == "00000000":
                    return parts[0]
    except OSError:
        return None
    return None


def read_interface_total_bytes(interface_name):
    if not interface_name:
        return None
    base = Path(f"/sys/class/net/{interface_name}/statistics")
    try:
        rx = int((base / "rx_bytes").read_text().strip())
        tx = int((base / "tx_bytes").read_text().strip())
        return rx + tx
    except OSError:
        return None


def traffic_summary_dict(user, traffic_monitor):
    refresh_user_traffic_cycle(user)
    remaining = user_remaining_quota_mb(user)
    anchor = cycle_anchor_for_user(user)
    reset_at = anchor + timedelta(days=TRAFFIC_RESET_DAYS)
    return {
        "monthly_quota_mb": round(float(user.monthly_quota_mb or 0.0), 2),
        "used_traffic_mb": round(float(user.used_traffic_mb or 0.0), 2),
        "remaining_traffic_mb": round(float(remaining), 2),
        "monthly_quota_text": format_mb(user.monthly_quota_mb),
        "used_traffic_text": format_mb(user.used_traffic_mb),
        "remaining_traffic_text": format_mb(remaining),
        "reset_at_text": reset_at.strftime("%Y-%m-%d %H:%M UTC"),
        "reset_cycle_days": TRAFFIC_RESET_DAYS,
        "traffic_interface": traffic_monitor.get("iface") or detect_traffic_interface() or "unknown",
    }


def build_turn_ice_servers(request_obj):
    urls_raw = (os.environ.get("TURN_URLS") or "").strip()
    username = (os.environ.get("TURN_USERNAME") or "").strip()
    credential = (os.environ.get("TURN_PASSWORD") or "").strip()
    if urls_raw and username and credential:
        urls = [item.strip() for item in urls_raw.split(",") if item.strip()]
    else:
        public_host = (os.environ.get("TURN_PUBLIC_HOST") or os.environ.get("PUBLIC_HOST") or request_obj.host.split(":")[0]).strip()
        urls = [f"turn:{public_host}:3478?transport=udp", f"turn:{public_host}:3478?transport=tcp"]
        username = username or (os.environ.get("TURN_USERNAME") or "turnuser").strip() or "turnuser"
        credential = credential or (os.environ.get("TURN_PASSWORD") or "turnpassword123").strip() or "turnpassword123"
    return [{"urls": urls, "username": username, "credential": credential}]


def is_meeting_expired(meeting, duration_seconds):
    if not meeting or not meeting.created_at:
        return False
    return datetime.utcnow() >= (meeting.created_at + timedelta(seconds=duration_seconds))
