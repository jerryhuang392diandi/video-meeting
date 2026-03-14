import io
import os
import secrets
import shutil
import sqlite3
import string
import subprocess
import tempfile
import threading
import time
from urllib.parse import quote
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps

from flask import Flask, abort, after_this_request, jsonify, redirect, render_template, request, send_file, session, url_for
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
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
DB_PATH = os.path.join(INSTANCE_DIR, "app.db")
os.makedirs(INSTANCE_DIR, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(16))
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

MAX_PARTICIPANTS = 6
ROOM_EMPTY_GRACE_SECONDS = 20
MEETING_DURATION_SECONDS = 90 * 60
rooms = {}
sid_to_user = {}
user_active_sids = {}

TRANSLATIONS = {
    "zh": {
        "app_name": "西小电视频会议系统",
        "subtitle": "西小电视频会议平台｜单设备登录｜管理员后台",
        "nav_home": "首页",
        "nav_history": "历史会议",
        "nav_admin": "管理员后台",
        "nav_logout": "退出登录",
        "nav_login": "登录",
        "nav_register": "注册",
        "current_user": "当前用户",
        "create_room": "创建会议",
        "join_room": "加入会议",
        "host_name": "主持人名称",
        "display_name": "显示名称",
        "room_id": "会议号",
        "room_password": "会议密码",
        "create_now": "立即创建",
        "join_now": "立即加入",
        "invite_link": "邀请链接",
        "copy": "复制",
        "copied": "已复制到剪贴板",
        "quick_actions": "快速操作",
        "permissions": "设备与会议控制",
        "request_media": "申请摄像头/麦克风权限",
        "switch_camera": "切换摄像头",
        "share_screen": "共享屏幕",
        "virtual_bg": "虚拟背景",
        "blur_bg": "背景虚化",
        "recording": "录制",
        "participants_panel": "参会者面板",
        "layout_switch": "切换布局",
        "virtual_bg_tip": "虚拟背景功能按钮已预留，当前为占位版本。",
        "blur_bg_tip": "背景虚化功能按钮已预留，当前为占位版本。",
        "recording_tip": "录制功能按钮已预留，当前为占位版本。",
        "participants_tip": "参会者面板功能按钮已预留，当前为占位版本。",
        "layout_tip": "布局切换功能按钮已预留，当前为占位版本。",
        "mic": "麦克风",
        "camera": "摄像头",
        "leave": "离开会议",
        "online_count": "在线人数",
        "meeting_history": "历史会议",
        "no_history": "暂无历史会议",
        "rejoin": "重新进入",
        "login_title": "登录",
        "register_title": "注册",
        "username": "用户名",
        "password": "密码",
        "submit_login": "登录",
        "submit_register": "注册",
        "admin_dashboard": "管理员后台",
        "users": "用户列表",
        "meetings": "会议列表",
        "online_rooms": "在线房间",
        "status": "状态",
        "enabled": "启用",
        "disabled": "禁用",
        "disable": "禁用",
        "enable": "启用",
        "end_meeting": "结束会议",
        "language": "语言",
        "lang_zh": "中文",
        "lang_en": "English",
        "permission_ready": "设备权限已获取",
        "permission_failed": "设备权限获取失败",
        "kicked": "你的账号已在其他设备登录，当前设备已退出。",
        "meeting_closed": "会议已被管理员结束。",
        "page_not_found": "页面不存在",
        "hero_title": "更清晰的会议入口",
        "hero_desc": "支持中英切换、管理员后台、历史记录、单设备登录，以及更现代化的会议 UI。",
        "placeholder_login_hint": "支持 root 管理员登录",
        "device_panel": "设备控制",
        "enter_room": "进入会议",
        "meeting_room": "会议室",
        "dashboard_title": "快速创建与加入会议",
        "dashboard_desc": "首页支持会议创建、加入、邀请链接复制和常用会议入口。",
        "meeting_actions": "会议操作",
        "admin_note": "管理员账号默认支持 root 登录",
        "system_status": "系统状态",
        "room_ready": "会议室已准备就绪",
        "mic_on": "麦克风：开启",
        "mic_off": "麦克风：关闭",
        "camera_on": "摄像头：开启",
        "camera_off": "摄像头：关闭",
        "join_failed": "加入会议失败",
        "meeting_not_found": "未找到会议",
        "wrong_password": "会议密码错误",
        "room_full": "会议室已满",
        "failed": "操作失败",
        "invalid_login": "用户名或密码错误",
        "account_disabled": "账号已被禁用",
        "username_password_required": "请输入用户名和密码",
        "username_exists": "用户名已存在",
        "back_home": "返回首页",
        "local_you": "你",
        "created_at": "创建时间",
        "ended_at": "结束时间",
        "host": "主持人",
        "admin_role": "管理员",
        "yes": "是",
        "no": "否",
        "no_online_rooms": "暂无在线房间",
        "no_meetings": "暂无会议记录",
        "host_end_meeting": "解散会议",
        "host_only_action": "仅主持人可执行此操作",
        "meeting_closed_by_host": "会议已被主持人解散。",
        "host_left_room": "主持人已离开会议，当前会议暂时没有主持人。",
        "host_returned_room": "主持人已返回会议，主持权限已恢复。",
        "you_left_meeting": "你已离开会议",
        "record_password_label": "会议密码",
        "record_direct_mp4": "浏览器已直接生成 MP4 文件",
        "delete_record": "删除记录",
        "batch_delete": "批量删除",
        "select_all": "全选",
        "selected_count": "已选数量",
        "history_records": "历史会议记录",
        "active_meetings": "进行中会议",
        "batch_delete_success": "批量删除完成",
        "no_meeting_selected": "未选择任何会议记录",
        "joined_meeting": "参与会议",
        "created_meeting": "创建会议",
        "meeting_role": "会议关系",
        "meeting_active": "进行中",
        "meeting_ended": "已结束",
        "expired_meeting": "会议已超过 90 分钟，系统已自动解散。",
        "delete_meeting_success": "会议记录已删除",
        "meeting_duration_limit": "会议时长上限 90 分钟",
        "enter_active_meeting": "进入会议",
        "ended_badge": "已结束",
        "login_help_title": "登录帮助",
        "user_guide": "用户指南",
        "support_hotline": "帮助电话",
        "guide_title": "用户指南",
        "guide_step_1": "输入用户名和密码登录系统。",
        "guide_step_2": "登录后可创建会议或加入已有会议。",
        "guide_step_3": "同一账号仅允许一台设备在线，后登录会将前设备踢下线。",
        "guide_step_4": "主持人离开会议后，会议会进入无主持状态；主持人返回后权限恢复。",
        "guide_step_5": "管理员可查看历史会议记录并删除失效记录。",
        "support_title": "帮助电话",
        "support_phone_label": "技术支持电话",
        "support_email_label": "技术支持邮箱",
        "support_hours_label": "服务时间",
        "support_hours_value": "周一至周日 09:00 - 21:00",
        "close": "关闭",
    },
    "en": {
        "app_name": "Video Meeting System",
        "subtitle": "Bilingual meeting platform | single-device login | admin console",
        "nav_home": "Home",
        "nav_history": "History",
        "nav_admin": "Admin",
        "nav_logout": "Logout",
        "nav_login": "Login",
        "nav_register": "Register",
        "current_user": "Current user",
        "create_room": "Create Meeting",
        "join_room": "Join Meeting",
        "host_name": "Host name",
        "display_name": "Display name",
        "room_id": "Room ID",
        "room_password": "Room password",
        "create_now": "Create now",
        "join_now": "Join now",
        "invite_link": "Invite link",
        "copy": "Copy",
        "copied": "Copied to clipboard",
        "quick_actions": "Quick actions",
        "permissions": "Device & meeting controls",
        "request_media": "Request camera/microphone access",
        "switch_camera": "Switch camera",
        "share_screen": "Share screen",
        "virtual_bg": "Virtual background",
        "blur_bg": "Background blur",
        "recording": "Recording",
        "participants_panel": "Participants panel",
        "layout_switch": "Switch layout",
        "virtual_bg_tip": "Virtual background button is ready as a placeholder for now.",
        "blur_bg_tip": "Background blur button is ready as a placeholder for now.",
        "recording_tip": "Recording button is ready as a placeholder for now.",
        "participants_tip": "Participants panel button is ready as a placeholder for now.",
        "layout_tip": "Layout switch button is ready as a placeholder for now.",
        "mic": "Microphone",
        "camera": "Camera",
        "leave": "Leave meeting",
        "online_count": "Online count",
        "meeting_history": "Meeting history",
        "no_history": "No meeting history yet",
        "rejoin": "Rejoin",
        "login_title": "Login",
        "register_title": "Register",
        "username": "Username",
        "password": "Password",
        "submit_login": "Login",
        "submit_register": "Register",
        "admin_dashboard": "Admin Dashboard",
        "users": "Users",
        "meetings": "Meetings",
        "online_rooms": "Online rooms",
        "status": "Status",
        "enabled": "Enabled",
        "disabled": "Disabled",
        "disable": "Disable",
        "enable": "Enable",
        "end_meeting": "End meeting",
        "language": "Language",
        "lang_zh": "中文",
        "lang_en": "English",
        "permission_ready": "Device access granted",
        "permission_failed": "Failed to obtain device access",
        "kicked": "This account signed in on another device. You have been logged out.",
        "meeting_closed": "The meeting has been ended by admin.",
        "page_not_found": "Page not found",
        "hero_title": "A cleaner meeting experience",
        "hero_desc": "Bilingual interface, admin console, meeting history, single-device login, and a more polished meeting UI.",
        "placeholder_login_hint": "Root admin login supported",
        "device_panel": "Device controls",
        "enter_room": "Enter room",
        "meeting_room": "Meeting room",
        "dashboard_title": "Create and join meetings quickly",
        "dashboard_desc": "The home page now supports meeting creation, joining, invite link copy, and common meeting entry actions.",
        "meeting_actions": "Meeting actions",
        "admin_note": "The default admin account supports root login",
        "system_status": "System status",
        "room_ready": "Room is ready",
        "mic_on": "Microphone: on",
        "mic_off": "Microphone: off",
        "camera_on": "Camera: on",
        "camera_off": "Camera: off",
        "join_failed": "Failed to join meeting",
        "meeting_not_found": "Meeting not found",
        "wrong_password": "Wrong meeting password",
        "room_full": "Room is full",
        "failed": "Operation failed",
        "invalid_login": "Invalid username or password",
        "account_disabled": "Account disabled",
        "username_password_required": "Username and password required",
        "username_exists": "Username already exists",
        "back_home": "Back to home",
        "local_you": "You",
        "created_at": "Created at",
        "ended_at": "Ended at",
        "host": "Host",
        "admin_role": "Admin",
        "yes": "Yes",
        "no": "No",
        "no_online_rooms": "No online rooms",
        "no_meetings": "No meeting records",
        "host_end_meeting": "End meeting",
        "host_only_action": "Only the host can perform this action",
        "meeting_closed_by_host": "The meeting has been ended by the host.",
        "host_left_room": "The host has left the meeting. The room currently has no active host.",
        "host_returned_room": "The host has returned. Host privileges have been restored.",
        "you_left_meeting": "You left the meeting",
        "delete_record": "Delete record",
        "batch_delete": "Batch delete",
        "select_all": "Select all",
        "selected_count": "Selected",
        "history_records": "Meeting history records",
        "active_meetings": "Active meetings",
        "batch_delete_success": "Batch delete completed",
        "no_meeting_selected": "No meeting records selected",
        "joined_meeting": "Joined meeting",
        "created_meeting": "Created meeting",
        "meeting_role": "Relation",
        "meeting_active": "Active",
        "meeting_ended": "Ended",
        "expired_meeting": "This meeting exceeded 90 minutes and was ended automatically.",
        "delete_meeting_success": "Meeting record deleted",
        "meeting_duration_limit": "90-minute meeting limit",
        "enter_active_meeting": "Enter meeting",
        "ended_badge": "Ended",
        "login_help_title": "Login Help",
        "user_guide": "User Guide",
        "support_hotline": "Support",
        "guide_title": "User Guide",
        "guide_step_1": "Enter your username and password to sign in.",
        "guide_step_2": "After login, you can create a meeting or join an existing one.",
        "guide_step_3": "Only one device is allowed per account. A new login will sign out the previous device.",
        "guide_step_4": "If the host leaves, the meeting becomes hostless temporarily. Host privileges return when the host comes back.",
        "guide_step_5": "Admins can review meeting history and delete expired records.",
        "support_title": "Support",
        "support_phone_label": "Support Phone",
        "support_email_label": "Support Email",
        "support_hours_label": "Service Hours",
        "support_hours_value": "Mon-Sun 09:00 - 21:00",
        "close": "Close",
    },
}


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    is_active_user = db.Column(db.Boolean, default=True)
    session_version = db.Column(db.Integer, default=0)

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


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def t(key: str) -> str:
    lang = session.get("lang", "zh")
    return TRANSLATIONS.get(lang, TRANSLATIONS["zh"]).get(key, key)


