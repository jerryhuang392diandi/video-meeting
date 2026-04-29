import io
import mimetypes
import os
import secrets
import shutil
import sqlite3
import string
import subprocess
import tempfile
import threading
import time
import uuid
import hashlib
import smtplib
from collections import deque
from email.message import EmailMessage
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import urlopen, Request
from urllib.error import URLError
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps

from flask import Flask, abort, after_this_request, jsonify, redirect, render_template, request, send_file, session, url_for
from dotenv import load_dotenv

try:
    import psutil
except Exception:
    psutil = None
from werkzeug.utils import secure_filename

try:
    from PIL import Image, ImageOps
except Exception:
    Image = None
    ImageOps = None
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from livekit import api as livekit_api
except Exception:
    livekit_api = None

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
DB_PATH = os.path.join(INSTANCE_DIR, "app.db")
load_dotenv(os.path.join(BASE_DIR, ".env"))
os.makedirs(INSTANCE_DIR, exist_ok=True)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(16))
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["PREFERRED_URL_SCHEME"] = (os.environ.get("PUBLIC_SCHEME") or "https").strip().lower() if (os.environ.get("PUBLIC_SCHEME") or "").strip().lower() in {"http", "https"} else "https"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax") if os.environ.get("SESSION_COOKIE_SAMESITE", "Lax") in {"Lax", "Strict", "None"} else "Lax"
app.config["SESSION_COOKIE_SECURE"] = ((os.environ.get("SESSION_COOKIE_SECURE") or "").strip().lower() in {"1", "true", "yes", "on"}) if (os.environ.get("SESSION_COOKIE_SECURE") or "").strip() else app.config["PREFERRED_URL_SCHEME"] == "https"
app.config["REMEMBER_COOKIE_HTTPONLY"] = True
app.config["REMEMBER_COOKIE_SAMESITE"] = os.environ.get("REMEMBER_COOKIE_SAMESITE", "Lax") if os.environ.get("REMEMBER_COOKIE_SAMESITE", "Lax") in {"Lax", "Strict", "None"} else "Lax"
app.config["REMEMBER_COOKIE_SECURE"] = ((os.environ.get("REMEMBER_COOKIE_SECURE") or "").strip().lower() in {"1", "true", "yes", "on"}) if (os.environ.get("REMEMBER_COOKIE_SECURE") or "").strip() else app.config["PREFERRED_URL_SCHEME"] == "https"

socketio = SocketIO(app, cors_allowed_origins=None, async_mode="threading", max_http_buffer_size=50_000_000)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


