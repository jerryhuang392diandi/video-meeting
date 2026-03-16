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
from urllib.parse import quote, urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps

from flask import Flask, abort, after_this_request, jsonify, redirect, render_template, request, send_file, session, url_for

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
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
DB_PATH = os.path.join(INSTANCE_DIR, "app.db")
os.makedirs(INSTANCE_DIR, exist_ok=True)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(16))
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading", max_http_buffer_size=50_000_000)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


def debug_log(tag, **kwargs):
    return None

MAX_PARTICIPANTS = 120
ROOM_EMPTY_GRACE_SECONDS = 20
MEETING_DURATION_SECONDS = 90 * 60
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
ALLOWED_CHAT_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "heic", "heif", "mp4", "webm", "mov", "m4v", "avi", "3gp", "pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "txt", "zip", "rar", "7z"}

TRANSLATIONS = {'zh': {'app_name': '西小电视频会议系统',
        'subtitle': '西小电视频会议平台｜单设备登录｜管理员后台',
        'nav_home': '首页',
        'nav_history': '历史会议',
        'nav_admin': '管理员后台',
        'nav_logout': '退出登录',
        'nav_login': '登录',
        'nav_register': '注册',
        'current_user': '当前用户',
        'create_room': '创建会议',
        'join_room': '加入会议',
        'host_name': '主持人名称',
        'display_name': '显示名称',
        'room_id': '会议号',
        'room_password': '会议密码',
        'create_now': '立即创建',
        'join_now': '立即加入',
        'invite_link': '邀请链接',
        'copy': '复制',
        'copied': '已复制到剪贴板',
        'quick_actions': '快速操作',
        'admin_short': '管理员',
        'turn_relay_short': 'TURN 中继',
        'live_tag': '实时',
        'support_tag': '服务',
        'help_tag': '帮助',
        'host_tag': '主持人',
        'guest_tag': '参会者',
        'single_device_mode': '单设备登录',
        'profile_section': '个人资料',
        'join_defaults': '入会默认偏好',
        'danmaku_display': '弹幕显示',
        'open_account_preferences': '前往个人偏好',
        'quick_switch_room': '快速切换会议',
        'switch_room': '切换会议',
        'chat_short': '聊天',
        'meeting_chat': '会议聊天',
        'meeting_chat_desc': '固定在右侧，可 @ 成员，可切换公开或仅主持人可见',
        'hide': '隐藏',
        'clear': '清空',
        'everyone_visible': '所有人可见',
        'host_only': '仅主持人可见',
        'attachment_permission': '附件权限',
        'chat_input_placeholder': '输入消息，支持文本、表情、图片、视频、文档和压缩包',
        'choose_emoji': '选择表情',
        'close': '收起',
        'media_short': '图片/视频',
        'docs_archive_short': '文档/PPT/压缩包',
        'emoji': '表情',
        'send': '发送',
        'drag_chat_panel': '拖动聊天窗口',
        'participants_label': '参会者',
        'root_admin_console': 'root / 管理员控制台',
        'meeting_mode': '模式',
        'permissions': '设备与会议控制',
        'request_media': '申请摄像头/麦克风权限',
        'switch_camera': '切换摄像头',
        'share_screen': '共享屏幕',
        'virtual_bg': '虚拟背景',
        'blur_bg': '背景虚化',
        'recording': '录制',
        'participants_panel': '参会者面板',
        'layout_switch': '切换布局',
        'virtual_bg_tip': '虚拟背景功能按钮已预留，当前为占位版本。',
        'blur_bg_tip': '背景虚化功能按钮已预留，当前为占位版本。',
        'recording_tip': '录制功能按钮已预留，当前为占位版本。',
        'participants_tip': '参会者面板功能按钮已预留，当前为占位版本。',
        'layout_tip': '布局切换功能按钮已预留，当前为占位版本。',
        'mic': '麦克风',
        'camera': '摄像头',
        'leave': '离开会议',
        'online_count': '在线人数',
        'meeting_history': '历史会议',
        'no_history': '暂无历史会议',
        'rejoin': '重新进入',
        'login_title': '登录',
        'register_title': '注册',
        'username': '用户名',
        'password': '密码',
        'submit_login': '登录',
        'submit_register': '注册',
        'admin_dashboard': '管理员后台',
        'users': '用户列表',
        'meetings': '会议列表',
        'online_rooms': '在线房间',
        'status': '状态',
        'enabled': '启用',
        'disabled': '禁用',
        'disable': '禁用',
        'enable': '启用',
        'end_meeting': '结束会议',
        'language': '语言',
        'lang_zh': '中文',
        'lang_en': '英文',
        'account_preferences': '个人账户与偏好',
        'profile': '基础资料',
        'change_password': '修改密码',
        'region_timezone': '地区 / 时区',
        'translation_default': '翻译默认语言',
        'auto_detect': '自动检测',
        'default_chat_attachment_permission': '聊天附件默认权限',
        'download_allowed': '可下载',
        'view_only': '仅查看',
        'meeting_defaults': '会议默认偏好',
        'show_danmaku_default': '进入会议后默认弹幕显示',
        'stage_rotation_enabled': '共享屏时自动轮换上台',
        'stage_rotation_interval': '轮换上台间隔',
        'stage_rotation_off': '关闭自动轮换',
        'stage_rotation_15': '15 秒',
        'stage_rotation_30': '30 秒',
        'stage_rotation_60': '60 秒',
        'raise_hand': '举手',
        'lower_hand': '放下手',
        'hand_raised': '已举手',
        'single_screen_share_only': '当前会议只允许 1 人共享屏幕，请等待对方结束后再试',
        'enable_camera_on_join': '进入会议时默认开启摄像头',
        'enable_microphone_on_join': '进入会议时默认开启麦克风',
        'on': '开启',
        'off': '关闭',
        'current_password': '当前密码',
        'new_password': '新密码',
        'update_password': '更新密码',
        'manage_account_desc': '管理用户名、会议显示名、地区与文件权限偏好',
        'profile_saved': '保存成功',
        'password_updated': '密码已更新',
        'forgot_password': '找回密码',
        'server_overview': '服务器概览',
        'memory': '内存',
        'disk_usage': '硬盘占用',
        'server_traffic_total': '累计服务器流量',
        'active_rooms': '在线会议',
        'active_sockets': '在线连接',
        'password_reset_requests': '找回密码申请',
        'resolved': '已处理',
        'reject': '拒绝',
        'no_requests': '暂无申请',
        'permission_ready': '设备权限已获取',
        'permission_failed': '设备权限获取失败',
        'kicked': '你的账号已在其他设备登录，当前设备已退出。',
        'meeting_closed': '会议已被管理员结束。',
        'page_not_found': '页面不存在',
        'hero_title': '更清晰的会议入口',
        'hero_desc': '支持中英切换、管理员后台、历史记录、单设备登录，以及更现代化的会议 UI。',
        'placeholder_login_hint': '支持 root 管理员登录',
        'device_panel': '设备控制',
        'enter_room': '进入会议',
        'meeting_room': '会议室',
        'dashboard_title': '快速创建与加入会议',
        'dashboard_desc': '首页支持会议创建、加入、邀请链接复制和常用会议入口。',
        'meeting_actions': '会议操作',
        'admin_note': '管理员账号默认支持 root 登录',
        'system_status': '系统状态',
        'room_ready': '会议室已准备就绪',
        'mic_on': '麦克风：开启',
        'mic_off': '麦克风：关闭',
        'camera_on': '摄像头：开启',
        'camera_off': '摄像头：关闭',
        'join_failed': '加入会议失败',
        'meeting_not_found': '未找到会议',
        'wrong_password': '会议密码错误',
        'room_full': '会议室已满',
        'failed': '操作失败',
        'invalid_login': '用户名或密码错误',
        'account_disabled': '账号已被禁用',
        'username_password_required': '请输入用户名和密码',
        'username_exists': '用户名已存在',
        'back_home': '返回首页',
        'local_you': '你',
        'created_at': '创建时间',
        'ended_at': '结束时间',
        'host': '主持人',
        'admin_role': '管理员',
        'yes': '是',
        'no': '否',
        'no_online_rooms': '暂无在线房间',
        'no_meetings': '暂无会议记录',
        'host_end_meeting': '解散会议',
        'host_only_action': '仅主持人可执行此操作',
        'meeting_closed_by_host': '会议已被主持人解散。',
        'host_left_room': '主持人已离开会议，当前会议暂时没有主持人。',
        'host_returned_room': '主持人已返回会议，主持权限已恢复。',
        'you_left_meeting': '你已离开会议',
        'record_password_label': '会议密码',
        'record_direct_mp4': '浏览器已直接生成 MP4 文件',
        'delete_record': '删除记录',
        'batch_delete': '批量删除',
        'select_all': '全选',
        'selected_count': '已选数量',
        'history_records': '历史会议记录',
        'active_meetings': '进行中会议',
        'batch_delete_success': '批量删除完成',
        'no_meeting_selected': '未选择任何会议记录',
        'joined_meeting': '参与会议',
        'created_meeting': '创建会议',
        'meeting_role': '会议关系',
        'meeting_active': '进行中',
        'meeting_ended': '已结束',
        'expired_meeting': '会议已超过 90 分钟，系统已自动解散。',
        'delete_meeting_success': '会议记录已删除',
        'meeting_duration_limit': '会议时长上限 90 分钟',
        'enter_active_meeting': '进入会议',
        'ended_badge': '已结束',
        'traffic_usage': '流量使用情况',
        'monthly_quota': '月流量额度',
        'used_traffic': '已用流量',
        'remaining_traffic': '剩余流量',
        'reset_cycle': '重置周期',
        'traffic_guide': '用户指南',
        'traffic_guide_desc': '当前采用服务端 TURN relay 口径统计流量，前端只负责展示。',
        'traffic_default_rule': '每个账号默认每 30 天赠送 3GB 流量，自注册日起滚动重置。',
        'traffic_admin_rule': '管理员可在后台调整用户月流量额度，用于充值或特殊授权。',
        'traffic_limit_reached': '你的本期流量额度已用完，请联系管理员。',
        'traffic_management': '流量管理',
        'kick_user': '踢出用户',
        'delete_user': '删除用户',
        'delete_user_confirm': '确认要永久删除用户 {username} 吗？此操作会删除账号及相关记录，且无法恢复。',
        'delete_user_done': '用户已删除',
        'reset_user_password': '重置密码',
        'new_password_admin': '新密码',
        'apply_reset': '应用重置',
        'pending_alerts': '待处理提醒',
        'pending_reset_count': '待处理申请',
        'online_users_count': '在线用户',
        'kick_reason': '原因',
        'kick_reason_default': '管理员已将你移出系统。',
        'kicked_by_admin': '你已被管理员移出系统。',
        'password_reset_done': '密码已重置',
        'processed_requests_cleanup': '清理已处理申请',
        'login_password_unavailable': '系统不保存明文密码，管理员只能重置密码。',
        'set_quota': '设置额度',
        'save': '保存',
        'traffic_cycle_since_register': '自注册日起每 30 天重置',
        'traffic_turn_relay': 'TURN 中继统计',
        'register_date': '注册时间',
        'quota_updated': '流量额度已更新',
        'guide_center': '用户指南与支持',
        'guide_directory': '指南目录',
        'guide_login': '登录',
        'guide_register': '注册',
        'guide_create_meeting': '开启会议',
        'guide_join_meeting': '加入会议',
        'guide_share_screen': '共享屏幕',
        'guide_traffic_rules': '流量规则',
        'guide_support': '客服支持',
        'guide_login_desc': '输入用户名和密码即可登录；如果同一账号在另一台设备登录，当前设备会被自动挤下线。',
        'guide_register_desc': '注册成功后可直接使用默认月流量额度进入系统，管理员可在后台调整配额和权限。',
        'guide_create_meeting_desc': '登录后在首页填写主持人名称并点击“立即创建”，系统会生成会议号、密码和邀请链接。',
        'guide_join_meeting_desc': '输入会议号与会议密码后即可加入会议，建议加入前先确认摄像头和麦克风权限已开启。',
        'guide_share_screen_desc': '进入会议后点击“共享屏幕”即可共享整个屏幕、窗口或浏览器标签页；停止共享后画面会自动恢复。',
        'guide_traffic_rules_desc': '当前采用服务端 TURN relay 口径统计流量，每个账号默认每 30 天赠送 3GB，自注册日起滚动重置。',
        'guide_support_desc': '登录或开会遇到异常时，可联系平台客服获取账号、会议和流量相关支持。',
        'support_title': '客服支持',
        'support_phone': '客服电话',
        'support_hours': '营业时间',
        'support_hours_value': '周一至周日 09:00 - 21:00',
        'support_email': '支持邮箱',
        'support_email_value': 'support@peoplelovesai.xyz',
        'support_phone_value': '+86 400-800-1234',
        'help_page_title': '用户指南',
        'help_page_intro': '这里汇总了登录、注册、创建会议、加入会议、共享屏幕和流量规则等使用说明。',
        'support_page_title': '客服支持',
        'support_page_intro': '如遇登录、会议、配额或设备问题，可通过下方联系方式联系平台客服。',
        'back_to_login': '返回登录页',
        'open_help_center': '用户指南',
        'open_support_center': '客服支持',
        'auth_tagline': '稳定、安全、现代化的视频会议体验',
        'auth_desc_simple': '支持双语界面、管理员后台、单设备登录和 TURN 中继流量统计。',
        'guide_chat_delivery': '聊天与文件投递',
        'guide_chat_delivery_desc': '聊天窗口支持文本、表情、图片、视频、PDF、Word、PPT、Excel '
                                    '和压缩包。发送附件时可设置“仅查看”或“可下载”，适合会议材料分发、作业提交和主持人统一收集文件。',
        'guide_account_region': '账户偏好与地区',
        'guide_account_region_desc': '在“我的账户”中可以设置显示名称、地区/时区、翻译偏好，以及聊天附件默认权限。跨时区会议用户建议提前设置地区，便于本地时间显示。',
        'forgot_password_intro': '提交申请后，管理员或客服会协助你重置密码。',
        'account_recovery': '账户恢复',
        'recover_access_title': '我们会帮你安全找回账户访问权限',
        'recover_access_desc': '填写用户名和可联系到你的方式后，管理员可在后台查看申请并协助重置密码。为提高处理效率，建议补充最近登录时间、常用设备或问题说明。',
        'faster_processing': '更快处理',
        'faster_processing_desc': '留下邮箱或手机号，便于尽快联系你。',
        'easier_verification': '更容易核验',
        'easier_verification_desc': '可补充常用登录设备、上次登录时间或问题描述。',
        'contact_info': '联系方式（邮箱 / 电话）',
        'contact_info_placeholder': '如：name@example.com / 138****8888',
        'note': '补充说明',
        'note_placeholder': '可填写最近登录时间、常用设备、无法登录的原因等',
        'submit_request': '提交申请',
        'attachment_view': '附件查看',
        'attachment_permission_download': '权限：可下载',
        'attachment_permission_view': '权限：仅查看',
        'size': '大小',
        'open_raw_preview': '新窗口查看',
        'download_file': '下载文件',
        'attachment_card_notice': '当前文件类型使用统一文件卡片展示。',
        'attachment_preview_notice': '如果发送者设置为仅查看，且该文件类型不支持浏览器在线预览，则这里不会触发直接下载。',
        'attachment_inline_types': '可在线预览的类型：图片、视频、音频、PDF、文本。'},
 'en': {'app_name': 'Xidian Video Meeting System',
        'subtitle': 'Video Meeting Platform | Single-device Login | Admin Console',
        'nav_home': 'Home',
        'nav_history': 'History',
        'nav_admin': 'Admin',
        'nav_logout': 'Logout',
        'nav_login': 'Login',
        'nav_register': 'Register',
        'current_user': 'Current user',
        'create_room': 'Create Meeting',
        'join_room': 'Join Meeting',
        'host_name': 'Host name',
        'display_name': 'Display name',
        'room_id': 'Room ID',
        'room_password': 'Room password',
        'create_now': 'Create now',
        'join_now': 'Join now',
        'invite_link': 'Invite link',
        'copy': 'Copy',
        'copied': 'Copied to clipboard',
        'quick_actions': 'Quick actions',
        'admin_short': 'Admin',
        'turn_relay_short': 'TURN Relay',
        'live_tag': 'Live',
        'support_tag': 'Support',
        'help_tag': 'Help',
        'host_tag': 'Host',
        'guest_tag': 'Guest',
        'single_device_mode': 'Single-device login',
        'profile_section': 'Profile',
        'join_defaults': 'Join defaults',
        'danmaku_display': 'Danmaku display',
        'open_account_preferences': 'Open account preferences',
        'quick_switch_room': 'Quick switch room',
        'switch_room': 'Switch room',
        'chat_short': 'Chat',
        'meeting_chat': 'Meeting chat',
        'meeting_chat_desc': 'Fixed on the right, supports @mentions and public or host-only chat',
        'hide': 'Hide',
        'clear': 'Clear',
        'everyone_visible': 'Everyone',
        'host_only': 'Host only',
        'attachment_permission': 'Attachment permission',
        'chat_input_placeholder': 'Type a message. Text, emoji, images, videos, documents, and archives are supported.',
        'choose_emoji': 'Choose emoji',
        'close': 'Close',
        'media_short': 'Media',
        'docs_archive_short': 'Docs / PPT / Archive',
        'emoji': 'Emoji',
        'send': 'Send',
        'drag_chat_panel': 'Drag chat panel',
        'participants_label': 'Participants',
        'root_admin_console': 'root / admin console',
        'meeting_mode': 'Mode',
        'permissions': 'Device & meeting controls',
        'request_media': 'Request camera/microphone access',
        'switch_camera': 'Switch camera',
        'share_screen': 'Share screen',
        'virtual_bg': 'Virtual background',
        'blur_bg': 'Background blur',
        'recording': 'Recording',
        'participants_panel': 'Participants panel',
        'layout_switch': 'Switch layout',
        'virtual_bg_tip': 'Virtual background button is ready as a placeholder for now.',
        'blur_bg_tip': 'Background blur button is ready as a placeholder for now.',
        'recording_tip': 'Recording button is ready as a placeholder for now.',
        'participants_tip': 'Participants panel button is ready as a placeholder for now.',
        'layout_tip': 'Layout switch button is ready as a placeholder for now.',
        'mic': 'Microphone',
        'camera': 'Camera',
        'leave': 'Leave meeting',
        'online_count': 'Online count',
        'meeting_history': 'Meeting history',
        'no_history': 'No meeting history yet',
        'rejoin': 'Rejoin',
        'login_title': 'Login',
        'register_title': 'Register',
        'username': 'Username',
        'password': 'Password',
        'submit_login': 'Login',
        'submit_register': 'Register',
        'admin_dashboard': 'Admin Dashboard',
        'users': 'Users',
        'meetings': 'Meetings',
        'online_rooms': 'Online rooms',
        'status': 'Status',
        'enabled': 'Enabled',
        'disabled': 'Disabled',
        'disable': 'Disable',
        'enable': 'Enable',
        'end_meeting': 'End meeting',
        'language': 'Language',
        'lang_zh': 'Chinese',
        'lang_en': 'English',
        'account_preferences': 'Account & Preferences',
        'profile': 'Basic Profile',
        'change_password': 'Change Password',
        'region_timezone': 'Region / Timezone',
        'translation_default': 'Default Translation Language',
        'auto_detect': 'Auto Detect',
        'default_chat_attachment_permission': 'Default Chat Attachment Permission',
        'download_allowed': 'Download Allowed',
        'view_only': 'View Only',
        'meeting_defaults': 'Meeting Defaults',
        'show_danmaku_default': 'Show Danmaku by Default',
        'enable_camera_on_join': 'Enable Camera on Join',
        'enable_microphone_on_join': 'Enable Microphone on Join',
        'on': 'On',
        'off': 'Off',
        'current_password': 'Current Password',
        'new_password': 'New Password',
        'update_password': 'Update Password',
        'manage_account_desc': 'Manage your username, meeting display name, region, and file permission preferences',
        'profile_saved': 'Profile saved',
        'password_updated': 'Password updated',
        'forgot_password': 'Forgot password',
        'server_overview': 'Server Overview',
        'memory': 'Memory',
        'disk_usage': 'Disk Usage',
        'server_traffic_total': 'Total server traffic',
        'active_rooms': 'Active Rooms',
        'active_sockets': 'Active Sockets',
        'password_reset_requests': 'Password Reset Requests',
        'resolved': 'Resolved',
        'reject': 'Reject',
        'no_requests': 'No requests yet',
        'permission_ready': 'Device access granted',
        'permission_failed': 'Failed to obtain device access',
        'kicked': 'This account signed in on another device. You have been logged out.',
        'meeting_closed': 'The meeting has been ended by admin.',
        'page_not_found': 'Page not found',
        'hero_title': 'A cleaner meeting experience',
        'hero_desc': 'Bilingual interface, admin console, meeting history, single-device login, and a more polished '
                     'meeting UI.',
        'placeholder_login_hint': 'Root admin login supported',
        'device_panel': 'Device controls',
        'enter_room': 'Enter room',
        'meeting_room': 'Meeting room',
        'dashboard_title': 'Create and join meetings quickly',
        'dashboard_desc': 'The home page now supports meeting creation, joining, invite link copy, and common meeting '
                          'entry actions.',
        'meeting_actions': 'Meeting actions',
        'admin_note': 'The default admin account supports root login',
        'system_status': 'System status',
        'room_ready': 'Room is ready',
        'mic_on': 'Microphone: on',
        'mic_off': 'Microphone: off',
        'camera_on': 'Camera: on',
        'camera_off': 'Camera: off',
        'join_failed': 'Failed to join meeting',
        'meeting_not_found': 'Meeting not found',
        'wrong_password': 'Wrong meeting password',
        'room_full': 'Room is full',
        'failed': 'Operation failed',
        'invalid_login': 'Invalid username or password',
        'account_disabled': 'Account disabled',
        'username_password_required': 'Username and password required',
        'username_exists': 'Username already exists',
        'back_home': 'Back to home',
        'local_you': 'You',
        'created_at': 'Created at',
        'ended_at': 'Ended at',
        'host': 'Host',
        'admin_role': 'Admin',
        'yes': 'Yes',
        'no': 'No',
        'no_online_rooms': 'No online rooms',
        'no_meetings': 'No meeting records',
        'host_end_meeting': 'End meeting',
        'host_only_action': 'Only the host can perform this action',
        'meeting_closed_by_host': 'The meeting has been ended by the host.',
        'host_left_room': 'The host has left the meeting. The room currently has no active host.',
        'host_returned_room': 'The host has returned. Host privileges have been restored.',
        'you_left_meeting': 'You left the meeting',
        'delete_record': 'Delete record',
        'delete_user': 'Delete user',
        'delete_user_confirm': 'Delete user {username} permanently? This will remove the account and related records and cannot be undone.',
        'delete_user_done': 'User deleted',
        'batch_delete': 'Batch delete',
        'select_all': 'Select all',
        'selected_count': 'Selected',
        'history_records': 'Meeting history records',
        'active_meetings': 'Active meetings',
        'batch_delete_success': 'Batch delete completed',
        'no_meeting_selected': 'No meeting records selected',
        'joined_meeting': 'Joined meeting',
        'created_meeting': 'Created meeting',
        'meeting_role': 'Relation',
        'meeting_active': 'Active',
        'meeting_ended': 'Ended',
        'expired_meeting': 'This meeting exceeded 90 minutes and was ended automatically.',
        'delete_meeting_success': 'Meeting record deleted',
        'meeting_duration_limit': '90-minute meeting limit',
        'enter_active_meeting': 'Enter meeting',
        'ended_badge': 'Ended',
        'traffic_usage': 'Traffic usage',
        'monthly_quota': 'Monthly quota',
        'used_traffic': 'Used traffic',
        'remaining_traffic': 'Remaining traffic',
        'reset_cycle': 'Reset cycle',
        'traffic_guide': 'User Guide',
        'traffic_guide_desc': 'Traffic is counted server-side from TURN relay traffic, and the frontend only displays '
                              'the result.',
        'traffic_default_rule': 'Each account gets 3 GB every 30 days by default, rolling from the registration date.',
        'traffic_admin_rule': "Admins can adjust each user's monthly quota for recharge or special access.",
        'traffic_limit_reached': 'Your traffic quota for this cycle has been used up. Please contact the '
                                 'administrator.',
        'traffic_management': 'Traffic management',
        'set_quota': 'Set quota',
        'save': 'Save',
        'traffic_cycle_since_register': 'Resets every 30 days from registration',
        'traffic_turn_relay': 'TURN Relay Statistics',
        'register_date': 'Register date',
        'quota_updated': 'Traffic quota updated',
        'guide_center': 'Guide & Support',
        'guide_directory': 'Guide directory',
        'guide_login': 'Login',
        'guide_register': 'Register',
        'guide_create_meeting': 'Start meeting',
        'guide_join_meeting': 'Join meeting',
        'guide_share_screen': 'Share screen',
        'guide_traffic_rules': 'Traffic policy',
        'guide_support': 'Support',
        'guide_login_desc': 'Sign in with your username and password. If the same account logs in on another device, '
                            'the current device will be signed out automatically.',
        'guide_register_desc': 'After registration, the account can use the default monthly traffic quota right away. '
                               'Admins can later adjust quota and permissions.',
        'guide_create_meeting_desc': 'After login, fill in the host name on the home page and click Create now. The '
                                     'system will generate a room ID, password, and invite link.',
        'guide_join_meeting_desc': 'Enter the room ID and room password to join. It is recommended to confirm camera '
                                   'and microphone permissions before joining.',
        'guide_share_screen_desc': 'In a meeting, click Share screen to share the full screen, a window, or a browser '
                                   'tab. When sharing stops, the layout returns automatically.',
        'guide_traffic_rules_desc': 'Traffic is counted server-side using the TURN relay path. Each account gets 3 GB '
                                    'every 30 days by default, rolling from the registration date.',
        'guide_support_desc': 'If you run into login or meeting issues, contact platform support for account, meeting, '
                              'and quota assistance.',
        'support_title': 'Support',
        'support_phone': 'Support phone',
        'support_hours': 'Business hours',
        'support_hours_value': 'Mon - Sun 09:00 - 21:00',
        'support_email': 'Support email',
        'support_email_value': 'support@peoplelovesai.xyz',
        'support_phone_value': '+86 400-800-1234',
        'help_page_title': 'User Guide',
        'help_page_intro': 'This page collects instructions for login, registration, starting meetings, joining '
                           'meetings, screen sharing, and traffic policy.',
        'support_page_title': 'Support',
        'support_page_intro': 'For login, meeting, quota, or device issues, contact platform support using the details '
                              'below.',
        'back_to_login': 'Back to login',
        'open_help_center': 'User Guide',
        'open_support_center': 'Support',
        'auth_tagline': 'Stable, secure, and modern video meeting experience',
        'auth_desc_simple': 'Supports a bilingual interface, admin console, single-device login, and TURN relay '
                            'traffic statistics.',
        'guide_chat_delivery': 'Chat and file delivery',
        'guide_chat_delivery_desc': 'The chat panel supports text, emoji, images, videos, PDF, Word, PowerPoint, '
                                    'Excel, and archive files. When sending attachments, you can choose View only or '
                                    'Download allowed for handouts, submissions, and meeting material collection.',
        'guide_account_region': 'Account preferences and region',
        'guide_account_region_desc': 'In My Account, you can set your display name, region/time zone, translation '
                                     'preference, and the default attachment permission for chat. Cross-time-zone '
                                     'users should set their region in advance for local-time displays.',
        'forgot_password_intro': 'Submit a request and the admin or support team can help reset your password.',
        'account_recovery': 'Account Recovery',
        'recover_access_title': 'We will help you recover account access safely',
        'recover_access_desc': 'Fill in your username and a reachable contact method. Admins can review the request in '
                               'the dashboard and help reset your password. Adding your recent login time, device, or '
                               'a short note can speed things up.',
        'faster_processing': 'Faster processing',
        'faster_processing_desc': 'Leave an email or phone number so support can reach you quickly.',
        'easier_verification': 'Easier verification',
        'easier_verification_desc': 'You can add your usual device, last login time, or a short description for '
                                    'verification.',
        'contact_info': 'Contact info (email / phone)',
        'contact_info_placeholder': 'Example: name@example.com / +1 555...',
        'note': 'Note',
        'note_placeholder': 'You can add your recent login time, device, or why you cannot sign in',
        'submit_request': 'Submit request',
        'attachment_view': 'Attachment view',
        'attachment_permission_download': 'Permission: Download allowed',
        'attachment_permission_view': 'Permission: View only',
        'size': 'Size',
        'open_raw_preview': 'Open raw preview',
        'download_file': 'Download file',
        'attachment_card_notice': 'This file type is shown in a standardized file card.',
        'attachment_preview_notice': 'If the sender selected view-only and this file type is not previewable in the '
                                     'browser, this page will not trigger a direct download.',
        'attachment_inline_types': 'Inline preview types: image, video, audio, PDF, and text.',
        'record_password_label': 'Meeting password',
        'record_direct_mp4': 'The browser generated an MP4 file directly'}}


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    is_active_user = db.Column(db.Boolean, default=True)
    session_version = db.Column(db.Integer, default=0)
    monthly_quota_mb = db.Column(db.Float, default=3072.0)
    used_traffic_mb = db.Column(db.Float, default=0.0)
    traffic_cycle_start_at = db.Column(db.DateTime, nullable=True)
    display_name = db.Column(db.String(32), nullable=True)
    region = db.Column(db.String(64), nullable=True, default="Asia/Tokyo")
    preferred_locale = db.Column(db.String(16), nullable=True, default="auto")
    default_attachment_permission = db.Column(db.String(16), nullable=True, default="download")
    default_danmaku_enabled = db.Column(db.Boolean, default=True)
    auto_enable_camera = db.Column(db.Boolean, default=True)
    auto_enable_microphone = db.Column(db.Boolean, default=True)
    stage_rotation_enabled = db.Column(db.Boolean, default=True)
    stage_rotation_seconds = db.Column(db.Integer, default=15)

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


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def t(key: str) -> str:
    lang = session.get("lang", "zh")
    return TRANSLATIONS.get(lang, TRANSLATIONS["zh"]).get(key, key)


