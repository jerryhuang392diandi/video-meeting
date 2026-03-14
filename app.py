import os
import secrets
import string
import time
from datetime import datetime

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(16))
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(INSTANCE_DIR, 'app.db')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "请先登录。"

MAX_PARTICIPANTS = 6
rooms = {}         # room_id -> runtime state
sid_to_user = {}   # sid -> {room_id, user_id, name}


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    hosted_meetings = db.relationship("Meeting", backref="host", lazy=True)

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)

    participants = db.relationship("MeetingParticipant", backref="meeting", lazy=True)


class MeetingParticipant(db.Model):
    __tablename__ = "meeting_participants"

    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    display_name = db.Column(db.String(32), nullable=False)
    sid = db.Column(db.String(128), nullable=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    left_at = db.Column(db.DateTime, nullable=True)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


with app.app_context():
    db.create_all()


def get_public_host():
    configured = os.environ.get("PUBLIC_HOST", "").strip()
    if configured:
        return configured
    return request.host


def get_public_scheme():
    configured = os.environ.get("PUBLIC_SCHEME", "").strip()
    if configured:
        return configured
    return request.headers.get("X-Forwarded-Proto", request.scheme)


def get_base_url():
    return f"{get_public_scheme()}://{get_public_host()}"


def build_join_url(room_id: str, password: str) -> str:
    return f"{get_base_url()}/room/{room_id}?pwd={password}"


def generate_room_id():
    while True:
        room_id = "".join(secrets.choice(string.digits) for _ in range(6))
        if not Meeting.query.filter_by(room_id=room_id).first():
            return room_id


def generate_password(length=6):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def normalize_password(pwd: str) -> str:
    return (pwd or "").strip().upper()


def ensure_runtime_room(room_id: str):
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
        "created_at": meeting.created_at.timestamp(),
        "meeting_db_id": meeting.id,
    }
    rooms[room_id] = room
    return room


def cleanup_runtime_room(room_id: str):
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


@app.route("/ping")
def ping():
    return "ok"


@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "GET":
        return render_template("register.html")

    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()

    if len(username) < 2:
        return render_template("register.html", error="用户名至少 2 个字符")
    if len(password) < 6:
        return render_template("register.html", error="密码至少 6 位")
    if User.query.filter_by(username=username).first():
        return render_template("register.html", error="用户名已存在")

    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return redirect(url_for("index"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "GET":
        return render_template("login.html")

    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return render_template("login.html", error="用户名或密码错误")

    login_user(user)
    return redirect(url_for("index"))


@app.get("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/index")
@login_required
def index():
    return render_template("index.html", current_user=current_user)


@app.get("/history")
@login_required
def history():
    hosted = (
        Meeting.query.filter_by(host_user_id=current_user.id)
        .order_by(Meeting.created_at.desc())
        .all()
    )
    joined = (
        db.session.query(Meeting, MeetingParticipant)
        .join(MeetingParticipant, MeetingParticipant.meeting_id == Meeting.id)
        .filter(MeetingParticipant.user_id == current_user.id)
        .order_by(MeetingParticipant.joined_at.desc())
        .all()
    )
    return render_template("history.html", hosted=hosted, joined=joined)


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

    return jsonify({
        "success": True,
        "room_id": room_id,
        "password": password,
        "join_url": build_join_url(room_id, password),
    })


@app.post("/api/join_room")
@login_required
def api_join_room():
    data = request.get_json(silent=True) or {}
    room_id = (data.get("room_id") or "").strip()
    password = normalize_password(data.get("password") or "")

    meeting = Meeting.query.filter_by(room_id=room_id, status="active").first()
    if not meeting:
        return jsonify({"success": False, "message": "会议不存在或已结束"}), 404

    if normalize_password(meeting.room_password) != password:
        return jsonify({"success": False, "message": "密码错误"}), 403

    ensure_runtime_room(room_id)
    return jsonify({"success": True, "message": "验证成功"})


@app.get("/room/<room_id>")
@login_required
def room_page(room_id):
    meeting = Meeting.query.filter_by(room_id=room_id, status="active").first()
    if not meeting:
        return render_template(
            "room.html",
            room_id=room_id,
            room_exists=False,
            prefilled_password="",
            invite_url="",
            current_user=current_user,
        ), 404

    ensure_runtime_room(room_id)
    pwd = request.args.get("pwd", "")
    return render_template(
        "room.html",
        room_id=room_id,
        room_exists=True,
        prefilled_password=pwd,
        invite_url=build_join_url(room_id, meeting.room_password),
        current_user=current_user,
    )


@socketio.on("join_room")
def on_join_room(data):
    room_id = (data.get("room_id") or "").strip()
    password = normalize_password(data.get("password") or "")
    user_name = (data.get("user_name") or current_user.username or "Guest").strip()[:32] or "Guest"

    room = ensure_runtime_room(room_id)
    if not room:
        emit("join_error", {"message": "会议不存在或已结束"})
        return

    if normalize_password(room["password"]) != password:
        emit("join_error", {"message": "密码错误"})
        return

    if len(room["participants"]) >= MAX_PARTICIPANTS:
        emit("join_error", {"message": f"会议人数已满（最多 {MAX_PARTICIPANTS} 人）"})
        return

    sid = request.sid
    if sid in room["participants"]:
        emit("join_ok", {"room_id": room_id, "self_sid": sid, "participant_count": len(room["participants"])})
        return

    existing = [
        {"sid": other_sid, "name": info["name"]}
        for other_sid, info in room["participants"].items()
    ]

    room["participants"][sid] = {"name": user_name, "joined_at": time.time()}
    sid_to_user[sid] = {
        "room_id": room_id,
        "user_id": current_user.id if current_user.is_authenticated else None,
        "name": user_name,
    }

    meeting_id = room.get("meeting_db_id")
    if meeting_id:
        participant = MeetingParticipant(
            meeting_id=meeting_id,
            user_id=current_user.id if current_user.is_authenticated else None,
            display_name=user_name,
            sid=sid,
        )
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
    emit("signal", {
        "from": sender_sid,
        "name": sender.get("name", "Unknown"),
        "payload": payload,
    }, to=target_sid)


@socketio.on("leave_room")
def on_leave_room():
    sid = request.sid
    info = sid_to_user.pop(sid, None)
    if not info:
        return

    room_id = info["room_id"]
    room = rooms.get(room_id)
    if not room:
        return

    leave_room(room_id)

    if sid in room["participants"]:
        name = room["participants"][sid]["name"]
        del room["participants"][sid]

        participant = (
            MeetingParticipant.query.filter_by(sid=sid)
            .order_by(MeetingParticipant.id.desc())
            .first()
        )
        if participant and not participant.left_at:
            participant.left_at = datetime.utcnow()
            db.session.commit()

        emit("participant_left", {
            "sid": sid,
            "name": name,
            "participant_count": len(room["participants"]),
        }, room=room_id)

    cleanup_runtime_room(room_id)


@socketio.on("disconnect")
def on_disconnect():
    on_leave_room()


if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"

    print("Starting server...")
    print(f"HTTP local:   http://127.0.0.1:{port}")
    print("Phone camera/mic needs HTTPS domain in most cases.")
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