DEBUG_ROOM = os.environ.get("DEBUG_ROOM") == "1"
PUBLIC_REGISTRATION_ENABLED = (os.environ.get("PUBLIC_REGISTRATION_ENABLED", "1") or "").strip().lower() in {"1", "true", "yes", "on"}
STRICT_SECURITY_CHECKS = (os.environ.get("STRICT_SECURITY_CHECKS", "0") or "").strip().lower() in {"1", "true", "yes", "on"}
SECURITY_HEADERS_ENABLED = (os.environ.get("SECURITY_HEADERS_ENABLED", "1") or "").strip().lower() in {"1", "true", "yes", "on"}
TURNSTILE_SITE_KEY = (os.environ.get("TURNSTILE_SITE_KEY") or "").strip()
TURNSTILE_SECRET_KEY = (os.environ.get("TURNSTILE_SECRET_KEY") or "").strip()
TURNSTILE_VERIFY_URL = (os.environ.get("TURNSTILE_VERIFY_URL") or "https://challenges.cloudflare.com/turnstile/v0/siteverify").strip()
TURNSTILE_TIMEOUT_SECONDS = max(3, int(os.environ.get("TURNSTILE_TIMEOUT_SECONDS", "5") or "5"))
LOGIN_RATE_LIMIT_PER_IP = max(3, int(os.environ.get("LOGIN_RATE_LIMIT_PER_IP", "20") or "20"))
LOGIN_RATE_LIMIT_PER_USER = max(3, int(os.environ.get("LOGIN_RATE_LIMIT_PER_USER", "8") or "8"))
LOGIN_RATE_LIMIT_WINDOW_SECONDS = max(60, int(os.environ.get("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "600") or "600"))
REGISTER_RATE_LIMIT_PER_IP = max(1, int(os.environ.get("REGISTER_RATE_LIMIT_PER_IP", "5") or "5"))
REGISTER_RATE_LIMIT_WINDOW_SECONDS = max(60, int(os.environ.get("REGISTER_RATE_LIMIT_WINDOW_SECONDS", "3600") or "3600"))
PASSWORD_RESET_RATE_LIMIT_PER_IP = max(1, int(os.environ.get("PASSWORD_RESET_RATE_LIMIT_PER_IP", "5") or "5"))
PASSWORD_RESET_RATE_LIMIT_WINDOW_SECONDS = max(60, int(os.environ.get("PASSWORD_RESET_RATE_LIMIT_WINDOW_SECONDS", "3600") or "3600"))
EMAIL_AUTH_ENABLED = (os.environ.get("EMAIL_AUTH_ENABLED", "0") or "").strip().lower() in {"1", "true", "yes", "on"}
EMAIL_SMTP_HOST = (os.environ.get("EMAIL_SMTP_HOST") or "").strip()
EMAIL_SMTP_PORT = max(1, int(os.environ.get("EMAIL_SMTP_PORT", "587") or "587"))
EMAIL_SMTP_USERNAME = (os.environ.get("EMAIL_SMTP_USERNAME") or "").strip()
EMAIL_SMTP_PASSWORD = os.environ.get("EMAIL_SMTP_PASSWORD") or ""
EMAIL_SMTP_USE_TLS = (os.environ.get("EMAIL_SMTP_USE_TLS", "1") or "").strip().lower() in {"1", "true", "yes", "on"}
EMAIL_SMTP_USE_SSL = (os.environ.get("EMAIL_SMTP_USE_SSL", "0") or "").strip().lower() in {"1", "true", "yes", "on"}
EMAIL_FROM_ADDRESS = (os.environ.get("EMAIL_FROM_ADDRESS") or "").strip()
EMAIL_FROM_NAME = (os.environ.get("EMAIL_FROM_NAME") or "Video Meeting").strip() or "Video Meeting"
ADMIN_ALERT_EMAIL = (os.environ.get("ADMIN_ALERT_EMAIL") or "").strip().lower()
ADMIN_EMAIL = (os.environ.get("ADMIN_EMAIL") or ADMIN_ALERT_EMAIL or "").strip().lower()
ADMIN_EMAIL_NOTIFY_ENABLED = (os.environ.get("ADMIN_EMAIL_NOTIFY_ENABLED", "0") or "").strip().lower() in {"1", "true", "yes", "on"}
ADMIN_NOTIFY_ON_USER_REGISTER = (os.environ.get("ADMIN_NOTIFY_ON_USER_REGISTER", "1") or "").strip().lower() in {"1", "true", "yes", "on"}
ADMIN_NOTIFY_ON_ROOM_JOIN = (os.environ.get("ADMIN_NOTIFY_ON_ROOM_JOIN", "1") or "").strip().lower() in {"1", "true", "yes", "on"}
ADMIN_NOTIFY_ON_DANGEROUS_ACTIONS = (os.environ.get("ADMIN_NOTIFY_ON_DANGEROUS_ACTIONS", "1") or "").strip().lower() in {"1", "true", "yes", "on"}
ADMIN_ROOM_JOIN_NOTIFY_COOLDOWN_SECONDS = max(0, int(os.environ.get("ADMIN_ROOM_JOIN_NOTIFY_COOLDOWN_SECONDS", "300") or "300"))
EMAIL_VERIFY_CODE_TTL_MINUTES = max(1, int(os.environ.get("EMAIL_VERIFY_CODE_TTL_MINUTES", "10") or "10"))
EMAIL_CODE_SEND_LIMIT = max(1, int(os.environ.get("EMAIL_CODE_SEND_LIMIT", "2") or "2"))
ADMIN_SECURITY_ALERTS_ENABLED = (os.environ.get("ADMIN_SECURITY_ALERTS_ENABLED", "1") or "").strip().lower() in {"1", "true", "yes", "on"}
ADMIN_SECURITY_LINK_DEFAULT_TTL_MINUTES = 60 * 24 * 365 * 5
ADMIN_SECURITY_LINK_TTL_MINUTES = max(
    60,
    int(
        os.environ.get(
            "ADMIN_SECURITY_LINK_TTL_MINUTES",
            str(ADMIN_SECURITY_LINK_DEFAULT_TTL_MINUTES),
        )
        or str(ADMIN_SECURITY_LINK_DEFAULT_TTL_MINUTES)
    ),
)
ADMIN_SECURITY_RECOVERY_CODE = (os.environ.get("ADMIN_SECURITY_RECOVERY_CODE") or "").strip()
SECURITY_LOCKDOWN_FILE = os.path.join(INSTANCE_DIR, "security_lockdown.json")

def normalize_admin_login_path(value: str | None) -> str:
    raw = (value or "/admin-login").strip() or "/admin-login"
    if not raw.startswith("/"):
        raw = "/" + raw
    if raw in {"/", "/login", "/register", "/forgot-password", "/forgot-password-support", "/admin"}:
        raw = "/admin-login"
    return raw

ADMIN_LOGIN_PATH = normalize_admin_login_path(os.environ.get("ADMIN_LOGIN_PATH"))
EMAIL_CODE_SEND_WINDOW_SECONDS = max(
    60,
    int(os.environ.get("EMAIL_CODE_SEND_WINDOW_SECONDS", str(EMAIL_VERIFY_CODE_TTL_MINUTES * 60)) or str(EMAIL_VERIFY_CODE_TTL_MINUTES * 60)),
)
REQUEST_THROTTLE = {}
REQUEST_THROTTLE_LOCK = threading.Lock()
ADMIN_NOTIFICATION_THROTTLE = {}
ADMIN_NOTIFICATION_THROTTLE_LOCK = threading.Lock()
SECURITY_LOCKDOWN_LOCK = threading.Lock()
SECURITY_LOCKDOWN_STATE = {"enabled": False, "activated_at": None, "reason": "", "source": ""}
WEAK_SECRET_VALUES = {
    "",
    "changeme",
    "change-me",
    "replace-me",
    "replace-with-a-long-random-secret",
    "replace-with-strong-admin-password",
    "replace-with-random-secret",
    "root1234",
    "admin",
    "admin123",
    "password",
    "password123",
    "123456",
    "12345678",
    "local-dev-secret-change-me",
}


def sanitize_host_port(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if "://" in raw:
        parsed = urlsplit(raw)
        raw = parsed.netloc or parsed.path
    raw = raw.strip().strip("/")
    if not re.fullmatch(r"[A-Za-z0-9.-]+(?::\d{1,5})?", raw):
        return ""
    return raw


def _client_address() -> str:
    remote_addr = (request.remote_addr or "").strip()
    forwarded = (request.headers.get("X-Forwarded-For") or "").split(",", 1)[0].strip()
    if remote_addr in {"127.0.0.1", "::1"} and forwarded:
        return forwarded[:64]
    return (remote_addr or forwarded or "unknown")[:64]


def _request_throttle_key(bucket: str, scope: str) -> str:
    normalized_scope = (scope or "").strip().lower()[:96] or "-"
    return f"{bucket}:{normalized_scope}"


def normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


def looks_like_email(value: str | None) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalize_email(value)))


def email_delivery_configured() -> bool:
    return bool(EMAIL_SMTP_HOST and EMAIL_FROM_ADDRESS)


def admin_email_notifications_configured() -> bool:
    return bool(ADMIN_EMAIL_NOTIFY_ENABLED and ADMIN_ALERT_EMAIL and email_delivery_configured())


def admin_security_alert_recipients() -> list[str]:
    recipients = []
    for address in [ADMIN_EMAIL, ADMIN_ALERT_EMAIL]:
        normalized = normalize_email(address)
        if normalized and looks_like_email(normalized) and normalized not in recipients:
            recipients.append(normalized)
    return recipients


def admin_security_alerts_configured() -> bool:
    return bool(ADMIN_SECURITY_ALERTS_ENABLED and admin_security_alert_recipients() and email_delivery_configured())


def email_auth_active() -> bool:
    return EMAIL_AUTH_ENABLED


def verification_email_required_for_user(user) -> bool:
    return bool(email_auth_active() and getattr(user, "email", None) and not getattr(user, "email_verified", False))


def email_code_hash(*, email: str, purpose: str, raw_code: str, user_id: int | None = None) -> str:
    payload = f"{normalize_email(email)}|{purpose}|{user_id or 0}|{raw_code or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def generate_email_verification_code() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(6))


def _consume_request_budget(bucket: str, scope: str, limit: int, window_seconds: int) -> int | None:
    now = time.time()
    key = _request_throttle_key(bucket, scope)
    with REQUEST_THROTTLE_LOCK:
        attempts = REQUEST_THROTTLE.get(key)
        if attempts is None:
            attempts = deque()
            REQUEST_THROTTLE[key] = attempts
        while attempts and attempts[0] <= now - window_seconds:
            attempts.popleft()
        if len(attempts) >= limit:
            retry_after = max(1, int(window_seconds - (now - attempts[0])))
            return retry_after
        attempts.append(now)
    return None


def _peek_request_budget(bucket: str, scope: str, window_seconds: int) -> tuple[int, int | None]:
    now = time.time()
    key = _request_throttle_key(bucket, scope)
    with REQUEST_THROTTLE_LOCK:
        attempts = REQUEST_THROTTLE.get(key)
        if attempts is None:
            return 0, None
        while attempts and attempts[0] <= now - window_seconds:
            attempts.popleft()
        if not attempts:
            REQUEST_THROTTLE.pop(key, None)
            return 0, None
        retry_after = max(1, int(window_seconds - (now - attempts[0])))
        return len(attempts), retry_after


def _too_many_attempts_response(template_name: str, *, status_code: int = 429):
    error = t("too_many_attempts")
    if template_name == "register.html":
        response = render_email_code_template(template_name, purpose="register", error=error)
    elif template_name == "login_email_code.html":
        response = render_email_code_template(template_name, purpose="login", error=error)
    elif template_name == "forgot_password.html":
        response = render_email_code_template(template_name, purpose="password_reset", error=error)
    elif template_name == "admin_login.html":
        response = render_template("pages/admin_login.html", error=error, admin_login_path=ADMIN_LOGIN_PATH)
    else:
        normalized_template = template_name if "/" in template_name else f"pages/{template_name}"
        response = render_template(normalized_template, error=error)
    return response, status_code, {"Retry-After": "60"}


def email_code_budget_bucket(purpose: str) -> str:
    return f"email_code_send:{(purpose or 'generic').strip().lower()[:24]}"


def get_email_code_send_state(*, purpose: str, scope: str | None) -> dict[str, int | bool | None]:
    normalized_scope = normalize_email(scope)
    if not normalized_scope:
        return {
            "count": 0,
            "remaining": EMAIL_CODE_SEND_LIMIT,
            "retry_after": None,
            "locked": False,
        }
    count, retry_after = _peek_request_budget(
        email_code_budget_bucket(purpose),
        normalized_scope,
        EMAIL_CODE_SEND_WINDOW_SECONDS,
    )
    remaining = max(0, EMAIL_CODE_SEND_LIMIT - count)
    return {
        "count": count,
        "remaining": remaining,
        "retry_after": retry_after if remaining == 0 else None,
        "locked": remaining == 0,
    }


def consume_email_code_send_budget(*, purpose: str, scope: str | None) -> int | None:
    normalized_scope = normalize_email(scope)
    if not normalized_scope:
        return None
    return _consume_request_budget(
        email_code_budget_bucket(purpose),
        normalized_scope,
        EMAIL_CODE_SEND_LIMIT,
        EMAIL_CODE_SEND_WINDOW_SECONDS,
    )


def build_email_code_flow_context(*, purpose: str, scope: str | None = None) -> dict[str, int | bool | str | None]:
    state = get_email_code_send_state(purpose=purpose, scope=scope)
    return {
        "email_code_send_count": state["count"],
        "email_code_send_limit": EMAIL_CODE_SEND_LIMIT,
        "email_code_send_remaining": state["remaining"],
        "email_code_send_locked": state["locked"],
        "email_code_send_retry_after": state["retry_after"],
        "email_code_send_window_minutes": max(1, EMAIL_CODE_SEND_WINDOW_SECONDS // 60),
        "email_code_button_key": "resend_email_verification_code" if state["count"] else "send_email_verification_code",
    }


def render_email_code_template(template_name: str, *, purpose: str, scope: str | None = None, **context):
    merged = build_email_code_flow_context(purpose=purpose, scope=scope)
    merged.update(context)
    normalized_template = template_name if '/' in template_name else f'pages/{template_name}'
    return render_template(normalized_template, **merged)


def build_email_code_sent_message(*, purpose: str, scope: str | None) -> str:
    state = get_email_code_send_state(purpose=purpose, scope=scope)
    return t("email_code_sent_status").format(remaining=state["remaining"], limit=EMAIL_CODE_SEND_LIMIT)


def build_email_code_limit_error() -> str:
    return t("email_code_send_limit_reached").format(
        limit=EMAIL_CODE_SEND_LIMIT,
        minutes=max(1, EMAIL_CODE_SEND_WINDOW_SECONDS // 60),
    )


def _validate_public_security_settings() -> list[str]:
    issues = []
    secret_key_env = (os.environ.get("SECRET_KEY") or "").strip()
    admin_password_env = (os.environ.get("ADMIN_PASSWORD") or "").strip()
    admin_username = (os.environ.get("ADMIN_USERNAME") or "root").strip() or "root"
    if not secret_key_env or len(secret_key_env) < 32 or secret_key_env.lower() in WEAK_SECRET_VALUES:
        issues.append("SECRET_KEY must be explicitly set to a long random value when STRICT_SECURITY_CHECKS=1.")
    if not admin_password_env or len(admin_password_env) < 12 or admin_password_env.lower() in WEAK_SECRET_VALUES:
        issues.append("ADMIN_PASSWORD must be explicitly set to a strong value when STRICT_SECURITY_CHECKS=1.")
    if admin_username.lower() == "root":
        issues.append("ADMIN_USERNAME should not stay as 'root' when STRICT_SECURITY_CHECKS=1.")
    if app.config["PREFERRED_URL_SCHEME"] == "https" and not app.config["SESSION_COOKIE_SECURE"]:
        issues.append("SESSION_COOKIE_SECURE must be enabled when PUBLIC_SCHEME=https and STRICT_SECURITY_CHECKS=1.")
    if app.config["PREFERRED_URL_SCHEME"] == "https" and not app.config["REMEMBER_COOKIE_SECURE"]:
        issues.append("REMEMBER_COOKIE_SECURE must be enabled when PUBLIC_SCHEME=https and STRICT_SECURITY_CHECKS=1.")
    if EMAIL_AUTH_ENABLED and not email_delivery_configured():
        issues.append("EMAIL_AUTH_ENABLED requires EMAIL_SMTP_HOST and EMAIL_FROM_ADDRESS to be configured when STRICT_SECURITY_CHECKS=1.")
    if ADMIN_EMAIL_NOTIFY_ENABLED and not admin_email_notifications_configured():
        issues.append("ADMIN_EMAIL_NOTIFY_ENABLED requires ADMIN_ALERT_EMAIL plus EMAIL_SMTP_HOST and EMAIL_FROM_ADDRESS when STRICT_SECURITY_CHECKS=1.")
    return issues


def turnstile_enabled() -> bool:
    return bool(TURNSTILE_SITE_KEY and TURNSTILE_SECRET_KEY)


def verify_turnstile_response(token: str | None) -> tuple[bool, str | None]:
    if not turnstile_enabled():
        return True, None
    response_token = (token or "").strip()
    if not response_token:
        return False, t("turnstile_required")
    payload = urlencode(
        {
            "secret": TURNSTILE_SECRET_KEY,
            "response": response_token,
            "remoteip": _client_address(),
        }
    ).encode("utf-8")
    try:
        req = Request(
            TURNSTILE_VERIFY_URL,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urlopen(req, timeout=TURNSTILE_TIMEOUT_SECONDS) as resp:
            raw = resp.read()
        data = json.loads(raw.decode("utf-8"))
    except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return False, t("turnstile_unavailable")
    if data.get("success"):
        return True, None
    return False, t("turnstile_failed")


def get_public_origin() -> str:
    scheme = (os.environ.get("PUBLIC_SCHEME") or "https").strip().lower()
    if scheme not in {"http", "https"}:
        scheme = "https"
    host = sanitize_host_port(os.environ.get("PUBLIC_HOST")) or sanitize_host_port(request.host)
    if not host:
        return request.url_root.rstrip("/")
    return f"{scheme}://{host}"


def is_valid_room_id(room_id: str) -> bool:
    return bool(re.fullmatch(r"\d{6}", (room_id or "").strip()))


def persist_bootstrap_secret(filename: str, value: str):
    path = os.path.join(INSTANCE_DIR, filename)
    if os.path.exists(path):
        return
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(value.strip() + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def get_admin_security_recovery_code() -> str:
    if ADMIN_SECURITY_RECOVERY_CODE:
        return ADMIN_SECURITY_RECOVERY_CODE
    path = os.path.join(INSTANCE_DIR, "security_recovery_code.txt")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                existing = (handle.read() or "").strip()
                if existing:
                    return existing
        except OSError:
            pass
    generated = secrets.token_urlsafe(18)
    persist_bootstrap_secret("security_recovery_code.txt", generated)
    return generated


def livekit_server_url() -> str:
    return (os.environ.get("LIVEKIT_URL") or "").strip()


def livekit_api_key() -> str:
    return (os.environ.get("LIVEKIT_API_KEY") or "").strip()


def livekit_api_secret() -> str:
    return (os.environ.get("LIVEKIT_API_SECRET") or "").strip()


def livekit_enabled() -> bool:
    return bool(livekit_api and livekit_server_url() and livekit_api_key() and livekit_api_secret())


def get_rtc_mode() -> str:
    return "livekit"


def debug_log(tag, **kwargs):
    if not DEBUG_ROOM:
        return None
    stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    payload = ", ".join(f"{key}={value!r}" for key, value in sorted(kwargs.items()))
    print(f"[{stamp}] [{tag}] {payload}")
    return None

MAX_PARTICIPANTS = 120
ROOM_EMPTY_GRACE_SECONDS = 20
MEETING_DURATION_SECONDS = 90 * 60
runtime_state_lock = threading.RLock()
rooms = {}
sid_to_user = {}
user_active_sids = {}
CHAT_UPLOAD_DIR = os.path.join(INSTANCE_DIR, "chat_uploads")
os.makedirs(CHAT_UPLOAD_DIR, exist_ok=True)
CHAT_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
CHAT_IMAGE_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
CHAT_VIDEO_MAX_UPLOAD_BYTES = 120 * 1024 * 1024
CHAT_ROOM_STORAGE_LIMIT_BYTES = 120 * 1024 * 1024
CHAT_GLOBAL_STORAGE_LIMIT_BYTES = 512 * 1024 * 1024
CHAT_IMAGE_MAX_DIMENSION = 1920
RECORDING_REMUX_TIMEOUT_SECONDS = 600
ALLOWED_CHAT_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "heic", "heif", "mp4", "webm", "mov", "m4v", "avi", "3gp", "pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "txt", "zip", "rar", "7z"}
CHAT_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".heic", ".heif"}
CHAT_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v", ".avi", ".3gp"}
REGION_TIMEZONE_OPTIONS = [
    "Asia/Tokyo",
    "Asia/Shanghai",
    "Asia/Hong_Kong",
    "Asia/Singapore",
    "Asia/Seoul",
    "Asia/Dubai",
    "Asia/Tehran",
    "Europe/Moscow",
    "Europe/Istanbul",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "America/Los_Angeles",
    "America/New_York",
    "America/Toronto",
    "Australia/Sydney",
    "UTC",
]
REGION_TIMEZONE_LABELS = {
    "zh": {
        "Asia/Tokyo": "东京，日本",
        "Asia/Shanghai": "上海，中国",
        "Asia/Hong_Kong": "香港，中国",
        "Asia/Singapore": "新加坡",
        "Asia/Seoul": "首尔，韩国",
        "Asia/Dubai": "迪拜，阿联酋",
        "Asia/Tehran": "德黑兰，伊朗",
        "Europe/Moscow": "莫斯科，俄罗斯",
        "Europe/Istanbul": "伊斯坦布尔，土耳其",
        "Europe/London": "伦敦，英国",
        "Europe/Paris": "巴黎，法国",
        "Europe/Berlin": "柏林，德国",
        "America/Los_Angeles": "洛杉矶，美国",
        "America/New_York": "纽约，美国",
        "America/Toronto": "多伦多，加拿大",
        "Australia/Sydney": "悉尼，澳大利亚",
        "UTC": "协调世界时",
    },
    "en": {
        "Asia/Tokyo": "Tokyo, Japan",
        "Asia/Shanghai": "Shanghai, China",
        "Asia/Hong_Kong": "Hong Kong, China",
        "Asia/Singapore": "Singapore",
        "Asia/Seoul": "Seoul, South Korea",
        "Asia/Dubai": "Dubai, United Arab Emirates",
        "Asia/Tehran": "Tehran, Iran",
        "Europe/Moscow": "Moscow, Russia",
        "Europe/Istanbul": "Istanbul, Turkey",
        "Europe/London": "London, United Kingdom",
        "Europe/Paris": "Paris, France",
        "Europe/Berlin": "Berlin, Germany",
        "America/Los_Angeles": "Los Angeles, United States",
        "America/New_York": "New York, United States",
        "America/Toronto": "Toronto, Canada",
        "Australia/Sydney": "Sydney, Australia",
        "UTC": "UTC",
    },
}

from i18n.translations import TRANSLATIONS

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), nullable=True)
    email_verified = db.Column(db.Boolean, default=True)
    email_verified_at = db.Column(db.DateTime, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    is_active_user = db.Column(db.Boolean, default=True)
    session_version = db.Column(db.Integer, default=0)
    display_name = db.Column(db.String(32), nullable=True)
    region = db.Column(db.String(64), nullable=True, default="Asia/Tokyo")
    preferred_locale = db.Column(db.String(16), nullable=True, default="auto")
    default_attachment_permission = db.Column(db.String(16), nullable=True, default="download")
    default_danmaku_enabled = db.Column(db.Boolean, default=True)
    auto_enable_camera = db.Column(db.Boolean, default=True)
    auto_enable_microphone = db.Column(db.Boolean, default=True)
    auto_enable_speaker = db.Column(db.Boolean, default=True)

    meetings = db.relationship("Meeting", backref="host", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Meeting(db.Model):
    __tablename__ = "meetings"

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(6), unique=True, nullable=False, index=True)
    room_password = db.Column(db.String(16), nullable=False)
    host_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    host_name = db.Column(db.String(32), nullable=False)
    status = db.Column(db.String(16), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)

    participants = db.relationship("MeetingParticipant", backref="meeting", lazy=True)


class MeetingParticipant(db.Model):
    __tablename__ = "meeting_participants"

    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    display_name = db.Column(db.String(32), nullable=False)
    sid = db.Column(db.String(128), nullable=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    left_at = db.Column(db.DateTime, nullable=True)


class PasswordResetRequest(db.Model):
    __tablename__ = "password_reset_requests"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False, index=True)
    contact = db.Column(db.String(128), nullable=True)
    note = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(16), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class EmailVerificationCode(db.Model):
    __tablename__ = "email_verification_codes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    purpose = db.Column(db.String(32), nullable=False, index=True)
    code_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="email_verification_codes", lazy=True)


class AdminSecurityActionToken(db.Model):
    __tablename__ = "admin_security_action_tokens"

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(32), nullable=False, index=True)
    context_key = db.Column(db.String(64), nullable=True, index=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def t(key: str) -> str:
    lang = session.get("lang", "zh")
    return TRANSLATIONS.get(lang, TRANSLATIONS["zh"]).get(key, key)


def tf(lang: str, key: str) -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["zh"]).get(key, key)


def localized_timezone_options(lang: str):
    labels = REGION_TIMEZONE_LABELS.get(lang, REGION_TIMEZONE_LABELS["zh"])
    return [
        {
            "value": value,
            "label": labels.get(value, value),
            "code": value,
        }
        for value in REGION_TIMEZONE_OPTIONS
    ]


def localized_timezone_label(value: str, lang: str) -> str:
    labels = REGION_TIMEZONE_LABELS.get(lang, REGION_TIMEZONE_LABELS["zh"])
    return labels.get(value, value)


def preferred_timezone(user=None) -> str:
    region = getattr(user, "region", None) if user else None
    if region in REGION_TIMEZONE_OPTIONS:
        return region
    return "Asia/Tokyo"


def preferred_display_name(user):
    if not user:
        return "Guest"
    return (getattr(user, "display_name", None) or getattr(user, "username", None) or "Guest").strip()[:32] or "Guest"

def utc_iso(dt):
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def asset_version(filename: str) -> int:
    static_path = os.path.join(BASE_DIR, "static", filename)
    try:
        return int(os.path.getmtime(static_path))
    except OSError:
        return int(time.time())


def build_livekit_room_name(room_id: str) -> str:
    return f"meeting-{room_id}"


@app.context_processor
def inject_globals():
    lang = session.get("lang", "zh")
    timezone = preferred_timezone(current_user) if current_user.is_authenticated else "Asia/Tokyo"
    return {
        "t": t,
        "lang": lang,
        "supported_langs": ["zh", "en"],
        "utc_iso": utc_iso,
        "asset_version": asset_version,
        "display_timezone": timezone,
        "display_timezone_label": localized_timezone_label(timezone, lang),
        "public_registration_enabled": PUBLIC_REGISTRATION_ENABLED,
        "email_auth_enabled": email_auth_active(),
        "turnstile_enabled": turnstile_enabled(),
        "turnstile_site_key": TURNSTILE_SITE_KEY,
    }


def ensure_user_columns():
    if not os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(users)")
    cols = {row[1] for row in cur.fetchall()}
    if "email" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN email VARCHAR(255)")
    if "email_verified" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT 1")
    if "email_verified_at" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN email_verified_at DATETIME")
    if "is_admin" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
    if "is_active_user" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN is_active_user BOOLEAN DEFAULT 1")
    if "session_version" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN session_version INTEGER DEFAULT 0")
    if "display_name" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN display_name VARCHAR(32)")
    if "region" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN region VARCHAR(64) DEFAULT 'Asia/Tokyo'")
    if "preferred_locale" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN preferred_locale VARCHAR(16) DEFAULT 'auto'")
    if "default_attachment_permission" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN default_attachment_permission VARCHAR(16) DEFAULT 'download'")
    if "default_danmaku_enabled" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN default_danmaku_enabled BOOLEAN DEFAULT 1")
    if "auto_enable_camera" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN auto_enable_camera BOOLEAN DEFAULT 1")
    if "auto_enable_microphone" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN auto_enable_microphone BOOLEAN DEFAULT 1")
    if "auto_enable_speaker" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN auto_enable_speaker BOOLEAN DEFAULT 1")
    cur.execute("CREATE TABLE IF NOT EXISTS password_reset_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, username VARCHAR(64) NOT NULL, contact VARCHAR(128), note TEXT, status VARCHAR(16) DEFAULT 'pending', created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("CREATE TABLE IF NOT EXISTS email_verification_codes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, email VARCHAR(255) NOT NULL, purpose VARCHAR(32) NOT NULL, code_hash VARCHAR(64) NOT NULL UNIQUE, expires_at DATETIME NOT NULL, used_at DATETIME, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id))")
    cur.execute("CREATE TABLE IF NOT EXISTS admin_security_action_tokens (id INTEGER PRIMARY KEY AUTOINCREMENT, action VARCHAR(32) NOT NULL, context_key VARCHAR(64), token_hash VARCHAR(64) NOT NULL UNIQUE, expires_at DATETIME NOT NULL, used_at DATETIME, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("PRAGMA table_info(admin_security_action_tokens)")
    admin_token_cols = {row[1] for row in cur.fetchall()}
    if "context_key" not in admin_token_cols:
        cur.execute("ALTER TABLE admin_security_action_tokens ADD COLUMN context_key VARCHAR(64)")
    conn.commit()
    conn.close()


def ensure_admin():
    admin_username = (os.environ.get("ADMIN_USERNAME") or "root").strip() or "root"
    admin_password = (os.environ.get("ADMIN_PASSWORD") or "").strip()
    admin_email = ADMIN_EMAIL if looks_like_email(ADMIN_EMAIL) else ""
    if STRICT_SECURITY_CHECKS:
        issues = _validate_public_security_settings()
        if issues:
            raise RuntimeError("Security configuration check failed: " + " ".join(issues))
    user = User.query.filter_by(username=admin_username).first()
    generated_password = None
    if not user:
        user = User(
            username=admin_username,
            email=admin_email or None,
            email_verified=True,
            email_verified_at=datetime.utcnow() if admin_email else None,
            is_admin=True,
            is_active_user=True,
            session_version=0,
        )
        if not admin_password:
            generated_password = secrets.token_urlsafe(18)
            admin_password = generated_password
        user.set_password(admin_password)
        db.session.add(user)
    else:
        user.is_admin = True
        user.is_active_user = True
        if admin_email and normalize_email(user.email) != admin_email:
            user.email = admin_email
            user.email_verified = True
            user.email_verified_at = datetime.utcnow()
        if not user.password_hash:
            if not admin_password:
                generated_password = secrets.token_urlsafe(18)
                admin_password = generated_password
            user.set_password(admin_password)
    db.session.commit()
    if generated_password:
        persist_bootstrap_secret("admin_password.txt", generated_password)
        app.logger.warning("ADMIN_PASSWORD was not set; generated an initial admin password and wrote it to instance/admin_password.txt")


@app.after_request
def apply_security_headers(response):
    if not SECURITY_HEADERS_ENABLED:
        return response
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(self), microphone=(self), geolocation=(), browsing-topics=()")
    if request.path in {"/login", "/register", "/forgot-password", "/admin", ADMIN_LOGIN_PATH}:
        response.headers.setdefault("Cache-Control", "no-store, private")
    return response


def normalize_password(pwd: str) -> str:
    return (pwd or "").strip().upper()


def generate_room_id():
    while True:
        room_id = "".join(secrets.choice(string.digits) for _ in range(6))
        if not Meeting.query.filter_by(room_id=room_id).first():
            return room_id


def generate_password(length=6):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def get_base_url():
    return get_public_origin()


def build_email_subject(key: str) -> str:
    prefix = t("app_name")
    return f"[{prefix}] {t(key)}"


def send_email_message(*, to_address: str, subject: str, text_body: str, html_body: str | None = None) -> None:
    if not email_delivery_configured():
        raise RuntimeError("Email delivery is not configured.")
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM_ADDRESS}>"
    message["To"] = to_address
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    smtp_class = smtplib.SMTP_SSL if EMAIL_SMTP_USE_SSL else smtplib.SMTP
    with smtp_class(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, timeout=15) as server:
        server.ehlo()
        if not EMAIL_SMTP_USE_SSL and EMAIL_SMTP_USE_TLS:
            server.starttls()
            server.ehlo()
        if EMAIL_SMTP_USERNAME:
            server.login(EMAIL_SMTP_USERNAME, EMAIL_SMTP_PASSWORD)
        server.send_message(message)


def _request_snapshot() -> dict[str, str]:
    try:
        return {
            "ip": _client_address(),
            "user_agent": (request.headers.get("User-Agent") or "")[:200],
            "path": (request.path or "")[:200],
        }
    except RuntimeError:
        return {"ip": "unknown", "user_agent": "", "path": ""}


def _format_admin_notification_body(title: str, fields: dict[str, object]) -> str:
    lines = [title, "", f"Time (UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"]
    for key, value in fields.items():
        if value is None or value == "":
            continue
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


def _security_action_token_hash(raw_token: str) -> str:
    return hashlib.sha256((raw_token or "").encode("utf-8")).hexdigest()


def create_admin_security_action_token(*, action: str, expires_minutes: int | None = None, context_key: str | None = None) -> str:
    raw_token = secrets.token_urlsafe(32)
    token = AdminSecurityActionToken(
        action=(action or "lockdown").strip().lower()[:32],
        context_key=(context_key or "").strip()[:64] or None,
        token_hash=_security_action_token_hash(raw_token),
        expires_at=datetime.utcnow() + timedelta(minutes=expires_minutes or ADMIN_SECURITY_LINK_TTL_MINUTES),
    )
    db.session.add(token)
    db.session.commit()
    return raw_token


def consume_admin_security_action_token(*, action: str, raw_token: str) -> AdminSecurityActionToken | None:
    token = AdminSecurityActionToken.query.filter_by(
        action=(action or "lockdown").strip().lower()[:32],
        token_hash=_security_action_token_hash(raw_token),
        used_at=None,
    ).order_by(AdminSecurityActionToken.created_at.desc()).first()
    if not token or token.expires_at < datetime.utcnow():
        return None
    token.used_at = datetime.utcnow()
    db.session.commit()
    return token


def invalidate_admin_security_action_tokens(*, context_key: str | None, actions: list[str] | tuple[str, ...] | set[str] | None = None) -> int:
    normalized_context = (context_key or "").strip()[:64]
    if not normalized_context:
        return 0
    query = AdminSecurityActionToken.query.filter_by(context_key=normalized_context, used_at=None)
    normalized_actions = [
        (action or "").strip().lower()[:32]
        for action in (actions or [])
        if (action or "").strip()
    ]
    if normalized_actions:
        query = query.filter(AdminSecurityActionToken.action.in_(normalized_actions))
    updated = query.update({"used_at": datetime.utcnow()}, synchronize_session=False)
    if updated:
        db.session.commit()
    return updated


def _load_security_lockdown_state() -> None:
    with SECURITY_LOCKDOWN_LOCK:
        if not os.path.exists(SECURITY_LOCKDOWN_FILE):
            SECURITY_LOCKDOWN_STATE.update({"enabled": False, "activated_at": None, "reason": "", "source": ""})
            return
        try:
            with open(SECURITY_LOCKDOWN_FILE, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception:
            payload = {}
        SECURITY_LOCKDOWN_STATE.update(
            {
                "enabled": bool(payload.get("enabled")),
                "activated_at": payload.get("activated_at"),
                "reason": str(payload.get("reason") or "")[:200],
                "source": str(payload.get("source") or "")[:120],
            }
        )


def _save_security_lockdown_state_locked() -> None:
    with open(SECURITY_LOCKDOWN_FILE, "w", encoding="utf-8") as fh:
        json.dump(SECURITY_LOCKDOWN_STATE, fh, ensure_ascii=False, indent=2)


def security_lockdown_active() -> bool:
    with SECURITY_LOCKDOWN_LOCK:
        return bool(SECURITY_LOCKDOWN_STATE.get("enabled"))


def activate_security_lockdown(*, reason: str, source: str) -> None:
    with SECURITY_LOCKDOWN_LOCK:
        SECURITY_LOCKDOWN_STATE.update(
            {
                "enabled": True,
                "activated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "reason": (reason or "security lockdown").strip()[:200],
                "source": (source or "unknown").strip()[:120],
            }
        )
        _save_security_lockdown_state_locked()
    with runtime_state_lock:
        active_sids = list(sid_to_user.keys())
    for sid in active_sids:
        try:
            socketio.server.disconnect(sid, namespace="/")
        except Exception:
            app.logger.exception("Failed to disconnect sid during security lockdown: %s", sid)
    app.logger.warning("Security lockdown activated: %s (%s)", reason, source)


def clear_security_lockdown(*, reason: str, source: str) -> None:
    with SECURITY_LOCKDOWN_LOCK:
        SECURITY_LOCKDOWN_STATE.update(
            {
                "enabled": False,
                "activated_at": None,
                "reason": (reason or "").strip()[:200],
                "source": (source or "").strip()[:120],
            }
        )
        if os.path.exists(SECURITY_LOCKDOWN_FILE):
            try:
                os.remove(SECURITY_LOCKDOWN_FILE)
            except OSError:
                _save_security_lockdown_state_locked()
    app.logger.warning("Security lockdown cleared: %s (%s)", reason, source)


def send_admin_security_alert(*, subject: str, fields: dict[str, object], cooldown_key: str | None = None, cooldown_seconds: int = 0) -> None:
    if not admin_security_alerts_configured():
        return
    if cooldown_key and cooldown_seconds > 0:
        now = time.time()
        key = f"security_alert:{cooldown_key}"[:180]
        with ADMIN_NOTIFICATION_THROTTLE_LOCK:
            last_sent = ADMIN_NOTIFICATION_THROTTLE.get(key, 0)
            if now - last_sent < cooldown_seconds:
                return
            ADMIN_NOTIFICATION_THROTTLE[key] = now
    alert_context = secrets.token_urlsafe(18)
    raw_token = create_admin_security_action_token(action="lockdown", context_key=alert_context)
    ignore_token = create_admin_security_action_token(action="ignore_lockdown", context_key=alert_context)
    lockdown_url = url_for("admin_security_lockdown", token=raw_token, _external=True)
    ignore_url = url_for("admin_security_lockdown_ignore", token=ignore_token, _external=True)
    payload = {
        **fields,
        "One-click lockdown URL": lockdown_url,
        "Ignore this alert URL": ignore_url,
        "Link validity": "The lockdown link stays active until you use it or open the ignore link from this alert email.",
        "If this was not you": "Open the lockdown URL immediately to force the service offline.",
    }
    body = _format_admin_notification_body(subject, payload)

    def _send():
        for recipient in admin_security_alert_recipients():
            try:
                send_email_message(
                    to_address=recipient,
                    subject=f"[Security Alert] {subject}",
                    text_body=body,
                )
            except Exception:
                app.logger.exception("Failed to send admin security alert email to %s", recipient)

    threading.Thread(target=_send, daemon=True).start()


def send_admin_notification(subject: str, body: str) -> None:
    if not admin_email_notifications_configured():
        return

    def _send():
        try:
            send_email_message(
                to_address=ADMIN_ALERT_EMAIL,
                subject=f"[Admin Alert] {subject}",
                text_body=body,
            )
        except Exception:
            app.logger.exception("Failed to send admin notification email")

    threading.Thread(target=_send, daemon=True).start()


def notify_admin_event(event_key: str, subject: str, fields: dict[str, object], *, cooldown_key: str | None = None, cooldown_seconds: int = 0) -> None:
    if not admin_email_notifications_configured():
        return
    if cooldown_key and cooldown_seconds > 0:
        now = time.time()
        key = f"{event_key}:{cooldown_key}"[:180]
        with ADMIN_NOTIFICATION_THROTTLE_LOCK:
            last_sent = ADMIN_NOTIFICATION_THROTTLE.get(key, 0)
            if now - last_sent < cooldown_seconds:
                return
            ADMIN_NOTIFICATION_THROTTLE[key] = now
    send_admin_notification(subject, _format_admin_notification_body(subject, fields))


def notify_admin_user_registered(user: "User") -> None:
    if not ADMIN_NOTIFY_ON_USER_REGISTER:
        return
    snap = _request_snapshot()
    notify_admin_event(
        "user_register",
        "New user registered",
        {
            "Username": user.username,
            "Email": user.email or "not set",
            "Verified email": bool(user.email_verified),
            "User ID": user.id,
            "IP": snap["ip"],
            "User-Agent": snap["user_agent"],
        },
    )


def notify_admin_room_joined(*, user: "User", meeting: "Meeting", display_name: str) -> None:
    if not ADMIN_NOTIFY_ON_ROOM_JOIN:
        return
    snap = _request_snapshot()
    notify_admin_event(
        "room_join",
        "User joined meeting room",
        {
            "Room ID": meeting.room_id,
            "Meeting title": getattr(meeting, "title", ""),
            "Username": user.username,
            "Display name": display_name,
            "Email": user.email or "not set",
            "User ID": user.id,
            "Host user ID": meeting.host_user_id,
            "IP": snap["ip"],
            "User-Agent": snap["user_agent"],
        },
        cooldown_key=f"{meeting.room_id}:{user.id}",
        cooldown_seconds=ADMIN_ROOM_JOIN_NOTIFY_COOLDOWN_SECONDS,
    )


def notify_admin_dangerous_action(action: str, fields: dict[str, object]) -> None:
    if not ADMIN_NOTIFY_ON_DANGEROUS_ACTIONS:
        return
    snap = _request_snapshot()
    admin_name = getattr(current_user, "username", "unknown") if getattr(current_user, "is_authenticated", False) else "unknown"
    payload = {
        "Action": action,
        "Admin": admin_name,
        "Admin user ID": getattr(current_user, "id", None),
        **fields,
        "IP": snap["ip"],
        "Path": snap["path"],
        "User-Agent": snap["user_agent"],
    }
    notify_admin_event("dangerous_action", f"Dangerous action: {action}", payload)


def create_email_verification_code(*, email: str, purpose: str, user_id: int | None = None) -> str:
    raw_code = generate_email_verification_code()
    query = EmailVerificationCode.query.filter_by(email=email, purpose=purpose, used_at=None)
    if user_id is None:
        query = query.filter(EmailVerificationCode.user_id.is_(None))
    else:
        query = query.filter_by(user_id=user_id)
    query.delete(synchronize_session=False)
    code = EmailVerificationCode(
        user_id=user_id,
        email=email,
        purpose=purpose,
        code_hash=email_code_hash(email=email, purpose=purpose, raw_code=raw_code, user_id=user_id),
        expires_at=datetime.utcnow() + timedelta(minutes=EMAIL_VERIFY_CODE_TTL_MINUTES),
    )
    db.session.add(code)
    db.session.commit()
    return raw_code


def find_email_verification_code(*, email: str, purpose: str, raw_code: str, user_id: int | None = None) -> EmailVerificationCode | None:
    query = EmailVerificationCode.query.filter_by(
        email=email,
        purpose=purpose,
        code_hash=email_code_hash(email=email, purpose=purpose, raw_code=raw_code, user_id=user_id),
        used_at=None,
    )
    if user_id is None:
        query = query.filter(EmailVerificationCode.user_id.is_(None))
    else:
        query = query.filter_by(user_id=user_id)
    code = query.order_by(EmailVerificationCode.created_at.desc()).first()
    if not code or code.expires_at < datetime.utcnow():
        return None
    return code


def purge_user_auth_artifacts(user_id: int, username: str | None = None) -> None:
    EmailVerificationCode.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    if username:
        PasswordResetRequest.query.filter_by(username=username).delete(synchronize_session=False)


def send_email_verification_code(*, email: str, purpose: str, user: User | None = None) -> None:
    raw_code = create_email_verification_code(
        email=email,
        purpose=purpose,
        user_id=user.id if user else None,
    )
    if purpose == "register":
        intro_key = "register_email_code_mail_intro"
    elif purpose == "login":
        intro_key = "login_email_code_mail_intro"
    elif purpose == "password_reset":
        intro_key = "password_reset_code_mail_intro"
    else:
        intro_key = "login_email_code_mail_intro"
    text_body = (
        f"{t(intro_key)}\n\n"
        f"{raw_code}\n\n"
        f"{t('email_verify_code_mail_expiry').format(minutes=EMAIL_VERIFY_CODE_TTL_MINUTES)}"
    )
    html_body = (
        f"<p>{t(intro_key)}</p>"
        f"<p><strong style=\"font-size:24px;letter-spacing:0.32em\">{raw_code}</strong></p>"
        f"<p>{t('email_verify_code_mail_expiry').format(minutes=EMAIL_VERIFY_CODE_TTL_MINUTES)}</p>"
    )
    send_email_message(
        to_address=email,
        subject=build_email_subject("email_verify_subject"),
        text_body=text_body,
        html_body=html_body,
    )


def mark_user_email_verified(user: User) -> None:
    user.email_verified = True
    user.email_verified_at = datetime.utcnow()


def create_password_reset_request(identifier: str, contact: str, note: str) -> None:
    req = PasswordResetRequest(
        username=(identifier or "").strip()[:64],
        contact=(contact or "").strip()[:128],
        note=(note or "").strip()[:500],
        status="pending",
    )
    db.session.add(req)
    db.session.commit()


def find_user_by_identifier(identifier: str) -> User | None:
    normalized_identifier = (identifier or "").strip()
    normalized_email = normalize_email(identifier)
    return User.query.filter(
        or_(
            User.username == normalized_identifier,
            func.lower(User.email) == normalized_email,
        )
    ).first()


def find_admin_by_identifier(identifier: str) -> User | None:
    normalized_identifier = (identifier or "").strip()
    normalized_email = normalize_email(identifier)
    admin_username = (os.environ.get("ADMIN_USERNAME") or "root").strip() or "root"

    if normalized_identifier == admin_username:
        return User.query.filter_by(username=admin_username, is_admin=True).first()

    if ADMIN_EMAIL and normalized_email == ADMIN_EMAIL:
        return User.query.filter_by(username=admin_username, is_admin=True).first()

    user = find_user_by_identifier(identifier)
    if user and user.is_admin:
        return user
    return None


def validate_login_target_user(
    user: User | None,
    *,
    identifier: str | None = None,
    require_admin: bool = False,
    allow_admin: bool = False,
) -> str | None:
    if not user:
        if require_admin:
            return t("invalid_admin_login")
        if identifier and looks_like_email(identifier):
            return t("email_not_registered")
        return t("invalid_login")
    if require_admin:
        if not user.is_admin:
            return t("invalid_admin_login")
    elif user.is_admin and not allow_admin:
        return t("admin_use_admin_login")
    if not user.is_active_user:
        return t("account_disabled")
    if not require_admin and verification_email_required_for_user(user):
        return t("email_not_verified")
    return None


def finalize_authenticated_session(user: User, *, force_logout_message: str | None = None) -> None:
    user.session_version = (user.session_version or 0) + 1
    db.session.commit()
    login_user(user)
    session["session_version"] = user.session_version
    disconnect_user_sockets(user.id, message=force_logout_message or t("kicked"))


def format_mb(mb_value):
    value = float(mb_value or 0.0)
    if value >= 1024:
        return f"{value / 1024:.2f} GB"
    return f"{value:.0f} MB"


def bool_from_form(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "on", "yes"}


def parse_int_list(values):
    parsed = []
    for item in values or []:
        try:
            parsed.append(int(item))
        except (TypeError, ValueError):
            continue
    return parsed


def room_user_marker_key(user_id, sid=None):
    return f"user:{user_id}" if user_id else f"sid:{sid or ''}"


def room_allowed_user_ids(room):
    if not room:
        return set()
    return {info.get("user_id") for info in room.get("participants", {}).values() if info.get("user_id")}


def can_user_access_room(room, user_id):
    if not room or not user_id:
        return False
    return user_id in room_allowed_user_ids(room) or user_id == room.get("host_user_id")


def build_room_participant_payload(sid, info, host_user_id):
    return {
        "sid": sid,
        "name": info.get("name") or "Guest",
        "is_host": bool(info.get("user_id") == host_user_id),
    }


def mark_meeting_participant_left(sid):
    participant = MeetingParticipant.query.filter_by(sid=sid).order_by(MeetingParticipant.id.desc()).first()
    if participant and not participant.left_at:
        participant.left_at = datetime.utcnow()
    return participant


def emit_host_presence_changed(room_id, host_present, message):
    socketio.emit(
        "host_presence_changed",
        {"host_present": bool(host_present), "message": message},
        room=room_id,
    )


def emit_participant_left(room_id, sid, participant_info, participant_count):
    if not participant_info:
        return
    socketio.emit(
        "participant_left",
        {
            "sid": sid,
            "name": participant_info.get("name") or "Guest",
            "participant_count": participant_count,
        },
        room=room_id,
    )


def runtime_state_snapshot():
    with runtime_state_lock:
        room_items = list(rooms.items())
        active_socket_count = len(sid_to_user)
        active_room_count = len(room_items)
        online_user_total = sum(1 for _, sids in user_active_sids.items() if sids)
        rooms_with_cleanup_timer = sum(1 for _, room in room_items if room.get("cleanup_timer"))
        rooms_with_expiry_timer = sum(1 for _, room in room_items if room.get("expiry_timer"))
        active_sharer_room_count = sum(
            1
            for _, room in room_items
            if room.get("active_sharer_sid") or room.get("active_sharer_user_id")
        )
        room_participant_counts = {
            room_id: len(room.get("participants", {}))
            for room_id, room in room_items
        }
        user_sid_counts = {
            user_id: len(sids)
            for user_id, sids in user_active_sids.items()
            if sids
        }
    return {
        "active_room_count": active_room_count,
        "active_socket_count": active_socket_count,
        "online_user_count": online_user_total,
        "rooms_with_cleanup_timer": rooms_with_cleanup_timer,
        "rooms_with_expiry_timer": rooms_with_expiry_timer,
        "active_sharer_room_count": active_sharer_room_count,
        "room_participant_counts": room_participant_counts,
        "user_sid_counts": user_sid_counts,
    }


def prune_stale_room_participants(room_id, room, user_id, current_sid):
    if not user_id:
        return []
    active_sids_for_user = set(user_active_sids.get(user_id, set()))
    stale_sids = []
    for sid, info in list(room.get("participants", {}).items()):
        if sid == current_sid or info.get("user_id") != user_id:
            continue
        if sid in active_sids_for_user and sid_to_user.get(sid):
            continue
        stale_sids.append(sid)
    for stale_sid in stale_sids:
        room.get("participants", {}).pop(stale_sid, None)
        sid_to_user.pop(stale_sid, None)
        unbind_user_socket(user_id, stale_sid)
        try:
            socketio.server.leave_room(stale_sid, room_id, namespace='/')
        except Exception:
            pass
        try:
            socketio.server.disconnect(stale_sid, namespace='/')
        except Exception:
            pass
        mark_meeting_participant_left(stale_sid)
    return stale_sids


def reconcile_rejoining_active_sharer(room_id, room, user_id):
    if not user_id or room.get("active_sharer_user_id") != user_id:
        return
    previous_sharer_sid = room.get("active_sharer_sid")
    sharer_active = bool(
        previous_sharer_sid
        and previous_sharer_sid in room.get("participants", {})
        and sid_to_user.get(previous_sharer_sid)
    )
    if sharer_active:
        return
    room["active_sharer_sid"] = None
    room["active_sharer_user_id"] = None
    if previous_sharer_sid:
        socketio.emit(
            "room_ui_event",
            {"type": "screen_share_stopped", "from": previous_sharer_sid, "reason": "sharer_reconnected"},
            room=room_id,
        )


def set_active_sharer(room, sid, user_id):
    room["active_sharer_sid"] = sid
    room["active_sharer_user_id"] = user_id


def clear_active_sharer(room):
    room["active_sharer_sid"] = None
    room["active_sharer_user_id"] = None


def normalize_active_sharer_state(room):
    active_sharer_sid = room.get("active_sharer_sid")
    active_sharer_user_id = room.get("active_sharer_user_id")
    if not active_sharer_sid and not active_sharer_user_id:
        return
    participants = room.get("participants", {})
    if active_sharer_sid and active_sharer_sid in participants and sid_to_user.get(active_sharer_sid):
        return
    replacement_sid = None
    if active_sharer_user_id:
        replacement_sid = next(
            (
                candidate
                for candidate in user_active_sids.get(active_sharer_user_id, set())
                if candidate in participants and sid_to_user.get(candidate)
            ),
            None,
        )
    if replacement_sid:
        set_active_sharer(room, replacement_sid, active_sharer_user_id)
        return
    clear_active_sharer(room)


def build_active_sharer_payload(room):
    normalize_active_sharer_state(room)
    return {
        "active_sharer_sid": room.get("active_sharer_sid"),
        "active_sharer_user_id": room.get("active_sharer_user_id"),
    }


def reconcile_departing_active_sharer(room_id, room, sid, user_id):
    if room.get("active_sharer_sid") != sid:
        return
    remaining_user_sids = list(user_active_sids.get(user_id, set())) if user_id else []
    replacement_sid = next(
        (candidate for candidate in remaining_user_sids if candidate != sid and candidate in room.get("participants", {})),
        None,
    )
    if replacement_sid:
        set_active_sharer(room, replacement_sid, user_id)
        socketio.emit(
            "room_ui_event",
            {"type": "screen_share_started", "from": replacement_sid, "hideSidebar": True, "restored": True},
            room=room_id,
        )
        return
    clear_active_sharer(room)
    socketio.emit("room_ui_event", {"type": "screen_share_stopped", "from": sid}, room=room_id)


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


def get_system_metrics():
    cpu_percent = 0.0
    memory_percent = 0.0
    if psutil:
        try:
            cpu_percent = float(psutil.cpu_percent(interval=0.15))
        except Exception:
            cpu_percent = 0.0
        try:
            memory_percent = float(psutil.virtual_memory().percent)
        except Exception:
            memory_percent = 0.0
    try:
        disk = shutil.disk_usage(BASE_DIR)
        disk_total = disk.total / (1024 * 1024)
        disk_used = (disk.used) / (1024 * 1024)
        disk_percent = (disk.used / disk.total * 100.0) if disk.total else 0.0
    except Exception:
        disk_total = disk_used = disk_percent = 0.0
    snapshot = runtime_state_snapshot()
    return {
        "cpu_percent": round(cpu_percent, 1),
        "memory_percent": round(memory_percent, 1),
        "disk_percent": round(disk_percent, 1),
        "disk_used_text": format_mb(disk_used),
        "disk_total_text": format_mb(disk_total),
        "active_room_count": snapshot["active_room_count"],
        "active_socket_count": snapshot["active_socket_count"],
    }


def build_recording_remux_commands(ffmpeg_path, input_path, output_path):
    common_prefix = [ffmpeg_path, "-y", "-fflags", "+genpts", "-i", input_path]
    audio_tail = ["-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2"]
    h264_video_tail = [
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-profile:v", "main", "-movflags", "+faststart",
    ]
    mpeg4_video_tail = [
        "-c:v", "mpeg4", "-q:v", "5", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
    ]
    return [
        common_prefix + ["-map", "0:v:0", "-map", "0:a?"] + h264_video_tail + audio_tail + ["-shortest", output_path],
        common_prefix + ["-map", "0:v:0", "-map", "0:a?"] + mpeg4_video_tail + audio_tail + ["-shortest", output_path],
        common_prefix + ["-map", "0:v:0"] + h264_video_tail + [output_path],
        common_prefix + ["-map", "0:v:0"] + mpeg4_video_tail + [output_path],
    ]


def remux_recording_with_ffmpeg(ffmpeg_path, input_path, output_path, timeout=RECORDING_REMUX_TIMEOUT_SECONDS):
    errors = []
    for command in build_recording_remux_commands(ffmpeg_path, input_path, output_path):
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        except Exception as exc:
            errors.append(str(exc))
            continue
        if completed.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True, errors
        err = (completed.stderr or completed.stdout or "ffmpeg failed").strip()
        errors.append(err[-800:])
        try:
            os.remove(output_path)
        except OSError:
            pass
    return False, errors


def build_turn_ice_servers():
    public_host = sanitize_host_port(os.environ.get("TURN_PUBLIC_HOST")) or sanitize_host_port(os.environ.get("PUBLIC_HOST")) or sanitize_host_port(request.host.split(":")[0]) or "localhost"
    urls_raw = (os.environ.get("TURN_URLS") or "").strip()
    username = (os.environ.get("TURN_USERNAME") or "").strip()
    credential = (os.environ.get("TURN_PASSWORD") or "").strip()
    if urls_raw and username and credential:
        urls = [item.strip() for item in urls_raw.split(",") if item.strip()]
    else:
        urls = []
    stun_urls_raw = (os.environ.get("STUN_URLS") or f"stun:{public_host}:3478").strip()
    stun_urls = [item.strip() for item in stun_urls_raw.split(",") if item.strip()]
    ice_servers = []
    if stun_urls:
        ice_servers.append({"urls": stun_urls})
    if urls:
        ice_servers.append({"urls": urls, "username": username, "credential": credential})
    elif urls_raw:
        app.logger.warning("TURN_URLS was set without TURN_USERNAME/TURN_PASSWORD; TURN relay entries were skipped")
    return ice_servers



def is_meeting_expired(meeting):
    if not meeting or not meeting.created_at:
        return False
    return datetime.utcnow() >= (meeting.created_at + timedelta(seconds=MEETING_DURATION_SECONDS))


def cancel_room_expiry(room_id):
    with runtime_state_lock:
        room = rooms.get(room_id)
        if not room:
            return
        timer = room.get("expiry_timer")
        room["expiry_timer"] = None
    if timer:
        timer.cancel()


def end_meeting_by_room_id(room_id, message_key=None):
    with app.app_context():
        meeting = Meeting.query.filter_by(room_id=room_id).first()
        if not meeting:
            cancel_room_expiry(room_id)
            shutil.rmtree(os.path.join(CHAT_UPLOAD_DIR, room_id), ignore_errors=True)
            with runtime_state_lock:
                rooms.pop(room_id, None)
            return
        if meeting.status != "ended":
            meeting.status = "ended"
            meeting.ended_at = datetime.utcnow()
            db.session.commit()

        cancel_room_cleanup(room_id)
        cancel_room_expiry(room_id)
        with runtime_state_lock:
            room = rooms.pop(room_id, None)
        if room:
            for participant_sid in list(room.get("participants", {}).keys()):
                participant = MeetingParticipant.query.filter_by(sid=participant_sid).order_by(MeetingParticipant.id.desc()).first()
                if participant and not participant.left_at:
                    participant.left_at = datetime.utcnow()
            db.session.commit()
            lang = room.get("lang", "zh")
            message = tf(lang, message_key) if message_key else tf(lang, "meeting_closed")
            socketio.emit("force_leave", {"message": message}, room=room_id)


def schedule_room_expiry(room_id, created_at_ts):
    cancel_room_expiry(room_id)
    remaining = max(0, int(created_at_ts + MEETING_DURATION_SECONDS - time.time()))
    timer = threading.Timer(remaining, end_meeting_by_room_id, args=(room_id, "expired_meeting"))
    timer.daemon = True
    with runtime_state_lock:
        room = rooms.get(room_id)
        if not room:
            return
        room["expiry_timer"] = timer
    timer.start()


def ensure_meeting_not_expired(meeting):
    if not meeting:
        return False
    if meeting.status == "ended":
        return False
    if is_meeting_expired(meeting):
        end_meeting_by_room_id(meeting.room_id, "expired_meeting")
        return False
    return True


def build_runtime_room_state(*, password, host_name, created_at_ts, meeting_id, host_user_id, lang):
    return {
        "password": password,
        "host_name": host_name,
        "participants": {},
        "created_at": created_at_ts,
        "meeting_db_id": meeting_id,
        "host_user_id": host_user_id,
        "host_present": False,
        "cleanup_timer": None,
        "empty_since": None,
        "expiry_timer": None,
        "lang": lang,
        "danmaku_enabled": True,
        "active_sharer_sid": None,
        "active_sharer_user_id": None,
        "chat_history": [],
        "chat_clear_markers": {},
    }


def init_runtime_room(room_id, room_state, created_at_ts):
    with runtime_state_lock:
        rooms[room_id] = room_state
    schedule_room_expiry(room_id, created_at_ts)
    return room_state


def ensure_runtime_room(meeting):
    with runtime_state_lock:
        room = rooms.get(meeting.room_id)
        if room:
            return room
    created_at_ts = meeting.created_at.timestamp()
    room_state = build_runtime_room_state(
        password=meeting.room_password,
        host_name=meeting.host_name,
        created_at_ts=created_at_ts,
        meeting_id=meeting.id,
        host_user_id=meeting.host_user_id,
        lang=session.get("lang", "zh"),
    )
    return init_runtime_room(meeting.room_id, room_state, created_at_ts)


def build_history_meetings_for_user(user_id):
    host_meetings = Meeting.query.filter_by(host_user_id=user_id).all()
    participant_rows = (
        db.session.query(MeetingParticipant.meeting_id)
        .filter(MeetingParticipant.user_id == user_id)
        .distinct()
        .all()
    )
    participant_ids = [row[0] for row in participant_rows]
    participant_meetings = Meeting.query.filter(Meeting.id.in_(participant_ids)).all() if participant_ids else []

    merged = {}
    for meeting in host_meetings:
        merged[meeting.id] = {
            "meeting": meeting,
            "relation": "created",
        }
    for meeting in participant_meetings:
        if meeting.id in merged:
            continue
        merged[meeting.id] = {
            "meeting": meeting,
            "relation": "joined",
        }

    items = []
    for item in merged.values():
        meeting = item["meeting"]
        is_active = ensure_meeting_not_expired(meeting)
        items.append({
            "id": meeting.id,
            "room_id": meeting.room_id,
            "room_password": meeting.room_password,
            "host_name": meeting.host_name,
            "created_at": meeting.created_at,
            "ended_at": meeting.ended_at,
            "status": "active" if is_active else "ended",
            "relation": item["relation"],
            "can_rejoin": is_active,
        })
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return items



def cancel_room_cleanup(room_id):
    with runtime_state_lock:
        room = rooms.get(room_id)
        if not room:
            return
        timer = room.get("cleanup_timer")
        room["cleanup_timer"] = None
        room["empty_since"] = None
    if timer:
        timer.cancel()


def finalize_room_if_still_empty(room_id):
    with app.app_context():
        with runtime_state_lock:
            room = rooms.get(room_id)
            if not room:
                return
            if room.get("participants"):
                room["cleanup_timer"] = None
                room["empty_since"] = None
                return
            meeting_db_id = room.get("meeting_db_id")

        meeting = Meeting.query.get(meeting_db_id)
        if meeting and meeting.status != "ended":
            meeting.status = "ended"
            meeting.ended_at = datetime.utcnow()
            db.session.commit()

        shutil.rmtree(os.path.join(CHAT_UPLOAD_DIR, room_id), ignore_errors=True)
        with runtime_state_lock:
            rooms.pop(room_id, None)


def schedule_room_cleanup(room_id, delay=ROOM_EMPTY_GRACE_SECONDS):
    cancel_room_cleanup(room_id)
    timer = threading.Timer(delay, finalize_room_if_still_empty, args=(room_id,))
    timer.daemon = True
    with runtime_state_lock:
        room = rooms.get(room_id)
        if not room:
            return
        room["empty_since"] = time.time()
        room["cleanup_timer"] = timer
    timer.start()

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("login"))
        if not current_user.is_admin:
            abort(403)
        return func(*args, **kwargs)

    return wrapper


def disconnect_user_sockets(user_id, exclude_sid=None, message=None):
    if not user_id:
        debug_log('SOCKET_KICK_SKIP', reason='empty_user_id', exclude_sid=exclude_sid)
        return
    with runtime_state_lock:
        active_sids = list(user_active_sids.get(user_id, set()))
    debug_log('SOCKET_KICK_BEGIN', user_id=user_id, exclude_sid=exclude_sid, active_sids=active_sids, message=message or t('kicked'))
    for sid in active_sids:
        if exclude_sid and sid == exclude_sid:
            debug_log('SOCKET_KICK_SKIP_SID', user_id=user_id, sid=sid, reason='exclude_sid')
            continue
        try:
            socketio.emit("force_logout", {"message": message or t("kicked")}, to=sid)
            debug_log('SOCKET_KICK_EMIT', user_id=user_id, sid=sid)
        except Exception as exc:
            debug_log('SOCKET_KICK_EMIT_ERROR', user_id=user_id, sid=sid, error=str(exc))
        try:
            socketio.server.disconnect(sid, namespace='/')
            debug_log('SOCKET_KICK_DISCONNECT', user_id=user_id, sid=sid)
        except Exception as exc:
            debug_log('SOCKET_KICK_DISCONNECT_ERROR', user_id=user_id, sid=sid, error=str(exc))
    if not active_sids:
        debug_log('SOCKET_KICK_EMPTY', user_id=user_id)


def remove_user_from_runtime_rooms(user_id, reason_message=None):
    if not user_id:
        debug_log('RUNTIME_REMOVE_SKIP', reason='empty_user_id')
        return
    with runtime_state_lock:
        room_ids_snapshot = list(rooms.keys())
    debug_log('RUNTIME_REMOVE_BEGIN', user_id=user_id, room_ids=room_ids_snapshot, reason_message=reason_message)
    found_any = False
    with runtime_state_lock:
        room_entries = list(rooms.items())
    for room_id, room in room_entries:
        participant_sids = [sid for sid, info in list(room.get("participants", {}).items()) if info.get("user_id") == user_id]
        if not participant_sids:
            continue
        found_any = True
        debug_log('RUNTIME_REMOVE_ROOM_MATCH', user_id=user_id, room_id=room_id, participant_sids=participant_sids, participant_count_before=len(room.get('participants', {})))
        for sid in participant_sids:
            with runtime_state_lock:
                participant_info = room.get("participants", {}).pop(sid, None)
            debug_log('RUNTIME_REMOVE_POP', user_id=user_id, room_id=room_id, sid=sid, participant_info=participant_info)
            with runtime_state_lock:
                if sid_to_user.get(sid):
                    sid_to_user.pop(sid, None)
                    debug_log('RUNTIME_REMOVE_SID_UNMAP', user_id=user_id, room_id=room_id, sid=sid)
            unbind_user_socket(user_id, sid)
            try:
                socketio.server.leave_room(sid, room_id, namespace='/')
                debug_log('RUNTIME_REMOVE_LEAVE_ROOM', user_id=user_id, room_id=room_id, sid=sid)
            except Exception as exc:
                debug_log('RUNTIME_REMOVE_LEAVE_ROOM_ERROR', user_id=user_id, room_id=room_id, sid=sid, error=str(exc))
            participant = mark_meeting_participant_left(sid)
            if participant:
                debug_log('RUNTIME_REMOVE_PARTICIPANT_MARK_LEFT', user_id=user_id, room_id=room_id, sid=sid, participant_db_id=participant.id)
            if participant_info:
                with runtime_state_lock:
                    participant_count_after = len(room.get("participants", {}))
                emit_participant_left(room_id, sid, participant_info, participant_count_after)
                broadcast_room_participant_snapshot(room_id)
                debug_log('RUNTIME_REMOVE_BROADCAST', user_id=user_id, room_id=room_id, sid=sid, participant_count_after=participant_count_after)
        with runtime_state_lock:
            host_present = bool(user_id == room.get("host_user_id") and room.get("host_present"))
            if host_present:
                room["host_present"] = False
            room_empty = not room.get("participants")
        if host_present:
            emit_host_presence_changed(room_id, False, reason_message or t("host_left_room"))
            debug_log('RUNTIME_REMOVE_HOST_LEFT', user_id=user_id, room_id=room_id)
        if room_empty:
            schedule_room_cleanup(room_id)
            debug_log('RUNTIME_REMOVE_SCHEDULE_CLEANUP', user_id=user_id, room_id=room_id)
    if not found_any:
        debug_log('RUNTIME_REMOVE_NOT_FOUND', user_id=user_id, room_ids=room_ids_snapshot)
    db.session.commit()
    debug_log('RUNTIME_REMOVE_DONE', user_id=user_id, active_socket_count=runtime_state_snapshot()["active_socket_count"], online_user_count=online_user_count())




def broadcast_room_participant_snapshot(room_id):
    with runtime_state_lock:
        room = rooms.get(room_id)
        if not room:
            return
        host_user_id = room.get("host_user_id")
        payload = {
            "participants": [
                build_room_participant_payload(sid, info, host_user_id)
                for sid, info in room.get("participants", {}).items()
            ],
            "participant_count": len(room.get("participants", {})),
            **build_active_sharer_payload(room),
        }
    socketio.emit("participant_snapshot", payload, room=room_id)


def online_user_count():
    with runtime_state_lock:
        return sum(1 for _, sids in user_active_sids.items() if sids)


def bind_user_socket(user_id, sid):
    if not user_id or not sid:
        return
    with runtime_state_lock:
        user_active_sids.setdefault(user_id, set()).add(sid)


def unbind_user_socket(user_id, sid):
    if not user_id or not sid:
        return
    with runtime_state_lock:
        active_sids = user_active_sids.get(user_id)
        if not active_sids:
            return
        active_sids.discard(sid)
        if not active_sids:
            user_active_sids.pop(user_id, None)


@app.before_request
def ensure_default_lang():
    session.setdefault("lang", "zh")


@app.before_request
def enforce_security_lockdown():
    if not security_lockdown_active():
        return
    if request.path.startswith("/static/"):
        return
    if request.path.startswith("/admin/security/lockdown/"):
        return
    if request.path.startswith("/admin/security/unlock"):
        return
    if request.path == "/api/healthz":
        return
    if getattr(current_user, "is_authenticated", False):
        logout_user()
        session.clear()
    reason = SECURITY_LOCKDOWN_STATE.get("reason") or "security lockdown"
    activated_at = SECURITY_LOCKDOWN_STATE.get("activated_at") or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"<h1>503 Security Lockdown</h1><p>Activated at UTC {activated_at}.</p><p>Reason: {reason}</p>"
        "<p>Open /admin/security/unlock and enter the recovery code to restore service.</p>",
        503,
        {"Content-Type": "text/html; charset=utf-8"},
    )


