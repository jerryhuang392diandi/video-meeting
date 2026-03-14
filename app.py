import os
import secrets
import string
import time
from datetime import datetime
from functools import wraps
from urllib.parse import urlencode

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
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

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(16))
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:////opt/video-meeting/instance/app.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# eventlet is more stable for long-lived websocket workloads.
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

MAX_PARTICIPANTS = int(os.environ.get("MAX_PARTICIPANTS", "6"))

# In-memory runtime state
rooms: dict[str, dict] = {}
sid_to_user: dict[str, dict] = {}
user_sids: dict[int, set[str]] = {}


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

    def set_password(self, password: str) -> None:
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
def load_user(user_id: str):
    return User.query.get(int(user_id))


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("login"))
        if not current_user.is_admin:
            abort(403)
        return func(*args, **kwargs)

    return wrapper


def ensure_admin() -> None:
    admin_username = os.environ.get("ADMIN_USERNAME", "root").strip()
    admin_password = os.environ.get("ADMIN_PASSWORD", "").strip()
    if not admin_password:
        return

    admin = User.query.filter_by(username=admin_username).first()
    if not admin:
        admin = User(
            username=admin_username,
            is_admin=True,
            is_active_user=True,
            session_version=0,
        )
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
    if changed:
        db.session.commit()


with app.app_context():
    os.makedirs("/opt/video-meeting/instance", exist_ok=True)
    db.create_all()
    ensure_admin()


def get_public_host() -> str:
    configured = os.environ.get("PUBLIC_HOST", "").strip()
    if configured:
        return configured
    return request.host



def get_base_url() -> str:
    configured_scheme = os.environ.get("PUBLIC_SCHEME", "").strip()
    if configured_scheme:
        scheme = configured_scheme
    else:
        scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
    return f"{scheme}://{get_public_host()}"



def normalize_password(pwd: str) -> str:
    return (pwd or "").strip().upper()



def generate_room_id() -> str:
    while True:
        room_id = "".join(secrets.choice(string.digits) for _ in range(6))
        exists_db = Meeting.query.filter_by(room_id=room_id).first()
        if room_id not in rooms and not exists_db:
            return room_id



def generate_password(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))



def build_join_url(room_id: str, password: str) -> str:
    query = urlencode({"pwd": password})
    return f"{get_base_url()}/room/{room_id}?{query}"



def cleanup_room(room_id: str) -> None:
    room = rooms.get(room_id)
    if room and not room["participants"]:
        meeting_id = room.get("meeting_db_id")
        if meeting_id:
            meeting = Meeting.query.get(meeting_id)
            if meeting and meeting.status != "ended":
                meeting.status = "ended"
                meeting.ended_at = datetime.utcnow()
                db.session.commit()
        rooms.pop(room_id, None)



def force_logout_other_sessions(user: User) -> None:
    existing_sids = list(user_sids.get(user.id, set()))
    for sid in existing_sids:
        socketio.emit(
            "force_logout",
            {"message": "你的账号已在另一台设备登录，当前设备已退出。"},
            to=sid,
        )
        socketio.server.disconnect(sid, namespace="/")



def restore_room_from_db(room_id: str) -> dict | None:
    if room_id in rooms:
        return rooms[room_id]

    meeting = Meeting.query.filter_by(room_id=room_id, status="active").first()
    if not meeting:
        return None

    rooms[room_id] = {
        "password": meeting.room_password,
        "host_name": meeting.host_name,
        "participants": {},
        "created_at": meeting.created_at.timestamp(),
        "meeting_db_id": meeting.id,
    }
    return rooms[room_id]


@app.before_request
def enforce_single_session():
    if not current_user.is_authenticated:
        return None

    db.session.refresh(current_user)

    if not current_user.is_active_user:
        logout_user()
        session.clear()
        flash("账号已被禁用。", "error")
        return redirect(url_for("login"))

    current_version = session.get("session_version")
    if current_version != current_user.session_version:
        logout_user()
        session.clear()
        flash("你的账号已在其他设备登录，当前设备已退出。", "error")
        return redirect(url_for("login"))
    return None