def tf(lang: str, key: str) -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["zh"]).get(key, key)


def utc_iso(dt):
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@app.context_processor
def inject_globals():
    lang = session.get("lang", "zh")
    return {"t": t, "lang": lang, "supported_langs": ["zh", "en"], "utc_iso": utc_iso}


def ensure_user_columns():
    if not os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(users)")
    cols = {row[1] for row in cur.fetchall()}
    if "is_admin" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
    if "is_active_user" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN is_active_user BOOLEAN DEFAULT 1")
    if "session_version" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN session_version INTEGER DEFAULT 0")
    conn.commit()
    conn.close()


def ensure_admin():
    admin_username = (os.environ.get("ADMIN_USERNAME") or "root").strip() or "root"
    admin_password = (os.environ.get("ADMIN_PASSWORD") or "Huang040726").strip() or "Huang040726"
    user = User.query.filter_by(username=admin_username).first()
    if not user:
        user = User(username=admin_username, is_admin=True, is_active_user=True, session_version=0)
        user.set_password(admin_password)
        db.session.add(user)
    else:
        user.is_admin = True
        user.is_active_user = True
        if not user.password_hash:
            user.set_password(admin_password)
    db.session.commit()


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
    scheme = (os.environ.get("PUBLIC_SCHEME") or request.headers.get("X-Forwarded-Proto") or "https").strip()
    host = (os.environ.get("PUBLIC_HOST") or request.host or "").strip()
    return f"{scheme}://{host}"