def tf(lang: str, key: str) -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["zh"]).get(key, key)


def normalize_stage_rotation_seconds(value, default=15):
    try:
        ivalue = int(value)
    except (TypeError, ValueError):
        ivalue = default
    return ivalue if ivalue in {15, 30, 60} else default





def preferred_display_name(user):
    if not user:
        return "Guest"
    return (getattr(user, "display_name", None) or getattr(user, "username", None) or "Guest").strip()[:32] or "Guest"

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
    if "monthly_quota_mb" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN monthly_quota_mb FLOAT DEFAULT 3072")
    if "used_traffic_mb" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN used_traffic_mb FLOAT DEFAULT 0")
    if "traffic_cycle_start_at" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN traffic_cycle_start_at DATETIME")
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
    if "stage_rotation_enabled" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN stage_rotation_enabled BOOLEAN DEFAULT 1")
    if "stage_rotation_seconds" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN stage_rotation_seconds INTEGER DEFAULT 15")
    cur.execute("CREATE TABLE IF NOT EXISTS password_reset_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, username VARCHAR(64) NOT NULL, contact VARCHAR(128), note TEXT, status VARCHAR(16) DEFAULT 'pending', created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
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


TRAFFIC_RESET_DAYS = 30
_TRAFFIC_MONITOR = {"iface": None, "last_total_bytes": None, "last_ts": None}


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


def get_system_metrics():
    sync_network_traffic()
    iface = _TRAFFIC_MONITOR.get("iface") or detect_traffic_interface()
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
    traffic_total_mb = 0.0
    try:
        if psutil and iface:
            counters = psutil.net_io_counters(pernic=True).get(iface)
            if counters:
                traffic_total_mb = (float(counters.bytes_sent) + float(counters.bytes_recv)) / (1024 * 1024)
    except Exception:
        traffic_total_mb = 0.0
    return {
        "cpu_percent": round(cpu_percent, 1),
        "memory_percent": round(memory_percent, 1),
        "disk_percent": round(disk_percent, 1),
        "disk_used_text": format_mb(disk_used),
        "disk_total_text": format_mb(disk_total),
        "traffic_total_text": format_mb(traffic_total_mb),
        "traffic_total_mb": round(traffic_total_mb, 2),
        "iface": iface or "unknown",
        "active_room_count": len(rooms),
        "active_socket_count": len(sid_to_user),
    }


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


def sync_network_traffic(now_ts=None):
    now_ts = now_ts or time.time()
    if not _TRAFFIC_MONITOR.get("iface"):
        _TRAFFIC_MONITOR["iface"] = detect_traffic_interface()
    iface = _TRAFFIC_MONITOR.get("iface")
    total_bytes = read_interface_total_bytes(iface)
    if total_bytes is None:
        return
    last_total = _TRAFFIC_MONITOR.get("last_total_bytes")
    _TRAFFIC_MONITOR["last_total_bytes"] = total_bytes
    _TRAFFIC_MONITOR["last_ts"] = now_ts
    if last_total is None or total_bytes < last_total:
        return
    delta_bytes = total_bytes - last_total
    if delta_bytes <= 0:
        return

    active_user_ids = []
    seen = set()
    for room in rooms.values():
        for info in room.get("participants", {}).values():
            user_id = info.get("user_id")
            if user_id and user_id not in seen:
                seen.add(user_id)
                active_user_ids.append(user_id)

    if not active_user_ids:
        return

    share_mb = delta_bytes / (1024 * 1024) / max(1, len(active_user_ids))
    if share_mb <= 0:
        return

    users = User.query.filter(User.id.in_(active_user_ids)).all()
    changed = False
    exceeded_ids = []
    for user in users:
        refresh_user_traffic_cycle(user)
        user.used_traffic_mb = float(user.used_traffic_mb or 0.0) + share_mb
        changed = True
        if user_quota_exceeded(user):
            exceeded_ids.append(user.id)
    if changed:
        db.session.commit()
    for user_id in exceeded_ids:
        disconnect_user_sockets(user_id, message=TRANSLATIONS["zh"].get("traffic_limit_reached", "Traffic quota exceeded"))


def sync_user_traffic(user_id=None):
    sync_network_traffic()
    if user_id:
        user = db.session.get(User, user_id)
        if user and refresh_user_traffic_cycle(user):
            db.session.commit()


def traffic_summary_dict(user):
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
        "traffic_interface": _TRAFFIC_MONITOR.get("iface") or detect_traffic_interface() or "unknown",
    }