@app.before_request
def enforce_single_session():
    if not current_user.is_authenticated:
        return
    fresh_user = db.session.get(User, current_user.id)
    if not fresh_user:
        logout_user()
        session.clear()
        return redirect(url_for("login"))
    if not fresh_user.is_active_user:
        logout_user()
        session.clear()
        return redirect(url_for("login", kicked=1))
    if session.get("session_version") != fresh_user.session_version:
        logout_user()
        session.clear()
        return redirect(url_for("login", kicked=1))


@app.route("/set-language/<lang>")
def set_language(lang):
    if lang in TRANSLATIONS:
        session["lang"] = lang
    return redirect(request.referrer or url_for("index"))


@app.route("/")
def index():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    db.session.refresh(current_user)
    return render_template("pages/index.html", preferred_display_name=preferred_display_name(current_user))


@app.route("/account", methods=["GET", "POST"])
@login_required
def account_page():
    message = None
    error = None
    if request.method == "POST":
        action = (request.form.get("action") or "profile").strip()
        fresh_user = db.session.get(User, current_user.id)
        if action == "profile":
            username = (request.form.get("username") or "").strip()[:32]
            display_name = (request.form.get("display_name") or "").strip()[:32]
            region = (request.form.get("region") or "Asia/Tokyo").strip()[:64]
            preferred_locale = (request.form.get("preferred_locale") or "auto").strip()[:16].lower()
            default_attachment_permission = (request.form.get("default_attachment_permission") or "download").strip()[:16].lower()
            default_danmaku_enabled = bool_from_form(request.form.get("default_danmaku_enabled"), True)
            auto_enable_camera = bool_from_form(request.form.get("auto_enable_camera"), True)
            auto_enable_microphone = bool_from_form(request.form.get("auto_enable_microphone"), True)
            auto_enable_speaker = bool_from_form(request.form.get("auto_enable_speaker"), True)
            if preferred_locale not in {"auto", "zh", "en"}:
                preferred_locale = "auto"
            if region not in REGION_TIMEZONE_OPTIONS:
                region = "Asia/Tokyo"
            if default_attachment_permission not in {"view", "download"}:
                default_attachment_permission = "download"
            if not username:
                error = t("username_password_required")
            else:
                existing = User.query.filter(User.username == username, User.id != fresh_user.id).first()
                if existing:
                    error = t("username_exists")
                else:
                    fresh_user.username = username
                    fresh_user.display_name = display_name or username
                    fresh_user.region = region or "Asia/Tokyo"
                    fresh_user.preferred_locale = preferred_locale
                    fresh_user.default_attachment_permission = default_attachment_permission
                    fresh_user.default_danmaku_enabled = default_danmaku_enabled
                    fresh_user.auto_enable_camera = auto_enable_camera
                    fresh_user.auto_enable_microphone = auto_enable_microphone
                    fresh_user.auto_enable_speaker = auto_enable_speaker
                    db.session.commit()
                    message = t("profile_saved")
        elif action == "password":
            current_password = (request.form.get("current_password") or "").strip()
            new_password = (request.form.get("new_password") or "").strip()
            if not fresh_user.check_password(current_password):
                error = t("invalid_login")
            elif not new_password:
                error = t("username_password_required")
            else:
                fresh_user.set_password(new_password)
                fresh_user.session_version = (fresh_user.session_version or 0) + 1
                db.session.commit()
                session["session_version"] = fresh_user.session_version
                disconnect_user_sockets(fresh_user.id, message=t("kicked"))
                message = t("password_updated")
    fresh_user = db.session.get(User, current_user.id)
    current_region = fresh_user.region or "Asia/Tokyo"
    current_lang = session.get("lang", "zh")
    return render_template(
        "pages/account.html",
        user=fresh_user,
        message=message,
        error=error,
        preferred_display_name=preferred_display_name(fresh_user),
        region=current_region,
        region_timezone_options=localized_timezone_options(current_lang),
        region_timezone_label=localized_timezone_label(current_region, current_lang),
        preferred_locale=(fresh_user.preferred_locale or "auto"),
        default_attachment_permission=(fresh_user.default_attachment_permission or "download"),
        default_danmaku_enabled=bool(getattr(fresh_user, "default_danmaku_enabled", True)),
        auto_enable_camera=bool(getattr(fresh_user, "auto_enable_camera", True)),
        auto_enable_microphone=bool(getattr(fresh_user, "auto_enable_microphone", True)),
        auto_enable_speaker=bool(getattr(fresh_user, "auto_enable_speaker", True)),
    )


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password_page():
    message = None
    error = None
    email_code_scope = None
    if request.method == "POST":
        retry_after = _consume_request_budget(
            "forgot_password_ip",
            _client_address(),
            PASSWORD_RESET_RATE_LIMIT_PER_IP,
            PASSWORD_RESET_RATE_LIMIT_WINDOW_SECONDS,
        )
        if retry_after is not None:
            response, status_code, headers = _too_many_attempts_response("forgot_password.html")
            headers["Retry-After"] = str(retry_after)
            return response, status_code, headers
        intent = (request.form.get("intent") or "submit").strip()
        identifier = (request.form.get("identifier") or "").strip()[:255]
        email_code = (request.form.get("email_code") or "").strip()
        new_password = (request.form.get("new_password") or "").strip()
        if not identifier:
            error = t("login_identifier_required") if email_auth_active() else t("username_password_required")
        else:
            user = find_user_by_identifier(identifier)
            email_code_scope = user.email if user and user.email and user.email_verified else (
                normalize_email(identifier) if looks_like_email(identifier) else None
            )
            if email_auth_active() and email_delivery_configured():
                if intent == "send_code":
                    if user and user.email and user.email_verified:
                        retry_after = consume_email_code_send_budget(purpose="password_reset", scope=user.email)
                        if retry_after is not None:
                            error = build_email_code_limit_error()
                        else:
                            try:
                                send_email_verification_code(email=user.email, purpose="password_reset", user=user)
                            except Exception:
                                app.logger.exception("Failed to send password reset code for user_id=%s", user.id)
                                error = t("password_reset_email_send_failed")
                            else:
                                message = build_email_code_sent_message(purpose="password_reset", scope=user.email)
                    else:
                        error = t("password_reset_email_unavailable")
                else:
                    if user and user.email and user.email_verified:
                        turnstile_ok, turnstile_error = verify_turnstile_response(request.form.get("cf-turnstile-response"))
                        if not turnstile_ok:
                            return render_email_code_template(
                                "forgot_password.html",
                                purpose="password_reset",
                                scope=email_code_scope,
                                message=message,
                                error=turnstile_error,
                            ), 403
                        elif not re.fullmatch(r"\d{6}", email_code):
                            error = t("verification_code_required")
                        elif not new_password:
                            error = t("new_password_required")
                        else:
                            code = find_email_verification_code(
                                email=user.email,
                                purpose="password_reset",
                                raw_code=email_code,
                                user_id=user.id,
                            )
                            if not code:
                                error = t("verification_code_invalid")
                            else:
                                user.set_password(new_password)
                                user.session_version = (user.session_version or 0) + 1
                                code.used_at = datetime.utcnow()
                                db.session.commit()
                                disconnect_user_sockets(user.id, message=t("kicked"))
                                logout_user()
                                session.clear()
                                return redirect(url_for("login", reset="1"))
                    else:
                        error = t("password_reset_email_unavailable")
            else:
                error = t("password_reset_email_unavailable")
    return render_email_code_template(
        "forgot_password.html",
        purpose="password_reset",
        scope=email_code_scope,
        message=message,
        error=error,
    )