def is_meeting_expired(meeting):
    if not meeting or not meeting.created_at:
        return False
    return datetime.utcnow() >= (meeting.created_at + timedelta(seconds=MEETING_DURATION_SECONDS))


def cancel_room_expiry(room_id):
    room = rooms.get(room_id)
    if not room:
        return
    timer = room.get("expiry_timer")
    if timer:
        timer.cancel()
    room["expiry_timer"] = None


def end_meeting_by_room_id(room_id, message_key=None):
    with app.app_context():
        room = rooms.get(room_id)
        meeting = Meeting.query.filter_by(room_id=room_id).first()
        if not meeting:
            cancel_room_expiry(room_id)
            rooms.pop(room_id, None)
            return
        if meeting.status != "ended":
            meeting.status = "ended"
            meeting.ended_at = datetime.utcnow()
            db.session.commit()

        cancel_room_cleanup(room_id)
        cancel_room_expiry(room_id)
        room = rooms.pop(room_id, room)
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
    room = rooms.get(room_id)
    if not room:
        return
    cancel_room_expiry(room_id)
    remaining = max(0, int(created_at_ts + MEETING_DURATION_SECONDS - time.time()))
    timer = threading.Timer(remaining, end_meeting_by_room_id, args=(room_id, "expired_meeting"))
    timer.daemon = True
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


