(function (global) {
  function normalizeParticipantSid(sid) {
    if (!sid) return sid;
    const socketId = global.socket?.id;
    return sid === socketId ? 'local' : sid;
  }

  function setStatus(msg, cls = '') {
    const statusBox = global.statusBox;
    if (!statusBox) return;
    statusBox.className = 'notice ' + cls;
    statusBox.textContent = msg;
  }

  function stopStreamTracks(stream) {
    if (!stream) return;
    stream.getTracks().forEach((track) => {
      try { track.stop(); } catch (_) {}
    });
  }

  function escapeHtml(text) {
    return String(text || '').replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  }

  async function copyText(text) {
    if (!text) return false;

    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        setStatus(global.TEXT_COPY_SUCCESS);
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
        setStatus(global.TEXT_COPY_SUCCESS);
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

    setStatus(global.TEXT_COPY_FAILED_MANUAL, 'error');
    return false;
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

  global.RoomPageUtils = {
    normalizeParticipantSid,
    setStatus,
    stopStreamTracks,
    escapeHtml,
    copyText,
    fileToDataUrl,
    compressImageFile,
  };
})(window);