def build_turn_ice_servers():
    urls_raw = (os.environ.get("TURN_URLS") or "").strip()
    username = (os.environ.get("TURN_USERNAME") or "").strip()
    credential = (os.environ.get("TURN_PASSWORD") or "").strip()
    if urls_raw and username and credential:
        urls = [item.strip() for item in urls_raw.split(",") if item.strip()]
    else:
        public_host = (os.environ.get("TURN_PUBLIC_HOST") or os.environ.get("PUBLIC_HOST") or request.host.split(":")[0]).strip()
        urls = [f"turn:{public_host}:3478?transport=udp", f"turn:{public_host}:3478?transport=tcp"]
        username = username or (os.environ.get("TURN_USERNAME") or "turnuser").strip() or "turnuser"
        credential = credential or (os.environ.get("TURN_PASSWORD") or "turnpassword123").strip() or "turnpassword123"
    return [{"urls": urls, "username": username, "credential": credential}]



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
        sync_network_traffic()
        meeting = Meeting.query.filter_by(room_id=room_id).first()
        if not meeting:
            cancel_room_expiry(room_id)
            shutil.rmtree(os.path.join(CHAT_UPLOAD_DIR, room_id), ignore_errors=True)
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
        "traffic_last_sync": time.time(),
        "danmaku_enabled": False,
        "chat_history": [],
        "chat_clear_markers": {},
        "current_sharer_sid": None,
        "raised_hands": {},
        "stage_rotation_enabled": bool(getattr(meeting.host, "stage_rotation_enabled", True)) if getattr(meeting, "host", None) else True,
        "stage_rotation_seconds": normalize_stage_rotation_seconds(getattr(meeting.host, "stage_rotation_seconds", 15) if getattr(meeting, "host", None) else 15),
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

        shutil.rmtree(os.path.join(CHAT_UPLOAD_DIR, room_id), ignore_errors=True)
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
        debug_log('SOCKET_KICK_SKIP', reason='empty_user_id', exclude_sid=exclude_sid)
        return
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
    debug_log('RUNTIME_REMOVE_BEGIN', user_id=user_id, room_ids=list(rooms.keys()), reason_message=reason_message)
    found_any = False
    for room_id, room in list(rooms.items()):
        participant_sids = [sid for sid, info in list(room.get("participants", {}).items()) if info.get("user_id") == user_id]
        if not participant_sids:
            continue
        found_any = True
        debug_log('RUNTIME_REMOVE_ROOM_MATCH', user_id=user_id, room_id=room_id, participant_sids=participant_sids, participant_count_before=len(room.get('participants', {})))
        for sid in participant_sids:
            participant_info = room.get("participants", {}).pop(sid, None)
            debug_log('RUNTIME_REMOVE_POP', user_id=user_id, room_id=room_id, sid=sid, participant_info=participant_info)
            if sid_to_user.get(sid):
                sid_to_user.pop(sid, None)
                debug_log('RUNTIME_REMOVE_SID_UNMAP', user_id=user_id, room_id=room_id, sid=sid)
            unbind_user_socket(user_id, sid)
            try:
                socketio.server.leave_room(sid, room_id, namespace='/')
                debug_log('RUNTIME_REMOVE_LEAVE_ROOM', user_id=user_id, room_id=room_id, sid=sid)
            except Exception as exc:
                debug_log('RUNTIME_REMOVE_LEAVE_ROOM_ERROR', user_id=user_id, room_id=room_id, sid=sid, error=str(exc))
            participant = MeetingParticipant.query.filter_by(sid=sid).order_by(MeetingParticipant.id.desc()).first()
            if participant and not participant.left_at:
                participant.left_at = datetime.utcnow()
                debug_log('RUNTIME_REMOVE_PARTICIPANT_MARK_LEFT', user_id=user_id, room_id=room_id, sid=sid, participant_db_id=participant.id)
            if participant_info:
                socketio.emit(
                    "participant_left",
                    {
                        "sid": sid,
                        "name": participant_info.get("name") or "Guest",
                        "participant_count": len(room.get("participants", {})),
                    },
                    room=room_id,
                )
                broadcast_room_participant_snapshot(room_id)
                debug_log('RUNTIME_REMOVE_BROADCAST', user_id=user_id, room_id=room_id, sid=sid, participant_count_after=len(room.get('participants', {})))
        if user_id == room.get("host_user_id") and room.get("host_present"):
            room["host_present"] = False
            socketio.emit(
                "host_presence_changed",
                {"host_present": False, "message": reason_message or t("host_left_room")},
                room=room_id,
            )
            debug_log('RUNTIME_REMOVE_HOST_LEFT', user_id=user_id, room_id=room_id)
        if not room.get("participants"):
            schedule_room_cleanup(room_id)
            debug_log('RUNTIME_REMOVE_SCHEDULE_CLEANUP', user_id=user_id, room_id=room_id)
    if not found_any:
        debug_log('RUNTIME_REMOVE_NOT_FOUND', user_id=user_id, room_ids=list(rooms.keys()))
    db.session.commit()
    debug_log('RUNTIME_REMOVE_DONE', user_id=user_id, active_socket_count=len(sid_to_user), online_user_count=online_user_count())




