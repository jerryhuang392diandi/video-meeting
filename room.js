
const ROOM_ID = {{ room_id|tojson }};
const ROOM_PASSWORD = {{ room_password|tojson }};
const DEFAULT_USER_NAME = {{ current_user.username|tojson }};
const DEFAULT_PREFERRED_NAME = {{ preferred_display_name|tojson }};
const PREF_ENABLE_DANMAKU = {{ 'true' if default_danmaku_enabled else 'false' }};
const PREF_AUTO_ENABLE_CAMERA = {{ 'true' if auto_enable_camera else 'false' }};
const PREF_AUTO_ENABLE_MICROPHONE = {{ 'true' if auto_enable_microphone else 'false' }};
let USER_NAME = (localStorage.getItem('meeting_display_name') || DEFAULT_PREFERRED_NAME || DEFAULT_USER_NAME).trim() || DEFAULT_PREFERRED_NAME || DEFAULT_USER_NAME;
const TEXT_PERMISSION_READY = {{ t('permission_ready')|tojson }};
const TEXT_PERMISSION_FAILED = {{ t('permission_failed')|tojson }};
const TEXT_MEETING_CLOSED = {{ t('meeting_closed')|tojson }};
const TEXT_COPIED = {{ t('copied')|tojson }};
const TEXT_MIC_ON = {{ t('mic_on')|tojson }};
const TEXT_MIC_OFF = {{ t('mic_off')|tojson }};
const TEXT_CAMERA_ON = {{ t('camera_on')|tojson }};
const TEXT_CAMERA_OFF = {{ t('camera_off')|tojson }};
const TEXT_SCREEN_SHARE_MODE = {{ ('共享屏幕模式已开启' if lang == 'zh' else 'Screen share mode enabled')|tojson }};
const TEXT_SCREEN_SHARE_STOPPED = {{ ('共享屏幕模式已结束' if lang == 'zh' else 'Screen share mode ended')|tojson }};
const TEXT_NO_VIDEO = {{ ('未开启摄像头' if lang == 'zh' else 'Camera off')|tojson }};
const TEXT_RECORD_STOP = {{ ('停止录屏' if lang == 'zh' else 'Stop recording')|tojson }};
const TEXT_RECORD_SAVED = {{ ('录屏文件已保存' if lang == 'zh' else 'Recording saved')|tojson }};
const TEXT_RECORD_NOT_SUPPORTED = {{ ('当前浏览器不支持录屏' if lang == 'zh' else 'Screen recording is not supported in this browser')|tojson }};
const TEXT_VIRTUAL_BG_PICK = {{ ('请选择一张背景图片，系统会开始做人像抠图并替换背景' if lang == 'zh' else 'Choose a background image and the app will start person segmentation with background replacement')|tojson }};
const TEXT_VIRTUAL_BG_LOADING = {{ ('正在加载虚拟背景模型...' if lang == 'zh' else 'Loading virtual background model...')|tojson }};
const TEXT_VIRTUAL_BG_READY = {{ ('虚拟背景已启用' if lang == 'zh' else 'Virtual background enabled')|tojson }};
const TEXT_VIRTUAL_BG_FAILED = {{ ('虚拟背景启动失败' if lang == 'zh' else 'Failed to enable virtual background')|tojson }};
const TEXT_VIRTUAL_BG_OFF = {{ ('虚拟背景已关闭' if lang == 'zh' else 'Virtual background disabled')|tojson }};
const TEXT_RECORD_CONVERTING = {{ ('正在转换为可拖动的 MP4，请稍候...' if lang == 'zh' else 'Converting to a seekable MP4, please wait...')|tojson }};
const TEXT_RECORD_MP4_FAILED = {{ ('MP4 转换失败，已回退保存为 WebM' if lang == 'zh' else 'MP4 conversion failed, saved as WebM instead')|tojson }};
const TEXT_RECORD_MP4_SERVER_ERROR = {{ ('服务器 MP4 转换失败' if lang == 'zh' else 'Server-side MP4 conversion failed')|tojson }};
const TEXT_RECORD_DIRECT_MP4 = {{ t('record_direct_mp4')|tojson }};
const TEXT_IMAGE_NOT_SUPPORTED = {{ ('该图片无法作为虚拟背景，请换一张 PNG/JPG 图片' if lang == 'zh' else 'This image cannot be used as a virtual background. Try a PNG or JPG image instead.')|tojson }};
const TEXT_HOST_END_CONFIRM = {{ ('确定要解散当前会议吗？所有参会者都会被移出。' if lang == 'zh' else 'End this meeting now? All participants will be removed.')|tojson }};
const TEXT_LEAVE_CONFIRM = {{ ('确定要离开当前会议吗？' if lang == 'zh' else 'Leave this meeting now?')|tojson }};
const TEXT_YOU_LEFT_MEETING = {{ t('you_left_meeting')|tojson }};
const TEXT_HOST_LEFT_ROOM = {{ t('host_left_room')|tojson }};
const TEXT_HOST_RETURNED_ROOM = {{ t('host_returned_room')|tojson }};
const TEXT_TRAFFIC_LIMIT_REACHED = {{ t('traffic_limit_reached')|tojson }};
const IS_HOST = {{ 'true' if is_host else 'false' }};
const TEXT_DANMAKU_ON = {{ ('弹幕已开启' if lang == 'zh' else 'Danmaku enabled')|tojson }};
const TEXT_DANMAKU_OFF = {{ ('弹幕已关闭' if lang == 'zh' else 'Danmaku disabled')|tojson }};
const TEXT_PROFILE_UPDATED = {{ ('显示名称已更新' if lang == 'zh' else 'Display name updated')|tojson }};
const TEXT_CHAT_WITHDRAWN = {{ ('此消息已撤回' if lang == 'zh' else 'This message was withdrawn')|tojson }};
const TEXT_CHAT_CLEARED = {{ ('聊天记录已清空' if lang == 'zh' else 'Chat history cleared')|tojson }};
const TEXT_TRANSLATE_OPEN = {{ ('已打开翻译结果' if lang == 'zh' else 'Opened translation result')|tojson }};
const TEXT_CHAT_CLEARED_SELF = {{ ('仅清空了你的聊天面板，主持人仍可见历史消息' if lang == 'zh' else 'Only your chat panel was cleared. The host can still see the chat history.')|tojson }};
const TEXT_CHAT_CLEARED_ALL = {{ ('主持人已清空所有人的聊天记录' if lang == 'zh' else 'The host cleared the chat history for everyone.')|tojson }};
const TEXT_COPY_SUCCESS = {{ ('文本已复制' if lang == 'zh' else 'Text copied')|tojson }};
const TEXT_UPLOAD_FAILED = {{ ('附件上传失败' if lang == 'zh' else 'Attachment upload failed')|tojson }};
const TEXT_ATTACHMENT_LIMIT_IMAGE = {{ ('图片请控制在 25MB 以内' if lang == 'zh' else 'Please keep images under 25MB')|tojson }};
const TEXT_ATTACHMENT_LIMIT_VIDEO = {{ ('视频请控制在 120MB 以内' if lang == 'zh' else 'Please keep videos under 120MB')|tojson }};
const TEXT_ATTACHMENT_LIMIT_FILE = {{ ('文档或压缩包请控制在 25MB 以内' if lang == 'zh' else 'Please keep documents or archives under 25MB')|tojson }};
const TEXT_ROOM_STORAGE_LIMIT = {{ ('当前会议附件空间已接近上限，请先清理聊天或稍后再试' if lang == 'zh' else 'Meeting attachment storage is nearly full. Please clear chat or try later')|tojson }};

const socket = io();
const rtcConfig = { iceServers: {{ turn_ice_servers|tojson }}, iceTransportPolicy: 'relay' };

let localStream = null;
let rawCameraStream = null;
let currentFacingMode = 'user';
let peerConnections = {};
let participantMeta = {};
let focusedSid = 'local';
let hiddenSidebar = false;
let currentSharerSid = null;
let currentGridPage = 0;
let videoSearchKeyword = '';

function getGridPageSize() {
  const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
  const stageWidth = videoMain?.clientWidth || videoStage?.clientWidth || 0;
  if (viewportWidth >= 1600 && stageWidth >= 1180) return 16;
  if (viewportWidth >= 1380 && stageWidth >= 980) return 12;
  if (viewportWidth >= 961) return 9;
  if (viewportWidth >= 640) return 6;
  return 4;
}
let isSharingScreen = false;
let activeRecorder = null;
let recorderStream = null;
let virtualBgEnabled = false;
let virtualBgImageDataUrl = null;
let virtualBgImageEl = new Image();
let segmentationModel = null;
let segmentationSending = false;
let virtualBgLoopActive = false;
let processedCanvasStream = null;
let processedVideoStream = null;
let processedFrameCount = 0;
let virtualBgActivationToken = 0;
let activeVirtualBgToken = 0;
let hasLeftMeeting = false;
const MAX_VBG_WIDTH = 960;
const MAX_VBG_HEIGHT = 540;
const VBG_CAPTURE_FPS = 15;

const localVideo = document.createElement('video');
localVideo.id = 'localVideo';
localVideo.autoplay = true;
localVideo.muted = true;
localVideo.playsInline = true;

const rawPreviewVideo = document.createElement('video');
rawPreviewVideo.autoplay = true;
rawPreviewVideo.muted = true;
rawPreviewVideo.playsInline = true;
rawPreviewVideo.style.display = 'none';
document.body.appendChild(rawPreviewVideo);

const processingCanvas = document.createElement('canvas');
processingCanvas.style.display = 'none';
document.body.appendChild(processingCanvas);
const processingCtx = processingCanvas.getContext('2d');

const videoStage = document.getElementById('videoStage');
const videoMain = document.getElementById('videoMain');
const videoSidebar = document.getElementById('videoSidebar');
const participantCountEl = document.getElementById('participantCount');
const statusBox = document.getElementById('statusBox');
const recordingBtn = document.getElementById('recordingBtn');
const virtualBgInput = document.getElementById('virtualBgInput');
const hostEndMeetingBtn = document.getElementById('hostEndMeetingBtn');
const chatWindow = document.getElementById('chatWindow');
const chatHeader = document.getElementById('chatHeader');
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const sendChatBtn = document.getElementById('sendChatBtn');
const chatMediaInput = document.getElementById('chatMediaInput');
const chatDocInput = document.getElementById('chatDocInput');
const chatAttachmentPreview = document.getElementById('chatAttachmentPreview');
const mentionPicker = document.getElementById('mentionPicker');
const MENTION_SEARCH_PLACEHOLDER = {{ ('搜索用户名' if lang == 'zh' else 'Search users')|tojson }};
const MENTION_EMPTY_TEXT = {{ ('没有匹配的用户' if lang == 'zh' else 'No matching users')|tojson }};
const MENTION_ALL_TEXT = {{ ('所有成员' if lang == 'zh' else 'All participants')|tojson }};
const emojiPicker = document.getElementById('emojiPicker');
const emojiPopover = document.getElementById('emojiPopover');
const chatContextMenu = document.getElementById('chatContextMenu');
const chatAttachmentPermission = document.getElementById('chatAttachmentPermission');
const chatComposer = document.querySelector('#chatWindow .chat-composer');
const chatPermissionRow = document.querySelector('#chatWindow .chat-file-permission-row');
const danmakuLayer = document.getElementById('danmakuLayer');
const videoPager = document.getElementById('videoPager');
const videoPrevPageBtn = document.getElementById('videoPrevPageBtn');
const videoNextPageBtn = document.getElementById('videoNextPageBtn');
const videoHomePageBtn = document.getElementById('videoHomePageBtn');
const videoSearchInput = document.getElementById('videoSearchInput');
const videoPagerInfo = document.getElementById('videoPagerInfo');
const shareScreenBtn = document.getElementById('shareScreenBtn');
const virtualBgBtn = document.getElementById('virtualBgBtn');
const IS_IOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

