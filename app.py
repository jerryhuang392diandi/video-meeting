import os
import secrets
import sqlite3
import string
import time
from datetime import datetime
from functools import wraps

from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(16))
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:////opt/video-meeting/instance/app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# 明确使用 threading，避免 eventlet / py3.12 兼容问题
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

MAX_PARTICIPANTS = 6
rooms = {}
sid_to_user = {}
user_current_sid = {}


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_active_user = db.Column(db.Boolean, default=True, nullable=False)
    session_version = db.Column(db.Integer, default=0, nullable=False)

    meetings = db.relationship("Meeting", backref="host", lazy=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Meeting(db.Model):
    __tablename__ = "meetings"

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(6), unique=True, nullable=False, index=True)
    room_password = db.Column(db.String(16), nullable=False)
    host_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    host_name = db.Column(db.String(32), nullable=False)
    status = db.Column(db.String(16), default="active", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)

    participants = db.relationship("MeetingParticipant", backref="meeting", lazy=True)


class MeetingParticipant(db.Model):
    __tablename__ = "meeting_participants"

    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id"), nullable=False)
    user_id = db.Column(db.Integer, nullable=True)
    display_name = db.Column(db.String(32), nullable=False)
    sid = db.Column(db.String(128), nullable=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    left_at = db.Column(db.DateTime, nullable=True)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("login"))
        if not current_user.is_admin:
            abort(403)
        return fn(*args, **kwargs)

    return wrapper


def ensure_instance_dir():
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if uri.startswith("sqlite:///"):
        db_path = uri.replace("sqlite:///", "", 1)
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)


def _get_sqlite_path():
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if not uri.startswith("sqlite:///"):
        return None
    return uri.replace("sqlite:///", "", 1)


def ensure_schema_compatibility():
    db_path = _get_sqlite_path()
    if not db_path:
        return

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    def table_exists(name: str) -> bool:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
        return cur.fetchone() is not None

    def add_column_if_missing(table: str, column: str, ddl: str):
        cur.execute(f"PRAGMA table_info({table})")
        existing = {row[1] for row in cur.fetchall()}
        if column not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")

    if table_exists("users"):
        add_column_if_missing("users", "is_admin", "is_admin BOOLEAN NOT NULL DEFAULT 0")
        add_column_if_missing("users", "is_active_user", "is_active_user BOOLEAN NOT NULL DEFAULT 1")
        add_column_if_missing("users", "session_version", "session_version INTEGER NOT NULL DEFAULT 0")

    if table_exists("meetings"):
        add_column_if_missing("meetings", "status", "status VARCHAR(16) NOT NULL DEFAULT 'active'")
        add_column_if_missing("meetings", "ended_at", "ended_at DATETIME")

    if table_exists("meeting_participants"):
        add_column_if_missing("meeting_participants", "user_id", "user_id INTEGER")
        add_column_if_missing("meeting_participants", "sid", "sid VARCHAR(128)")
        add_column_if_missing("meeting_participants", "left_at", "left_at DATETIME")

    conn.commit()
    conn.close()


def ensure_admin_user():
    admin_username = os.environ.get("ADMIN_USERNAME", "root").strip() or "root"
    admin_password = os.environ.get("ADMIN_PASSWORD", "").strip()
    if not admin_password:
        return

    admin = User.query.filter_by(username=admin_username).first()
    if not admin:
        admin = User(username=admin_username, is_admin=True, is_active_user=True, session_version=0)
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        return

    changed = False
    if not admin.is_admin:
        admin.is_admin = True
        changed = True
    if not admin.is_active_user:
        admin.is_active_user = True
        changed = True
    if not admin.check_password(admin_password):
        admin.set_password(admin_password)
        changed = True
    if changed:
        db.session.commit()


def get_public_host():
    configured = os.environ.get("PUBLIC_HOST", "").strip()
    return configured or request.host


def get_base_url():
    configured_scheme = os.environ.get("PUBLIC_SCHEME", "").strip()
    scheme = configured_scheme or request.headers.get("X-Forwarded-Proto", request.scheme)
    return f"{scheme}://{get_public_host()}"


def normalize_password(pwd: str) -> str:
    return (pwd or "").strip().upper()


def generate_room_id() -> str:
    while True:
        room_id = "".join(secrets.choice(string.digits) for _ in range(6))
        if not Meeting.query.filter_by(room_id=room_id).first() and room_id not in rooms:
            return room_id