def broadcast_room_participant_snapshot(room_id):
    room = rooms.get(room_id)
    if not room:
        return
    payload = {
        "participants": [
            {"sid": sid, "name": info.get("name") or "Guest", "raised_hand": bool((room.get("raised_hands") or {}).get(sid))}
            for sid, info in room.get("participants", {}).items()
        ],
        "participant_count": len(room.get("participants", {})),
        "current_sharer_sid": room.get("current_sharer_sid"),
        "stage_rotation_enabled": bool(room.get("stage_rotation_enabled", True)),
        "stage_rotation_seconds": normalize_stage_rotation_seconds(room.get("stage_rotation_seconds", 15), 15),
    }
    debug_log('PARTICIPANT_SNAPSHOT', room_id=room_id, payload=payload)
    socketio.emit("participant_snapshot", payload, room=room_id)


def online_user_count():
    return sum(1 for _, sids in user_active_sids.items() if sids)


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


def prune_duplicate_room_sockets(room_id, user_id, keep_sid=None):
    if not room_id or not user_id:
        return []
    room = rooms.get(room_id)
    if not room:
        return []
    removed = []
    for stale_sid, participant_info in list(room.get("participants", {}).items()):
        if stale_sid == keep_sid:
            continue
        if participant_info.get("user_id") != user_id:
            continue
        removed.append({
            "sid": stale_sid,
            "name": participant_info.get("name") or "Guest",
        })
        room["participants"].pop(stale_sid, None)
        sid_to_user.pop(stale_sid, None)
        unbind_user_socket(user_id, stale_sid)
        try:
            socketio.server.leave_room(stale_sid, room_id, namespace='/')
        except Exception as exc:
            debug_log('SOCKET_DUPLICATE_LEAVE_ROOM_ERROR', room_id=room_id, user_id=user_id, sid=stale_sid, error=str(exc))
        participant = MeetingParticipant.query.filter_by(sid=stale_sid).order_by(MeetingParticipant.id.desc()).first()
        if participant and not participant.left_at:
            participant.left_at = datetime.utcnow()
        try:
            socketio.server.disconnect(stale_sid, namespace='/')
        except Exception as exc:
            debug_log('SOCKET_DUPLICATE_DISCONNECT_ERROR', room_id=room_id, user_id=user_id, sid=stale_sid, error=str(exc))
    if removed:
        debug_log('SOCKET_DUPLICATE_PRUNED', room_id=room_id, user_id=user_id, keep_sid=keep_sid, removed=removed, remaining_participants=list(room.get("participants", {}).keys()))
    return removed



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
    sync_user_traffic(current_user.id)
    db.session.refresh(current_user)
    return render_template("index.html", traffic=traffic_summary_dict(current_user), preferred_display_name=preferred_display_name(current_user))


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
            stage_rotation_enabled = bool_from_form(request.form.get("stage_rotation_enabled"), True)
            stage_rotation_seconds = normalize_stage_rotation_seconds(request.form.get("stage_rotation_seconds"), 15)
            if preferred_locale not in {"auto", "zh", "en"}:
                preferred_locale = "auto"
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
                    fresh_user.stage_rotation_enabled = stage_rotation_enabled
                    fresh_user.stage_rotation_seconds = stage_rotation_seconds
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
    return render_template(
        "account.html",
        user=fresh_user,
        message=message,
        error=error,
        preferred_display_name=preferred_display_name(fresh_user),
        region=(fresh_user.region or "Asia/Tokyo"),
        preferred_locale=(fresh_user.preferred_locale or "auto"),
        default_attachment_permission=(fresh_user.default_attachment_permission or "download"),
        default_danmaku_enabled=bool(getattr(fresh_user, "default_danmaku_enabled", True)),
        auto_enable_camera=bool(getattr(fresh_user, "auto_enable_camera", True)),
        auto_enable_microphone=bool(getattr(fresh_user, "auto_enable_microphone", True)),
        stage_rotation_enabled=bool(getattr(fresh_user, "stage_rotation_enabled", True)),
        stage_rotation_seconds=normalize_stage_rotation_seconds(getattr(fresh_user, "stage_rotation_seconds", 15), 15),
    )


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password_page():
    message = None
    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()[:64]
        contact = (request.form.get("contact") or "").strip()[:128]
        note = (request.form.get("note") or "").strip()[:500]
        if not username:
            error = t("username_password_required")
        else:
            req = PasswordResetRequest(username=username, contact=contact, note=note, status="pending")
            db.session.add(req)
            db.session.commit()
            message = "找回密码申请已提交，请等待管理员联系。" if session.get("lang", "zh") == "zh" else "Password reset request submitted. Please wait for admin support."
    return render_template("forgot_password.html", message=message, error=error)