function setStatus(msg, cls='') {
  if (!statusBox) return;
  statusBox.className = 'notice ' + cls;
  statusBox.textContent = msg;
}

function getDisplayName(sid) {
  return sid === 'local' ? `${USER_NAME} · {{ t('local_you') }}` : (participantMeta[sid]?.name || sid);
}

function isMobileDevice() {
  return window.matchMedia('(max-width: 768px)').matches || /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
}

async function safePlayVideo(videoEl) {
  if (!videoEl) return false;
  try {
    const p = videoEl.play?.();
    if (p && typeof p.then === 'function') await p;
    return true;
  } catch (_) {
    const retry = () => {
      videoEl.play?.().catch(() => {});
      window.removeEventListener('touchstart', retry, true);
      window.removeEventListener('click', retry, true);
    };
    window.addEventListener('touchstart', retry, true);
    window.addEventListener('click', retry, true);
    return false;
  }
}

function updateShareUiState() {
  const canShare = !!navigator.mediaDevices?.getDisplayMedia;
  const occupiedByOther = !!currentSharerSid && currentSharerSid !== 'local';
  if (shareScreenBtn) {
    shareScreenBtn.disabled = !canShare || occupiedByOther;
    shareScreenBtn.title = !canShare
      ? {{ ('当前设备/浏览器不支持共享屏幕' if lang == 'zh' else 'This device/browser does not support screen sharing')|tojson }}
      : (occupiedByOther ? {{ ('已有其他用户正在共享屏幕' if lang == 'zh' else 'Another participant is already sharing the screen')|tojson }} : '');
  }
  if (virtualBgBtn) {
    const disabledByShare = !!isSharingScreen || !!currentSharerSid;
    virtualBgBtn.disabled = disabledByShare;
    virtualBgBtn.title = disabledByShare ? {{ ('共享屏幕期间不可使用虚拟背景' if lang == 'zh' else 'Virtual background is unavailable during screen sharing')|tojson }} : '';
  }
}

const roomDebugEnabled = new URLSearchParams(window.location.search).get('debugRoom') === '1';
let simulatedFullscreenCardSid = null;
let pendingLayoutAfterFullscreen = false;

function roomDebugLog(...args) {
  if (!roomDebugEnabled) return;
  console.log('[room-debug]', ...args);
}

function getFullscreenElement() {
  return document.fullscreenElement || document.webkitFullscreenElement || document.msFullscreenElement || null;
}

function getSimulatedFullscreenCard() {
  return simulatedFullscreenCardSid ? document.getElementById('card-' + simulatedFullscreenCardSid) : null;
}

function clearSimulatedFullscreen() {
  const active = document.querySelector('.video-card.fullscreen-simulated');
  if (active) active.classList.remove('fullscreen-simulated');
  document.body.classList.remove('has-simulated-fullscreen');
  simulatedFullscreenCardSid = null;
}

function hasActiveFullscreenSession(videoEl = null) {
  return !!getFullscreenElement() || !!getSimulatedFullscreenCard() || !!(videoEl?.webkitDisplayingFullscreen);
}

function flushPendingLayoutIfNeeded() {
  if (!pendingLayoutAfterFullscreen) return;
  pendingLayoutAfterFullscreen = false;
  roomDebugLog('flush deferred layout after fullscreen exit');
  renderLayout(true);
}

function applySimulatedFullscreen(card, sid) {
  if (!card) return false;
  clearSimulatedFullscreen();
  card.classList.add('fullscreen-simulated');
  document.body.classList.add('has-simulated-fullscreen');
  simulatedFullscreenCardSid = sid || card.dataset.sid || null;
  roomDebugLog('simulated fullscreen applied', { sid: simulatedFullscreenCardSid });
  return true;
}

async function exitAnyFullscreen(videoEl = null) {
  clearSimulatedFullscreen();
  if (document.exitFullscreen && getFullscreenElement()) {
    return document.exitFullscreen();
  }
  if (document.webkitExitFullscreen && getFullscreenElement()) {
    return document.webkitExitFullscreen();
  }
  if (document.msExitFullscreen && getFullscreenElement()) {
    return document.msExitFullscreen();
  }
  if (videoEl?.webkitDisplayingFullscreen && videoEl.webkitExitFullscreen) {
    return videoEl.webkitExitFullscreen();
  }
}

async function requestBestFullscreen({ card, videoEl, preferVideo = false, sid = null } = {}) {
  const candidates = preferVideo ? [videoEl, card] : [card, videoEl];
  for (const el of candidates) {
    if (!el) continue;
    try {
      roomDebugLog('try fullscreen candidate', { sid, tag: el.tagName, hasRequest: !!el.requestFullscreen, hasWebkit: !!el.webkitRequestFullscreen, hasVideoWebkit: !!el.webkitEnterFullscreen });
      if (el.requestFullscreen) {
        try {
          await el.requestFullscreen({ navigationUI: 'hide' });
        } catch (err) {
          roomDebugLog('requestFullscreen with options failed, retrying without options', err?.message || err);
          await el.requestFullscreen();
        }
        return getFullscreenElement() === el || getFullscreenElement() === card || true;
      }
      if (el.webkitRequestFullscreen) {
        el.webkitRequestFullscreen();
        return true;
      }
      if (el.msRequestFullscreen) {
        el.msRequestFullscreen();
        return true;
      }
      if (el.webkitEnterFullscreen) {
        el.webkitEnterFullscreen();
        return true;
      }
    } catch (err) {
      roomDebugLog('fullscreen candidate failed', { sid, error: err?.message || String(err) });
    }
  }
  return applySimulatedFullscreen(card, sid);
}

async function toggleCardFullscreen(card, sid) {
  const videoEl = card?.querySelector('.video-el') || card?.querySelector('video');
  const isMobile = window.matchMedia('(max-width: 768px)').matches;
  const isScreenShareCard = currentSharerSid === sid;
  const activeFullscreenEl = getFullscreenElement();
  const simulatedCard = getSimulatedFullscreenCard();
  const isSameFullscreen = !!activeFullscreenEl && (activeFullscreenEl === card || activeFullscreenEl === videoEl);
  const isSimulatedSame = !!simulatedCard && simulatedCard === card;
  const isVideoNativeFullscreen = !!(videoEl?.webkitDisplayingFullscreen);

  roomDebugLog('toggle fullscreen', { sid, isMobile, isScreenShareCard, isSameFullscreen, isSimulatedSame, isVideoNativeFullscreen });

  if (isSameFullscreen || isSimulatedSame || isVideoNativeFullscreen) {
    await exitAnyFullscreen(videoEl);
    return;
  }

  const preferVideo = isScreenShareCard || isMobile;
  const entered = await requestBestFullscreen({ card, videoEl, preferVideo, sid });
  roomDebugLog('fullscreen result', { sid, entered, active: !!getFullscreenElement(), simulated: !!getSimulatedFullscreenCard() });
  if (entered && (isScreenShareCard || isMobile) && screen.orientation?.lock) {
    screen.orientation.lock('landscape').catch(() => {});
  }
}

function ensureCard(sid, displayName = null, isLocal = false) {
  let card = document.getElementById('card-' + sid);
  if (card) {
    const labelEl = card.querySelector('.video-label');
    if (displayName && labelEl) labelEl.textContent = displayName;
    return card;
  }

  card = document.createElement('div');
  card.className = 'video-card' + (isLocal ? ' self-card' : '');
  card.id = 'card-' + sid;
  card.dataset.sid = sid;
  card.innerHTML = `
    <div class="video-toolbar">
      <button class="card-btn" data-action="fullscreen">{{ ('全屏' if lang == 'zh' else 'Fullscreen') }}</button>
    </div>
    <div class="video-placeholder">${TEXT_NO_VIDEO}</div>
    <div class="video-label-stack">
      <div class="video-label">${displayName || getDisplayName(sid)}</div>
    </div>
  `;
  if (simulatedFullscreenCardSid && simulatedFullscreenCardSid === sid) {
    card.classList.add('fullscreen-simulated');
    document.body.classList.add('has-simulated-fullscreen');
  }

  const videoEl = sid === 'local' ? localVideo : document.createElement('video');
  if (sid !== 'local') {
    videoEl.autoplay = true;
    videoEl.playsInline = true;
  }
  videoEl.setAttribute('autoplay', 'autoplay');
  videoEl.setAttribute('playsinline', 'playsinline');
  videoEl.setAttribute('webkit-playsinline', 'true');
  videoEl.className = 'video-el';
  card.prepend(videoEl);

  if (!card.parentElement) {
    videoMain.appendChild(card);
  }

  card.querySelector('[data-action="fullscreen"]').addEventListener('click', async () => {
    try {
      await toggleCardFullscreen(card, sid);
    } catch (err) {
      console.error(err);
    }
  });

  return card;
}

function updatePlaceholder(card, hasVideo) {
  if (!card) return;
  card.classList.toggle('has-video', !!hasVideo);
}

function getGridColumns(cardCount) {
  if (cardCount <= 1) return 1;
  if (cardCount === 2) return 2;
  if (cardCount <= 4) return 2;
  return 3;
}

function updateVideoPager(totalCards, totalPages) {
  if (!videoPager || !videoPrevPageBtn || !videoNextPageBtn || !videoPagerInfo) return;
  const pageSize = getGridPageSize();
  const hasSearch = !!getVideoSearchKeyword();
  const showPager = !currentSharerSid && ((totalCards > pageSize && totalPages > 1) || hasSearch);
  videoPager.classList.toggle('hidden', !showPager);
  if (!showPager) {
    videoPagerInfo.textContent = '1 / 1';
    if (videoHomePageBtn) videoHomePageBtn.disabled = true;
    if (videoSearchInput) videoSearchInput.value = videoSearchKeyword;
    return;
  }
  videoPagerInfo.textContent = `${currentGridPage + 1} / ${totalPages}`;
  videoPrevPageBtn.disabled = currentGridPage <= 0;
  videoNextPageBtn.disabled = currentGridPage >= totalPages - 1;
  if (videoHomePageBtn) videoHomePageBtn.disabled = currentGridPage <= 0;
  if (videoSearchInput && videoSearchInput.value !== videoSearchKeyword) videoSearchInput.value = videoSearchKeyword;
}

function getVideoSearchKeyword() {
  return String(videoSearchKeyword || '').trim().toLocaleLowerCase('zh-Hans-CN');
}

function getRenderableCards() {
  const orderedSids = ['local', ...Object.keys(participantMeta)];
  const seen = new Set();
  const keyword = getVideoSearchKeyword();
  return orderedSids
    .filter(sid => {
      if (seen.has(sid)) return false;
      seen.add(sid);
      if (!keyword) return true;
      const displayName = sid === 'local' ? getDisplayName('local') : getDisplayName(sid);
      const haystack = `${displayName || ''} ${sid || ''} ${ROOM_ID || ''}`.toLocaleLowerCase('zh-Hans-CN');
      return haystack.includes(keyword);
    })
    .map(sid => ensureCard(
      sid,
      sid === 'local' ? getDisplayName('local') : getDisplayName(sid),
      sid === 'local'
    ));
}