def generate_password(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def get_or_bootstrap_room(room_id: str):
    room = rooms.get(room_id)
    if room:
        return room
    meeting = Meeting.query.filter_by(room_id=room_id, status="active").first()
    if not meeting:
        return None
    room = {
        "password": meeting.room_password,
        "host_name": meeting.host_name,
        "participants": {},
        "created_at": meeting.created_at.timestamp() if meeting.created_at else time.time(),
        "meeting_db_id": meeting.id,
    }
    rooms[room_id] = room
    return room


def cleanup_room(room_id: str):
    room = rooms.get(room_id)
    if room and not room["participants"]:
        meeting_id = room.get("meeting_db_id")
        if meeting_id:
            meeting = db.session.get(Meeting, meeting_id)
            if meeting and meeting.status != "ended":
                meeting.status = "ended"
                meeting.ended_at = datetime.utcnow()
                db.session.commit()
        rooms.pop(room_id, None)


def kick_user_session(user_id: int, reason: str = "该账号已在其他设备登录"):
    sid = user_current_sid.get(user_id)
    if sid:
        socketio.emit("force_logout", {"message": reason}, to=sid)


@app.before_request
def enforce_single_device_login():
    if not current_user.is_authenticated:
        return

    db.session.expire_all()
    latest_user = db.session.get(User, current_user.id)
    if not latest_user:
        logout_user()
        session.clear()
        return redirect(url_for("login"))

    if not latest_user.is_active_user:
        logout_user()
        session.clear()
        return redirect(url_for("login"))

    if session.get("session_version") != latest_user.session_version:
        logout_user()
        session.clear()
        return redirect(url_for("login", kicked=1))


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/ping")
def ping():
    return "ok"


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()

    if not username or not password:
        return render_template("register.html", error="用户名和密码不能为空")
    if User.query.filter_by(username=username).first():
        return render_template("register.html", error="用户名已存在")

    user = User(username=username, is_admin=False, is_active_user=True, session_version=0)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return redirect(url_for("login", registered=1))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return render_template("login.html", error="用户名或密码错误")
    if not user.is_active_user:
        return render_template("login.html", error="账号已被禁用")

    user.session_version = (user.session_version or 0) + 1
    db.session.commit()

    kick_user_session(user.id)
    login_user(user)
    session["session_version"] = user.session_version
    return redirect(url_for("index"))


@app.get("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("login"))


@app.get("/history")
@login_required
def history():
    meetings = (
        Meeting.query.filter_by(host_user_id=current_user.id)
        .order_by(Meeting.created_at.desc())
        .all()
    )
    return render_template("history.html", meetings=meetings)


@app.get("/admin")
@login_required
@admin_required
def admin_dashboard():
    users = User.query.order_by(User.created_at.desc()).all()
    meetings = Meeting.query.order_by(Meeting.created_at.desc()).all()
    active_rooms = []
    for room_id, info in rooms.items():
        active_rooms.append({
            "room_id": room_id,
            "host_name": info.get("host_name", ""),
            "participant_count": len(info.get("participants", {})),
        })
    return render_template("admin.html", users=users, meetings=meetings, active_rooms=active_rooms)


@app.post("/admin/user/<int:user_id>/disable")
@login_required
@admin_required
def admin_disable_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"success": False, "message": "用户不存在"}), 404
    if user.is_admin:
        return jsonify({"success": False, "message": "不能禁用管理员"}), 400
    user.is_active_user = False
    user.session_version = (user.session_version or 0) + 1
    db.session.commit()
    kick_user_session(user.id, "你的账号已被管理员禁用")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/user/<int:user_id>/enable")
@login_required
@admin_required
def admin_enable_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"success": False, "message": "用户不存在"}), 404
    user.is_active_user = True
    db.session.commit()
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/meeting/<int:meeting_id>/end")
@login_required
@admin_required
def admin_end_meeting(meeting_id):
    meeting = db.session.get(Meeting, meeting_id)
    if not meeting:
        return jsonify({"success": False, "message": "会议不存在"}), 404

    room = rooms.get(meeting.room_id)
    if room:
        for sid in list(room["participants"].keys()):
            socketio.emit("force_leave", {"message": "会议已被管理员结束"}, to=sid)
        rooms.pop(meeting.room_id, None)

    meeting.status = "ended"
    meeting.ended_at = datetime.utcnow()
    db.session.commit()
    return redirect(url_for("admin_dashboard"))


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
    }

    join_url = f"{get_base_url()}/room/{room_id}?pwd={password}"
    return jsonify({"success": True, "room_id": room_id, "password": password, "join_url": join_url})