@app.route("/help")
def help_page():
    return render_template("help.html")


@app.route("/support")
def support_page():
    return render_template("support.html")


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

    user = User(username=username, display_name=username, is_active_user=True, session_version=0, monthly_quota_mb=3072.0, used_traffic_mb=0.0, traffic_cycle_start_at=datetime.utcnow())
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
    sync_user_traffic(current_user.id)
    db.session.refresh(current_user)
    if user_quota_exceeded(current_user):
        return jsonify({"success": False, "message": t("traffic_limit_reached")}), 403
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
        "traffic_last_sync": time.time(),
        "danmaku_enabled": False,
        "chat_history": [],
        "chat_clear_markers": {},
        "current_sharer_sid": None,
        "raised_hands": {},
        "stage_rotation_enabled": bool(getattr(meeting.host, "stage_rotation_enabled", True)) if getattr(meeting, "host", None) else True,
        "stage_rotation_seconds": normalize_stage_rotation_seconds(getattr(meeting.host, "stage_rotation_seconds", 15) if getattr(meeting, "host", None) else 15),
    }
    schedule_room_expiry(room_id, meeting.created_at.timestamp())

    join_url = f"{get_base_url()}/room/{room_id}?pwd={password}"
    return jsonify({"success": True, "room_id": room_id, "password": password, "join_url": join_url})