function renderLayout(force = false) {
  if (!videoMain || !videoSidebar || !videoStage) return;
  if (!force && hasActiveFullscreenSession()) {
    pendingLayoutAfterFullscreen = true;
    roomDebugLog('renderLayout deferred due to active fullscreen');
    return;
  }
  const cards = getRenderableCards();
  if (!cards.length) {
    videoMain.innerHTML = '<div class="video-empty-state">' + escapeHtml({{ ('未找到匹配的参会者' if lang == 'zh' else 'No matching participants found')|tojson }}) + '</div>';
    videoSidebar.innerHTML = '';
    videoStage.classList.remove('grid-1', 'grid-2', 'grid-3', 'paged-grid', 'focus-layout', 'grid-layout');
    videoStage.classList.add('sidebar-hidden');
    updateVideoPager(0, 1);
    return;
  }

  videoMain.innerHTML = '';
  videoSidebar.innerHTML = '';

  cards.forEach(card => card.classList.remove('is-focused', 'is-sidebar'));
  videoStage.classList.remove('grid-1', 'grid-2', 'grid-3', 'paged-grid');

  const pageSize = getGridPageSize();
  const totalPages = Math.max(1, Math.ceil(cards.length / pageSize));
  currentGridPage = Math.max(0, Math.min(currentGridPage, totalPages - 1));

  const focusTarget = document.getElementById('card-' + (focusedSid || 'local')) || document.getElementById('card-local') || cards[0];
  if (!focusTarget) return;

  const canUseGrid = !currentSharerSid && !hiddenSidebar;
  const shouldUseGrid = canUseGrid && cards.length <= pageSize;
  const shouldUsePagedGrid = canUseGrid && cards.length > pageSize;

  videoStage.classList.toggle('screen-share-mode', !!currentSharerSid);
  videoStage.classList.toggle('grid-layout', shouldUseGrid || shouldUsePagedGrid);
  videoStage.classList.toggle('focus-layout', !shouldUseGrid && !shouldUsePagedGrid);

  if (shouldUseGrid || shouldUsePagedGrid) {
    videoStage.classList.add('sidebar-hidden');
    const start = shouldUsePagedGrid ? currentGridPage * pageSize : 0;
    const end = shouldUsePagedGrid ? start + pageSize : cards.length;
    const visibleCards = cards.slice(start, end);
    const gridCols = getGridColumns(visibleCards.length);
    videoStage.classList.add(`grid-${gridCols}`);
    if (shouldUsePagedGrid) videoStage.classList.add('paged-grid');
    visibleCards.forEach(card => videoMain.appendChild(card));
    updateVideoPager(cards.length, totalPages);
    return;
  }

  updateVideoPager(cards.length, totalPages);
  focusTarget.classList.add('is-focused');
  videoMain.appendChild(focusTarget);

  const sidebarCards = cards.filter(card => card !== focusTarget);
  sidebarCards.forEach(card => {
    card.classList.add('is-sidebar');
    videoSidebar.appendChild(card);
  });

  videoStage.classList.toggle('sidebar-hidden', hiddenSidebar || sidebarCards.length === 0);
  updateShareUiState();
}

function focusParticipant(sid, opts = {}) {
  focusedSid = sid;
  if (typeof opts.hideSidebar === 'boolean') hiddenSidebar = opts.hideSidebar;
  if (Object.prototype.hasOwnProperty.call(opts, 'screenShare')) currentSharerSid = opts.screenShare ? sid : null;
  renderLayout();
}

function updateParticipantCount() {
  participantCountEl.textContent = 1 + Object.keys(participantMeta).length;
}

function stopStreamTracks(stream) {
  if (!stream) return;
  stream.getTracks().forEach(track => {
    try { track.stop(); } catch (_) {}
  });
}

function cleanupProcessedVideoStream({ stopCanvas = false } = {}) {
  if (processedVideoStream && processedVideoStream !== rawCameraStream) {
    const extraVideoTracks = processedVideoStream.getVideoTracks();
    extraVideoTracks.forEach(track => {
      try { track.stop(); } catch (_) {}
    });
  }
  processedVideoStream = null;
  if (stopCanvas && processedCanvasStream) {
    stopStreamTracks(processedCanvasStream);
    processedCanvasStream = null;
  }
}

function disableVirtualBackgroundState({ stopCanvas = false } = {}) {
  virtualBgEnabled = false;
  virtualBgLoopActive = false;
  segmentationSending = false;
  virtualBgActivationToken += 1;
  activeVirtualBgToken = 0;
  cleanupProcessedVideoStream({ stopCanvas });
}

function fallbackToRawCamera(message = null) {
  if (!rawCameraStream) return;
  disableVirtualBackgroundState();
  rawPreviewVideo.srcObject = rawCameraStream;
  useLocalOutputStream(rawCameraStream);
  if (message) setStatus(message, 'warning');
}

function deactivateVirtualBackground(message = null) {
  virtualBgImageDataUrl = null;
  fallbackToRawCamera(message || TEXT_VIRTUAL_BG_OFF);
}

function useLocalOutputStream(stream) {
  localStream = stream;
  localVideo.srcObject = stream;
  safePlayVideo(localVideo);
  const localCard = ensureCard('local', getDisplayName('local'), true);
  updatePlaceholder(localCard, !!stream?.getVideoTracks?.()[0]?.enabled);
  syncPeerMedia().catch(err => console.error(err));
  renderLayout();
}

function getScaledSize(width, height) {
  if (!width || !height) return { width: 640, height: 360 };
  const scale = Math.min(MAX_VBG_WIDTH / width, MAX_VBG_HEIGHT / height, 1);
  const scaledWidth = Math.max(2, Math.round((width * scale) / 2) * 2);
  const scaledHeight = Math.max(2, Math.round((height * scale) / 2) * 2);
  return { width: scaledWidth, height: scaledHeight };
}

async function waitForVideoReady(videoEl, timeoutMs = 2000) {
  if (videoEl.readyState >= 2 && videoEl.videoWidth && videoEl.videoHeight) return true;
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      cleanup();
      reject(new Error('Camera preview not ready'));
    }, timeoutMs);
    const onReady = () => {
      cleanup();
      resolve(true);
    };
    const cleanup = () => {
      clearTimeout(timer);
      videoEl.removeEventListener('loadedmetadata', onReady);
      videoEl.removeEventListener('canplay', onReady);
    };
    videoEl.addEventListener('loadedmetadata', onReady);
    videoEl.addEventListener('canplay', onReady);
  });
  return true;
}

async function ensureProcessedCanvasStream() {
  if (processedCanvasStream && processedCanvasStream.getVideoTracks()[0] && processedCanvasStream.getVideoTracks()[0].readyState === 'live') {
    return processedCanvasStream;
  }
  if (!processingCanvas.width || !processingCanvas.height) throw new Error('Processed canvas is empty');
  processedCanvasStream = processingCanvas.captureStream(VBG_CAPTURE_FPS);
  return processedCanvasStream;
}

async function transcodeRecordingBlob(blob, filename = 'meeting-recording.webm') {
  const formData = new FormData();
  formData.append('recording', blob, filename);
  const response = await fetch('/api/remux-recording', { method: 'POST', body: formData, credentials: 'same-origin' });
  if (!response.ok) {
    let message = 'convert failed';
    try {
      const data = await response.json();
      message = data?.message || message;
    } catch (_) {}
    throw new Error(message);
  }
  return await response.blob();
}

async function requestMedia(forceFacingMode = null, manualRequest = false, preferredKinds = null) {
  const wantsVideo = Array.isArray(preferredKinds) ? preferredKinds.includes('video') : (manualRequest ? true : !!PREF_AUTO_ENABLE_CAMERA);
  const wantsAudio = Array.isArray(preferredKinds) ? preferredKinds.includes('audio') : (manualRequest ? true : !!PREF_AUTO_ENABLE_MICROPHONE);
  if (!wantsVideo && !wantsAudio) {
    setStatus({{ ('当前未设置自动打开摄像头或麦克风，请手动开启。' if lang == 'zh' else 'Camera and microphone are both off by default. Enable either one manually when needed.')|tojson }});
    return null;
  }
  try {
    const constraints = {
      audio: wantsAudio,
      video: wantsVideo ? (forceFacingMode && !IS_IOS ? { facingMode: { ideal: forceFacingMode } } : true) : false,
    };
    const nextRawStream = await navigator.mediaDevices.getUserMedia(constraints);
    const nextVideoTrack = nextRawStream.getVideoTracks()[0] || null;
    const nextAudioTrack = nextRawStream.getAudioTracks()[0] || null;

    if (rawCameraStream) {
      const oldVideoTrack = rawCameraStream.getVideoTracks()[0] || null;
      const oldAudioTrack = rawCameraStream.getAudioTracks()[0] || null;
      if (oldVideoTrack && nextVideoTrack && oldVideoTrack !== nextVideoTrack) { try { oldVideoTrack.stop(); } catch (_) {} }
      if (oldAudioTrack && nextAudioTrack && oldAudioTrack !== nextAudioTrack) { try { oldAudioTrack.stop(); } catch (_) {} }
      const merged = new MediaStream();
      if (nextVideoTrack || oldVideoTrack) merged.addTrack(nextVideoTrack || oldVideoTrack);
      if (nextAudioTrack || oldAudioTrack) merged.addTrack(nextAudioTrack || oldAudioTrack);
      rawCameraStream = merged;
    } else {
      rawCameraStream = nextRawStream;
    }

    disableVirtualBackgroundState({ stopCanvas: true });
    rawPreviewVideo.srcObject = rawCameraStream;
    await safePlayVideo(rawPreviewVideo);

    if (!manualRequest) {
      rawCameraStream.getVideoTracks().forEach(track => { track.enabled = !!PREF_AUTO_ENABLE_CAMERA; });
      rawCameraStream.getAudioTracks().forEach(track => { track.enabled = !!PREF_AUTO_ENABLE_MICROPHONE; });
    }

    useLocalOutputStream(rawCameraStream);

    if (virtualBgImageDataUrl && !isSharingScreen && !currentSharerSid) {
      try {
        await activateVirtualBackground();
      } catch (vbgErr) {
        console.error(vbgErr);
        fallbackToRawCamera(TEXT_VIRTUAL_BG_FAILED + ': ' + (vbgErr.message || 'unknown error'));
      }
    } else {
      setStatus(TEXT_PERMISSION_READY);
    }
    return rawCameraStream;
  } catch (err) {
    console.error(err);
    setStatus(TEXT_PERMISSION_FAILED + ': ' + err.message, 'error');
    return null;
  }
}

async function ensureRequestedTrack(kind) {
  const track = kind === 'video' ? rawCameraStream?.getVideoTracks?.()[0] : rawCameraStream?.getAudioTracks?.()[0];
  if (track) return track;
  const stream = await requestMedia(currentFacingMode, true, [kind]);
  return kind === 'video' ? stream?.getVideoTracks?.()[0] : stream?.getAudioTracks?.()[0];
}

async function syncPeerMedia(targetSid = null) {
  const entries = targetSid
    ? (peerConnections[targetSid] ? [[targetSid, peerConnections[targetSid]]] : [])
    : Object.entries(peerConnections);
  const tracks = Array.isArray(localStream?.getTracks?.()) ? localStream.getTracks() : [];
  const renegotiateTasks = [];

  entries.forEach(([sid, pc]) => {
    if (!pc) return;
    const senders = pc.getSenders();
    let addedTrack = false;

    tracks.forEach((track) => {
      const sender = senders.find((item) => item.track && item.track.kind === track.kind);
      if (sender) {
        sender.replaceTrack(track).catch((err) => console.error(err));
      } else {
        try {
          pc.addTrack(track, localStream);
          addedTrack = true;
        } catch (err) {
          console.error(err);
        }
      }
    });

    if (addedTrack && pc.signalingState === 'stable') {
      renegotiateTasks.push((async () => {
        try {
          const offer = await pc.createOffer();
          await pc.setLocalDescription(offer);
          socket.emit('signal', { target: sid, from: socket.id, description: pc.localDescription, senderName: USER_NAME });
        } catch (err) {
          console.error(err);
        }
      })());
    }
  });

  if (renegotiateTasks.length) await Promise.allSettled(renegotiateTasks);
}

function ensurePeer(targetSid) {
  if (peerConnections[targetSid]) return peerConnections[targetSid];
  const pc = new RTCPeerConnection(rtcConfig);
  peerConnections[targetSid] = pc;

  if (localStream) {
    localStream.getTracks().forEach(track => pc.addTrack(track, localStream));
  }

  pc.onicecandidate = (event) => {
    if (event.candidate) {
      socket.emit('signal', { target: targetSid, from: socket.id, candidate: event.candidate });
    }
  };

  pc.ontrack = (event) => addRemoteVideo(targetSid, event.streams[0]);
  pc.onconnectionstatechange = () => {
    if (['disconnected', 'failed', 'closed'].includes(pc.connectionState)) {
      removeRemoteVideo(targetSid);
      delete peerConnections[targetSid];
    }
  };
  return pc;
}

