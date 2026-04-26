(function (global) {
  function bindSocketEvents(ctx) {
    const {
      socket,
      ensureCard,
      getDisplayName,
      queueRenderLayout,
      ROOM_ID,
      ROOM_PASSWORD,
      USER_NAME,
      ensureLiveKitController,
      LIVEKIT_URL,
      participantCountEl,
      chatMessages,
      syncParticipantRoster,
      appendChatMessage,
      focusParticipant,
      finalizeJoinBootstrap,
      refreshRtcDiagnostics,
      setStatus,
      TEXT_HOST_RETURNED_ROOM,
      TEXT_HOST_LEFT_ROOM,
      IS_HOST,
      addRemoteParticipant,
      removeRemoteVideo,
      renderMentionPicker,
      applySnapshotSharerState,
      participantMetaRef,
      documentRef,
      normalizeParticipantSid,
      syncScreenShareSpeakerRule,
      updateShareUiState,
      TEXT_SCREEN_SHARE_MODE,
      TEXT_SCREEN_SHARE_STOPPED,
      TEXT_DANMAKU_ON,
      TEXT_DANMAKU_OFF,
      hideFloatingPanels,
      renderChatMessageState,
      cleanupMeetingSession,
      TEXT_MEETING_CLOSED,
      TEXT_KICKED,
      TEXT_SCREEN_SHARE_DENIED,
      roomState,
    } = ctx;

    socket.on('connect', () => {
      ensureCard('local', getDisplayName('local'), true);
      queueRenderLayout();
      socket.emit('join_room', { room_id: ROOM_ID, password: ROOM_PASSWORD, user_name: USER_NAME() });
      ensureLiveKitController()?.prepareConnection?.(LIVEKIT_URL);
    });

    socket.on('join_ok', async (data) => {
      participantCountEl.textContent = data.participant_count;
      chatMessages.innerHTML = '';
      const existingParticipants = Array.isArray(data?.participants) ? data.participants : [];
      syncParticipantRoster(existingParticipants);
      (data.chat_history || []).forEach((item) => appendChatMessage(item));
      focusParticipant('local');
      roomState.setDanmakuEnabled(!!data.danmaku_enabled);
      await finalizeJoinBootstrap(data);
      refreshRtcDiagnostics().catch(() => {});
      if (data && data.host_present === false && IS_HOST) {
        setStatus(TEXT_HOST_RETURNED_ROOM);
      } else if (data && data.host_present === false) {
        setStatus(TEXT_HOST_LEFT_ROOM, 'warning');
      }
    });

    socket.on('participant_joined', async (data) => {
      addRemoteParticipant(data.sid, data.name, !!data.is_host);
      participantCountEl.textContent = data.participant_count;
      refreshRtcDiagnostics().catch(() => {});
    });

    socket.on('participant_left', (data) => {
      participantCountEl.textContent = data.participant_count;
      if (roomState.getCurrentGridPage() > 0) {
        roomState.setCurrentGridPage(Math.max(0, roomState.getCurrentGridPage() - 1));
      }
      removeRemoteVideo(data.sid);
      renderMentionPicker();
      refreshRtcDiagnostics().catch(() => {});
    });

    socket.on('participant_snapshot', async (data) => {
      const list = Array.isArray(data?.participants) ? data.participants : [];
      const count = Number(data?.participant_count || list.length || 0);
      syncParticipantRoster(list, { pruneMissing: true });
      applySnapshotSharerState(data?.active_sharer_sid || null);
      participantCountEl.textContent = String(Math.max(1, count));
      renderMentionPicker();
      refreshRtcDiagnostics().catch(() => {});
    });

    socket.on('participant_updated', (data) => {
      if (!data || !data.sid) return;
      if (data.sid === socket.id) {
        roomState.setUserName(data.name);
      }
      const participantMeta = participantMetaRef();
      if (participantMeta[data.sid]) participantMeta[data.sid].name = data.name;
      const card = documentRef.getElementById('card-' + data.sid);
      const labelEl = card?.querySelector('.video-label');
      if (labelEl) labelEl.textContent = data.name;
      renderMentionPicker();
    });

    socket.on('meeting_chat_message', (data) => appendChatMessage(data));
    socket.on('meeting_chat_cleared', (data) => {
      if (chatMessages) chatMessages.innerHTML = '';
      const scope = data?.scope || 'all';
      setStatus(scope === 'self' ? ctx.TEXT_CHAT_CLEARED_SELF : ctx.TEXT_CHAT_CLEARED_ALL);
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
        senderUserId: item.dataset.senderUserId || '',
        from: item.dataset.senderSid || '',
      });
    });

    socket.on('join_error', (data) => {
      alert(data.message || 'Join failed');
      global.location.href = '/';
    });

    socket.on('force_leave', (data) => {
      cleanupMeetingSession();
      alert(data.message || TEXT_MEETING_CLOSED);
      global.location.href = '/';
    });

    socket.on('force_logout', (data) => {
      cleanupMeetingSession();
      try { socket.disconnect(); } catch (_) {}
      alert(data?.message || TEXT_KICKED);
      global.location.href = '/login?kicked=1';
    });

    socket.on('host_presence_changed', (data) => {
      if (!data) return;
      setStatus(data.message || (data.host_present ? TEXT_HOST_RETURNED_ROOM : TEXT_HOST_LEFT_ROOM), data.host_present ? '' : 'warning');
    });

    socket.on('host_action_error', (data) => {
      setStatus(data?.message || 'Action failed', 'error');
    });

    socket.on('room_ui_event', (data) => {
      if (!data || !data.type) return;
      if (data.type === 'screen_share_started') {
        const sharerSid = normalizeParticipantSid(data.from);
        roomState.setCurrentSharerSid(sharerSid);
        roomState.setFocusedSid(sharerSid);
        focusParticipant(sharerSid, { hideSidebar: true, screenShare: true });
        syncScreenShareSpeakerRule({ userGesture: false });
        setStatus(TEXT_SCREEN_SHARE_MODE);
      } else if (data.type === 'screen_share_stopped') {
        roomState.setCurrentSharerSid(null);
        roomState.setHiddenSidebar(false);
        roomState.setFocusedSid('local');
        syncScreenShareSpeakerRule({ userGesture: false });
        queueRenderLayout();
        setStatus(TEXT_SCREEN_SHARE_STOPPED);
      } else if (data.type === 'screen_share_denied') {
        roomState.setCurrentSharerSid(normalizeParticipantSid(data.activeSharerSid || roomState.getCurrentSharerSid()));
        syncScreenShareSpeakerRule({ userGesture: false });
        updateShareUiState();
        setStatus(data.message || TEXT_SCREEN_SHARE_DENIED, 'warning');
      } else if (data.type === 'danmaku_toggled') {
        roomState.setDanmakuEnabled(!!data.enabled);
        setStatus(data.enabled ? TEXT_DANMAKU_ON : TEXT_DANMAKU_OFF);
      }
    });
  }

  function bindWindowEvents(ctx) {
    const {
      documentRef,
      getFullscreenElement,
      screenRef,
      clearSimulatedFullscreen,
      flushPendingLayoutIfNeeded,
      roomDebugLog,
      getSimulatedFullscreenCard,
      nativeFullscreenState,
      queueRenderLayout,
      getRenderableCards,
      getGridPageSize,
      hasActiveFullscreenSession,
      layoutScheduler,
      roomState,
      writeReloadRecoveryHint,
      hasLeftMeetingRef,
      socket,
    } = ctx;

    documentRef.addEventListener('fullscreenchange', () => {
      if (!getFullscreenElement() && screenRef.orientation?.unlock) {
        try { screenRef.orientation.unlock(); } catch (_) {}
      }
      if (getFullscreenElement()) {
        clearSimulatedFullscreen();
      } else {
        flushPendingLayoutIfNeeded();
      }
      roomDebugLog('fullscreenchange', { active: !!getFullscreenElement(), simulated: !!getSimulatedFullscreenCard() });
    });

    documentRef.addEventListener('webkitfullscreenchange', () => {
      if (!getFullscreenElement() && screenRef.orientation?.unlock) {
        try { screenRef.orientation.unlock(); } catch (_) {}
      }
      if (getFullscreenElement()) {
        clearSimulatedFullscreen();
      } else {
        flushPendingLayoutIfNeeded();
      }
      roomDebugLog('webkitfullscreenchange', { active: !!getFullscreenElement(), simulated: !!getSimulatedFullscreenCard() });
    });

    documentRef.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && getSimulatedFullscreenCard()) {
        clearSimulatedFullscreen();
      }
    });

    global.addEventListener('pageshow', () => {
      if (nativeFullscreenState.get() && !nativeFullscreenState.get().webkitDisplayingFullscreen) {
        nativeFullscreenState.set(null);
      }
      flushPendingLayoutIfNeeded();
    });

    documentRef.addEventListener('visibilitychange', () => {
      if (!documentRef.hidden && nativeFullscreenState.get() && !nativeFullscreenState.get().webkitDisplayingFullscreen) {
        nativeFullscreenState.set(null);
        flushPendingLayoutIfNeeded();
      }
    });

    global.addEventListener('resize', () => {
      const totalCards = getRenderableCards().length;
      const totalPages = Math.max(1, Math.ceil(totalCards / getGridPageSize()));
      roomState.setCurrentGridPage(Math.min(roomState.getCurrentGridPage(), totalPages - 1));
      if (hasActiveFullscreenSession()) {
        layoutScheduler.defer();
        roomDebugLog('resize while fullscreen active; layout deferred');
        return;
      }
      queueRenderLayout();
    });

    global.addEventListener('beforeunload', () => {
      writeReloadRecoveryHint();
      if (!hasLeftMeetingRef()) {
        try { socket.emit('leave_room'); } catch (_) {}
      }
    });
  }

  function bindUiEvents(ctx) {
    const {
      videoPrevPageBtn,
      videoNextPageBtn,
      videoHomePageBtn,
      getRenderableCards,
      getGridPageSize,
      queueRenderLayout,
      roomState,
      toggleSpeakerBtn,
      runMediaTask,
      setSpeakerEnabled,
      toggleMicBtn,
      toggleMicrophoneAction,
      toggleCameraBtn,
      toggleCameraAction,
      shareProfileBtn,
      toggleShareProfileMode,
      shareScreenBtn,
      toggleScreenShareAction,
      virtualBgBtn,
      toggleVirtualBackgroundAction,
      recordingBtn,
      toggleScreenRecording,
      leaveMeetingBtn,
      participantMetaRef,
      IS_HOST,
      TEXT_HOST_MUST_END_MEETING,
      TEXT_LEAVE_CONFIRM,
      TEXT_YOU_LEFT_MEETING,
      leaveMeetingAndExit,
      hostEndMeetingBtn,
      TEXT_HOST_END_CONFIRM,
      socket,
      ROOM_ID,
      saveProfileBtn,
      displayNameInput,
      localStorageRef,
      USER_NAME,
      livekitControllerRef,
      ensureCard,
      getDisplayName,
      renderMentionPicker,
      setStatus,
      TEXT_PROFILE_UPDATED,
      inviteInput,
      copyInviteBtn,
      copyText,
      showQrBtn,
      inviteQrWrap,
      inviteQrImage,
      TEXT_HIDE_QR,
      TEXT_SHOW_QR,
      TEXT_MANUAL_COPY_LINK,
      switchRoomBtn,
      switchRoomIdInput,
      switchRoomPasswordInput,
      setStatusError,
    } = ctx;

    videoPrevPageBtn?.addEventListener('click', () => {
      if (roomState.getCurrentGridPage() <= 0) return;
      roomState.setCurrentGridPage(roomState.getCurrentGridPage() - 1);
      queueRenderLayout();
    });
    videoNextPageBtn?.addEventListener('click', () => {
      const totalCards = getRenderableCards().length;
      const totalPages = Math.max(1, Math.ceil(totalCards / getGridPageSize()));
      if (roomState.getCurrentGridPage() >= totalPages - 1) return;
      roomState.setCurrentGridPage(roomState.getCurrentGridPage() + 1);
      queueRenderLayout();
    });
    videoHomePageBtn?.addEventListener('click', () => {
      if (roomState.getCurrentGridPage() <= 0) return;
      roomState.setCurrentGridPage(0);
      queueRenderLayout();
    });

    if (toggleSpeakerBtn) {
      toggleSpeakerBtn.onclick = () => runMediaTask('toggle-speaker', async () => {
        setSpeakerEnabled(!roomState.getSpeakerEnabled(), { userGesture: true, persist: true, showStatus: true });
        if (roomState.getCurrentSharerSid() || roomState.getIsSharingScreen() || roomState.getLivekitLocalShareActive()) {
          roomState.setSpeakerForcedByShareRule(false);
          roomState.setSpeakerStateBeforeShare(roomState.getSpeakerEnabled());
        }
      });
    }
    toggleMicBtn.onclick = () => runMediaTask('toggle-mic', toggleMicrophoneAction);
    toggleCameraBtn.onclick = () => runMediaTask('toggle-camera', toggleCameraAction);
    if (shareProfileBtn) {
      shareProfileBtn.onclick = () => runMediaTask('share-profile-toggle', async () => {
        await toggleShareProfileMode();
      });
    }
    shareScreenBtn.onclick = () => runMediaTask('share-screen', toggleScreenShareAction);
    virtualBgBtn.onclick = () => runMediaTask('virtual-background-toggle', toggleVirtualBackgroundAction);
    recordingBtn.onclick = () => toggleScreenRecording();
    leaveMeetingBtn.onclick = () => {
      const otherParticipantCount = Object.keys(participantMetaRef()).length;
      if (IS_HOST && otherParticipantCount > 0) {
        setStatus(TEXT_HOST_MUST_END_MEETING, 'warning');
        alert(TEXT_HOST_MUST_END_MEETING);
        return;
      }
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

    saveProfileBtn.onclick = () => {
      const name = (displayNameInput.value || '').trim();
      if (!name) return;
      roomState.setUserName(name);
      localStorageRef.setItem('meeting_display_name', name);
      socket.emit('update_profile', { name });
      const livekitController = livekitControllerRef();
      if (ctx.IS_LIVEKIT_MODE && livekitController) {
        livekitController.updateDisplayName(name).catch((err) => console.error(err));
      }
      ensureCard('local', getDisplayName('local'), true);
      renderMentionPicker();
      setStatus(TEXT_PROFILE_UPDATED);
    };

    if (inviteInput) {
      inviteInput.value = global.location.href;
    }
    if (copyInviteBtn) {
      copyInviteBtn.onclick = async () => {
        const text = inviteInput?.value || global.location.href;
        const ok = await copyText(text);
        if (!ok) {
          try { global.prompt(TEXT_MANUAL_COPY_LINK, text); } catch (_) {}
        }
      };
    }
    if (showQrBtn && inviteQrWrap && inviteQrImage) {
      showQrBtn.onclick = () => {
        const text = encodeURIComponent(inviteInput?.value || global.location.href);
        inviteQrImage.src = `https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${text}`;
        inviteQrWrap.classList.toggle('hidden');
        const showing = !inviteQrWrap.classList.contains('hidden');
        showQrBtn.textContent = showing ? TEXT_HIDE_QR : TEXT_SHOW_QR;
      };
    }
    if (switchRoomBtn) {
      switchRoomBtn.onclick = async () => {
        const nextRoomId = (switchRoomIdInput?.value || '').trim();
        const nextPwd = (switchRoomPasswordInput?.value || '').trim();
        if (!nextRoomId || !nextPwd) return;
        const res = await fetch('/api/join_room', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ room_id: nextRoomId, password: nextPwd }),
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
          setStatusError(data.message || 'failed');
          return;
        }
        leaveMeetingAndExit(null, `/room/${nextRoomId}?pwd=${encodeURIComponent(nextPwd)}`);
      };
    }
  }

  function initialize(ctx) {
    bindSocketEvents(ctx);
    bindWindowEvents(ctx);
    bindUiEvents(ctx);
    ctx.initChatUi();
    ctx.roomState.setPendingReloadRecoveryHint(ctx.readReloadRecoveryHint());
    ctx.setSpeakerEnabled(ctx.roomState.getSpeakerEnabled(), { userGesture: false, persist: false, showStatus: false });
    ctx.updateShareProfileUi();
    ctx.refreshRtcStatsBtn?.addEventListener('click', () => { ctx.refreshRtcDiagnostics().catch(() => {}); });
    ctx.ensureCard('local', ctx.getDisplayName('local'), true);
    ctx.updateVirtualBackgroundButtonState();
    ctx.queueRenderLayout();
    ctx.startRtcDiagnosticsLoop();
  }

  global.RoomPageBootstrap = {
    initialize,
  };
})(window);