@app.post("/api/join_room")
@login_required
def api_join_room():
    sync_user_traffic(current_user.id)
    db.session.refresh(current_user)
    if user_quota_exceeded(current_user):
        return jsonify({"success": False, "message": t("traffic_limit_reached")}), 403
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
    sync_user_traffic(current_user.id)
    db.session.refresh(current_user)
    return render_template(
        "room.html",
        room_id=room_id,
        room_password=room_password,
        invite_url=invite_url,
        is_host=is_host,
        traffic=traffic_summary_dict(current_user),
        turn_ice_servers=build_turn_ice_servers(),
        preferred_display_name=preferred_display_name(current_user),
        default_danmaku_enabled=bool(getattr(current_user, "default_danmaku_enabled", True)),
        auto_enable_camera=bool(getattr(current_user, "auto_enable_camera", True)),
        auto_enable_microphone=bool(getattr(current_user, "auto_enable_microphone", True)),
        stage_rotation_enabled=bool(getattr(current_user, "stage_rotation_enabled", True)),
        stage_rotation_seconds=normalize_stage_rotation_seconds(getattr(current_user, "stage_rotation_seconds", 15), 15),
    )


@app.get("/api/traffic_summary")
@login_required
def api_traffic_summary():
    sync_user_traffic(current_user.id)
    db.session.refresh(current_user)
    if user_quota_exceeded(current_user):
        disconnect_user_sockets(current_user.id, message=t("traffic_limit_reached"))
    return jsonify({"success": True, **traffic_summary_dict(current_user)})


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


@app.get("/api/admin/system_stats")
@login_required
@admin_required
def api_admin_system_stats():
    payload = {"success": True, **get_system_metrics()}
    debug_log('ADMIN_STATS_API', payload=payload, rooms={rid: len(info.get('participants', {})) for rid, info in rooms.items()}, user_active_sids={uid: list(sids) for uid, sids in user_active_sids.items() if sids})
    return jsonify(payload)



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
    debug_log('ADMIN_DASHBOARD_ENTER', rooms={rid: {'participants': list(info.get('participants', {}).keys()), 'host_user_id': info.get('host_user_id'), 'host_present': info.get('host_present')} for rid, info in rooms.items()}, user_active_sids={uid: list(sids) for uid, sids in user_active_sids.items() if sids}, sid_to_user=dict(sid_to_user))
    sync_network_traffic()
    for meeting in Meeting.query.filter_by(status="active").all():
        ensure_meeting_not_expired(meeting)
    users = User.query.order_by(User.created_at.desc()).all()
    for user in users:
        refresh_user_traffic_cycle(user)
    db.session.commit()
    meetings = Meeting.query.order_by(Meeting.created_at.desc(), Meeting.id.desc()).all()
    active_meetings = [m for m in meetings if m.status == "active"]
    history_meetings = [m for m in meetings if m.status != "active"]
    reset_requests = PasswordResetRequest.query.order_by(PasswordResetRequest.created_at.desc()).limit(30).all()
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
        traffic_summaries={u.id: traffic_summary_dict(u) for u in users},
        reset_requests=reset_requests,
        system_stats=get_system_metrics(),
    )


@app.post("/admin/user/<int:user_id>/quota")
@login_required
@admin_required
def admin_set_user_quota(user_id):
    user = User.query.get_or_404(user_id)
    try:
        quota_gb = float((request.form.get("monthly_quota_gb") or "0").strip())
    except ValueError:
        return redirect(url_for("admin_dashboard"))
    quota_gb = max(0.0, quota_gb)
    sync_user_traffic(user.id)
    user.monthly_quota_mb = round(quota_gb * 1024.0, 2)
    db.session.commit()
    if user_quota_exceeded(user):
        disconnect_user_sockets(user.id, message=t("traffic_limit_reached"))
    return redirect(url_for("admin_dashboard"))



@app.post("/admin/user/<int:user_id>/kick")
@login_required
@admin_required
def admin_kick_user(user_id):
    user = User.query.get_or_404(user_id)
    debug_log('ADMIN_KICK_ENTER', requested_user_id=user_id, found_user_id=user.id if user else None, username=user.username if user else None, is_admin=user.is_admin if user else None, user_active_sids=list(user_active_sids.get(user_id, set())), rooms={rid: {'participant_user_ids': [info.get('user_id') for info in info_map.get('participants', {}).values()], 'participant_sids': list(info_map.get('participants', {}).keys())} for rid, info_map in rooms.items()})
    if user.is_admin:
        debug_log('ADMIN_KICK_ABORT', requested_user_id=user_id, reason='target_is_admin')
        return redirect(url_for("admin_dashboard"))
    kick_message = t("kicked_by_admin")
    user.session_version = (user.session_version or 0) + 1
    db.session.commit()
    debug_log('ADMIN_KICK_SESSION_VERSION_BUMP', user_id=user.id, session_version=user.session_version)
    remove_user_from_runtime_rooms(user.id, reason_message=kick_message)
    disconnect_user_sockets(user.id, message=kick_message)
    debug_log('ADMIN_KICK_DONE', user_id=user.id, remaining_sids=list(user_active_sids.get(user.id, set())), rooms={rid: {'participant_user_ids': [info.get('user_id') for info in info_map.get('participants', {}).values()], 'participant_sids': list(info_map.get('participants', {}).keys())} for rid, info_map in rooms.items()})
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
    PasswordResetRequest.query.filter_by(username=username).delete(synchronize_session=False)
    db.session.delete(user)
    db.session.commit()
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
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/reset-requests/cleanup")
@login_required
@admin_required
def admin_cleanup_reset_requests():
    PasswordResetRequest.query.filter(PasswordResetRequest.status != "pending").delete(synchronize_session=False)
    db.session.commit()
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