function addRemoteParticipant(sid, name) {
  participantMeta[sid] = { name: name || sid };
  const card = ensureCard(sid, participantMeta[sid].name, false);
  updatePlaceholder(card, false);
  currentGridPage = 0;
  renderLayout();
  updateParticipantCount();
}

function addRemoteVideo(sid, stream) {
  const card = ensureCard(sid, getDisplayName(sid), false);
  const videoEl = card.querySelector('video');
  videoEl.srcObject = stream;
  safePlayVideo(videoEl);
  updatePlaceholder(card, true);
  renderLayout();
}

function removeRemoteVideo(sid) {
  document.getElementById('card-' + sid)?.remove();
  delete participantMeta[sid];
  if (focusedSid === sid) focusedSid = 'local';
  if (currentSharerSid === sid) {
    currentSharerSid = null;
    hiddenSidebar = false;
    setStatus(TEXT_SCREEN_SHARE_STOPPED);
  }
  updateShareUiState();
  const totalCards = document.querySelectorAll('.video-card').length;
  const totalPages = Math.max(1, Math.ceil(totalCards / getGridPageSize()));
  currentGridPage = Math.min(currentGridPage, totalPages - 1);
  renderLayout();
  updateParticipantCount();
}

async function callPeer(targetSid) {
  const pc = ensurePeer(targetSid);
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
  socket.emit('signal', { target: targetSid, from: socket.id, description: pc.localDescription, senderName: USER_NAME });
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

async function toggleScreenRecording() {
  if (activeRecorder) {
    activeRecorder.stop();
    recorderStream?.getTracks().forEach(track => track.stop());
    return;
  }

  if (!navigator.mediaDevices?.getDisplayMedia || typeof MediaRecorder === 'undefined') {
    setStatus(TEXT_RECORD_NOT_SUPPORTED, 'error');
    return;
  }

  try {
    try {
      recorderStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true });
    } catch (audioErr) {
      recorderStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
    }
    const chunks = [];

    let mimeType = '';
    let outputExt = 'webm';
    if (MediaRecorder.isTypeSupported('video/mp4;codecs=avc1.42E01E,mp4a.40.2')) {
      mimeType = 'video/mp4;codecs=avc1.42E01E,mp4a.40.2';
      outputExt = 'mp4';
    } else if (MediaRecorder.isTypeSupported('video/mp4')) {
      mimeType = 'video/mp4';
      outputExt = 'mp4';
    } else if (MediaRecorder.isTypeSupported('video/webm;codecs=vp9,opus')) {
      mimeType = 'video/webm;codecs=vp9,opus';
    } else if (MediaRecorder.isTypeSupported('video/webm;codecs=vp8,opus')) {
      mimeType = 'video/webm;codecs=vp8,opus';
    } else if (MediaRecorder.isTypeSupported('video/webm')) {
      mimeType = 'video/webm';
    } else {
      setStatus(TEXT_RECORD_NOT_SUPPORTED, 'error');
      recorderStream.getTracks().forEach(track => track.stop());
      recorderStream = null;
      return;
    }

    activeRecorder = new MediaRecorder(recorderStream, mimeType ? { mimeType } : undefined);
    activeRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) chunks.push(event.data);
    };
    activeRecorder.onstop = async () => {
      const recordedBlob = new Blob(chunks, { type: mimeType || 'video/webm' });
      recordingBtn.textContent = {{ t('recording')|tojson }};
      activeRecorder = null;
      recorderStream = null;

      if (outputExt === 'mp4' || (recordedBlob.type || '').includes('mp4')) {
        downloadBlob(recordedBlob, `meeting-recording-${Date.now()}.mp4`);
        setStatus(TEXT_RECORD_DIRECT_MP4);
        return;
      }

      try {
        setStatus(TEXT_RECORD_CONVERTING, 'warning');
        const mp4Blob = await transcodeRecordingBlob(recordedBlob, 'meeting-recording.webm');
        downloadBlob(mp4Blob, `meeting-recording-${Date.now()}.mp4`);
        setStatus(TEXT_RECORD_SAVED);
      } catch (err) {
        console.error(err);
        downloadBlob(recordedBlob, `meeting-recording-${Date.now()}.webm`);
        const reason = err?.message ? `${TEXT_RECORD_MP4_SERVER_ERROR}: ${err.message}` : TEXT_RECORD_MP4_FAILED;
        setStatus(reason, 'warning');
      }
    };
    recorderStream.getVideoTracks()[0].onended = () => {
      if (activeRecorder && activeRecorder.state !== 'inactive') activeRecorder.stop();
    };
    activeRecorder.start(1000);
    recordingBtn.textContent = TEXT_RECORD_STOP;
    setStatus(TEXT_RECORD_STOP);
  } catch (err) {
    activeRecorder = null;
    recorderStream?.getTracks().forEach(track => track.stop());
    recorderStream = null;
    setStatus(err.message || TEXT_RECORD_NOT_SUPPORTED, 'error');
  }
}