@app.route("/forgot-password-support", methods=["GET", "POST"])
def forgot_password_support_page():
    message = None
    error = None
    if request.method == "POST":
        retry_after = _consume_request_budget(
            "forgot_password_ip",
            _client_address(),
            PASSWORD_RESET_RATE_LIMIT_PER_IP,
            PASSWORD_RESET_RATE_LIMIT_WINDOW_SECONDS,
        )
        if retry_after is not None:
            response, status_code, headers = _too_many_attempts_response("forgot_password_support.html")
            headers["Retry-After"] = str(retry_after)
            return response, status_code, headers
        turnstile_ok, turnstile_error = verify_turnstile_response(request.form.get("cf-turnstile-response"))
        if not turnstile_ok:
            return render_template("pages/forgot_password_support.html", message=message, error=turnstile_error), 403
        identifier = (request.form.get("identifier") or "").strip()[:255]
        contact = (request.form.get("contact") or "").strip()[:128]
        note = (request.form.get("note") or "").strip()[:500]
        if not identifier:
            error = t("login_identifier_required") if email_auth_active() else t("username_password_required")
        else:
            create_password_reset_request(identifier, contact, note)
            message = t("password_reset_request_submitted")
    return render_template("pages/forgot_password_support.html", message=message, error=error)


@app.route("/help")
def help_page():
    return render_template("pages/help.html")