@app.post("/admin/reset-request/<int:request_id>/<status>")
@login_required
@admin_required
def admin_update_reset_request(request_id, status):
    reset_request = PasswordResetRequest.query.get_or_404(request_id)
    if status not in {"pending", "resolved", "rejected"}:
        status = "pending"
    reset_request.status = status
    db.session.commit()
    return redirect(url_for("admin_dashboard"))


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


@app.errorhandler(403)
def forbidden(_):
    return render_template("404.html", error_title="403", error_message="Forbidden"), 403


@socketio.on("connect")
def on_socket_connect():
    debug_log('SOCKET_CONNECT', sid=request.sid, authenticated=getattr(current_user, "is_authenticated", False), current_user_id=getattr(current_user, "id", None), session_version=session.get('session_version'))


@socketio.on("join_room")
def on_join_room(data):
    debug_log('SOCKET_JOIN_ROOM_BEGIN', sid=request.sid, current_user_id=getattr(current_user, "id", None), authenticated=getattr(current_user, "is_authenticated", False), session_version=session.get('session_version'), data=data)
    room_id = (data.get("room_id") or "").strip()
    password = normalize_password(data.get("password") or "")
    user_name = (data.get("user_name") or preferred_display_name(current_user)).strip()[:32] or preferred_display_name(current_user)

    meeting = Meeting.query.filter_by(room_id=room_id).first()
    if not ensure_meeting_not_expired(meeting):
        debug_log('SOCKET_JOIN_ROOM_MEETING_MISSING', sid=request.sid, room_id=room_id)
        emit("join_error", {"message": t("meeting_not_found")})
        return

    room = ensure_runtime_room(meeting)
    room["lang"] = session.get("lang", "zh")

    if normalize_password(room["password"]) != password:
        debug_log('SOCKET_JOIN_ROOM_BAD_PASSWORD', sid=request.sid, room_id=room_id)
        emit("join_error", {"message": t("wrong_password")})
        return

    sid = request.sid
    if len(room["participants"]) >= MAX_PARTICIPANTS and sid not in room["participants"]:
        debug_log('SOCKET_JOIN_ROOM_FULL', sid=sid, room_id=room_id, participants=list(room['participants'].keys()))
        emit("join_error", {"message": f"{t('room_full')} ({MAX_PARTICIPANTS})"})
        return

    if not current_user.is_authenticated:
        debug_log('SOCKET_JOIN_ROOM_NOT_AUTH', sid=sid, room_id=room_id)
        emit("join_error", {"message": t("invalid_login")})
        return
    fresh_user = db.session.get(User, current_user.id)
    if not fresh_user or not fresh_user.is_active_user or session.get("session_version") != fresh_user.session_version:
        debug_log('SOCKET_JOIN_ROOM_SESSION_INVALID', sid=sid, room_id=room_id, fresh_user_id=getattr(fresh_user, "id", None), fresh_session_version=getattr(fresh_user, "session_version", None), browser_session_version=session.get("session_version"))
        emit("force_logout", {"message": t("kicked")})
        return
    sync_network_traffic()
    db.session.refresh(fresh_user)
    if user_quota_exceeded(fresh_user):
        debug_log('SOCKET_JOIN_ROOM_TRAFFIC_DENY', sid=sid, room_id=room_id, user_id=fresh_user.id)
        emit("join_error", {"message": t("traffic_limit_reached")})
        return

    cancel_room_cleanup(room_id)
    existing = [{"sid": osid, "name": info["name"]} for osid, info in room["participants"].items() if info.get("user_id") != current_user.id]
    room["participants"][sid] = {"name": user_name, "joined_at": time.time(), "user_id": current_user.id}
    sid_to_user[sid] = {"room_id": room_id, "name": user_name, "user_id": current_user.id}
    bind_user_socket(current_user.id, sid)
    join_room(room_id)
    pruned_duplicates = prune_duplicate_room_sockets(room_id, current_user.id, keep_sid=sid)
    debug_log('SOCKET_JOIN_ROOM_REGISTERED', sid=sid, room_id=room_id, user_id=current_user.id, pruned_duplicates=pruned_duplicates, room_participants=list(room['participants'].keys()), user_active_sids={uid: list(sids) for uid, sids in user_active_sids.items() if sids}, sid_to_user_entry=sid_to_user.get(sid))

    host_returned = False
    danmaku_auto_enabled_by_host = False
    if current_user.is_authenticated and current_user.id == room.get("host_user_id"):
        host_returned = not room.get("host_present")
        room["host_present"] = True
        if bool(getattr(fresh_user, "default_danmaku_enabled", True)) and not bool(room.get("danmaku_enabled")):
            room["danmaku_enabled"] = True
            danmaku_auto_enabled_by_host = True
        room["stage_rotation_enabled"] = bool(getattr(fresh_user, "stage_rotation_enabled", True))
        room["stage_rotation_seconds"] = normalize_stage_rotation_seconds(getattr(fresh_user, "stage_rotation_seconds", 15), 15)

    participant = MeetingParticipant(
        meeting_id=room["meeting_db_id"],
        user_id=current_user.id if current_user.is_authenticated else None,
        display_name=user_name,
        sid=sid,
    )
    db.session.add(participant)
    db.session.commit()

    is_room_host = bool(current_user.is_authenticated and current_user.id == room.get("host_user_id"))
    visible_chat_history = visible_chat_history_for_user(room, current_user.id, sid, is_room_host=is_room_host)

    debug_log('SOCKET_JOIN_ROOM_OK', sid=sid, room_id=room_id, participant_count=len(room["participants"]), host_present=bool(room.get("host_present")))
    emit(
        "join_ok",
        {
            "room_id": room_id,
            "participants": existing,
            "self_sid": sid,
            "participant_count": len(room["participants"]),
            "host_present": bool(room.get("host_present")),
            "danmaku_enabled": bool(room.get("danmaku_enabled")),
            "chat_history": visible_chat_history,
            "current_sharer_sid": room.get("current_sharer_sid"),
            "raised_hands": [hand_sid for hand_sid, raised in (room.get("raised_hands") or {}).items() if raised],
            "stage_rotation_enabled": bool(room.get("stage_rotation_enabled", True)),
            "stage_rotation_seconds": normalize_stage_rotation_seconds(room.get("stage_rotation_seconds", 15), 15),
        },
    )
    emit(
        "participant_joined",
        {"sid": sid, "name": user_name, "participant_count": len(room["participants"])},
        room=room_id,
        include_self=False,
    )
    for removed in pruned_duplicates:
        socketio.emit(
            "participant_left",
            {"sid": removed["sid"], "name": removed["name"], "participant_count": len(room["participants"])},
            room=room_id,
        )
    broadcast_room_participant_snapshot(room_id)

    if host_returned:
        socketio.emit(
            "host_presence_changed",
            {"host_present": True, "message": t("host_returned_room")},
            room=room_id,
        )
    if danmaku_auto_enabled_by_host:
        socketio.emit("room_ui_event", {"type": "danmaku_toggled", "enabled": True, "from": sid}, room=room_id)


@socketio.on("update_profile")
def on_update_profile(data):
    sid = request.sid
    info = sid_to_user.get(sid)
    if not info:
        return
    room_id = info["room_id"]
    room = rooms.get(room_id)
    if not room or sid not in room.get("participants", {}):
        return
    new_name = ((data or {}).get("name") or "").strip()[:32]
    if not new_name:
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
    if not room:
        return False
    allowed_user_ids = {info.get("user_id") for info in room.get("participants", {}).values() if info.get("user_id")}
    return current_user.id in allowed_user_ids or current_user.id == room.get("host_user_id")