async function loadSegmentationModel() {
  if (segmentationModel) return segmentationModel;
  if (typeof SelfieSegmentation === 'undefined') {
    throw new Error('SelfieSegmentation not loaded');
  }
  segmentationModel = new SelfieSegmentation({
    locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/selfie_segmentation/${file}`,
  });
  segmentationModel.setOptions({ modelSelection: 1 });
  segmentationModel.onResults(onSegmentationResults);
  return segmentationModel;
}

function drawImageCover(ctx, img, x, y, width, height) {
  const scale = Math.max(width / img.width, height / img.height);
  const drawWidth = img.width * scale;
  const drawHeight = img.height * scale;
  const dx = x + (width - drawWidth) / 2;
  const dy = y + (height - drawHeight) / 2;
  ctx.drawImage(img, dx, dy, drawWidth, drawHeight);
}

function onSegmentationResults(results) {
  if (!virtualBgEnabled || !virtualBgImageEl?.src) return;

  const sourceWidth = results.image.videoWidth || results.image.width || 1280;
  const sourceHeight = results.image.videoHeight || results.image.height || 720;
  const { width, height } = getScaledSize(sourceWidth, sourceHeight);
  if (processingCanvas.width !== width || processingCanvas.height !== height) {
    processingCanvas.width = width;
    processingCanvas.height = height;
  }

  processingCtx.save();
  processingCtx.clearRect(0, 0, width, height);
  processingCtx.drawImage(results.segmentationMask, 0, 0, width, height);
  processingCtx.globalCompositeOperation = 'source-out';
  drawImageCover(processingCtx, virtualBgImageEl, 0, 0, width, height);
  processingCtx.globalCompositeOperation = 'destination-atop';
  processingCtx.drawImage(results.image, 0, 0, width, height);
  processingCtx.restore();
  processedFrameCount += 1;
}

async function startSegmentationLoop() {
  if (virtualBgLoopActive) return;
  virtualBgLoopActive = true;

  const loop = async () => {
    if (!virtualBgEnabled) {
      virtualBgLoopActive = false;
      return;
    }
    if (segmentationSending || !rawPreviewVideo.srcObject) {
      requestAnimationFrame(loop);
      return;
    }
    try {
      segmentationSending = true;
      await segmentationModel.send({ image: rawPreviewVideo });
    } catch (err) {
      console.error(err);
    } finally {
      segmentationSending = false;
      requestAnimationFrame(loop);
    }
  };

  requestAnimationFrame(loop);
}

async function activateVirtualBackground() {
  if (!rawCameraStream || !virtualBgImageDataUrl) return false;
  const activationToken = ++virtualBgActivationToken;
  let hadWorkingVbg = !!processedVideoStream && localStream === processedVideoStream;
  const previousBgImageEl = virtualBgImageEl;
  setStatus(TEXT_VIRTUAL_BG_LOADING, 'warning');

  try {
    await loadSegmentationModel();
    const bgImage = new Image();
    await new Promise((resolve, reject) => {
      bgImage.onload = () => {
        if (!bgImage.naturalWidth || !bgImage.naturalHeight) {
          reject(new Error(TEXT_IMAGE_NOT_SUPPORTED));
          return;
        }
        resolve();
      };
      bgImage.onerror = () => reject(new Error(TEXT_IMAGE_NOT_SUPPORTED));
      bgImage.src = virtualBgImageDataUrl;
    });

    rawPreviewVideo.srcObject = rawCameraStream;
    await rawPreviewVideo.play().catch(() => {});
    await waitForVideoReady(rawPreviewVideo, 2500);

    const startCount = processedFrameCount;

    virtualBgImageEl = bgImage;
    virtualBgEnabled = true;
    await startSegmentationLoop();

    const deadline = Date.now() + 3000;
    while (processedFrameCount < startCount + 2) {
      if (activationToken !== virtualBgActivationToken) return false;
      if (Date.now() > deadline) throw new Error('Segmentation timeout');
      await new Promise(resolve => setTimeout(resolve, 60));
    }

    await ensureProcessedCanvasStream();
    const processedTrack = processedCanvasStream.getVideoTracks()[0];
    if (!processedTrack) throw new Error('Processed video track unavailable');

    const nextOutputStream = new MediaStream();
    nextOutputStream.addTrack(processedTrack.clone());
    rawCameraStream.getAudioTracks().forEach(track => nextOutputStream.addTrack(track));

    if (activationToken !== virtualBgActivationToken) {
      stopStreamTracks(nextOutputStream);
      return false;
    }

    cleanupProcessedVideoStream();
    processedVideoStream = nextOutputStream;
    activeVirtualBgToken = activationToken;
    useLocalOutputStream(processedVideoStream);
    setStatus(TEXT_VIRTUAL_BG_READY);
    return true;
  } catch (err) {
    console.error(err);
    if (hadWorkingVbg && processedVideoStream) {
      virtualBgImageEl = previousBgImageEl;
      virtualBgEnabled = true;
      setStatus(TEXT_VIRTUAL_BG_FAILED + ': ' + (err.message || 'unknown error'), 'warning');
    } else {
      fallbackToRawCamera(TEXT_VIRTUAL_BG_FAILED + ': ' + (err.message || 'unknown error'));
    }
    return false;
  }
}

let activeChatMode = 'all';
let pendingAttachment = null;
let danmakuEnabled = false;
const CHAT_EMOJIS = ['😀','😄','😁','😂','😉','😊','😍','🥳','😎','🤔','👍','👏','🙌','🎉','❤️','🔥','🚀','🤝','🙏','📌'];

function escapeHtml(text) {
  return String(text || '').replace(/[&<>"']/g, (m) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}

function getMentionablePeople() {
  const byName = new Map();
  [{ sid: 'local', name: USER_NAME }]
    .concat(Object.entries(participantMeta).map(([sid, info]) => ({ sid, name: info.name || sid })))
    .forEach(person => {
      const name = String(person?.name || '').trim();
      if (!name) return;
      const key = name.toLowerCase();
      if (!byName.has(key)) byName.set(key, { sid: person.sid, name });
    });
  return Array.from(byName.values()).sort((a, b) => a.name.localeCompare(b.name, 'zh-Hans-CN-u-co-pinyin'));
}

function normalizeMentionKeyword(value) {
  return String(value || '').trim().toLocaleLowerCase('zh-Hans-CN');
}

function buildMentionPickerShell(rawFilterText = '') {
  mentionPicker.innerHTML = `
    <div class="mention-dropdown">
      <div class="mention-dropdown-head">
        <span class="mention-dropdown-title">${escapeHtml(MENTION_ALL_TEXT)}</span>
        <button type="button" class="card-btn mention-collapse-btn">${escapeHtml({{ ('收起' if lang == 'zh' else 'Collapse')|tojson }})}</button>
      </div>
      <div class="mention-search-wrap">
        <input id="mentionSearchInput" class="mention-search-input" type="text" autocomplete="off" autocapitalize="off" spellcheck="false" inputmode="text" placeholder="${escapeHtml(MENTION_SEARCH_PLACEHOLDER)}" value="${escapeHtml(rawFilterText)}" />
      </div>
      <div class="mention-options-list"></div>
    </div>`;

  mentionPicker.querySelector('.mention-collapse-btn')?.addEventListener('click', () => {
    mentionPicker.classList.add('hidden');
  });

  const searchInput = mentionPicker.querySelector('#mentionSearchInput');
  const optionList = mentionPicker.querySelector('.mention-options-list');
  let composing = false;

  const paintList = (filterValue = '') => {
    if (!optionList) return;
    const keyword = normalizeMentionKeyword(filterValue);
    const people = getMentionablePeople();
    const filtered = keyword ? people.filter(person => normalizeMentionKeyword(person.name).includes(keyword)) : people;
    optionList.innerHTML = filtered.length
      ? filtered.map(person => `<button type="button" class="mention-option mention-option-row" data-name="${escapeHtml(person.name)}"><span class="mention-option-at">@</span><span class="mention-option-name">${escapeHtml(person.name)}</span></button>`).join('')
      : `<div class="mention-empty">${escapeHtml(MENTION_EMPTY_TEXT)}</div>`;

    optionList.querySelectorAll('.mention-option').forEach(btn => {
      btn.addEventListener('click', () => {
        chatInput.value = `${chatInput.value}${chatInput.value && !chatInput.value.endsWith(' ') ? ' ' : ''}@${btn.dataset.name} `;
        mentionPicker.classList.add('hidden');
        chatInput.focus();
      });
    });
  };

  searchInput?.addEventListener('compositionstart', () => {
    composing = true;
  });
  searchInput?.addEventListener('compositionend', (e) => {
    composing = false;
    paintList(e.target.value);
  });
  searchInput?.addEventListener('input', (e) => {
    if (composing || e.isComposing) return;
    paintList(e.target.value);
  });

  if (searchInput) {
    const caret = rawFilterText.length;
    requestAnimationFrame(() => {
      try { searchInput.focus({ preventScroll: true }); } catch (_) { searchInput.focus(); }
      try { searchInput.setSelectionRange(caret, caret); } catch (_) {}
    });
  }

  paintList(rawFilterText);
}

function renderMentionPicker(filterText = '') {
  if (!mentionPicker) return;
  const currentInput = mentionPicker.querySelector('#mentionSearchInput');
  const hasShell = !!mentionPicker.querySelector('.mention-dropdown');
  const rawFilterText = String(filterText || '');
  if (!hasShell) {
    buildMentionPickerShell(rawFilterText);
    return;
  }
  if (currentInput) {
    currentInput.value = rawFilterText;
    currentInput.dispatchEvent(new Event('input', { bubbles: true }));
    return;
  }
  buildMentionPickerShell(rawFilterText);
}

function renderEmojiPicker() {
  if (!emojiPicker) return;
  emojiPicker.innerHTML = CHAT_EMOJIS.map(emoji => `<button type="button" class="emoji-option" data-emoji="${emoji}">${emoji}</button>`).join('');
  emojiPicker.querySelectorAll('.emoji-option').forEach(btn => {
    btn.addEventListener('click', () => {
      chatInput.value = `${chatInput.value}${btn.dataset.emoji}`;
      chatInput.focus();
    });
  });
}

function hideFloatingPanels() {
  mentionPicker?.classList.add('hidden');
  emojiPopover?.classList.add('hidden');
  chatContextMenu?.classList.add('hidden');
}

function getAttachmentExt(name) {
  const str = String(name || '');
  const idx = str.lastIndexOf('.');
  return idx >= 0 ? str.slice(idx + 1).toUpperCase() : 'FILE';
}

function getAttachmentBadge(attachment) {
  const ext = getAttachmentExt(attachment?.name);
  if ((attachment?.kind || '') === 'pdf') return 'PDF';
  if ((attachment?.kind || '') === 'image') return 'IMG';
  if ((attachment?.kind || '') === 'video') return 'VIDEO';
  if ((attachment?.kind || '') === 'audio') return 'AUDIO';
  return ext.slice(0, 6) || 'FILE';
}

function buildAttachmentHtml(attachment) {
  if (!attachment) return '';
  const name = escapeHtml(attachment.name || 'attachment');
  const permissionLabel = attachment.permission === 'download'
    ? {{ ('可下载' if lang == 'zh' else 'Download allowed')|tojson }}
    : {{ ('仅查看' if lang == 'zh' else 'View only')|tojson }};
  const openLabel = attachment.permission === 'download'
    ? {{ ('查看/打开' if lang == 'zh' else 'Open' )|tojson }}
    : {{ ('查看' if lang == 'zh' else 'View' )|tojson }};
  const rawUrl = attachment.rawUrl || '';
  if (rawUrl && attachment.kind === 'image') {
    return `<div class="chat-attachment-block"><img class="chat-media" src="${rawUrl}" alt="${name}" /><div class="chat-file-meta"><span>${name}</span><span>${permissionLabel}</span></div><div class="chat-file-links"><a class="ghost-btn" href="${attachment.viewUrl}" target="_blank">${openLabel}</a>${attachment.downloadUrl ? `<a class="ghost-btn" href="${attachment.downloadUrl}" target="_blank">{{ '下载' if lang == 'zh' else 'Download' }}</a>` : ''}</div></div>`;
  }
  if (rawUrl && attachment.kind === 'video') {
    return `<div class="chat-attachment-block"><video class="chat-media" src="${rawUrl}" controls playsinline preload="metadata"></video><div class="chat-file-meta"><span>${name}</span><span>${permissionLabel}</span></div><div class="chat-file-links"><a class="ghost-btn" href="${attachment.viewUrl}" target="_blank">${openLabel}</a>${attachment.downloadUrl ? `<a class="ghost-btn" href="${attachment.downloadUrl}" target="_blank">{{ '下载' if lang == 'zh' else 'Download' }}</a>` : ''}</div></div>`;
  }
  if (attachment.viewUrl) {
    return `<div class="chat-attachment-block chat-file-card standardized"><div class="chat-file-badge">${getAttachmentBadge(attachment)}</div><div class="chat-file-meta"><strong>${name}</strong><span>${permissionLabel}</span></div><div class="chat-file-links"><a class="ghost-btn" href="${attachment.viewUrl}" target="_blank">${openLabel}</a>${attachment.downloadUrl ? `<a class="ghost-btn" href="${attachment.downloadUrl}" target="_blank">{{ '下载' if lang == 'zh' else 'Download' }}</a>` : ''}</div></div>`;
  }
  return '';
}

function getMessageTextForTranslate(item) {
  return item?.dataset?.messageText || '';
}

function renderChatMessageState(item, data) {
  const withdrawn = !!data.withdrawn;
  const text = data.message || '';
  const canRetract = !withdrawn && (String(data.senderUserId || '') === String({{ current_user.id|tojson }}) || IS_HOST === true || IS_HOST === 'true');
  item.dataset.withdrawn = withdrawn ? '1' : '0';
  item.dataset.messageText = text;
  item.dataset.messageId = data.id || '';
  item.dataset.senderUserId = data.senderUserId || '';
  item.dataset.senderSid = data.from || '';
  item.innerHTML = `
    <div class="chat-message-head">
      <strong>${escapeHtml(data.senderName || 'Guest')}</strong>
      <span>${data.mode === 'host' ? '{{ '仅主持人' if lang == 'zh' else 'Host only' }}' : '{{ '公开' if lang == 'zh' else 'Public' }}'}</span>
      <span>${escapeHtml(data.createdAt || '')}</span>
    </div>
    <div class="chat-message-body${withdrawn ? ' withdrawn' : ''}">${withdrawn ? TEXT_CHAT_WITHDRAWN : `${((data.mentions || []).map(m => `<span class="mention-badge">@${escapeHtml(String(m).replace(/^@/, ''))}</span>`).join(''))}${escapeHtml(text).replace(/\n/g, '<br>')}`}</div>
    ${withdrawn ? '' : buildAttachmentHtml(data.attachment)}
    <div class="chat-message-actions">
      ${text ? `<button type="button" class="msg-action-btn" data-action="copy">{{ '复制' if lang == 'zh' else 'Copy' }}</button>` : ''}
      ${text ? `<button type="button" class="msg-action-btn" data-action="translate">{{ '翻译' if lang == 'zh' else 'Translate' }}</button>` : ''}
      ${canRetract ? `<button type="button" class="msg-action-btn danger" data-action="retract">{{ '撤回' if lang == 'zh' else 'Retract' }}</button>` : ''}
    </div>
  `;
}

function appendChatMessage(data) {
  if (!chatMessages || !data) return;
  const shouldStickToBottom = isChatNearBottom() || String(data.senderUserId || '') === String({{ current_user.id|tojson }});
  let item = data.id ? chatMessages.querySelector(`.chat-message[data-message-id="${data.id}"]`) : null;
  if (!item) {
    item = document.createElement('div');
    item.className = 'chat-message ' + (data.mode === 'host' ? 'host-only' : '');
    chatMessages.appendChild(item);
  } else {
    item.className = 'chat-message ' + (data.mode === 'host' ? 'host-only' : '');
  }
  renderChatMessageState(item, data);
  if (!data.preserveScroll && shouldStickToBottom) {
    requestAnimationFrame(() => {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    });
  }
  if (PREF_ENABLE_DANMAKU && danmakuEnabled && data.mode === 'all' && data.message && !data.withdrawn) showDanmaku(`${data.senderName}: ${data.message}`);
}

async function copyText(text) {
  if (!text) return false;

  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      setStatus(TEXT_COPY_SUCCESS);
      return true;
    }
  } catch (_) {}

  try {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', 'readonly');
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    ta.style.pointerEvents = 'none';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    ta.setSelectionRange(0, ta.value.length);
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    if (ok) {
      setStatus(TEXT_COPY_SUCCESS);
      return true;
    }
  } catch (_) {}

  try {
    const input = document.getElementById('inviteInput');
    if (input) {
      input.focus();
      input.removeAttribute('readonly');
      input.select();
      input.setSelectionRange(0, input.value.length);
      input.setAttribute('readonly', 'readonly');
    }
  } catch (_) {}

  setStatus({{ ('复制失败，请长按或手动复制' if lang == 'zh' else 'Copy failed, please copy manually')|tojson }}, 'error');
  return false;
}

async function translateToEnglish(item, text) {
  if (!text || !item) return;
  let box = item.querySelector('.chat-translation');
  if (!box) {
    box = document.createElement('div');
    box.className = 'chat-translation';
    item.appendChild(box);
  }
  box.textContent = {{ ('翻译中…' if lang == 'zh' else 'Translating...')|tojson }};
  try {
    const resp = await fetch('/api/translate_message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    const data = await resp.json();
    if (!resp.ok || !data.ok) throw new Error(data.error || 'translate_failed');
    const target = String(data.target || '').toLowerCase();
    const label = target.startsWith('zh') ? {{ ('中文翻译' if lang == 'zh' else 'Chinese translation')|tojson }} : {{ ('英文翻译' if lang == 'zh' else 'English translation')|tojson }};
    box.innerHTML = `<div class="chat-translation-label">${escapeHtml(label)}</div><div>${escapeHtml(data.translation || '')}</div>`;
    setStatus({{ ('翻译已显示在消息下方' if lang == 'zh' else 'Translation shown below the message')|tojson }});
  } catch (err) {
    box.textContent = {{ ('翻译失败，请稍后重试' if lang == 'zh' else 'Translation failed. Please try again later.')|tojson }};
    setStatus(box.textContent, 'warning');
  }
}

function openContextMenu(x, y, items) {
  if (!chatContextMenu) return;
  chatContextMenu.innerHTML = items.map((item, idx) => `<button type="button" class="context-item${item.danger ? ' danger' : ''}" data-idx="${idx}">${item.label}</button>`).join('');
  const maxX = Math.max(12, window.innerWidth - 220);
  const maxY = Math.max(12, window.innerHeight - 220);
  chatContextMenu.style.left = `${Math.min(Math.max(12, x), maxX)}px`;
  chatContextMenu.style.top = `${Math.min(Math.max(12, y), maxY)}px`;
  chatContextMenu.classList.remove('hidden');
  chatContextMenu.querySelectorAll('.context-item').forEach(btn => {
    btn.addEventListener('click', () => {
      const picked = items[Number(btn.dataset.idx)];
      hideFloatingPanels();
      picked?.action?.();
    });
  });
}

function openMessageContextMenu(event, item) {
  event.preventDefault();
  event.stopPropagation();
  const text = getMessageTextForTranslate(item);
  const isWithdrawn = item.dataset.withdrawn === '1';
  const canRetract = !isWithdrawn && (String(item.dataset.senderUserId || '') === String({{ current_user.id|tojson }}) || IS_HOST === true || IS_HOST === 'true');
  const menu = [];
  if (canRetract) {
    menu.push({ label: {{ ('撤回消息' if lang == 'zh' else 'Retract message')|tojson }}, danger: true, action: () => socket.emit('meeting_chat_retract', { id: item.dataset.messageId }) });
  }
  if (text) {
    menu.push({ label: {{ ('复制文本' if lang == 'zh' else 'Copy text')|tojson }}, action: () => copyText(text) });
    menu.push({ label: {{ ('翻译消息' if lang == 'zh' else 'Translate message')|tojson }}, action: () => translateToEnglish(item, text) });
  }
  menu.push({ label: {{ ('清空聊天记录' if lang == 'zh' else 'Clear chat history')|tojson }}, danger: true, action: () => socket.emit('meeting_chat_clear') });
  openContextMenu(event.clientX, event.clientY, menu);
}

function openChatAreaContextMenu(event) {
  if (event.target.closest('.chat-message')) return;
  event.preventDefault();
  event.stopPropagation();
  openContextMenu(event.clientX, event.clientY, [
    { label: {{ ('清空聊天记录' if lang == 'zh' else 'Clear chat history')|tojson }}, danger: true, action: () => socket.emit('meeting_chat_clear') }
  ]);
}

function showDanmaku(text) {
  if (!danmakuLayer || !text) return;
  const node = document.createElement('div');
  node.className = 'danmaku-item';
  node.textContent = text;
  node.style.top = `${Math.max(8, Math.floor(Math.random() * 120))}px`;
  node.style.animationDuration = `${8 + Math.floor(Math.random() * 6)}s`;
  danmakuLayer.appendChild(node);
  setTimeout(() => node.remove(), 15000);
}


async function fileToDataUrl(file) {
  return await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function compressImageFile(file) {
  const imageUrl = URL.createObjectURL(file);
  try {
    const img = await new Promise((resolve, reject) => {
      const node = new Image();
      node.onload = () => resolve(node);
      node.onerror = reject;
      node.src = imageUrl;
    });
    const maxSide = 1600;
    const scale = Math.min(maxSide / img.width, maxSide / img.height, 1);
    const width = Math.max(1, Math.round(img.width * scale));
    const height = Math.max(1, Math.round(img.height * scale));
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d', { alpha: false });
    ctx.drawImage(img, 0, 0, width, height);
    let mime = 'image/jpeg';
    if (file.type === 'image/png' && file.size < 1024 * 1024) mime = 'image/png';
    const quality = mime === 'image/png' ? undefined : 0.82;
    const dataUrl = canvas.toDataURL(mime, quality);
    return { type: mime, name: file.name, dataUrl };
  } finally {
    URL.revokeObjectURL(imageUrl);
  }
}

function isChatNearBottom() {
  if (!chatMessages) return true;
  const remaining = chatMessages.scrollHeight - chatMessages.clientHeight - chatMessages.scrollTop;
  return remaining < 40;
}

function keepChatViewportStable(wasNearBottom) {
  if (!chatMessages) return;
  requestAnimationFrame(() => {
    if (wasNearBottom) {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
  });
}

function updateAttachmentPreview() {
  if (!chatAttachmentPreview) return;
  const wasNearBottom = isChatNearBottom();
  if (!pendingAttachment) {
    chatAttachmentPreview.classList.add('hidden');
    chatAttachmentPreview.innerHTML = '';
    keepChatViewportStable(wasNearBottom);
    return;
  }
  chatAttachmentPreview.classList.remove('hidden');
  const permissionText = (chatAttachmentPermission?.value || 'download') === 'download'
    ? {{ ('接收方可下载' if lang == 'zh' else 'Recipients can download')|tojson }}
    : {{ ('接收方仅可查看' if lang == 'zh' else 'Recipients can only view')|tojson }};
  if ((pendingAttachment.type || '').startsWith('image') && pendingAttachment.previewUrl) {
    chatAttachmentPreview.innerHTML = `<img class="chat-media" src="${pendingAttachment.previewUrl}" alt="preview" /><div class="chat-file-meta"><span>${escapeHtml(pendingAttachment.name || 'attachment')}</span><span>${permissionText}</span></div><button class="ghost-btn" id="clearAttachmentBtn">{{ '移除附件' if lang == 'zh' else 'Remove attachment' }}</button>`;
  } else if ((pendingAttachment.type || '').startsWith('video') && pendingAttachment.previewUrl) {
    chatAttachmentPreview.innerHTML = `<video class="chat-media" src="${pendingAttachment.previewUrl}" controls playsinline></video><div class="chat-file-meta"><span>${escapeHtml(pendingAttachment.name || 'attachment')}</span><span>${permissionText}</span></div><button class="ghost-btn" id="clearAttachmentBtn">{{ '移除附件' if lang == 'zh' else 'Remove attachment' }}</button>`;
  } else {
    chatAttachmentPreview.innerHTML = `<div class="chat-file-card"><div class="chat-file-meta"><strong>${escapeHtml(pendingAttachment.name || 'attachment')}</strong><span>${permissionText}</span></div><button class="ghost-btn" id="clearAttachmentBtn">{{ '移除附件' if lang == 'zh' else 'Remove attachment' }}</button></div>`;
  }
  document.getElementById('clearAttachmentBtn').onclick = () => { pendingAttachment = null; updateAttachmentPreview(); };
  keepChatViewportStable(wasNearBottom);
}

function setChatMode(mode) {
  activeChatMode = mode === 'host' ? 'host' : 'all';
  document.querySelectorAll('.chat-mode-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.mode === activeChatMode));
}

function extractMentions(text) {
  return Array.from(new Set((text.match(/@[\w一-龥.-]+/g) || []).map(x => x.replace(/^@/, ''))));
}

async function uploadPendingAttachment() {
  if (!pendingAttachment?.file) return null;
  const formData = new FormData();
  formData.append('room_id', ROOM_ID);
  formData.append('permission', chatAttachmentPermission?.value || 'download');
  formData.append('file', pendingAttachment.file, pendingAttachment.name || pendingAttachment.file.name || 'attachment');
  const endpoint = pendingAttachment.uploadKind === 'media' ? '/api/chat_upload_media' : '/api/chat_upload_doc';
  const resp = await fetch(endpoint, { method: 'POST', body: formData });
  const contentType = resp.headers.get('content-type') || '';
  let data = null;
  if (contentType.includes('application/json')) {
    data = await resp.json();
  } else {
    const text = await resp.text().catch(() => '');
    data = { ok: false, error: text || `http_${resp.status}` };
  }
  if (!resp.ok || !data.ok) {
    const errorCode = data?.error || `http_${resp.status}`;
    throw new Error(errorCode);
  }
  return data.attachment;
}

async function sendChatMessage() {
  const message = (chatInput.value || '').trim();
  if (!message && !pendingAttachment) return;
  let attachmentPayload = null;
  if (pendingAttachment) {
    try {
      attachmentPayload = await uploadPendingAttachment();
    } catch (err) {
      console.error(err);
      const msg = String(err?.message || '');
      if (msg.includes('room_storage_limit') || msg.includes('server_storage_limit')) {
        setStatus(TEXT_ROOM_STORAGE_LIMIT, 'warning');
      } else if (msg.includes('file_too_large') || msg.includes('http_413')) {
        const file = pendingAttachment?.file;
        const extra = msg.includes('http_413')
          ? {{ ('（服务器或 Nginx 上传上限过小，请同步调大 client_max_body_size）' if lang == 'zh' else '(Server or Nginx upload limit is too small. Increase client_max_body_size as well.)')|tojson }}
          : '';
        const baseMsg = file?.type?.startsWith('image/') ? TEXT_ATTACHMENT_LIMIT_IMAGE : (file?.type?.startsWith('video/') ? TEXT_ATTACHMENT_LIMIT_VIDEO : TEXT_ATTACHMENT_LIMIT_FILE);
        setStatus(`${baseMsg}${extra}`, 'warning');
      } else if (msg.includes('file_type_not_allowed')) {
        setStatus({{ ('该图片/视频格式被服务器拒绝，请换 jpg/png/mp4 或升级后重试' if lang == 'zh' else 'The server rejected this media format. Try jpg/png/mp4 or retry after upgrading.')|tojson }}, 'error');
      } else if (msg.includes('upload_internal_error')) {
        setStatus(TEXT_UPLOAD_FAILED + (msg ? ` (${msg})` : '') + {{ ('，后端已返回内部错误，请更新这一版后再试' if lang == 'zh' else ', the backend returned an internal error. Please try again with this build.')|tojson }}, 'error');
      } else {
        setStatus(TEXT_UPLOAD_FAILED + (msg ? ` (${msg})` : ''), 'error');
      }
      return;
    }
  }
  socket.emit('meeting_chat_send', {
    room_id: ROOM_ID,
    mode: activeChatMode,
    message,
    mentions: extractMentions(message),
    attachment: attachmentPayload,
  });
  chatInput.value = '';
  pendingAttachment = null;
  updateAttachmentPreview();
}

function normalizeChatLayout() {
  if (!chatWindow || !chatComposer) return;
  if (chatAttachmentPreview && chatAttachmentPreview.parentElement !== chatComposer) {
    chatComposer.insertBefore(chatAttachmentPreview, chatComposer.firstChild);
  }
  if (chatPermissionRow && chatPermissionRow.parentElement !== chatComposer) {
    chatComposer.insertBefore(chatPermissionRow, chatComposer.firstChild);
  }
}

function enableChatDrag() {
  const handle = document.getElementById('chatMobileHandle');
  if (!chatWindow || !handle) return;
  if (handle.dataset.bound === '1') return;
  handle.dataset.bound = '1';

  const isMobile = () => window.matchMedia('(max-width: 768px)').matches;
  const setHeight = (valuePx) => {
    const viewport = window.innerHeight || document.documentElement.clientHeight || 800;
    const minPx = Math.max(320, Math.round(viewport * 0.42));
    const maxPx = Math.max(minPx + 80, Math.round(viewport * 0.84));
    const next = Math.max(minPx, Math.min(maxPx, valuePx));
    chatWindow.style.setProperty('--mobile-chat-height', `${next}px`);
    return next;
  };

  const syncDefault = () => {
    if (!isMobile()) {
      chatWindow.style.removeProperty('--mobile-chat-height');
      return;
    }
    if (!chatWindow.style.getPropertyValue('--mobile-chat-height')) {
      setHeight(Math.round((window.innerHeight || 800) * 0.62));
    }
  };

  let dragging = false;
  let startY = 0;
  let startHeight = 0;

  const getY = (event) => event.touches?.[0]?.clientY ?? event.clientY;

  const onMove = (event) => {
    if (!dragging || !isMobile()) return;
    const currentY = getY(event);
    if (typeof currentY !== 'number') return;
    const delta = startY - currentY;
    setHeight(startHeight + delta);
    event.preventDefault?.();
  };

  const stopDrag = () => {
    dragging = false;
    document.body.classList.remove('chat-dragging');
  };

  const startDrag = (event) => {
    if (!isMobile()) return;
    dragging = true;
    startY = getY(event);
    startHeight = chatWindow.getBoundingClientRect().height;
    document.body.classList.add('chat-dragging');
    event.preventDefault?.();
  };

  handle.addEventListener('touchstart', startDrag, { passive: false });
  handle.addEventListener('mousedown', startDrag);
  window.addEventListener('touchmove', onMove, { passive: false });
  window.addEventListener('mousemove', onMove);
  window.addEventListener('touchend', stopDrag);
  window.addEventListener('mouseup', stopDrag);
  window.addEventListener('resize', syncDefault);
  window.addEventListener('resize', refreshChatCollapsedLayout);
  syncDefault();
}


function refreshChatCollapsedLayout() {
  if (!chatWindow) return;
  const collapsed = chatWindow.classList.contains('chat-collapsed');
  document.querySelector('.video-panel')?.classList.toggle('chat-collapsed-layout', !!collapsed && !window.matchMedia('(max-width: 768px)').matches);
}

function setChatCollapsed(collapsed) {
  if (!chatWindow) return;
  const showBtn = document.getElementById('chatShowBtn');
  const isMobile = window.matchMedia('(max-width: 768px)').matches;
  chatWindow.classList.toggle('chat-collapsed', !!collapsed);
  document.querySelector('.video-panel')?.classList.toggle('chat-collapsed-layout', !!collapsed && !isMobile);
  if (showBtn) {
    showBtn.classList.toggle('hidden', !collapsed);
    showBtn.style.display = collapsed ? 'inline-flex' : 'none';
  }
}

function initChatUi() {
  normalizeChatLayout();
  enableChatDrag();
  if (chatMessages) chatMessages.dataset.stuckBottom = '1';
  setChatCollapsed(false);
  renderMentionPicker();
  setChatMode('all');
  document.querySelectorAll('.chat-mode-btn').forEach(btn => btn.addEventListener('click', () => setChatMode(btn.dataset.mode)));
  document.getElementById('clearChatBtn')?.addEventListener('click', () => {
    if (confirm({{ ('确认清空当前会议聊天记录？' if lang == 'zh' else 'Clear the current meeting chat history?')|tojson }})) {
      socket.emit('meeting_chat_clear');
    }
  });
  chatAttachmentPermission?.addEventListener('change', updateAttachmentPreview);
  sendChatBtn?.addEventListener('click', sendChatMessage);
  chatInput?.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage(); } });
  document.getElementById('mentionBtn')?.addEventListener('click', () => { const willShow = mentionPicker.classList.contains('hidden'); emojiPopover?.classList.add('hidden'); if (willShow) { renderMentionPicker(''); mentionPicker.classList.remove('hidden'); } else { mentionPicker.classList.add('hidden'); } });
  document.getElementById('emojiBtn')?.addEventListener('click', () => { renderEmojiPicker(); emojiPopover?.classList.toggle('hidden'); mentionPicker.classList.add('hidden'); });
  document.getElementById('emojiCloseBtn')?.addEventListener('click', () => emojiPopover?.classList.add('hidden'));
  chatMessages?.addEventListener('scroll', () => {
    chatMessages.dataset.stuckBottom = isChatNearBottom() ? '1' : '0';
  }, { passive: true });

  chatMessages?.addEventListener('click', async (event) => {
    const btn = event.target.closest('.msg-action-btn');
    if (!btn) return;
    const item = btn.closest('.chat-message');
    if (!item) return;
    const action = btn.dataset.action;
    const text = getMessageTextForTranslate(item);
    if (action === 'copy') {
      await copyText(text);
    } else if (action === 'translate') {
      await translateToEnglish(item, text);
    } else if (action === 'retract') {
      socket.emit('meeting_chat_retract', { id: item.dataset.messageId });
    }
  });
  document.addEventListener('click', (e) => { if (!e.target.closest('#emojiBtn') && !e.target.closest('#emojiPopover') && !e.target.closest('#mentionBtn') && !e.target.closest('#mentionPicker')) hideFloatingPanels(); });
  const prepareAttachment = async (file, uploadKind) => {
    if (!file) return;
    try {
      const isImage = file.type.startsWith('image/');
      const isVideo = file.type.startsWith('video/');
      const ext = (file.name.split('.').pop() || '').toLowerCase();
      const mediaAllowed = ['png','jpg','jpeg','gif','webp','bmp','heic','heif','mp4','webm','mov','m4v','avi','3gp'];
      const docAllowed = ['pdf','doc','docx','ppt','pptx','xls','xlsx','txt','zip','rar','7z'];
      if (uploadKind === 'media') {
        if ((!mediaAllowed.includes(ext)) && !isImage && !isVideo) {
          setStatus({{ ('暂不支持该图片或视频格式' if lang == 'zh' else 'This media format is not supported yet')|tojson }}, 'warning');
          return;
        }
      } else {
        if (!docAllowed.includes(ext)) {
          setStatus({{ ('暂不支持该文档类型' if lang == 'zh' else 'This document type is not supported yet')|tojson }}, 'warning');
          return;
        }
      }
      const limit = isImage ? (25 * 1024 * 1024) : (isVideo ? (120 * 1024 * 1024) : (25 * 1024 * 1024));
      if (file.size > limit) {
        setStatus(isImage ? TEXT_ATTACHMENT_LIMIT_IMAGE : (isVideo ? TEXT_ATTACHMENT_LIMIT_VIDEO : TEXT_ATTACHMENT_LIMIT_FILE), 'warning');
        return;
      }
      let previewUrl = '';
      if (isImage || isVideo) previewUrl = URL.createObjectURL(file);
      pendingAttachment = { type: file.type || 'application/octet-stream', name: file.name, file, previewUrl, uploadKind };
      updateAttachmentPreview();
      setStatus({{ ('附件已准备好，可发送' if lang == 'zh' else 'Attachment is ready to send')|tojson }});
    } catch (err) {
      console.error(err);
      setStatus({{ ('附件处理失败' if lang == 'zh' else 'Failed to process attachment')|tojson }}, 'error');
    }
  };

  chatMediaInput?.addEventListener('change', async (e) => {
    const file = e.target.files?.[0];
    await prepareAttachment(file, 'media');
    e.target.value = '';
  });
  chatDocInput?.addEventListener('change', async (e) => {
    const file = e.target.files?.[0];
    await prepareAttachment(file, 'doc');
    e.target.value = '';
  });
  document.getElementById('toggleDanmakuBtn')?.addEventListener('click', () => socket.emit('toggle_danmaku', { enabled: !danmakuEnabled }));
  document.getElementById('chatHideBtn')?.addEventListener('click', () => setChatCollapsed(true));
  document.getElementById('chatShowBtn')?.addEventListener('click', () => setChatCollapsed(false));
}

function broadcastUiEvent(payload) {
  socket.emit('room_ui_event', payload);
}

function cleanupMeetingSession() {
  if (hasLeftMeeting) return;
  hasLeftMeeting = true;
  try {
    if (activeRecorder && activeRecorder.state !== 'inactive') activeRecorder.stop();
  } catch (_) {}
  try { recorderStream?.getTracks?.().forEach(track => track.stop()); } catch (_) {}
  recorderStream = null;
  try { stopStreamTracks(localStream); } catch (_) {}
  try { stopStreamTracks(rawCameraStream); } catch (_) {}
  try { stopStreamTracks(processedCanvasStream); } catch (_) {}
  Object.values(peerConnections).forEach(pc => {
    try { pc.close(); } catch (_) {}
  });
  peerConnections = {};
  participantMeta = {};
}

function leaveMeetingAndExit(message = TEXT_YOU_LEFT_MEETING, redirectUrl = '/') {
  cleanupMeetingSession();
  try { socket.emit('leave_room'); } catch (_) {}
  try { socket.disconnect(); } catch (_) {}
  if (message) alert(message);
  window.location.href = redirectUrl;
}

socket.on('connect', async () => {
  ensureCard('local', getDisplayName('local'), true);
  renderLayout();
  if ((PREF_AUTO_ENABLE_CAMERA || PREF_AUTO_ENABLE_MICROPHONE) && !rawCameraStream && !localStream) await requestMedia(currentFacingMode, false);
  socket.emit('join_room', { room_id: ROOM_ID, password: ROOM_PASSWORD, user_name: USER_NAME });
});

socket.on('join_ok', async (data) => {
  participantCountEl.textContent = data.participant_count;
  chatMessages.innerHTML = '';
  for (const p of data.participants) addRemoteParticipant(p.sid, p.name);
  (data.chat_history || []).forEach(item => appendChatMessage(item));
  focusParticipant('local');
  danmakuEnabled = !!data.danmaku_enabled;
  currentSharerSid = data?.active_sharer_sid || null;
  if (currentSharerSid) {
    focusedSid = currentSharerSid;
    hiddenSidebar = true;
    renderLayout();
  } else {
    updateShareUiState();
  }
  if (data && data.host_present === false && IS_HOST) {
    setStatus(TEXT_HOST_RETURNED_ROOM);
  } else if (data && data.host_present === false) {
    setStatus(TEXT_HOST_LEFT_ROOM, 'warning');
  }
});

socket.on('participant_joined', async (data) => {
  addRemoteParticipant(data.sid, data.name);
  participantCountEl.textContent = data.participant_count;
  await callPeer(data.sid);
});

socket.on('participant_left', (data) => {
  participantCountEl.textContent = data.participant_count;
  if (currentGridPage > 0) currentGridPage = Math.max(0, currentGridPage - 1);
  removeRemoteVideo(data.sid);
  renderMentionPicker();
});

socket.on('participant_snapshot', (data) => {
  const list = Array.isArray(data?.participants) ? data.participants : [];
  const count = Number(data?.participant_count || list.length || 0);
  const keep = new Set();
  list.forEach((item) => {
    if (!item?.sid || item.sid === socket.id) return;
    keep.add(item.sid);
    if (!participantMeta[item.sid]) {
      addRemoteParticipant(item.sid, item.name || item.sid);
    } else {
      participantMeta[item.sid].name = item.name || item.sid;
      const labelEl = document.querySelector(`#card-${CSS.escape(item.sid)} .video-label`);
      if (labelEl) labelEl.textContent = item.name || item.sid;
    }
  });
  Object.keys(participantMeta).forEach((sid) => {
    if (!keep.has(sid)) removeRemoteVideo(sid);
  });
  participantCountEl.textContent = String(Math.max(1, count));
  renderMentionPicker();
});

