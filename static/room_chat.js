(function (global) {
  const { escapeHtml, copyText } = global.RoomPageUtils || {};

  function getMentionablePeople() {
    const byName = new Map();
    [{ sid: 'local', name: global.USER_NAME }]
      .concat(Object.entries(global.participantMeta || {}).map(([sid, info]) => ({ sid, name: info.name || sid })))
      .forEach((person) => {
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
    const mentionPicker = global.mentionPicker;
    const chatInput = global.chatInput;
    mentionPicker.innerHTML = `
      <div class="mention-dropdown">
        <div class="mention-dropdown-head">
          <span class="mention-dropdown-title">${escapeHtml(global.MENTION_ALL_TEXT)}</span>
          <button type="button" class="card-btn mention-collapse-btn">${escapeHtml(global.TEXT_MENTION_COLLAPSE)}</button>
        </div>
        <div class="mention-search-wrap">
          <input id="mentionSearchInput" class="mention-search-input" type="text" autocomplete="off" autocapitalize="off" spellcheck="false" inputmode="text" placeholder="${escapeHtml(global.MENTION_SEARCH_PLACEHOLDER)}" value="${escapeHtml(rawFilterText)}" />
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
      const filtered = keyword ? people.filter((person) => normalizeMentionKeyword(person.name).includes(keyword)) : people;
      optionList.innerHTML = filtered.length
        ? filtered.map((person) => `<button type="button" class="mention-option mention-option-row" data-name="${escapeHtml(person.name)}"><span class="mention-option-at">@</span><span class="mention-option-name">${escapeHtml(person.name)}</span></button>`).join('')
        : `<div class="mention-empty">${escapeHtml(global.MENTION_EMPTY_TEXT)}</div>`;

      optionList.querySelectorAll('.mention-option').forEach((btn) => {
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
    const mentionPicker = global.mentionPicker;
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
    const emojiPicker = global.emojiPicker;
    const chatInput = global.chatInput;
    if (!emojiPicker) return;
    emojiPicker.innerHTML = global.CHAT_EMOJIS.map((emoji) => `<button type="button" class="emoji-option" data-emoji="${emoji}">${emoji}</button>`).join('');
    emojiPicker.querySelectorAll('.emoji-option').forEach((btn) => {
      btn.addEventListener('click', () => {
        chatInput.value = `${chatInput.value}${btn.dataset.emoji}`;
        chatInput.focus();
      });
    });
  }

  function hideFloatingPanels() {
    global.mentionPicker?.classList.add('hidden');
    global.emojiPopover?.classList.add('hidden');
    global.chatContextMenu?.classList.add('hidden');
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
    const permissionLabel = attachment.permission === 'download' ? global.TEXT_PERMISSION_DOWNLOAD_ALLOWED : global.TEXT_PERMISSION_VIEW_ONLY;
    const openLabel = attachment.permission === 'download' ? global.TEXT_ATTACHMENT_OPEN : global.TEXT_ATTACHMENT_VIEW;
    const downloadLabel = global.TEXT_DOWNLOAD_LABEL;
    const rawUrl = attachment.rawUrl || '';
    if (rawUrl && attachment.kind === 'image') {
      return `<div class="chat-attachment-block"><img class="chat-media" src="${rawUrl}" alt="${name}" /><div class="chat-file-meta"><span>${name}</span><span>${permissionLabel}</span></div><div class="chat-file-links"><a class="ghost-btn" href="${attachment.viewUrl}" target="_blank">${openLabel}</a>${attachment.downloadUrl ? `<a class="ghost-btn" href="${attachment.downloadUrl}" target="_blank">${downloadLabel}</a>` : ''}</div></div>`;
    }
    if (rawUrl && attachment.kind === 'video') {
      return `<div class="chat-attachment-block"><video class="chat-media" src="${rawUrl}" controls playsinline preload="metadata"></video><div class="chat-file-meta"><span>${name}</span><span>${permissionLabel}</span></div><div class="chat-file-links"><a class="ghost-btn" href="${attachment.viewUrl}" target="_blank">${openLabel}</a>${attachment.downloadUrl ? `<a class="ghost-btn" href="${attachment.downloadUrl}" target="_blank">${downloadLabel}</a>` : ''}</div></div>`;
    }
    if (attachment.viewUrl) {
      return `<div class="chat-attachment-block chat-file-card standardized"><div class="chat-file-badge">${getAttachmentBadge(attachment)}</div><div class="chat-file-meta"><strong>${name}</strong><span>${permissionLabel}</span></div><div class="chat-file-links"><a class="ghost-btn" href="${attachment.viewUrl}" target="_blank">${openLabel}</a>${attachment.downloadUrl ? `<a class="ghost-btn" href="${attachment.downloadUrl}" target="_blank">${downloadLabel}</a>` : ''}</div></div>`;
    }
    return '';
  }

  function getMessageTextForTranslate(item) {
    return item?.dataset?.messageText || '';
  }

  function renderChatMessageState(item, data) {
    const withdrawn = !!data.withdrawn;
    const text = data.message || '';
    const currentUserId = String(global.CURRENT_USER_ID || '');
    const canRetract = !withdrawn && (String(data.senderUserId || '') === currentUserId || global.IS_HOST === true || global.IS_HOST === 'true');
    item.dataset.withdrawn = withdrawn ? '1' : '0';
    item.dataset.messageText = text;
    item.dataset.messageId = data.id || '';
    item.dataset.senderUserId = data.senderUserId || '';
    item.dataset.senderSid = data.from || '';
    item.innerHTML = `
      <div class="chat-message-head">
        <strong>${escapeHtml(data.senderName || 'Guest')}</strong>
        <span>${data.mode === 'host' ? global.TEXT_CHAT_MODE_HOST : global.TEXT_CHAT_MODE_PUBLIC}</span>
        <span>${escapeHtml(data.createdAt || '')}</span>
      </div>
      <div class="chat-message-body${withdrawn ? ' withdrawn' : ''}">${withdrawn ? global.TEXT_CHAT_WITHDRAWN : `${((data.mentions || []).map((m) => `<span class="mention-badge">@${escapeHtml(String(m).replace(/^@/, ''))}</span>`).join(''))}${escapeHtml(text).replace(/\n/g, '<br>')}`}</div>
      ${withdrawn ? '' : buildAttachmentHtml(data.attachment)}
      <div class="chat-message-actions">
        ${text ? `<button type="button" class="msg-action-btn" data-action="copy">${global.TEXT_COPY_BUTTON}</button>` : ''}
        ${text ? `<button type="button" class="msg-action-btn" data-action="translate">${global.TEXT_TRANSLATE_BUTTON}</button>` : ''}
        ${canRetract ? `<button type="button" class="msg-action-btn danger" data-action="retract">${global.TEXT_RETRACT_BUTTON}</button>` : ''}
      </div>
    `;
  }

  function appendChatMessage(data) {
    const chatMessages = global.chatMessages;
    if (!chatMessages || !data) return;
    const shouldStickToBottom = global.isChatNearBottom() || String(data.senderUserId || '') === String(global.CURRENT_USER_ID || '');
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
    if (global.PREF_ENABLE_DANMAKU && global.danmakuEnabled && data.mode === 'all' && data.message && !data.withdrawn) global.showDanmaku(`${data.senderName}: ${data.message}`);
  }

  global.RoomPageChat = {
    getMentionablePeople,
    normalizeMentionKeyword,
    buildMentionPickerShell,
    renderMentionPicker,
    renderEmojiPicker,
    hideFloatingPanels,
    getAttachmentExt,
    getAttachmentBadge,
    buildAttachmentHtml,
    getMessageTextForTranslate,
    renderChatMessageState,
    appendChatMessage,
    copyText,
  };
})(window);
