# Stable video meeting bundle

这版优先保证稳定启动：
- Flask-SocketIO 使用 threading 模式，不依赖 eventlet
- 自动补齐旧 SQLite 数据库缺失字段
- 单账号单设备登录，后登录会踢掉前设备
- 管理员后台 /admin
- 邀请链接统一由 PUBLIC_HOST + PUBLIC_SCHEME 生成

## 建议的 systemd 环境变量
PUBLIC_HOST=peoplelovesai.xyz
PUBLIC_SCHEME=https
ADMIN_USERNAME=root
ADMIN_PASSWORD=你的管理员密码

## 安装
pip install -r requirements.txt