@app.route("/quickstart")
def quickstart_page():
    return render_template("pages/quickstart.html")


@app.route("/support")
def support_page():
    return render_template("pages/support.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if not PUBLIC_REGISTRATION_ENABLED:
        return render_email_code_template("register.html", purpose="register", error=t("registration_disabled")), 403
    if request.method == "GET":
        return render_email_code_template("register.html", purpose="register")

    retry_after = _consume_request_budget(
        "register_ip",
        _client_address(),
        REGISTER_RATE_LIMIT_PER_IP,
        REGISTER_RATE_LIMIT_WINDOW_SECONDS,
    )
    if retry_after is not None:
        response, status_code, headers = _too_many_attempts_response("register.html")
        headers["Retry-After"] = str(retry_after)
        return response, status_code, headers

    intent = (request.form.get("intent") or "register").strip()
    username = (request.form.get("username") or "").strip()
    email = normalize_email(request.form.get("email"))
    password = (request.form.get("password") or "").strip()
    email_code = (request.form.get("email_code") or "").strip()

    if email_auth_active() and not email_delivery_configured():
        return render_email_code_template("register.html", purpose="register", scope=email, error=t("email_delivery_not_configured")), 503
    if intent == "send_code" and email_auth_active():
        if not looks_like_email(email):
            return render_email_code_template("register.html", purpose="register", scope=email, error=t("invalid_email"))
        if User.query.filter(func.lower(User.email) == email).first():
            return render_email_code_template("register.html", purpose="register", scope=email, error=t("email_exists"))
        retry_after = consume_email_code_send_budget(purpose="register", scope=email)
        if retry_after is not None:
            return render_email_code_template(
                "register.html",
                purpose="register",
                scope=email,
                error=build_email_code_limit_error(),
            )
        try:
            send_email_verification_code(email=email, purpose="register")
        except Exception:
            app.logger.exception("Failed to send register verification code to %s", email)
            return render_email_code_template("register.html", purpose="register", scope=email, error=t("verification_email_send_failed")), 502
        return render_email_code_template(
            "register.html",
            purpose="register",
            scope=email,
            message=build_email_code_sent_message(purpose="register", scope=email),
        )
    if email_auth_active():
        if not looks_like_email(email):
            return render_email_code_template("register.html", purpose="register", scope=email, error=t("invalid_email"))
        if User.query.filter(func.lower(User.email) == email).first():
            return render_email_code_template("register.html", purpose="register", scope=email, error=t("email_exists"))

    if not username or not password or (email_auth_active() and (not email or not email_code)):
        return render_email_code_template(
            "register.html",
            purpose="register",
            scope=email,
            error=t("register_fields_required") if email_auth_active() else t("username_password_required"),
        )
    if User.query.filter_by(username=username).first():
        return render_email_code_template("register.html", purpose="register", scope=email, error=t("username_exists"))

    user = User(
        username=username,
        email=email or None,
        email_verified=not email_auth_active(),
        email_verified_at=datetime.utcnow() if not email_auth_active() else None,
        display_name=username,
        is_active_user=True,
        session_version=0,
    )

    if email_auth_active():
        turnstile_ok, turnstile_error = verify_turnstile_response(request.form.get("cf-turnstile-response"))
        if not turnstile_ok:
            return render_email_code_template("register.html", purpose="register", scope=email, error=turnstile_error), 403
        if not re.fullmatch(r"\d{6}", email_code):
            return render_email_code_template("register.html", purpose="register", scope=email, error=t("verification_code_required"))
        code = find_email_verification_code(email=email, purpose="register", raw_code=email_code)
        if not code:
            return render_email_code_template("register.html", purpose="register", scope=email, error=t("verification_code_invalid"))
        code.used_at = datetime.utcnow()
        mark_user_email_verified(user)

    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    notify_admin_user_registered(user)
    finalize_authenticated_session(user)
    return redirect(url_for("index"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("pages/login.html")

    identifier = (request.form.get("identifier") or "").strip()
    retry_after_ip = _consume_request_budget(
        "login_ip",
        _client_address(),
        LOGIN_RATE_LIMIT_PER_IP,
        LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    )
    retry_after_user = _consume_request_budget(
        "login_user",
        identifier or "<empty>",
        LOGIN_RATE_LIMIT_PER_USER,
        LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    )
    retry_after = retry_after_ip if retry_after_ip is not None else retry_after_user
    if retry_after is not None:
        response, status_code, headers = _too_many_attempts_response("login.html")
        headers["Retry-After"] = str(retry_after)
        return response, status_code, headers

    password = (request.form.get("password") or "").strip()
    turnstile_ok, turnstile_error = verify_turnstile_response(request.form.get("cf-turnstile-response"))
    if not turnstile_ok:
        return render_template("pages/login.html", error=turnstile_error), 403

    user = find_user_by_identifier(identifier)
    if not user:
        validation_error = validate_login_target_user(user, identifier=identifier)
        return render_template("pages/login.html", error=validation_error)
    if not user.check_password(password):
        return render_template("pages/login.html", error=t("invalid_login"))
    if user.is_admin:
        snap = _request_snapshot()
        send_admin_security_alert(
            subject="Admin credentials were used on the public login page",
            fields={
                "Identifier": identifier,
                "IP": snap["ip"],
                "Path": snap["path"],
                "User-Agent": snap["user_agent"],
            },
            cooldown_key=f"public-login-admin:{identifier}:{snap['ip']}",
            cooldown_seconds=300,
        )
        return render_template("pages/login.html", error=t("invalid_login"))
    validation_error = validate_login_target_user(user, identifier=identifier)
    if validation_error:
        return render_template("pages/login.html", error=validation_error)

    finalize_authenticated_session(user)
    return redirect(url_for("index"))



@app.route(ADMIN_LOGIN_PATH, methods=["GET", "POST"], endpoint="admin_login")
def admin_login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for("index"))
    if request.method == "GET":
        return render_template("pages/admin_login.html", admin_login_path=ADMIN_LOGIN_PATH)

    identifier = (request.form.get("identifier") or "").strip()
    retry_after_ip = _consume_request_budget("admin_login_ip", _client_address(), LOGIN_RATE_LIMIT_PER_IP, LOGIN_RATE_LIMIT_WINDOW_SECONDS)
    retry_after_user = _consume_request_budget("admin_login_user", identifier or "<empty>", LOGIN_RATE_LIMIT_PER_USER, LOGIN_RATE_LIMIT_WINDOW_SECONDS)
    retry_after = retry_after_ip if retry_after_ip is not None else retry_after_user
    if retry_after is not None:
        response, status_code, headers = _too_many_attempts_response("admin_login.html")
        headers["Retry-After"] = str(retry_after)
        return response, status_code, headers

    password = (request.form.get("password") or "").strip()
    turnstile_ok, turnstile_error = verify_turnstile_response(request.form.get("cf-turnstile-response"))
    if not turnstile_ok:
        return render_template("pages/admin_login.html", error=turnstile_error, admin_login_path=ADMIN_LOGIN_PATH), 403

    user = find_admin_by_identifier(identifier)
    if not user or not user.check_password(password):
        return render_template("pages/admin_login.html", error=t("invalid_admin_login"), admin_login_path=ADMIN_LOGIN_PATH)
    validation_error = validate_login_target_user(user, require_admin=True)
    if validation_error:
        return render_template("pages/admin_login.html", error=validation_error, admin_login_path=ADMIN_LOGIN_PATH)

    finalize_authenticated_session(user)
    snap = _request_snapshot()
    send_admin_security_alert(
        subject="Admin login succeeded",
        fields={
            "Admin username": user.username,
            "Admin email": user.email or ADMIN_EMAIL or "not set",
            "IP": snap["ip"],
            "Path": snap["path"],
            "User-Agent": snap["user_agent"],
        },
        cooldown_key=f"admin-login-success:{user.id}:{snap['ip']}",
        cooldown_seconds=30,
    )
    return redirect(url_for("index"))

@app.route("/login-email-code", methods=["GET", "POST"])
def login_email_code():
    message = None
    error = None
    if request.method == "GET":
        return render_email_code_template("login_email_code.html", purpose="login")

    intent = (request.form.get("intent") or "email_code").strip()
    email = normalize_email(request.form.get("email"))
    retry_after_ip = _consume_request_budget(
        "login_ip",
        _client_address(),
        LOGIN_RATE_LIMIT_PER_IP,
        LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    )
    retry_after_user = _consume_request_budget(
        "login_user",
        email or "<empty>",
        LOGIN_RATE_LIMIT_PER_USER,
        LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    )
    retry_after = retry_after_ip if retry_after_ip is not None else retry_after_user
    if retry_after is not None:
        response, status_code, headers = _too_many_attempts_response("login_email_code.html")
        headers["Retry-After"] = str(retry_after)
        return response, status_code, headers
    if not looks_like_email(email):
        return render_email_code_template("login_email_code.html", purpose="login", scope=email, error=t("invalid_email"))

    user = User.query.filter(func.lower(User.email) == email).first()
    if intent == "send_login_code":
        if not user or not user.email:
            return render_email_code_template("login_email_code.html", purpose="login", scope=email, error=t("email_not_registered"))
        if user.is_admin:
            snap = _request_snapshot()
            send_admin_security_alert(
                subject="Admin email was targeted from the public email-code login",
                fields={
                    "Email": email,
                    "IP": snap["ip"],
                    "Path": snap["path"],
                    "User-Agent": snap["user_agent"],
                },
                cooldown_key=f"public-email-admin:{email}:{snap['ip']}",
                cooldown_seconds=300,
            )
            message = build_email_code_sent_message(purpose="login", scope=email)
            return render_email_code_template("login_email_code.html", purpose="login", scope=email, message=message)
        if not user.is_active_user:
            return render_email_code_template("login_email_code.html", purpose="login", scope=email, error=t("account_disabled"))
        retry_after = consume_email_code_send_budget(purpose="login", scope=user.email)
        if retry_after is not None:
            return render_email_code_template(
                "login_email_code.html",
                purpose="login",
                scope=email,
                error=build_email_code_limit_error(),
            )
        try:
            send_email_verification_code(email=user.email, purpose="login", user=user)
        except Exception:
            app.logger.exception("Failed to send login code to %s", email)
            return render_email_code_template("login_email_code.html", purpose="login", scope=email, error=t("verification_email_send_failed")), 502
        message = build_email_code_sent_message(purpose="login", scope=user.email)
        return render_email_code_template("login_email_code.html", purpose="login", scope=email, message=message)

    email_code = (request.form.get("email_code") or "").strip()
    turnstile_ok, turnstile_error = verify_turnstile_response(request.form.get("cf-turnstile-response"))
    if not turnstile_ok:
        return render_email_code_template("login_email_code.html", purpose="login", scope=email, error=turnstile_error), 403
    if not re.fullmatch(r"\d{6}", email_code):
        return render_email_code_template("login_email_code.html", purpose="login", scope=email, error=t("verification_code_required"))
    if user and user.is_admin:
        return render_email_code_template("login_email_code.html", purpose="login", scope=email, error=t("verification_code_invalid"))
    validation_error = validate_login_target_user(user, identifier=email)
    if validation_error or not user or not user.email:
        return render_email_code_template("login_email_code.html", purpose="login", scope=email, error=validation_error or t("email_not_registered"))
    code = find_email_verification_code(email=user.email, purpose="login", raw_code=email_code, user_id=user.id)
    if not code:
        return render_email_code_template("login_email_code.html", purpose="login", scope=email, error=t("verification_code_invalid"))
    code.used_at = datetime.utcnow()
    mark_user_email_verified(user)
    finalize_authenticated_session(user)
    return redirect(url_for("index"))


@app.get("/logout")
@login_required
def logout():
    disconnect_user_sockets(current_user.id, message=t("kicked"))
    logout_user()
    session.clear()
    return redirect(url_for("login"))


@app.post("/api/create_room")
@login_required
def api_create_room():
    db.session.refresh(current_user)
    data = request.get_json(silent=True) or {}
    host_name = (data.get("host_name") or current_user.username).strip()[:32] or current_user.username
    room_id = generate_room_id()
    password = generate_password()

    meeting = Meeting(
        room_id=room_id,
        room_password=password,
        host_user_id=current_user.id,
        host_name=host_name,
        status="active",
    )
    db.session.add(meeting)
    db.session.commit()

    created_at_ts = meeting.created_at.timestamp()
    room_state = build_runtime_room_state(
        password=password,
        host_name=host_name,
        created_at_ts=created_at_ts,
        meeting_id=meeting.id,
        host_user_id=meeting.host_user_id,
        lang=session.get("lang", "zh"),
    )
    init_runtime_room(room_id, room_state, created_at_ts)

    join_url = f"{get_base_url()}/room/{room_id}?pwd={password}"
    return jsonify({"success": True, "room_id": room_id, "password": password, "join_url": join_url})


@app.post("/api/join_room")
@login_required
def api_join_room():
    db.session.refresh(current_user)
    data = request.get_json(silent=True) or {}
    room_id = (data.get("room_id") or "").strip()
    password = normalize_password(data.get("password") or "")
    if not is_valid_room_id(room_id):
        return jsonify({"success": False, "message": t("meeting_not_found")}), 404

    meeting = Meeting.query.filter_by(room_id=room_id).first()
    if not ensure_meeting_not_expired(meeting):
        return jsonify({"success": False, "message": t("meeting_not_found")}), 404
    if normalize_password(meeting.room_password) != password:
        return jsonify({"success": False, "message": t("wrong_password")}), 403

    ensure_runtime_room(meeting)
    return jsonify({"success": True, "message": "ok"})


@app.get("/room/<room_id>")
@login_required
def room_page(room_id):
    if not livekit_enabled():
        return render_template(
            "pages/404.html",
            error_title="503",
            error_message="LiveKit is not configured. Set LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET.",
        ), 503
    if not is_valid_room_id(room_id):
        abort(404)
    meeting = Meeting.query.filter_by(room_id=room_id).first()
    if not ensure_meeting_not_expired(meeting):
        abort(404)
    room_password = request.args.get("pwd", meeting.room_password)
    invite_url = f"{get_base_url()}{url_for('room_page', room_id=room_id)}?pwd={quote(room_password)}"
    is_host = current_user.is_authenticated and current_user.id == meeting.host_user_id
    rtc_mode = get_rtc_mode()
    db.session.refresh(current_user)
    return render_template(
        "pages/room.html",
        room_id=room_id,
        room_password=room_password,
        invite_url=invite_url,
        is_host=is_host,
        turn_ice_servers=build_turn_ice_servers(),
        rtc_mode=rtc_mode,
        livekit_enabled=livekit_enabled(),
        livekit_url=livekit_server_url(),
        livekit_token_endpoint=url_for("api_livekit_token"),
        preferred_display_name=preferred_display_name(current_user),
        default_danmaku_enabled=bool(getattr(current_user, "default_danmaku_enabled", True)),
        auto_enable_camera=bool(getattr(current_user, "auto_enable_camera", True)),
        auto_enable_microphone=bool(getattr(current_user, "auto_enable_microphone", True)),
        auto_enable_speaker=bool(getattr(current_user, "auto_enable_speaker", True)),
    )


@app.post("/api/livekit/token")
@login_required
def api_livekit_token():
    if get_rtc_mode() != "livekit" or not livekit_enabled():
        return jsonify({"success": False, "message": "LiveKit is not configured"}), 503

    payload = request.get_json(silent=True) or {}
    room_id = (payload.get("room_id") or "").strip()
    participant_sid = (payload.get("participant_sid") or "").strip()
    display_name = (payload.get("name") or preferred_display_name(current_user)).strip()[:32] or preferred_display_name(current_user)
    password = normalize_password(payload.get("password"))

    if not room_id or not participant_sid:
        return jsonify({"success": False, "message": "room_id and participant_sid are required"}), 400
    if not is_valid_room_id(room_id):
        return jsonify({"success": False, "message": t("meeting_not_found")}), 404

    meeting = Meeting.query.filter_by(room_id=room_id).first()
    if not ensure_meeting_not_expired(meeting):
        return jsonify({"success": False, "message": t("meeting_not_found")}), 404
    if normalize_password(meeting.room_password) != password:
        return jsonify({"success": False, "message": t("wrong_password")}), 403

    with runtime_state_lock:
        socket_info = sid_to_user.get(participant_sid)
    if not socket_info or socket_info.get("room_id") != room_id or socket_info.get("user_id") != current_user.id:
        return jsonify({"success": False, "message": "Invalid participant session"}), 403

    is_host = current_user.id == meeting.host_user_id
    metadata = json.dumps(
        {
            "user_id": current_user.id,
            "room_id": room_id,
            "socket_sid": participant_sid,
            "is_host": is_host,
        },
        ensure_ascii=True,
    )
    token = (
        livekit_api.AccessToken(livekit_api_key(), livekit_api_secret())
        .with_identity(participant_sid)
        .with_name(display_name)
        .with_metadata(metadata)
        .with_grants(
            livekit_api.VideoGrants(
                room_join=True,
                room=build_livekit_room_name(room_id),
                room_admin=is_host,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
                can_update_own_metadata=True,
            )
        )
        .to_jwt()
    )
    return jsonify(
        {
            "success": True,
            "rtc_mode": "livekit",
            "url": livekit_server_url(),
            "room_name": build_livekit_room_name(room_id),
            "identity": participant_sid,
            "token": token,
        }
    )


@app.get("/history")
@login_required
def history():
    meetings = build_history_meetings_for_user(current_user.id)
    return render_template("pages/history.html", meetings=meetings)


@app.post("/api/remux-recording")
@login_required
def api_remux_recording():
    upload = request.files.get("recording")
    if not upload or not upload.filename:
        return jsonify({"success": False, "message": "No recording uploaded"}), 400

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        return jsonify({"success": False, "message": "ffmpeg not installed on server"}), 501

    workdir = tempfile.mkdtemp(prefix="meeting-remux-")
    input_ext = Path(upload.filename).suffix.lower() or ".webm"
    input_path = os.path.join(workdir, f"input{input_ext}")
    output_path = os.path.join(workdir, "output.mp4")
    upload.save(input_path)

    success, errors = remux_recording_with_ffmpeg(ffmpeg_path, input_path, output_path)
    if not success:
        shutil.rmtree(workdir, ignore_errors=True)
        app.logger.warning("recording remux failed: %s", " | ".join(errors[-3:]) or "ffmpeg failed")
        return jsonify({"success": False, "message": "ffmpeg failed"}), 500

    data = Path(output_path).read_bytes()

    @after_this_request
    def cleanup(response):
        shutil.rmtree(workdir, ignore_errors=True)
        return response

    return send_file(
        io.BytesIO(data),
        mimetype="video/mp4",
        as_attachment=True,
        download_name=f"meeting-recording-{int(time.time() * 1000)}.mp4",
    )


@app.get("/api/admin/system_stats")
@login_required
@admin_required
def api_admin_system_stats():
    payload = {"success": True, **get_system_metrics()}
    snapshot = runtime_state_snapshot()
    debug_log('ADMIN_STATS_API', payload=payload, room_participant_counts=snapshot["room_participant_counts"], user_sid_counts=snapshot["user_sid_counts"])
    return jsonify(payload)


@app.get("/api/healthz")
def api_healthz():
    snapshot = runtime_state_snapshot()
    return jsonify({
        "success": True,
        "status": "ok",
        "rtc_mode": get_rtc_mode(),
        "livekit_enabled": livekit_enabled(),
        "security_lockdown_active": security_lockdown_active(),
        "security_lockdown_reason": SECURITY_LOCKDOWN_STATE.get("reason") if security_lockdown_active() else "",
        **snapshot,
    })


@app.get("/admin/security/lockdown/<token>")
def admin_security_lockdown(token: str):
    consumed = consume_admin_security_action_token(action="lockdown", raw_token=token)
    if not consumed:
        return "<h1>Link invalid</h1><p>This security lockdown link is invalid, expired, or already used.</p>", 410
    invalidate_admin_security_action_tokens(context_key=consumed.context_key, actions={"ignore_lockdown"})
    activate_security_lockdown(reason="Triggered from admin security email", source=f"token:{consumed.id}")
    return (
        "<h1>Security lockdown activated</h1>"
        "<p>The service has entered lockdown mode and active sessions were disconnected.</p>"
        "<p>Open /admin/security/unlock and enter the recovery code to restore service.</p>",
        200,
        {"Content-Type": "text/html; charset=utf-8"},
    )


@app.get("/admin/security/lockdown/ignore/<token>")
def admin_security_lockdown_ignore(token: str):
    consumed = consume_admin_security_action_token(action="ignore_lockdown", raw_token=token)
    if not consumed:
        return "<h1>Link invalid</h1><p>This ignore link is invalid, expired, or already used.</p>", 410
    invalidate_admin_security_action_tokens(context_key=consumed.context_key, actions={"lockdown"})
    return (
        "<h1>Security alert dismissed</h1>"
        "<p>This alert email's lockdown link has been invalidated.</p>"
        "<p>A new security alert email will generate a new lockdown link if another suspicious event happens.</p>",
        200,
        {"Content-Type": "text/html; charset=utf-8"},
    )


@app.route("/admin/security/unlock", methods=["GET", "POST"])
def admin_security_unlock():
    error = None
    success = None
    active_note = t("security_unlock_active_note") if security_lockdown_active() else t("security_unlock_idle_note")
    if request.method == "POST":
        submitted = (request.form.get("recovery_code") or "").strip()
        if submitted and secrets.compare_digest(submitted, get_admin_security_recovery_code()):
            clear_security_lockdown(reason="Recovery code accepted", source="unlock-form")
            success = t("security_unlock_success_desc")
            active_note = t("security_unlock_idle_note")
        else:
            error = t("security_unlock_invalid_code")
    return render_template(
        "pages/security_unlock.html",
        error=error,
        success=success,
        active_note=active_note,
    )



@app.get("/api/admin/alerts")
@login_required
@admin_required
def api_admin_alerts():
    return jsonify({
        "success": True,
        "pending_reset_count": PasswordResetRequest.query.filter_by(status="pending").count(),
        "active_room_count": sum(1 for m in Meeting.query.filter_by(status="active").all() if ensure_meeting_not_expired(m)),
        "online_user_count": online_user_count(),
    })


@app.get("/admin")
@login_required
@admin_required
def admin_dashboard():
    snapshot = runtime_state_snapshot()
    debug_log('ADMIN_DASHBOARD_ENTER', room_participant_counts=snapshot["room_participant_counts"], user_sid_counts=snapshot["user_sid_counts"], active_socket_count=snapshot["active_socket_count"])
    for meeting in Meeting.query.filter_by(status="active").all():
        ensure_meeting_not_expired(meeting)
    users = User.query.order_by(User.created_at.desc()).all()
    meetings = Meeting.query.order_by(Meeting.created_at.desc(), Meeting.id.desc()).all()
    active_meetings = [m for m in meetings if m.status == "active"]
    history_meetings = [m for m in meetings if m.status != "active"]
    reset_requests = PasswordResetRequest.query.order_by(PasswordResetRequest.created_at.desc()).limit(30).all()
    with runtime_state_lock:
        online_rooms = [
            {"room_id": rid, "participant_count": len(info["participants"]), "host_name": info["host_name"]}
            for rid, info in rooms.items()
        ]
    return render_template(
        "pages/admin.html",
        users=users,
        meetings=meetings,
        active_meetings=active_meetings,
        history_meetings=history_meetings,
        online_rooms=online_rooms,
        reset_requests=reset_requests,
        system_stats=get_system_metrics(),
    )


@app.post("/admin/user/<int:user_id>/kick")
@login_required
@admin_required
def admin_kick_user(user_id):
    user = User.query.get_or_404(user_id)
    snapshot = runtime_state_snapshot()
    debug_log('ADMIN_KICK_ENTER', requested_user_id=user_id, found_user_id=user.id if user else None, username=user.username if user else None, is_admin=user.is_admin if user else None, user_active_sids=snapshot["user_sid_counts"].get(user_id, 0), rooms=snapshot["room_participant_counts"])
    if user.is_admin:
        debug_log('ADMIN_KICK_ABORT', requested_user_id=user_id, reason='target_is_admin')
        return redirect(url_for("admin_dashboard"))
    kick_message = t("kicked_by_admin")
    user.session_version = (user.session_version or 0) + 1
    db.session.commit()
    debug_log('ADMIN_KICK_SESSION_VERSION_BUMP', user_id=user.id, session_version=user.session_version)
    remove_user_from_runtime_rooms(user.id, reason_message=kick_message)
    disconnect_user_sockets(user.id, message=kick_message)
    snapshot = runtime_state_snapshot()
    debug_log('ADMIN_KICK_DONE', user_id=user.id, remaining_sids=snapshot["user_sid_counts"].get(user.id, 0), rooms=snapshot["room_participant_counts"])
    notify_admin_dangerous_action("kick user", {"Target username": user.username, "Target user ID": user.id})
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/user/<int:user_id>/delete")
@login_required
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin or user.id == current_user.id:
        return redirect(url_for("admin_dashboard"))

    username = user.username
    remove_user_from_runtime_rooms(user.id, reason_message=t("kicked_by_admin"))
    disconnect_user_sockets(user.id, message=t("kicked_by_admin"))

    hosted_meetings = Meeting.query.filter_by(host_user_id=user.id).all()
    for meeting in hosted_meetings:
        if meeting.status == "active":
            end_meeting_by_room_id(meeting.room_id, "meeting_closed")
        MeetingParticipant.query.filter_by(meeting_id=meeting.id).delete(synchronize_session=False)
        db.session.delete(meeting)

    MeetingParticipant.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    purge_user_auth_artifacts(user.id, username)
    db.session.delete(user)
    db.session.commit()
    notify_admin_dangerous_action("delete user", {"Target username": username, "Target user ID": user_id})
    return redirect(url_for("admin_dashboard"))



@app.post("/admin/user/<int:user_id>/reset-password")
@login_required
@admin_required
def admin_reset_user_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = (request.form.get("new_password") or "").strip()
    if len(new_password) < 4:
        return redirect(url_for("admin_dashboard"))
    user.set_password(new_password)
    user.session_version = (user.session_version or 0) + 1
    db.session.commit()
    disconnect_user_sockets(user.id, message=t("password_reset_done"))
    notify_admin_dangerous_action("reset user password", {"Target username": user.username, "Target user ID": user.id})
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/reset-requests/cleanup")
@login_required
@admin_required
def admin_cleanup_reset_requests():
    deleted_count = PasswordResetRequest.query.filter(PasswordResetRequest.status != "pending").delete(synchronize_session=False)
    db.session.commit()
    notify_admin_dangerous_action("cleanup reset requests", {"Deleted requests": deleted_count})
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/user/<int:user_id>/disable")
@login_required
@admin_required
def admin_disable_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        return redirect(url_for("admin_dashboard"))
    user.is_active_user = False
    user.session_version = (user.session_version or 0) + 1
    db.session.commit()
    notify_admin_dangerous_action("disable user", {"Target username": user.username, "Target user ID": user.id})
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/user/<int:user_id>/enable")
@login_required
@admin_required
def admin_enable_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active_user = True
    db.session.commit()
    notify_admin_dangerous_action("enable user", {"Target username": user.username, "Target user ID": user.id})
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/meeting/<int:meeting_id>/end")
@login_required
@admin_required
def admin_end_meeting(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    room_id = meeting.room_id
    title = getattr(meeting, "title", "")
    end_meeting_by_room_id(room_id, "meeting_closed")
    notify_admin_dangerous_action("end meeting", {"Meeting ID": meeting_id, "Room ID": room_id, "Meeting title": title})
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/meetings/bulk-end")
@login_required
@admin_required
def admin_bulk_end_meetings():
    meeting_ids = parse_int_list(request.form.getlist("meeting_ids"))
    if not meeting_ids:
        return redirect(url_for("admin_dashboard"))

    meetings = Meeting.query.filter(Meeting.id.in_(meeting_ids)).all()
    ended_rooms = []
    for meeting in meetings:
        if meeting.status == "active":
            ended_rooms.append(meeting.room_id)
            end_meeting_by_room_id(meeting.room_id, "meeting_closed")
    notify_admin_dangerous_action("bulk end meetings", {"Meeting IDs": ",".join(map(str, meeting_ids)), "Ended rooms": ",".join(ended_rooms)})
    return redirect(url_for("admin_dashboard"))


def delete_meeting_record(meeting):
    if not meeting:
        return False
    if meeting.status != "ended":
        end_meeting_by_room_id(meeting.room_id, "meeting_closed")
        meeting = Meeting.query.get(meeting.id)
        if not meeting:
            return False
    MeetingParticipant.query.filter_by(meeting_id=meeting.id).delete()
    cancel_room_cleanup(meeting.room_id)
    cancel_room_expiry(meeting.room_id)
    rooms.pop(meeting.room_id, None)
    db.session.delete(meeting)
    return True


@app.post("/admin/meeting/<int:meeting_id>/delete")
@login_required
@admin_required
def admin_delete_meeting(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    room_id = meeting.room_id
    title = getattr(meeting, "title", "")
    delete_meeting_record(meeting)
    db.session.commit()
    notify_admin_dangerous_action("delete meeting", {"Meeting ID": meeting_id, "Room ID": room_id, "Meeting title": title})
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/meetings/bulk-delete")
@login_required
@admin_required
def admin_bulk_delete_meetings():
    meeting_ids = parse_int_list(request.form.getlist("meeting_ids"))
    if not meeting_ids:
        return redirect(url_for("admin_dashboard"))

    meetings = Meeting.query.filter(Meeting.id.in_(meeting_ids)).all()
    deleted_rooms = [meeting.room_id for meeting in meetings]
    for meeting in meetings:
        delete_meeting_record(meeting)
    db.session.commit()
    notify_admin_dangerous_action("bulk delete meetings", {"Meeting IDs": ",".join(map(str, meeting_ids)), "Deleted rooms": ",".join(deleted_rooms)})
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/reset-request/<int:request_id>/<status>")
@login_required
@admin_required
def admin_update_reset_request(request_id, status):
    reset_request = PasswordResetRequest.query.get_or_404(request_id)
    if status not in {"pending", "resolved", "rejected"}:
        status = "pending"
    old_status = reset_request.status
    reset_request.status = status
    db.session.commit()
    notify_admin_dangerous_action(
        "update password reset request",
        {"Request ID": request_id, "Username": reset_request.username, "Old status": old_status, "New status": status},
    )
    return redirect(url_for("admin_dashboard"))


@app.errorhandler(404)
def not_found(_):
    return render_template("pages/404.html"), 404


@app.errorhandler(403)
def forbidden(_):
    return render_template("pages/404.html", error_title="403", error_message="Forbidden"), 403


@socketio.on("connect")
def on_socket_connect():
    debug_log('SOCKET_CONNECT', sid=request.sid, authenticated=getattr(current_user, "is_authenticated", False), current_user_id=getattr(current_user, "id", None), session_version=session.get('session_version'))


@socketio.on("join_room")
def on_join_room(data):
    debug_log('SOCKET_JOIN_ROOM_BEGIN', sid=request.sid, current_user_id=getattr(current_user, "id", None), authenticated=getattr(current_user, "is_authenticated", False), session_version=session.get('session_version'), data=data)
    room_id = (data.get("room_id") or "").strip()
    password = normalize_password(data.get("password") or "")
    user_name = (data.get("user_name") or preferred_display_name(current_user)).strip()[:32] or preferred_display_name(current_user)
    if not is_valid_room_id(room_id):
        emit("join_error", {"message": t("meeting_not_found")})
        return

    meeting = Meeting.query.filter_by(room_id=room_id).first()
    if not ensure_meeting_not_expired(meeting):
        debug_log('SOCKET_JOIN_ROOM_MEETING_MISSING', sid=request.sid, room_id=room_id)
        emit("join_error", {"message": t("meeting_not_found")})
        return

    sid = request.sid
    if not current_user.is_authenticated:
        debug_log('SOCKET_JOIN_ROOM_NOT_AUTH', sid=sid, room_id=room_id)
        emit("join_error", {"message": t("invalid_login")})
        return
    fresh_user = db.session.get(User, current_user.id)
    if not fresh_user or not fresh_user.is_active_user or session.get("session_version") != fresh_user.session_version:
        debug_log('SOCKET_JOIN_ROOM_SESSION_INVALID', sid=sid, room_id=room_id, fresh_user_id=getattr(fresh_user, "id", None), fresh_session_version=getattr(fresh_user, "session_version", None), browser_session_version=session.get("session_version"))
        emit("force_logout", {"message": t("kicked")})
        return
    db.session.refresh(fresh_user)
    cancel_room_cleanup(room_id)

    with runtime_state_lock:
        room = ensure_runtime_room(meeting)
        room["lang"] = session.get("lang", "zh")

        if normalize_password(room["password"]) != password:
            debug_log('SOCKET_JOIN_ROOM_BAD_PASSWORD', sid=request.sid, room_id=room_id)
            emit("join_error", {"message": t("wrong_password")})
            return

        if len(room["participants"]) >= MAX_PARTICIPANTS and sid not in room["participants"]:
            debug_log('SOCKET_JOIN_ROOM_FULL', sid=sid, room_id=room_id, participants=list(room['participants'].keys()))
            emit("join_error", {"message": f"{t('room_full')} ({MAX_PARTICIPANTS})"})
            return

        # Clean up only truly stale sockets for the same authenticated user.
        # Keep other active sessions/tabs alive; only prune entries that are no
        # longer tracked as active sockets.
        prune_stale_room_participants(room_id, room, current_user.id, sid)

        existing = [
            build_room_participant_payload(osid, info, room.get("host_user_id"))
            for osid, info in room["participants"].items()
        ]
        room["participants"][sid] = {"name": user_name, "joined_at": time.time(), "user_id": current_user.id}
        sid_to_user[sid] = {"room_id": room_id, "name": user_name, "user_id": current_user.id}
        bind_user_socket(current_user.id, sid)

        host_returned = False
        if current_user.id == room.get("host_user_id"):
            host_returned = not room.get("host_present")
            room["host_present"] = True

        # Only clear stale screen-share ownership when the previous sharer
        # socket is no longer active. Active sibling sessions keep ownership.
        reconcile_rejoining_active_sharer(room_id, room, current_user.id)

        snapshot = runtime_state_snapshot()
        debug_log('SOCKET_JOIN_ROOM_REGISTERED', sid=sid, room_id=room_id, user_id=current_user.id, room_participants=list(room['participants'].keys()), user_active_sids=snapshot["user_sid_counts"], sid_to_user_entry=sid_to_user.get(sid))
        is_room_host = bool(current_user.id == room.get("host_user_id"))
        visible_chat_history = visible_chat_history_for_user(room, current_user.id, sid, is_room_host=is_room_host)
        join_payload = {
            "room_id": room_id,
            "participants": existing,
            "self_sid": sid,
            "participant_count": len(room["participants"]),
            "host_present": bool(room.get("host_present")),
            "danmaku_enabled": bool(room.get("danmaku_enabled")),
            "chat_history": visible_chat_history,
            **build_active_sharer_payload(room),
        }

    participant = MeetingParticipant(
        meeting_id=room["meeting_db_id"],
        user_id=current_user.id if current_user.is_authenticated else None,
        display_name=user_name,
        sid=sid,
    )
    db.session.add(participant)
    db.session.commit()
    notify_admin_room_joined(user=fresh_user, meeting=meeting, display_name=user_name)
    join_room(room_id)

    debug_log('SOCKET_JOIN_ROOM_OK', sid=sid, room_id=room_id, participant_count=len(room["participants"]), host_present=bool(room.get("host_present")))
    emit("join_ok", join_payload)
    emit(
        "participant_joined",
        {"sid": sid, "name": user_name, "is_host": is_room_host, "participant_count": join_payload["participant_count"]},
        room=room_id,
        include_self=False,
    )
    broadcast_room_participant_snapshot(room_id)

    if host_returned:
        emit_host_presence_changed(room_id, True, t("host_returned_room"))


@socketio.on("update_profile")
def on_update_profile(data):
    sid = request.sid
    new_name = ((data or {}).get("name") or "").strip()[:32]
    if not new_name:
        return
    with runtime_state_lock:
        info = sid_to_user.get(sid)
        if not info:
            return
        room_id = info["room_id"]
        room = rooms.get(room_id)
        if not room or sid not in room.get("participants", {}):
            return
        room["participants"][sid]["name"] = new_name
        info["name"] = new_name
    participant = MeetingParticipant.query.filter_by(sid=sid).order_by(MeetingParticipant.id.desc()).first()
    if participant:
        participant.display_name = new_name
    if current_user.is_authenticated:
        user = db.session.get(User, current_user.id)
        if user:
            user.display_name = new_name
    db.session.commit()
    socketio.emit("participant_updated", {"sid": sid, "name": new_name}, room=room_id)
    broadcast_room_participant_snapshot(room_id)


def _pick_translation_target(text: str) -> str:
    sample = (text or "")[:400]
    if re.search(r"[一-鿿]", sample):
        return "en"
    latin_words = re.findall(r"[A-Za-z]+", sample)
    if latin_words:
        return "zh-CN"
    return "en"


def _translate_via_google(text: str, target_lang: str):
    query = urlencode({"client": "gtx", "sl": "auto", "tl": target_lang, "dt": "t", "q": text})
    req = Request(f"https://translate.googleapis.com/translate_a/single?{query}", headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=8) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    data = json.loads(raw)
    translated = "".join(part[0] for part in (data[0] or []) if isinstance(part, list) and part and part[0])
    detected = data[2] if isinstance(data, list) and len(data) > 2 else "auto"
    return translated or text, detected


def _guess_extension_from_content_type(content_type: str | None) -> str:
    content_type = (content_type or "").split(";", 1)[0].strip().lower()
    mapping = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "image/heic": ".heic",
        "image/heif": ".heif",
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/quicktime": ".mov",
        "video/x-msvideo": ".avi",
        "video/3gpp": ".3gp",
        "application/pdf": ".pdf",
    }
    return mapping.get(content_type, mimetypes.guess_extension(content_type or "") or "")


def _allowed_chat_file(filename: str, content_type: str | None = None) -> bool:
    suffix = (Path(filename or "").suffix or "").lower().lstrip(".")
    if suffix and suffix in ALLOWED_CHAT_EXTENSIONS:
        return True
    content_type = (content_type or "").split(";", 1)[0].strip().lower()
    if content_type.startswith("image/") or content_type.startswith("video/"):
        return True
    ext_from_type = _guess_extension_from_content_type(content_type).lstrip(".").lower()
    return bool(ext_from_type and ext_from_type in ALLOWED_CHAT_EXTENSIONS)


def _build_safe_upload_name(filename: str, content_type: str | None = None) -> str:
    raw_name = (filename or "").strip()
    safe_name = secure_filename(raw_name)
    stem = Path(safe_name or raw_name or "attachment").stem
    suffix = (Path(safe_name or raw_name).suffix or "").lower()
    if not suffix:
        suffix = _guess_extension_from_content_type(content_type)
    stem = secure_filename(stem) or "attachment"
    return f"{stem}{suffix}" if suffix else stem


def _dir_size_bytes(path: str) -> int:
    total = 0
    if not os.path.isdir(path):
        return 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                continue
    return total


def _enforce_chat_storage_limits(room_id: str, incoming_size: int):
    room_dir = os.path.join(CHAT_UPLOAD_DIR, room_id)
    room_size = _dir_size_bytes(room_dir)
    total_size = _dir_size_bytes(CHAT_UPLOAD_DIR)
    if room_size + incoming_size > CHAT_ROOM_STORAGE_LIMIT_BYTES:
        return "room_storage_limit"
    if total_size + incoming_size > CHAT_GLOBAL_STORAGE_LIMIT_BYTES:
        return "server_storage_limit"
    return None


def _optimize_image_to_path(upload, original_name: str, dest_dir: str):
    if Image is None or ImageOps is None:
        return None
    suffix = (Path(original_name).suffix or '').lower()
    if suffix == '.gif':
        return None
    upload.stream.seek(0)
    try:
        with Image.open(upload.stream) as img:
            img = ImageOps.exif_transpose(img)
            width, height = img.size
            if max(width, height) > CHAT_IMAGE_MAX_DIMENSION:
                img.thumbnail((CHAT_IMAGE_MAX_DIMENSION, CHAT_IMAGE_MAX_DIMENSION))
            base_name = secure_filename(Path(original_name).stem) or 'image'
            if img.mode in ('RGBA', 'LA', 'P') and suffix in {'.png', '.webp'}:
                ext = '.webp'
                content_type = 'image/webp'
                final_name = f"{base_name}{ext}"
                stored_name = f"{uuid.uuid4().hex}_{final_name}"
                abs_path = os.path.join(dest_dir, stored_name)
                img.save(abs_path, format='WEBP', quality=82, method=6)
            else:
                ext = '.jpg'
                content_type = 'image/jpeg'
                final_name = f"{base_name}{ext}"
                stored_name = f"{uuid.uuid4().hex}_{final_name}"
                abs_path = os.path.join(dest_dir, stored_name)
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                elif img.mode == 'L':
                    img = img.convert('RGB')
                img.save(abs_path, format='JPEG', quality=84, optimize=True, progressive=True)
            return {
                'path': abs_path,
                'stored_name': stored_name,
                'display_name': final_name[:120],
                'content_type': content_type,
                'size': os.path.getsize(abs_path),
            }
    except Exception:
        upload.stream.seek(0)
        return None


def _normalize_attachment_content_type(filename: str, content_type: str | None) -> str:
    suffix = (Path(filename or "").suffix or "").lower()
    content_type = (content_type or "").strip().lower()
    extension_map = {
        ".pdf": "application/pdf",
        ".txt": "text/plain; charset=utf-8",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".ppt": "application/vnd.ms-powerpoint",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".xls": "application/vnd.ms-excel",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".zip": "application/zip",
        ".rar": "application/vnd.rar",
        ".7z": "application/x-7z-compressed",
    }
    if suffix in extension_map:
        return extension_map[suffix]
    guessed, _ = mimetypes.guess_type(filename or "")
    if guessed:
        if guessed.startswith("text/") and "charset" not in guessed:
            return f"{guessed}; charset=utf-8"
        return guessed
    return content_type or "application/octet-stream"


def _attachment_kind(filename: str, content_type: str) -> str:
    content_type = (content_type or "").lower()
    suffix = (Path(filename or "").suffix or "").lower()
    if content_type.startswith("image/") or suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}:
        return "image"
    if content_type.startswith("video/") or suffix in {".mp4", ".webm", ".mov", ".m4v"}:
        return "video"
    if content_type.startswith("audio/"):
        return "audio"
    if content_type == "application/pdf" or suffix == ".pdf":
        return "pdf"
    if suffix in {".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".txt"}:
        return "document"
    if suffix in {".zip", ".rar", ".7z"}:
        return "archive"
    return "file"


def _inline_content_disposition(filename: str) -> str:
    safe_ascii = secure_filename(filename or "attachment") or "attachment"
    quoted = quote(filename or safe_ascii)
    return f"inline; filename=\"{safe_ascii}\"; filename*=UTF-8''{quoted}"


def _find_attachment_by_token(room_id: str, token: str):
    with runtime_state_lock:
        room = rooms.get(room_id)
        if not room:
            return None, None
        for item in room.get("chat_history", []):
            attachment = item.get("attachment") if isinstance(item, dict) else None
            if isinstance(attachment, dict) and attachment.get("token") == token:
                return room, attachment
    return room, None


def _attachment_extension(filename: str) -> str:
    return (Path(filename or "").suffix or "").lower()

def _attachment_is_inline_previewable(attachment: dict | None) -> bool:
    if not isinstance(attachment, dict):
        return False
    kind = str(attachment.get("kind") or "").lower()
    ctype = str(attachment.get("type") or "").lower()
    ext = _attachment_extension(str(attachment.get("name") or ""))
    if kind in {"image", "video", "audio"}:
        return True
    if ctype.startswith("text/"):
        return True
    if ctype == "application/pdf" or ext == ".pdf":
        return True
    return False

def _chat_attachment_abs_path(room_id: str, attachment: dict):
    stored_name = str(attachment.get("storedName") or "").strip()
    room_dir = os.path.join(CHAT_UPLOAD_DIR, room_id)
    if stored_name:
        direct = os.path.join(room_dir, stored_name)
        if os.path.exists(direct):
            return direct
        for sub in ('media', 'docs'):
            candidate = os.path.join(room_dir, sub, stored_name)
            if os.path.exists(candidate):
                return candidate
    filename = attachment.get("name") or f"file-{attachment.get('token') or ''}"
    legacy_path = os.path.join(room_dir, f"{attachment.get('token')}_{filename}")
    if os.path.exists(legacy_path):
        return legacy_path
    token = str(attachment.get("token") or "").strip()
    if token and os.path.isdir(room_dir):
        for root, _, files in os.walk(room_dir):
            for candidate in files:
                if candidate.startswith(f"{token}_"):
                    return os.path.join(root, candidate)
    return legacy_path

def _can_access_room_attachment(room: dict | None) -> bool:
    return can_user_access_room(room, current_user.id)


def _remove_path_quietly(path: str):
    try:
        os.remove(path)
    except OSError:
        pass


def _normalize_upload_permission(value: str | None) -> str:
    permission = str(value or "download").strip().lower()
    return permission if permission in {"view", "download"} else "download"


def _resolve_upload_kind(original_name: str, incoming_content_type: str, upload_mode: str):
    content_type = _normalize_attachment_content_type(original_name, incoming_content_type)
    kind = _attachment_kind(original_name, content_type)
    ext = (Path(original_name).suffix or "").lower()

    if upload_mode == "media" and kind not in {"image", "video", "audio"}:
        if ext in CHAT_IMAGE_EXTENSIONS:
            kind = "image"
            content_type = _normalize_attachment_content_type(original_name, incoming_content_type)
        elif ext in CHAT_VIDEO_EXTENSIONS:
            kind = "video"
            content_type = _normalize_attachment_content_type(original_name, incoming_content_type)
        else:
            return None, None, {"ok": False, "error": "media_only_upload", "detail": incoming_content_type, "name": original_name}, 400
    if upload_mode == "doc" and kind in {"image", "video", "audio"}:
        return None, None, {"ok": False, "error": "document_only_upload"}, 400
    return kind, content_type, None, None

def _api_chat_upload_impl(upload_mode: str = "any"):
    try:
        room_id = str(request.form.get("room_id") or "").strip()
        permission = _normalize_upload_permission(request.form.get("permission"))
        if not is_valid_room_id(room_id):
            return jsonify({"ok": False, "error": "room_not_found"}), 404
        with runtime_state_lock:
            room = rooms.get(room_id)
        if not room:
            return jsonify({"ok": False, "error": "room_not_found"}), 404
        if not can_user_access_room(room, current_user.id):
            return jsonify({"ok": False, "error": "not_in_room"}), 403
        upload = request.files.get("file")
        if not upload or not upload.filename:
            return jsonify({"ok": False, "error": "missing_file"}), 400

        incoming_content_type = (upload.mimetype or upload.content_type or "application/octet-stream").split(';', 1)[0].strip().lower()
        original_name = _build_safe_upload_name(upload.filename, incoming_content_type)
        kind, content_type, upload_error, status_code = _resolve_upload_kind(original_name, incoming_content_type, upload_mode)
        if upload_error:
            return jsonify(upload_error), status_code

        if not _allowed_chat_file(upload.filename, incoming_content_type):
            return jsonify({"ok": False, "error": "file_type_not_allowed", "detail": incoming_content_type}), 400

        size_limit = CHAT_MAX_UPLOAD_BYTES
        if kind == 'image':
            size_limit = CHAT_IMAGE_MAX_UPLOAD_BYTES
        elif kind == 'video':
            size_limit = CHAT_VIDEO_MAX_UPLOAD_BYTES

        token = secrets.token_urlsafe(16)
        room_dir = os.path.join(CHAT_UPLOAD_DIR, room_id)
        os.makedirs(room_dir, exist_ok=True)

        bucket = 'media' if kind in {'image', 'video', 'audio'} else 'docs'
        target_dir = os.path.join(room_dir, bucket)
        os.makedirs(target_dir, exist_ok=True)
        stored_name = f"{token}_{original_name}"
        abs_path = os.path.join(target_dir, stored_name)

        # 先落盘再取大小，避免某些桌面浏览器上传流 seek/tell 异常导致 500
        upload.save(abs_path)
        size = os.path.getsize(abs_path)
        if size > size_limit:
            _remove_path_quietly(abs_path)
            return jsonify({"ok": False, "error": "file_too_large", "limit": size_limit}), 413
        quota_error = _enforce_chat_storage_limits(room_id, size)
        if quota_error:
            _remove_path_quietly(abs_path)
            return jsonify({"ok": False, "error": quota_error}), 507

        display_name = original_name[:120]
        attachment_kind = _attachment_kind(display_name, content_type)
        inline_previewable = _attachment_is_inline_previewable({"kind": attachment_kind, "type": content_type, "name": display_name})
        attachment = {
            "token": token,
            "storedName": stored_name,
            "type": content_type,
            "kind": attachment_kind,
            "name": display_name,
            "size": int(size),
            "permission": permission,
            "viewUrl": url_for("chat_attachment_view", room_id=room_id, token=token),
            "rawUrl": url_for("chat_attachment_raw", room_id=room_id, token=token) if inline_previewable else None,
            "downloadUrl": url_for("chat_attachment_download", room_id=room_id, token=token) if permission == "download" else None,
        }
        return jsonify({"ok": True, "attachment": attachment})
    except Exception as exc:
        app.logger.exception("chat upload failed")
        return jsonify({"ok": False, "error": "upload_internal_error"}), 500

@app.post("/api/chat_upload")
@login_required
def api_chat_upload():
    return _api_chat_upload_impl("any")

@app.post("/api/chat_upload_media")
@login_required
def api_chat_upload_media():
    return _api_chat_upload_impl("media")

@app.post("/api/chat_upload_doc")
@login_required
def api_chat_upload_doc():
    return _api_chat_upload_impl("doc")


@app.get("/chat_attachment/<room_id>/<token>")
@login_required
def chat_attachment_view(room_id, token):
    room, attachment = _find_attachment_by_token(room_id, token)
    if not room or not attachment:
        abort(404)
    if not _can_access_room_attachment(room):
        abort(403)
    filename = attachment.get("name") or f"file-{token}"
    inline_previewable = _attachment_is_inline_previewable(attachment)
    return render_template(
        "pages/attachment_view.html",
        attachment=attachment,
        room_id=room_id,
        filename=filename,
        inline_previewable=inline_previewable,
        raw_url=url_for("chat_attachment_raw", room_id=room_id, token=token) if inline_previewable else None,
        allow_download=(attachment.get("permission") == "download"),
        download_url=url_for("chat_attachment_download", room_id=room_id, token=token) if attachment.get("permission") == "download" else None,
        lang=(session.get("lang") or "zh"),
    )


@app.get("/chat_attachment/<room_id>/<token>/raw")
@login_required
def chat_attachment_raw(room_id, token):
    room, attachment = _find_attachment_by_token(room_id, token)
    if not room or not attachment:
        abort(404)
    if not _can_access_room_attachment(room):
        abort(403)
    if not _attachment_is_inline_previewable(attachment):
        abort(403)
    filename = attachment.get("name") or f"file-{token}"
    abs_path = _chat_attachment_abs_path(room_id, attachment)
    if not os.path.exists(abs_path):
        abort(404)
    mimetype = _normalize_attachment_content_type(filename, attachment.get("type") or "application/octet-stream")
    resp = send_file(abs_path, mimetype=mimetype, as_attachment=False, conditional=True, download_name=filename)
    resp.headers["Content-Disposition"] = _inline_content_disposition(filename)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Cache-Control"] = "private, no-store, max-age=0"
    return resp


@app.get("/chat_attachment/<room_id>/<token>/download")
@login_required
def chat_attachment_download(room_id, token):
    room, attachment = _find_attachment_by_token(room_id, token)
    if not room or not attachment:
        abort(404)
    if not _can_access_room_attachment(room):
        abort(403)
    if attachment.get("permission") != "download":
        abort(403)
    filename = attachment.get("name") or f"file-{token}"
    abs_path = _chat_attachment_abs_path(room_id, attachment)
    if not os.path.exists(abs_path):
        abort(404)
    return send_file(abs_path, mimetype=_normalize_attachment_content_type(filename, attachment.get("type") or "application/octet-stream"), as_attachment=True, conditional=True, download_name=filename)


@app.post("/api/translate_message")
@login_required
def api_translate_message():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text") or "").strip()[:2000]
    if not text:
        return jsonify({"ok": False, "error": "empty_text"}), 400
    target_lang = str(payload.get("target") or "").strip() or _pick_translation_target(text)
    try:
        translated, detected = _translate_via_google(text, target_lang)
        return jsonify({"ok": True, "translation": translated, "target": target_lang, "detected": detected})
    except Exception as exc:
        app.logger.warning("translation failed: %s", exc)
        return jsonify({"ok": False, "error": "translation_failed"}), 502


@app.post("/api/translate_to_english")
@login_required
def api_translate_to_english():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text") or "").strip()[:2000]
    if not text:
        return jsonify({"ok": False, "error": "empty_text"}), 400
    try:
        translated, detected = _translate_via_google(text, "en")
        return jsonify({"ok": True, "translation": translated, "target": "en", "detected": detected})
    except Exception as exc:
        app.logger.warning("translation to english failed: %s", exc)
        return jsonify({"ok": False, "error": "translation_failed"}), 502


@socketio.on("meeting_chat_send")
def on_meeting_chat_send(data):
    sid = request.sid
    payload = data or {}
    message = (payload.get("message") or "").strip()[:1000]
    attachment = payload.get("attachment") or None
    if attachment and isinstance(attachment, dict):
        token = str(attachment.get("token") or "").strip()
        if token:
            permission = str(attachment.get("permission") or "download").strip().lower()
            if permission not in {"view", "download"}:
                permission = "download"
            attachment = {
                "token": token,
                "storedName": str(attachment.get("storedName") or "")[:180],
                "type": str(attachment.get("type") or "application/octet-stream")[:120],
                "kind": str(attachment.get("kind") or "file")[:24],
                "name": str(attachment.get("name") or "attachment")[:120],
                "size": int(attachment.get("size") or 0),
                "permission": permission,
                "viewUrl": str(attachment.get("viewUrl") or "")[:500],
                "rawUrl": str(attachment.get("rawUrl") or "")[:500],
                "downloadUrl": str(attachment.get("downloadUrl") or "")[:500] if permission == "download" else None,
            }
        else:
            attachment = None
    mode = (payload.get("mode") or "all").strip()
    mentions = payload.get("mentions") if isinstance(payload.get("mentions"), list) else []
    mentions = [str(x)[:64] for x in mentions[:12]]
    if not message and not attachment:
        return
    with runtime_state_lock:
        info = sid_to_user.get(sid)
        if not info:
            return
        room_id = info["room_id"]
        room = rooms.get(room_id)
        if not room:
            return
        event = {
            "id": secrets.token_hex(8),
            "seq": len(room.get("chat_history", [])),
            "from": sid,
            "senderUserId": info.get("user_id"),
            "senderName": room["participants"].get(sid, {}).get("name") or info.get("name") or "Guest",
            "message": message,
            "mode": "host" if mode == "host" else "all",
            "mentions": mentions,
            "attachment": attachment,
            "createdAt": datetime.utcnow().strftime("%H:%M:%S"),
            "withdrawn": False,
        }
        room.setdefault("chat_history", []).append(event)
        if len(room["chat_history"]) > 200:
            room["chat_history"] = room["chat_history"][-200:]
        if event["mode"] == "host":
            target_sids = {sid}
            for participant_sid, participant_info in room.get("participants", {}).items():
                if participant_info.get("user_id") == room.get("host_user_id"):
                    target_sids.add(participant_sid)
        else:
            target_sids = None
    if event["mode"] == "host":
        for target_sid in target_sids:
            socketio.emit("meeting_chat_message", event, to=target_sid)
    else:
        socketio.emit("meeting_chat_message", event, room=room_id)




@socketio.on("meeting_chat_clear")
def on_meeting_chat_clear():
    sid = request.sid
    with runtime_state_lock:
        info = sid_to_user.get(sid)
        if not info:
            return
        room_id = info["room_id"]
        room = rooms.get(room_id)
        if not room:
            return
        is_host = bool(current_user.is_authenticated and current_user.id == room.get("host_user_id"))
        clear_marker = len(room.get("chat_history", []))
        if is_host:
            room["chat_history"] = []
            room["chat_clear_markers"] = {}
        else:
            room.setdefault("chat_clear_markers", {})[room_user_marker_key(info.get("user_id"), sid)] = clear_marker
    if is_host:
        shutil.rmtree(os.path.join(CHAT_UPLOAD_DIR, room_id), ignore_errors=True)
        socketio.emit("meeting_chat_cleared", {"by": sid, "scope": "all"}, room=room_id)
    else:
        socketio.emit("meeting_chat_cleared", {"by": sid, "scope": "self"}, to=sid)


@socketio.on("meeting_chat_retract")
def on_meeting_chat_retract(data):
    sid = request.sid
    message_id = str((data or {}).get("id") or "")[:32]
    if not message_id:
        return
    with runtime_state_lock:
        info = sid_to_user.get(sid)
        if not info:
            return
        room = rooms.get(info["room_id"])
        if not room:
            return
        is_host = bool(current_user.is_authenticated and current_user.id == room.get("host_user_id"))
        sender_name = None
        for item in room.get("chat_history", []):
            if item.get("id") != message_id:
                continue
            if item.get("senderUserId") != info.get("user_id") and item.get("from") != sid and not is_host:
                return
            item["withdrawn"] = True
            item["message"] = ""
            item["mentions"] = []
            item["attachment"] = None
            sender_name = item.get("senderName") or "Guest"
            break
        if sender_name is None:
            return
    socketio.emit(
        "meeting_chat_retracted",
        {"id": message_id, "senderName": sender_name},
        room=info["room_id"],
    )
    return

@socketio.on("toggle_danmaku")
def on_toggle_danmaku(data):
    sid = request.sid
    with runtime_state_lock:
        info = sid_to_user.get(sid)
        if not info:
            return
        room_id = info["room_id"]
        room = rooms.get(room_id)
    meeting = Meeting.query.filter_by(room_id=room_id).first()
    if not room or not meeting or not current_user.is_authenticated or current_user.id != meeting.host_user_id:
        emit("host_action_error", {"message": t("host_only_action")})
        return
    enabled = bool((data or {}).get("enabled"))
    with runtime_state_lock:
        room["danmaku_enabled"] = enabled
    socketio.emit("room_ui_event", {"type": "danmaku_toggled", "enabled": enabled, "from": sid}, room=room_id)


@socketio.on("signal")
def on_signal(data):
    return None


@socketio.on("room_ui_event")
def on_room_ui_event(data):
    sid = request.sid
    payload = data or {}
    event_type = (payload.get("type") or "").strip()
    with runtime_state_lock:
        info = sid_to_user.get(sid)
        if not info:
            return
        room_id = info["room_id"]
        room = rooms.get(room_id)
        if not room:
            return
        if event_type == "screen_share_started":
            active_sharer_sid = room.get("active_sharer_sid")
            active_sharer_user_id = room.get("active_sharer_user_id")
            requester_user_id = info.get("user_id")
            same_authenticated_user = bool(
                active_sharer_user_id and requester_user_id and active_sharer_user_id == requester_user_id
            )
            if active_sharer_sid and active_sharer_sid != sid and not same_authenticated_user:
                emit("room_ui_event", {
                    "type": "screen_share_denied",
                    "from": active_sharer_sid,
                    "activeSharerSid": active_sharer_sid,
                    "message": TRANSLATIONS.get(room.get("lang"), TRANSLATIONS["zh"]).get("another_participant_sharing_screen", "已有其他用户正在共享屏幕"),
                }, to=sid)
                return
            set_active_sharer(room, sid, requester_user_id)
        elif event_type == "screen_share_stopped":
            if room.get("active_sharer_sid") == sid or room.get("active_sharer_user_id") == info.get("user_id"):
                clear_active_sharer(room)
    payload["from"] = sid
    emit("room_ui_event", payload, room=room_id, include_self=False)


@socketio.on("host_end_meeting")
def on_host_end_meeting(data=None):
    sid = request.sid
    with runtime_state_lock:
        info = sid_to_user.get(sid)
    if not info:
        emit("host_action_error", {"message": t("failed")})
        return

    room_id = info["room_id"]
    meeting = Meeting.query.filter_by(room_id=room_id).first()
    if not meeting or meeting.status == "ended":
        emit("host_action_error", {"message": t("meeting_not_found")})
        return

    if not current_user.is_authenticated or current_user.id != meeting.host_user_id:
        emit("host_action_error", {"message": t("host_only_action")})
        return

    end_meeting_by_room_id(room_id, "meeting_closed_by_host")


@socketio.on("leave_room")
def on_leave_room(*_args):
    explicit_leave = False
    if _args:
        maybe_payload = _args[0]
        if isinstance(maybe_payload, dict):
            explicit_leave = bool(maybe_payload.get("explicit"))
    sid = request.sid
    with runtime_state_lock:
        sid_info_snapshot = sid_to_user.get(sid)
    debug_log('SOCKET_LEAVE_BEGIN', sid=sid, sid_info=sid_info_snapshot, current_user_id=getattr(current_user, "id", None))
    with runtime_state_lock:
        info = sid_to_user.pop(sid, None)
        if not info:
            debug_log('SOCKET_LEAVE_NOINFO', sid=sid)
            return
        room_id = info["room_id"]
        unbind_user_socket(info.get("user_id"), sid)
        room = rooms.get(room_id)
        if room and explicit_leave and info.get("user_id") == room.get("host_user_id") and len(room.get("participants", {})) > 1:
            sid_to_user[sid] = info
            bind_user_socket(info.get("user_id"), sid)
            emit("host_action_error", {"message": t("host_must_end_meeting_first")})
            return
    leave_room(room_id)
    if room and sid in room["participants"]:
        with runtime_state_lock:
            name = room["participants"][sid]["name"]
            del room["participants"][sid]
            host_left = False
            reconcile_departing_active_sharer(room_id, room, sid, info.get("user_id"))
            if current_user.is_authenticated and current_user.id == room.get("host_user_id"):
                if room.get("host_present"):
                    host_left = True
                room["host_present"] = False
            participant_count_after = len(room["participants"])
            should_schedule_cleanup = not room["participants"]
        participant = mark_meeting_participant_left(sid)
        if participant:
            db.session.commit()
        emit_participant_left(room_id, sid, {"name": name}, participant_count_after)
        broadcast_room_participant_snapshot(room_id)
        if host_left:
            emit_host_presence_changed(room_id, False, t("host_left_room"))
        snapshot = runtime_state_snapshot()
        debug_log('SOCKET_LEAVE_DONE', sid=sid, room_id=room_id, remaining_participants=list(room.get("participants", {}).keys()), user_active_sids=snapshot["user_sid_counts"])
        if should_schedule_cleanup:
            schedule_room_cleanup(room_id)


@socketio.on("disconnect")
def on_disconnect():
    with runtime_state_lock:
        sid_info_snapshot = sid_to_user.get(request.sid)
    debug_log('SOCKET_DISCONNECT', sid=request.sid, sid_info=sid_info_snapshot, current_user_id=getattr(current_user, "id", None))
    on_leave_room()


with app.app_context():
    _load_security_lockdown_state()
    db.create_all()
    ensure_user_columns()
    ensure_admin()
    get_admin_security_recovery_code()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False, allow_unsafe_werkzeug=True)