def _api_chat_upload_impl(upload_mode: str = "any"):
    try:
        room_id = str(request.form.get("room_id") or "").strip()
        permission = str(request.form.get("permission") or "download").strip().lower()
        if permission not in {"view", "download"}:
            permission = "download"
        room = rooms.get(room_id)
        if not room:
            return jsonify({"ok": False, "error": "room_not_found"}), 404
        allowed_user_ids = {info.get("user_id") for info in room.get("participants", {}).values() if info.get("user_id")}
        if current_user.id not in allowed_user_ids and current_user.id != room.get("host_user_id"):
            return jsonify({"ok": False, "error": "not_in_room"}), 403
        upload = request.files.get("file")
        if not upload or not upload.filename:
            return jsonify({"ok": False, "error": "missing_file"}), 400

        incoming_content_type = (upload.mimetype or upload.content_type or "application/octet-stream").split(';', 1)[0].strip().lower()
        original_name = _build_safe_upload_name(upload.filename, incoming_content_type)
        content_type = _normalize_attachment_content_type(original_name, incoming_content_type)
        kind = _attachment_kind(original_name, content_type)
        ext = (Path(original_name).suffix or '').lower()

        if upload_mode == "media" and kind not in {"image", "video", "audio"}:
            # 桌面端有些浏览器会把图片/视频传成 octet-stream，这里用扩展名兜底
            if ext in {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.heic', '.heif'}:
                kind = 'image'
                content_type = _normalize_attachment_content_type(original_name, incoming_content_type)
            elif ext in {'.mp4', '.webm', '.mov', '.m4v', '.avi', '.3gp'}:
                kind = 'video'
                content_type = _normalize_attachment_content_type(original_name, incoming_content_type)
            else:
                return jsonify({"ok": False, "error": "media_only_upload", "detail": incoming_content_type, "name": original_name}), 400
        if upload_mode == "doc" and kind in {"image", "video", "audio"}:
            return jsonify({"ok": False, "error": "document_only_upload"}), 400

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
            try:
                os.remove(abs_path)
            except OSError:
                pass
            return jsonify({"ok": False, "error": "file_too_large", "limit": size_limit}), 413
        quota_error = _enforce_chat_storage_limits(room_id, size)
        if quota_error:
            try:
                os.remove(abs_path)
            except OSError:
                pass
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
        return jsonify({"ok": False, "error": "upload_internal_error", "detail": str(exc)}), 500

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
        "attachment_view.html",
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
        return jsonify({"ok": False, "error": str(exc)}), 502


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
        return jsonify({"ok": False, "error": str(exc)}), 502


@socketio.on("meeting_chat_send")
def on_meeting_chat_send(data):
    sync_network_traffic()
    sid = request.sid
    info = sid_to_user.get(sid)
    if not info:
        return
    room_id = info["room_id"]
    room = rooms.get(room_id)
    if not room:
        return
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
        for target_sid in target_sids:
            socketio.emit("meeting_chat_message", event, to=target_sid)
    else:
        socketio.emit("meeting_chat_message", event, room=room_id)




@socketio.on("meeting_chat_clear")
def on_meeting_chat_clear():
    sid = request.sid
    info = sid_to_user.get(sid)
    if not info:
        return
    room = rooms.get(info["room_id"])
    if not room:
        return
    is_host = bool(current_user.is_authenticated and current_user.id == room.get("host_user_id"))
    if is_host:
        room["chat_history"] = []
        room["chat_clear_markers"] = {}
        shutil.rmtree(os.path.join(CHAT_UPLOAD_DIR, info["room_id"]), ignore_errors=True)
        socketio.emit("meeting_chat_cleared", {"by": sid, "scope": "all"}, room=info["room_id"])
    else:
        room.setdefault("chat_clear_markers", {})[room_user_marker_key(info.get("user_id"), sid)] = len(room.get("chat_history", []))
        socketio.emit("meeting_chat_cleared", {"by": sid, "scope": "self"}, to=sid)


@socketio.on("meeting_chat_retract")
def on_meeting_chat_retract(data):
    sid = request.sid
    info = sid_to_user.get(sid)
    if not info:
        return
    room = rooms.get(info["room_id"])
    if not room:
        return
    message_id = str((data or {}).get("id") or "")[:32]
    if not message_id:
        return
    is_host = bool(current_user.is_authenticated and current_user.id == room.get("host_user_id"))
    for item in room.get("chat_history", []):
        if item.get("id") != message_id:
            continue
        if item.get("senderUserId") != info.get("user_id") and item.get("from") != sid and not is_host:
            return
        item["withdrawn"] = True
        item["message"] = ""
        item["mentions"] = []
        item["attachment"] = None
        socketio.emit(
            "meeting_chat_retracted",
            {"id": message_id, "senderName": item.get("senderName") or "Guest"},
            room=info["room_id"],
        )
        return
@socketio.on("toggle_danmaku")
def on_toggle_danmaku(data):
    sid = request.sid
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
    room["danmaku_enabled"] = enabled
    socketio.emit("room_ui_event", {"type": "danmaku_toggled", "enabled": enabled, "from": sid}, room=room_id)


@socketio.on("signal")
def on_signal(data):
    target_sid = data.get("target")
    if target_sid:
        emit("signal", data, to=target_sid)


@socketio.on("room_ui_event")
def on_room_ui_event(data):
    sync_network_traffic()
    sid = request.sid
    info = sid_to_user.get(sid)
    if not info:
        return
    room_id = info["room_id"]
    room = rooms.get(room_id)
    if not room:
        return
    payload = data or {}
    event_type = (payload.get("type") or "").strip()
    payload["from"] = sid
    debug_log('ROOM_UI_EVENT_IN', room_id=room_id, sid=sid, payload=payload, current_sharer=room.get('current_sharer_sid'), participants=list(room.get('participants', {}).keys()))

    if event_type == "screen_share_started":
        active_sharer = room.get("current_sharer_sid")
        if active_sharer and active_sharer != sid and active_sharer in room.get("participants", {}):
            emit("room_ui_event", {"type": "screen_share_denied", "message": t("single_screen_share_only"), "from": active_sharer})
            return
        room["current_sharer_sid"] = sid
    elif event_type == "screen_share_stopped":
        if room.get("current_sharer_sid") == sid:
            room["current_sharer_sid"] = None
    elif event_type == "raise_hand":
        raised = bool(payload.get("raised"))
        room.setdefault("raised_hands", {})[sid] = raised
        payload["raised"] = raised
        broadcast_room_participant_snapshot(room_id)
    elif event_type == "stage_rotation_updated":
        meeting = Meeting.query.filter_by(room_id=room_id).first()
        if not meeting or not current_user.is_authenticated or current_user.id != meeting.host_user_id:
            emit("host_action_error", {"message": t("host_only_action")})
            return
        room["stage_rotation_enabled"] = bool(payload.get("enabled", True))
        room["stage_rotation_seconds"] = normalize_stage_rotation_seconds(payload.get("seconds"), room.get("stage_rotation_seconds", 15))
        payload["enabled"] = bool(room["stage_rotation_enabled"])
        payload["seconds"] = normalize_stage_rotation_seconds(room["stage_rotation_seconds"], 15)
        user = db.session.get(User, current_user.id)
        if user:
            user.stage_rotation_enabled = bool(room["stage_rotation_enabled"])
            user.stage_rotation_seconds = normalize_stage_rotation_seconds(room["stage_rotation_seconds"], 15)
            db.session.commit()
        broadcast_room_participant_snapshot(room_id)
    debug_log('ROOM_UI_EVENT_OUT', room_id=room_id, sid=sid, payload=payload, current_sharer=room.get('current_sharer_sid'))
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
    debug_log('SOCKET_LEAVE_BEGIN', sid=sid, sid_info=sid_to_user.get(sid), current_user_id=getattr(current_user, "id", None))
    info = sid_to_user.pop(sid, None)
    if not info:
        debug_log('SOCKET_LEAVE_NOINFO', sid=sid)
        return
    room_id = info["room_id"]
    unbind_user_socket(info.get("user_id"), sid)
    room = rooms.get(room_id)
    if room and sid in room.get("participants", {}):
        sync_network_traffic()
    leave_room(room_id)
    if room and sid in room["participants"]:
        name = room["participants"][sid]["name"]
        del room["participants"][sid]
        if room.get("raised_hands"):
            room["raised_hands"].pop(sid, None)
        if room.get("current_sharer_sid") == sid:
            room["current_sharer_sid"] = None
            socketio.emit("room_ui_event", {"type": "screen_share_stopped", "from": sid}, room=room_id)
        host_left = False
        leaving_user_id = info.get("user_id")
        if leaving_user_id and leaving_user_id == room.get("host_user_id"):
            remaining_host_sids = [
                psid for psid, pinfo in room.get("participants", {}).items()
                if psid != sid and pinfo.get("user_id") == leaving_user_id
            ]
            if remaining_host_sids:
                room["host_present"] = True
                debug_log('SOCKET_LEAVE_HOST_DUPLICATE_REMAINING', sid=sid, room_id=room_id, remaining_host_sids=remaining_host_sids)
            else:
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
        broadcast_room_participant_snapshot(room_id)
        if host_left:
            socketio.emit(
                "host_presence_changed",
                {"host_present": False, "message": t("host_left_room")},
                room=room_id,
            )
        debug_log('SOCKET_LEAVE_DONE', sid=sid, room_id=room_id, remaining_participants=list(room.get("participants", {}).keys()), user_active_sids={uid: list(sids) for uid, sids in user_active_sids.items() if sids})
        if not room["participants"]:
            schedule_room_cleanup(room_id)


@socketio.on("disconnect")
def on_disconnect():
    debug_log('SOCKET_DISCONNECT', sid=request.sid, sid_info=sid_to_user.get(request.sid), current_user_id=getattr(current_user, "id", None))
    on_leave_room()


with app.app_context():
    db.create_all()
    ensure_user_columns()
    ensure_admin()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False, allow_unsafe_werkzeug=True)