@app.post("/api/join_room")
@login_required
def api_join_room():
    data = request.get_json(silent=True) or {}
    room_id = (data.get("room_id") or "").strip()
    password = normalize_password(data.get("password") or "")

    room = get_or_bootstrap_room(room_id)
    if not room:
        return jsonify({"success": False, "message": "会议不存在"}), 404
    if normalize_password(room["password"]) != password:
        return jsonify({"success": False, "message": "密码错误"}), 403

    return jsonify({"success": True, "message": "验证成功"})


@app.get("/room/<room_id>")
@login_required
def room_page(room_id):
    room = get_or_bootstrap_room(room_id)
    if not room:
        return render_template("room.html", room_id=room_id, room_exists=False, prefilled_password=""), 404

    pwd = request.args.get("pwd", "")
    return render_template("room.html", room_id=room_id, room_exists=True, prefilled_password=pwd)


@socketio.on("join_room")
def on_join_room(data):
    room_id = (data.get("room_id") or "").strip()
    password = normalize_password(data.get("password") or "")
    user_name = (data.get("user_name") or "Guest").strip()[:32] or "Guest"
    user_id = data.get("user_id")

    room = get_or_bootstrap_room(room_id)
    if not room:
        emit("join_error", {"message": "会议不存在"})
        return
    if normalize_password(room["password"]) != password:
        emit("join_error", {"message": "密码错误"})
        return
    if len(room["participants"]) >= MAX_PARTICIPANTS:
        emit("join_error", {"message": f"会议人数已满（最多 {MAX_PARTICIPANTS} 人）"})
        return

    sid = request.sid
    existing = [{"sid": other_sid, "name": info["name"]} for other_sid, info in room["participants"].items()]

    room["participants"][sid] = {"name": user_name, "joined_at": time.time(), "user_id": user_id}
    sid_to_user[sid] = {"room_id": room_id, "name": user_name, "user_id": user_id}
    if user_id:
        old_sid = user_current_sid.get(user_id)
        user_current_sid[user_id] = sid
        if old_sid and old_sid != sid:
            socketio.emit("force_logout", {"message": "你的账号已在其他设备登录"}, to=old_sid)

    meeting_id = room.get("meeting_db_id")
    if meeting_id:
        participant = MeetingParticipant(meeting_id=meeting_id, user_id=user_id, display_name=user_name, sid=sid)
        db.session.add(participant)
        db.session.commit()

    join_room(room_id)
    emit("join_ok", {
        "room_id": room_id,
        "participants": existing,
        "self_sid": sid,
        "participant_count": len(room["participants"]),
    })
    emit("participant_joined", {
        "sid": sid,
        "name": user_name,
        "participant_count": len(room["participants"]),
    }, room=room_id, include_self=False)


@socketio.on("signal")
def on_signal(data):
    target_sid = data.get("target")
    payload = data.get("payload", {})
    sender_sid = request.sid
    sender = sid_to_user.get(sender_sid, {})
    if not target_sid:
        return
    emit("signal", {"from": sender_sid, "name": sender.get("name", "Unknown"), "payload": payload}, to=target_sid)


@socketio.on("leave_room")
def on_leave_room():
    sid = request.sid
    info = sid_to_user.pop(sid, None)
    if not info:
        return

    room_id = info["room_id"]
    room = rooms.get(room_id)
    leave_room(room_id)

    if room and sid in room["participants"]:
        participant_info = room["participants"].pop(sid)
        name = participant_info["name"]
        participant = MeetingParticipant.query.filter_by(sid=sid).order_by(MeetingParticipant.id.desc()).first()
        if participant and not participant.left_at:
            participant.left_at = datetime.utcnow()
            db.session.commit()
        emit("participant_left", {"sid": sid, "name": name, "participant_count": len(room["participants"])}, room=room_id)
        cleanup_room(room_id)

    user_id = info.get("user_id")
    if user_id and user_current_sid.get(user_id) == sid:
        user_current_sid.pop(user_id, None)


@socketio.on("disconnect")
def on_disconnect():
    on_leave_room()


@app.context_processor
def inject_globals():
    return {"current_user": current_user}


with app.app_context():
    ensure_instance_dir()
    db.create_all()
    ensure_schema_compatibility()
    db.create_all()
    ensure_admin_user()


if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print(f"Starting on http://127.0.0.1:{port}")
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