socket.on('participant_updated', (data) => {
  if (!data || !data.sid) return;
  if (data.sid === socket.id) { USER_NAME = data.name; }
  if (participantMeta[data.sid]) participantMeta[data.sid].name = data.name;
  const card = document.getElementById('card-' + data.sid);
  const labelEl = card?.querySelector('.video-label');
  if (labelEl) labelEl.textContent = data.name;
  renderMentionPicker();
});

socket.on('meeting_chat_message', (data) => appendChatMessage(data));
socket.on('meeting_chat_cleared', (data) => {
  if (chatMessages) chatMessages.innerHTML = '';
  const scope = data?.scope || 'all';
  setStatus(scope === 'self' ? TEXT_CHAT_CLEARED_SELF : TEXT_CHAT_CLEARED_ALL);
  hideFloatingPanels();
});
socket.on('meeting_chat_retracted', (data) => {
  const item = data?.id ? chatMessages?.querySelector(`.chat-message[data-message-id="${data.id}"]`) : null;
  if (!item) return;
  renderChatMessageState(item, {
    id: data.id,
    senderName: data.senderName || item.querySelector('strong')?.textContent || 'Guest',
    mode: item.classList.contains('host-only') ? 'host' : 'all',
    createdAt: item.querySelector('.chat-message-head span:last-child')?.textContent || '',
    message: '',
    mentions: [],
    attachment: null,
    withdrawn: true,
    senderUserId: item.dataset.senderUserId || '' ,
    from: item.dataset.senderSid || ''
  });
});