def ensure_runtime_room(meeting):
    room = rooms.get(meeting.room_id)
    if room:
        return room
    room = rooms[meeting.room_id] = {
        "password": meeting.room_password,
        "host_name": meeting.host_name,
        "participants": {},
        "created_at": meeting.created_at.timestamp(),
        "meeting_db_id": meeting.id,
        "host_user_id": meeting.host_user_id,
        "host_present": False,
        "cleanup_timer": None,
        "empty_since": None,
        "expiry_timer": None,
        "lang": session.get("lang", "zh"),
    }
    schedule_room_expiry(meeting.room_id, meeting.created_at.timestamp())
    return room


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
    room = rooms.get(room_id)
    if not room:
        return
    timer = room.get("cleanup_timer")
    if timer:
        timer.cancel()
    room["cleanup_timer"] = None
    room["empty_since"] = None


def finalize_room_if_still_empty(room_id):
    with app.app_context():
        room = rooms.get(room_id)
        if not room:
            return
        if room.get("participants"):
            room["cleanup_timer"] = None
            room["empty_since"] = None
            return

        meeting = Meeting.query.get(room.get("meeting_db_id"))
        if meeting and meeting.status != "ended":
            meeting.status = "ended"
            meeting.ended_at = datetime.utcnow()
            db.session.commit()

        rooms.pop(room_id, None)