@app.route("/ping")
def ping():
    return "ok"


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()

    if not username or not password:
        return render_template("register.html", error="用户名和密码不能为空")
    if len(username) > 32:
        return render_template("register.html", error="用户名过长")
    if User.query.filter_by(username=username).first():
        return render_template("register.html", error="用户名已存在")

    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    user.session_version = 1
    db.session.commit()
    login_user(user)
    session["session_version"] = user.session_version
    return redirect(url_for("index"))


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

    force_logout_other_sessions(user)

    login_user(user)
    session["session_version"] = user.session_version
    return redirect(url_for("index"))


@app.get("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    flash("已退出登录。", "info")
    return redirect(url_for("login"))


@app.get("/history")
@login_required
def history():
    meetings = (
        Meeting.query.filter_by(host_user_id=current_user.id)
        .order_by(Meeting.created_at.desc())
        .all()
    )
    return render_template("history.html", meetings=meetings, build_join_url=build_join_url)


@app.get("/room/<room_id>")
@login_required
def room_page(room_id):
    room = restore_room_from_db(room_id)
    pwd = request.args.get("pwd", "")
    if not room:
        return (
            render_template(
                "room.html",
                room_id=room_id,
                room_exists=False,
                prefilled_password=pwd,
                invite_url="",
            ),
            404,
        )

    invite_url = build_join_url(room_id, room["password"])
    return render_template(
        "room.html",
        room_id=room_id,
        room_exists=True,
        prefilled_password=pwd,
        invite_url=invite_url,
    )


@app.post("/api/create_room")
@login_required
def api_create_room():
    if not current_user.is_active_user:
        return jsonify({"success": False, "message": "账号不可用"}), 403

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

    join_url = build_join_url(room_id, password)
    return jsonify({
        "success": True,
        "room_id": room_id,
        "password": password,
        "join_url": join_url,
    })


@app.post("/api/join_room")
@login_required
def api_join_room():
    data = request.get_json(silent=True) or {}
    room_id = (data.get("room_id") or "").strip()
    password = normalize_password(data.get("password") or "")

    room = restore_room_from_db(room_id)
    if not room:
        return jsonify({"success": False, "message": "会议不存在"}), 404
    if normalize_password(room["password"]) != password:
        return jsonify({"success": False, "message": "密码错误"}), 403

    return jsonify({"success": True, "message": "验证成功"})


@app.get("/admin")
@login_required
@admin_required
def admin_dashboard():
    users = User.query.order_by(User.created_at.desc()).all()
    meetings = Meeting.query.order_by(Meeting.created_at.desc()).limit(200).all()
    online_user_ids = {uid for uid, sids in user_sids.items() if sids}
    active_rooms = []
    for room_id, room in rooms.items():
        active_rooms.append(
            {
                "room_id": room_id,
                "host_name": room.get("host_name", ""),
                "participant_count": len(room.get("participants", {})),
            }
        )
    return render_template(
        "admin.html",
        users=users,
        meetings=meetings,
        online_user_ids=online_user_ids,
        active_rooms=active_rooms,
    )


@app.post("/admin/user/<int:user_id>/disable")
@login_required
@admin_required
def admin_disable_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash("不能禁用管理员。", "error")
        return redirect(url_for("admin_dashboard"))

    user.is_active_user = False
    user.session_version = (user.session_version or 0) + 1
    db.session.commit()
    force_logout_other_sessions(user)
    flash(f"用户 {user.username} 已禁用。", "info")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/user/<int:user_id>/enable")
@login_required
@admin_required
def admin_enable_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active_user = True
    db.session.commit()
    flash(f"用户 {user.username} 已启用。", "info")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/meeting/<int:meeting_id>/end")
@login_required
@admin_required
def admin_end_meeting(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    meeting.status = "ended"
    meeting.ended_at = datetime.utcnow()
    db.session.commit()

    room = rooms.get(meeting.room_id)
    if room:
        for sid in list(room.get("participants", {}).keys()):
            socketio.emit("force_leave", {"message": "会议已被管理员结束。"}, to=sid)
            socketio.server.disconnect(sid, namespace="/")
        rooms.pop(meeting.room_id, None)

    flash(f"会议 {meeting.room_id} 已结束。", "info")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/meeting/<room_id>/kick/<sid>")
@login_required
@admin_required
def admin_kick_participant(room_id, sid):
    room = rooms.get(room_id)
    if not room or sid not in room.get("participants", {}):
        flash("参会者不存在。", "error")
        return redirect(url_for("admin_dashboard"))

    socketio.emit("force_leave", {"message": "你已被管理员移出会议。"}, to=sid)
    socketio.server.disconnect(sid, namespace="/")
    flash("已移出参会者。", "info")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/meeting/<int:meeting_id>/delete")
@login_required
@admin_required
def admin_delete_meeting(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    if meeting.status == "active":
        room = rooms.get(meeting.room_id)
        if room:
            for sid in list(room.get("participants", {}).keys()):
                socketio.emit("force_leave", {"message": "会议已被管理员删除。"}, to=sid)
                socketio.server.disconnect(sid, namespace="/")
            rooms.pop(meeting.room_id, None)
    MeetingParticipant.query.filter_by(meeting_id=meeting.id).delete()
    db.session.delete(meeting)
    db.session.commit()
    flash("会议记录已删除。", "info")
    return redirect(url_for("admin_dashboard"))


@socketio.on("connect")
def on_connect():
    if current_user.is_authenticated:
        user_sids.setdefault(current_user.id, set()).add(request.sid)


@socketio.on("join_room")
def on_join_room(data):
    if not current_user.is_authenticated:
        emit("join_error", {"message": "请先登录"})
        return
    db.session.refresh(current_user)
    if session.get("session_version") != current_user.session_version:
        emit("force_logout", {"message": "你的账号已在其他设备登录，当前设备已退出。"})
        return

    room_id = (data.get("room_id") or "").strip()
    password = normalize_password(data.get("password") or "")
    user_name = (data.get("user_name") or current_user.username).strip()[:32] or current_user.username

    room = restore_room_from_db(room_id)
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
    if sid in room["participants"]:
        emit("join_ok", {"room_id": room_id, "self_sid": sid})
        return

    existing = [
        {"sid": other_sid, "name": info["name"]}
        for other_sid, info in room["participants"].items()
    ]

    room["participants"][sid] = {
        "name": user_name,
        "joined_at": time.time(),
        "user_id": current_user.id,
    }
    sid_to_user[sid] = {
        "room_id": room_id,
        "name": user_name,
        "user_id": current_user.id,
    }

    participant = MeetingParticipant(
        meeting_id=room.get("meeting_db_id"),
        user_id=current_user.id,
        display_name=user_name,
        sid=sid,
    )
    db.session.add(participant)
    db.session.commit()

    join_room(room_id)

    emit(
        "join_ok",
        {
            "room_id": room_id,
            "participants": existing,
            "self_sid": sid,
            "participant_count": len(room["participants"]),
        },
    )

    emit(
        "participant_joined",
        {
            "sid": sid,
            "name": user_name,
            "participant_count": len(room["participants"]),
        },
        room=room_id,
        include_self=False,
    )


@socketio.on("signal")
def on_signal(data):
    target_sid = data.get("target")
    payload = data.get("payload", {})
    sender_sid = request.sid
    sender = sid_to_user.get(sender_sid, {})
    if not target_sid:
        return
    emit(
        "signal",
        {
            "from": sender_sid,
            "name": sender.get("name", "Unknown"),
            "payload": payload,
        },
        to=target_sid,
    )


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

        emit(
            "participant_left",
            {
                "sid": sid,
                "name": name,
                "participant_count": len(room["participants"]),
            },
            room=room_id,
        )

    cleanup_room(room_id)


@socketio.on("disconnect")
def on_disconnect():
    if current_user.is_authenticated and current_user.id in user_sids:
        user_sids[current_user.id].discard(request.sid)
        if not user_sids[current_user.id]:
            user_sids.pop(current_user.id, None)
    on_leave_room()


if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"

    print("Starting server...")
    print(f"Base URL: {os.environ.get('PUBLIC_SCHEME', 'http')}://{os.environ.get('PUBLIC_HOST', '127.0.0.1')} ")
    socketio.run(app, host=host, port=port, debug=debug)
