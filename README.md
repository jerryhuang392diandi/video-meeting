# Video Meeting v2

## 功能
- 用户注册 / 登录 / 退出
- 创建会议、会议号 + 密码加入
- 历史会议
- 邀请链接统一由后端生成
- 小型多人视频会议（WebRTC Mesh）
- 摄像头 / 麦克风开关
- 切换前后摄像头
- 屏幕共享
- 断线、刷新后重新进入

## 这版没有真正完成的点
- AI 虚拟背景暂未接入。
- 这个功能通常要在前端引入 MediaPipe 或 TensorFlow.js 做人像分割。

## 运行
```bash
pip install -r requirements.txt
python app.py
```

打开：
- 登录页：`http://127.0.0.1:5000/login`
- 首页：`http://127.0.0.1:5000/index`

## HTTPS 邀请链接
如果你部署到服务器，建议配置：

```bash
PUBLIC_HOST=your-domain.com
PUBLIC_SCHEME=https
```

这样生成的邀请链接会统一变成：

```text
https://your-domain.com/room/xxxxxx?pwd=XXXXXX
```