def schedule_room_cleanup(room_id, delay=ROOM_EMPTY_GRACE_SECONDS):
    room = rooms.get(room_id)
    if not room:
        return
    cancel_room_cleanup(room_id)
    room["empty_since"] = time.time()
    timer = threading.Timer(delay, finalize_room_if_still_empty, args=(room_id,))
    timer.daemon = True
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
        return
    active_sids = list(user_active_sids.get(user_id, set()))
    for sid in active_sids:
        if exclude_sid and sid == exclude_sid:
            continue
        try:
            socketio.emit("force_logout", {"message": message or t("kicked")}, to=sid)
        except Exception:
            pass
        try:
            socketio.server.disconnect(sid)
        except Exception:
            pass


def bind_user_socket(user_id, sid):
    if not user_id or not sid:
        return
    user_active_sids.setdefault(user_id, set()).add(sid)


def unbind_user_socket(user_id, sid):
    if not user_id or not sid:
        return
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
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()

    if not username or not password:
        return render_template("register.html", error=t("username_password_required"))
    if User.query.filter_by(username=username).first():
        return render_template("register.html", error=t("username_exists"))

    user = User(username=username, is_active_user=True, session_version=0)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    user.session_version = (user.session_version or 0) + 1
    db.session.commit()
    login_user(user)
    session["session_version"] = user.session_version
    disconnect_user_sockets(user.id, message=t("kicked"))
    return redirect(url_for("index"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return render_template("login.html", error=t("invalid_login"))
    if not user.is_active_user:
        return render_template("login.html", error=t("account_disabled"))

    user.session_version = (user.session_version or 0) + 1
    db.session.commit()
    login_user(user)
    session["session_version"] = user.session_version
    disconnect_user_sockets(user.id, message=t("kicked"))
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

    rooms[room_id] = {
        "password": password,
        "host_name": host_name,
        "participants": {},
        "created_at": time.time(),
        "meeting_db_id": meeting.id,
        "host_user_id": meeting.host_user_id,
        "host_present": False,
        "cleanup_timer": None,
        "empty_since": None,
        "expiry_timer": None,
        "lang": session.get("lang", "zh"),
    }
    schedule_room_expiry(room_id, meeting.created_at.timestamp())

    join_url = f"{get_base_url()}/room/{room_id}?pwd={password}"
    return jsonify({"success": True, "room_id": room_id, "password": password, "join_url": join_url})


@app.post("/api/join_room")
@login_required
def api_join_room():
    data = request.get_json(silent=True) or {}
    room_id = (data.get("room_id") or "").strip()
    password = normalize_password(data.get("password") or "")

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
    meeting = Meeting.query.filter_by(room_id=room_id).first()
    if not ensure_meeting_not_expired(meeting):
        abort(404)
    room_password = request.args.get("pwd", meeting.room_password)
    invite_url = f"{get_base_url()}{url_for('room_page', room_id=room_id)}?pwd={quote(room_password)}"
    is_host = current_user.is_authenticated and current_user.id == meeting.host_user_id
    return render_template(
        "room.html",
        room_id=room_id,
        room_password=room_password,
        invite_url=invite_url,
        is_host=is_host,
    )


@app.get("/history")
@login_required
def history():
    meetings = build_history_meetings_for_user(current_user.id)
    return render_template("history.html", meetings=meetings)


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

    command_candidates = [
        [
            ffmpeg_path, "-y", "-fflags", "+genpts", "-i", input_path,
            "-map", "0:v:0", "-map", "0:a?",
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-profile:v", "main", "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
            "-shortest", output_path,
        ],
        [
            ffmpeg_path, "-y", "-fflags", "+genpts", "-i", input_path,
            "-map", "0:v:0", "-map", "0:a?",
            "-c:v", "mpeg4", "-q:v", "5", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
            "-shortest", output_path,
        ],
        [
            ffmpeg_path, "-y", "-fflags", "+genpts", "-i", input_path,
            "-map", "0:v:0",
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-profile:v", "main", "-movflags", "+faststart",
            output_path,
        ],
        [
            ffmpeg_path, "-y", "-fflags", "+genpts", "-i", input_path,
            "-map", "0:v:0",
            "-c:v", "mpeg4", "-q:v", "5", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_path,
        ],
    ]

    errors = []
    for cmd in command_candidates:
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except Exception as exc:
            errors.append(str(exc))
            continue
        if completed.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            break
        err = (completed.stderr or completed.stdout or "ffmpeg failed").strip()
        errors.append(err[-800:])
        try:
            os.remove(output_path)
        except OSError:
            pass
    else:
        shutil.rmtree(workdir, ignore_errors=True)
        return jsonify({"success": False, "message": " | ".join(errors[-3:]) or "ffmpeg failed"}), 500

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


@app.get("/admin")
@login_required
@admin_required
def admin_dashboard():
    for meeting in Meeting.query.filter_by(status="active").all():
        ensure_meeting_not_expired(meeting)
    users = User.query.order_by(User.created_at.desc()).all()
    meetings = Meeting.query.order_by(Meeting.created_at.desc(), Meeting.id.desc()).all()
    active_meetings = [m for m in meetings if m.status == "active"]
    history_meetings = [m for m in meetings if m.status != "active"]
    online_rooms = [
        {"room_id": rid, "participant_count": len(info["participants"]), "host_name": info["host_name"]}
        for rid, info in rooms.items()
    ]
    return render_template(
        "admin.html",
        users=users,
        meetings=meetings,
        active_meetings=active_meetings,
        history_meetings=history_meetings,
        online_rooms=online_rooms,
    )


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
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/user/<int:user_id>/enable")
@login_required
@admin_required
def admin_enable_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active_user = True
    db.session.commit()
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/meeting/<int:meeting_id>/end")
@login_required
@admin_required
def admin_end_meeting(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    end_meeting_by_room_id(meeting.room_id, "meeting_closed")
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
    delete_meeting_record(meeting)
    db.session.commit()
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/meetings/bulk-delete")
@login_required
@admin_required
def admin_bulk_delete_meetings():
    raw_ids = request.form.getlist("meeting_ids")
    meeting_ids = []
    for item in raw_ids:
        try:
            meeting_ids.append(int(item))
        except (TypeError, ValueError):
            continue
    if not meeting_ids:
        return redirect(url_for("admin_dashboard"))

    meetings = Meeting.query.filter(Meeting.id.in_(meeting_ids)).all()
    for meeting in meetings:
        delete_meeting_record(meeting)
    db.session.commit()
    return redirect(url_for("admin_dashboard"))

@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


@app.errorhandler(403)
def forbidden(_):
    return render_template("404.html", error_title="403", error_message="Forbidden"), 403


@socketio.on("join_room")
def on_join_room(data):
    room_id = (data.get("room_id") or "").strip()
    password = normalize_password(data.get("password") or "")
    user_name = (data.get("user_name") or "Guest").strip()[:32] or "Guest"

    meeting = Meeting.query.filter_by(room_id=room_id).first()
    if not ensure_meeting_not_expired(meeting):
        emit("join_error", {"message": t("meeting_not_found")})
        return

    room = ensure_runtime_room(meeting)
    room["lang"] = session.get("lang", "zh")

    if normalize_password(room["password"]) != password:
        emit("join_error", {"message": t("wrong_password")})
        return

    sid = request.sid
    if len(room["participants"]) >= MAX_PARTICIPANTS and sid not in room["participants"]:
        emit("join_error", {"message": f"{t('room_full')} ({MAX_PARTICIPANTS})"})
        return

    if not current_user.is_authenticated:
        emit("join_error", {"message": t("invalid_login")})
        return
    fresh_user = db.session.get(User, current_user.id)
    if not fresh_user or not fresh_user.is_active_user or session.get("session_version") != fresh_user.session_version:
        emit("force_logout", {"message": t("kicked")})
        return

    cancel_room_cleanup(room_id)
    existing = [{"sid": osid, "name": info["name"]} for osid, info in room["participants"].items()]
    room["participants"][sid] = {"name": user_name, "joined_at": time.time()}
    sid_to_user[sid] = {"room_id": room_id, "name": user_name, "user_id": current_user.id}
    bind_user_socket(current_user.id, sid)
    join_room(room_id)

    host_returned = False
    if current_user.is_authenticated and current_user.id == room.get("host_user_id"):
        host_returned = not room.get("host_present")
        room["host_present"] = True

    participant = MeetingParticipant(
        meeting_id=room["meeting_db_id"],
        user_id=current_user.id if current_user.is_authenticated else None,
        display_name=user_name,
        sid=sid,
    )
    db.session.add(participant)
    db.session.commit()

    emit(
        "join_ok",
        {
            "room_id": room_id,
            "participants": existing,
            "self_sid": sid,
            "participant_count": len(room["participants"]),
            "host_present": bool(room.get("host_present")),
        },
    )
    emit(
        "participant_joined",
        {"sid": sid, "name": user_name, "participant_count": len(room["participants"])},
        room=room_id,
        include_self=False,
    )

    if host_returned:
        socketio.emit(
            "host_presence_changed",
            {"host_present": True, "message": t("host_returned_room")},
            room=room_id,
        )


@socketio.on("signal")
def on_signal(data):
    target_sid = data.get("target")
    if target_sid:
        emit("signal", data, to=target_sid)


@socketio.on("room_ui_event")
def on_room_ui_event(data):
    sid = request.sid
    info = sid_to_user.get(sid)
    if not info:
        return
    room_id = info["room_id"]
    payload = data or {}
    payload["from"] = sid
    emit("room_ui_event", payload, room=room_id, include_self=False)


@socketio.on("host_end_meeting")
def on_host_end_meeting(data=None):
    sid = request.sid
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
    sid = request.sid
    info = sid_to_user.pop(sid, None)
    if not info:
        return
    room_id = info["room_id"]
    unbind_user_socket(info.get("user_id"), sid)
    room = rooms.get(room_id)
    leave_room(room_id)
    if room and sid in room["participants"]:
        name = room["participants"][sid]["name"]
        del room["participants"][sid]
        host_left = False
        if current_user.is_authenticated and current_user.id == room.get("host_user_id"):
            if room.get("host_present"):
                host_left = True
            room["host_present"] = False
        participant = MeetingParticipant.query.filter_by(sid=sid).order_by(MeetingParticipant.id.desc()).first()
        if participant and not participant.left_at:
            participant.left_at = datetime.utcnow()
            db.session.commit()
        emit(
            "participant_left",
            {"sid": sid, "name": name, "participant_count": len(room["participants"])},
            room=room_id,
        )
        if host_left:
            socketio.emit(
                "host_presence_changed",
                {"host_present": False, "message": t("host_left_room")},
                room=room_id,
            )
        if not room["participants"]:
            schedule_room_cleanup(room_id)


@socketio.on("disconnect")
def on_disconnect():
    on_leave_room()


with app.app_context():
    db.create_all()
    ensure_user_columns()
    ensure_admin()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False, allow_unsafe_werkzeug=True)