socket.on('join_error', (data) => {
  alert(data.message || 'Join failed');
  window.location.href = '/';
});

socket.on('force_leave', (data) => {
  cleanupMeetingSession();
  alert(data.message || TEXT_MEETING_CLOSED);
  window.location.href = '/';
});

socket.on('force_logout', (data) => {
  cleanupMeetingSession();
  try { socket.disconnect(); } catch (_) {}
  alert(data?.message || {{ t('kicked')|tojson }});
  window.location.href = '/login?kicked=1';
});

socket.on('host_presence_changed', (data) => {
  if (!data) return;
  setStatus(data.message || (data.host_present ? TEXT_HOST_RETURNED_ROOM : TEXT_HOST_LEFT_ROOM), data.host_present ? '' : 'warning');
});

socket.on('host_action_error', (data) => {
  setStatus(data?.message || 'Action failed', 'error');
});

socket.on('signal', async (data) => {
  const from = data.from;
  const pc = ensurePeer(from);
  try {
    if (data.description) {
      await pc.setRemoteDescription(data.description);
      if (data.description.type === 'offer') {
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        socket.emit('signal', { target: from, from: socket.id, description: pc.localDescription, senderName: USER_NAME });
      }
    } else if (data.candidate) {
      await pc.addIceCandidate(data.candidate);
    }
  } catch (err) {
    console.error(err);
  }
});

socket.on('room_ui_event', (data) => {
  if (!data || !data.type) return;
  if (data.type === 'screen_share_started') {
    currentSharerSid = data.from;
    focusParticipant(data.from, { hideSidebar: true, screenShare: true });
    setStatus(TEXT_SCREEN_SHARE_MODE);
  } else if (data.type === 'screen_share_stopped') {
    currentSharerSid = null;
    hiddenSidebar = false;
    focusedSid = 'local';
    renderLayout();
    setStatus(TEXT_SCREEN_SHARE_STOPPED);
  } else if (data.type === 'screen_share_denied') {
    currentSharerSid = data.activeSharerSid || currentSharerSid;
    updateShareUiState();
    setStatus(data.message || {{ ('已有其他用户正在共享屏幕' if lang == 'zh' else 'Another participant is already sharing the screen')|tojson }}, 'warning');
  } else if (data.type === 'danmaku_toggled') {
    danmakuEnabled = !!data.enabled;
    setStatus(danmakuEnabled ? TEXT_DANMAKU_ON : TEXT_DANMAKU_OFF);
  }
});

document.addEventListener('fullscreenchange', () => {
  if (!getFullscreenElement() && screen.orientation?.unlock) {
    try { screen.orientation.unlock(); } catch (_) {}
  }
  if (getFullscreenElement()) {
    clearSimulatedFullscreen();
  }
  roomDebugLog('fullscreenchange', { active: !!getFullscreenElement(), simulated: !!getSimulatedFullscreenCard() });
});

document.addEventListener('webkitfullscreenchange', () => {
  if (!getFullscreenElement() && screen.orientation?.unlock) {
    try { screen.orientation.unlock(); } catch (_) {}
  }
  if (getFullscreenElement()) {
    clearSimulatedFullscreen();
  }
  roomDebugLog('webkitfullscreenchange', { active: !!getFullscreenElement(), simulated: !!getSimulatedFullscreenCard() });
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && getSimulatedFullscreenCard()) {
    clearSimulatedFullscreen();
  }
});

window.addEventListener('resize', () => {
  const totalCards = getRenderableCards().length;
  const totalPages = Math.max(1, Math.ceil(totalCards / getGridPageSize()));
  currentGridPage = Math.min(currentGridPage, totalPages - 1);
  if (hasActiveFullscreenSession()) {
    pendingLayoutAfterFullscreen = true;
    roomDebugLog('resize while fullscreen active; layout deferred');
    return;
  }
  renderLayout();
});

videoPrevPageBtn?.addEventListener('click', () => {
  if (currentGridPage <= 0) return;
  currentGridPage -= 1;
  renderLayout();
});
videoNextPageBtn?.addEventListener('click', () => {
  const totalCards = getRenderableCards().length;
  const totalPages = Math.max(1, Math.ceil(totalCards / getGridPageSize()));
  if (currentGridPage >= totalPages - 1) return;
  currentGridPage += 1;
  renderLayout();
});
videoHomePageBtn?.addEventListener('click', () => {
  if (currentGridPage <= 0) return;
  currentGridPage = 0;
  renderLayout();
});

document.getElementById('toggleMicBtn').onclick = async () => {
  let rawTrack = rawCameraStream?.getAudioTracks?.()[0] || localStream?.getAudioTracks?.()[0];
  if (!rawTrack) {
    rawTrack = await ensureRequestedTrack('audio');
    if (!rawTrack) return;
  }
  rawTrack.enabled = !rawTrack.enabled;
  const localTrack = localStream?.getAudioTracks?.()[0];
  if (localTrack && localTrack !== rawTrack) localTrack.enabled = rawTrack.enabled;
  setStatus(rawTrack.enabled ? TEXT_MIC_ON : TEXT_MIC_OFF);
};
document.getElementById('toggleCameraBtn').onclick = async () => {
  let rawTrack = rawCameraStream?.getVideoTracks?.()[0] || localStream?.getVideoTracks?.()[0];
  const localCard = ensureCard('local', getDisplayName('local'), true);
  if (!rawTrack) {
    rawTrack = await ensureRequestedTrack('video');
    if (!rawTrack) return;
  }
  rawTrack.enabled = !rawTrack.enabled;
  const outputVideoTrack = localStream?.getVideoTracks?.()[0];
  if (outputVideoTrack && outputVideoTrack !== rawTrack) outputVideoTrack.enabled = rawTrack.enabled;
  updatePlaceholder(localCard, rawTrack.enabled);
  if (rawTrack.enabled) {
    await syncPeerMedia().catch(err => console.error(err));
  }
  setStatus(rawTrack.enabled ? TEXT_CAMERA_ON : TEXT_CAMERA_OFF);
};
document.getElementById('shareScreenBtn').onclick = async () => {
  if (!navigator.mediaDevices?.getDisplayMedia) {
    setStatus({{ ('当前设备/浏览器不支持共享屏幕' if lang == 'zh' else 'This device/browser does not support screen sharing')|tojson }}, 'warning');
    return;
  }
  if (currentSharerSid && currentSharerSid !== 'local') {
    setStatus({{ ('已有其他用户正在共享屏幕' if lang == 'zh' else 'Another participant is already sharing the screen')|tojson }}, 'warning');
    return;
  }
  try {
    const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true });
    const screenTrack = screenStream.getVideoTracks()[0];
    const screenCard = ensureCard('local', getDisplayName('local'), true);
    Object.values(peerConnections).forEach(pc => {
      const sender = pc.getSenders().find(s => s.track && s.track.kind === 'video');
      if (sender) sender.replaceTrack(screenTrack);
    });
    localVideo.srcObject = screenStream;
    safePlayVideo(localVideo);
    updatePlaceholder(screenCard, true);
    isSharingScreen = true;
    currentSharerSid = 'local';
    hiddenSidebar = true;
    focusedSid = 'local';
    renderLayout();
    setStatus(TEXT_SCREEN_SHARE_MODE);
    broadcastUiEvent({ type: 'screen_share_started', hideSidebar: true });

    screenTrack.onended = async () => {
      isSharingScreen = false;
      if (virtualBgImageDataUrl) {
        await activateVirtualBackground();
      } else if (rawCameraStream) {
        fallbackToRawCamera();
      } else {
        await requestMedia(currentFacingMode, true, ['video', 'audio']);
      }
      currentSharerSid = null;
      hiddenSidebar = false;
      focusedSid = 'local';
      renderLayout();
      broadcastUiEvent({ type: 'screen_share_stopped' });
      setStatus(TEXT_SCREEN_SHARE_STOPPED);
    };
  } catch (err) {
    setStatus(err.message, 'error');
  }
};
document.getElementById('virtualBgBtn').onclick = async () => {
  if (isSharingScreen || currentSharerSid) {
    setStatus({{ ('共享屏幕期间不可使用虚拟背景' if lang == 'zh' else 'Virtual background is unavailable during screen sharing')|tojson }}, 'warning');
    return;
  }
  if (virtualBgEnabled) {
    deactivateVirtualBackground(TEXT_VIRTUAL_BG_OFF);
    return;
  }
  if (!rawCameraStream) {
    await requestMedia(currentFacingMode, true);
    if (!rawCameraStream) return;
  }
  setStatus(TEXT_VIRTUAL_BG_PICK, 'warning');
  virtualBgInput.click();
};
virtualBgInput.onchange = async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    virtualBgImageDataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
    if (!rawCameraStream) {
      await requestMedia(currentFacingMode, true);
      if (!rawCameraStream) return;
    }
    await activateVirtualBackground();
  } catch (err) {
    console.error(err);
    setStatus(TEXT_VIRTUAL_BG_FAILED + ': ' + (err.message || TEXT_IMAGE_NOT_SUPPORTED), 'warning');
  } finally {
    event.target.value = '';
  }
};
recordingBtn.onclick = () => toggleScreenRecording();
document.getElementById('leaveMeetingBtn').onclick = () => {
  if (confirm(TEXT_LEAVE_CONFIRM)) {
    leaveMeetingAndExit(TEXT_YOU_LEFT_MEETING);
  }
};
if (hostEndMeetingBtn) {
  hostEndMeetingBtn.onclick = () => {
    if (confirm(TEXT_HOST_END_CONFIRM)) {
      socket.emit('host_end_meeting', { room_id: ROOM_ID });
    }
  };
}

document.getElementById('saveProfileBtn').onclick = () => {
  const name = (document.getElementById('displayNameInput').value || '').trim();
  if (!name) return;
  USER_NAME = name;
  localStorage.setItem('meeting_display_name', name);
  socket.emit('update_profile', { name });
  ensureCard('local', getDisplayName('local'), true);
  renderMentionPicker();
  setStatus(TEXT_PROFILE_UPDATED);
};
document.getElementById('switchRoomBtn').onclick = async () => {
  const nextRoomId = document.getElementById('switchRoomId').value.trim();
  const nextPwd = document.getElementById('switchRoomPassword').value.trim();
  if (!nextRoomId || !nextPwd) return;
  const res = await fetch('/api/join_room', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ room_id: nextRoomId, password: nextPwd }) });
  const data = await res.json();
  if (!res.ok || !data.success) { setStatus(data.message || 'failed', 'error'); return; }
  leaveMeetingAndExit(null, `/room/${nextRoomId}?pwd=${encodeURIComponent(nextPwd)}`);
};

window.addEventListener('beforeunload', () => {
  if (!hasLeftMeeting) {
    try { socket.emit('leave_room'); } catch (_) {}
  }
});

initChatUi();
ensureCard('local', getDisplayName('local'), true);
renderLayout();

async function refreshTrafficPanel() {
  try {
    const res = await fetch('/api/traffic_summary');
    if (!res.ok) return;
    const data = await res.json();
    const total = document.getElementById('trafficQuotaTotal');
    const used = document.getElementById('trafficQuotaUsed');
    const remaining = document.getElementById('trafficQuotaRemaining');
    const reset = document.getElementById('trafficQuotaReset');
    if (total) total.textContent = data.monthly_quota_text;
    if (used) used.textContent = data.used_traffic_text;
    if (remaining) remaining.textContent = data.remaining_traffic_text;
    if (reset) reset.textContent = data.reset_at_text;
    if ((data.remaining_traffic_mb || 0) <= 0) {
      leaveMeetingAndExit(TEXT_TRAFFIC_LIMIT_REACHED);
    }
  } catch (_) {}
}

refreshTrafficPanel();
setInterval(refreshTrafficPanel, 20000);
