(function (global) {
  const lk = global.LivekitClient;
  const SOURCE_FIELD_MAP = new Map([
    [lk?.Track?.Source?.Camera, 'cameraVideo'],
    [lk?.Track?.Source?.ScreenShare, 'screenVideo'],
    [lk?.Track?.Source?.Microphone, 'microphone'],
    [lk?.Track?.Source?.ScreenShareAudio, 'screenAudio'],
  ]);

  function createRemoteState() {
    return {
      cameraVideo: null,
      screenVideo: null,
      microphone: null,
      screenAudio: null,
      stream: null,
    };
  }

  function createController(options) {
    if (!lk) {
      throw new Error('LiveKit client SDK is not loaded');
    }

    const {
      url,
      tokenEndpoint,
      roomId,
      roomPassword,
      getParticipantSid,
      getDisplayName,
      addRemoteVideo,
      clearRemoteMedia,
      removeRemoteVideo,
      setLocalPreview,
      onScreenShareState,
      onLocalScreenShareState,
      setStatus,
    } = options;

    let room = null;
    let connected = false;
    let localState = createRemoteState();
    const remoteStates = new Map();

    function getRemoteState(identity) {
      if (!remoteStates.has(identity)) {
        remoteStates.set(identity, createRemoteState());
      }
      return remoteStates.get(identity);
    }

    function setTrackField(target, source, mediaTrack) {
      const fieldName = SOURCE_FIELD_MAP.get(source);
      if (fieldName) target[fieldName] = mediaTrack || null;
    }

    function buildStream(target) {
      const stream = new MediaStream();
      const preferredVideo = target.screenVideo || target.cameraVideo || null;
      const preferredAudio = target.screenAudio || target.microphone || null;
      if (preferredVideo && preferredVideo.readyState === 'live') {
        stream.addTrack(preferredVideo);
      }
      if (preferredAudio && preferredAudio.readyState === 'live') {
        stream.addTrack(preferredAudio);
      }
      return stream;
    }

    function syncLocalPreview() {
      const stream = buildStream(localState);
      const hasVideo = stream.getVideoTracks().length > 0;
      setLocalPreview(hasVideo ? stream : null, {
        hasVideo,
        isScreenShare: !!localState.screenVideo,
      });
    }

    function syncRemoteParticipant(identity) {
      const state = remoteStates.get(identity);
      if (!state) return;
      const stream = buildStream(state);
      state.stream = stream;
      if (!stream.getTracks().length) {
        remoteStates.delete(identity);
        clearRemoteMedia(identity);
        onScreenShareState(identity, false);
        return;
      }
      addRemoteVideo(identity, stream);
      onScreenShareState(identity, !!state.screenVideo);
    }

    function trackToMediaStreamTrack(track) {
      return track?.mediaStreamTrack || null;
    }

    function requireRoom() {
      if (!room) throw new Error('LiveKit room is not connected');
      return room;
    }

    function bindRoomEvents() {
      room
        .on(lk.RoomEvent.TrackSubscribed, (track, publication, participant) => {
          const mediaTrack = trackToMediaStreamTrack(track);
          if (!mediaTrack || !participant?.identity) return;
          const state = getRemoteState(participant.identity);
          setTrackField(state, publication?.source, mediaTrack);
          syncRemoteParticipant(participant.identity);
        })
        .on(lk.RoomEvent.TrackUnsubscribed, (track, publication, participant) => {
          if (!participant?.identity) return;
          const state = getRemoteState(participant.identity);
          setTrackField(state, publication?.source, null);
          syncRemoteParticipant(participant.identity);
        })
        .on(lk.RoomEvent.ParticipantDisconnected, (participant) => {
          const identity = participant?.identity;
          if (!identity) return;
          remoteStates.delete(identity);
          removeRemoteVideo(identity);
          onScreenShareState(identity, false);
        })
        .on(lk.RoomEvent.LocalTrackPublished, (publication) => {
          const mediaTrack = trackToMediaStreamTrack(publication?.track);
          setTrackField(localState, publication?.source, mediaTrack);
          syncLocalPreview();
          if (publication?.source === lk.Track.Source.ScreenShare) {
            onLocalScreenShareState?.(true);
          }
        })
        .on(lk.RoomEvent.LocalTrackUnpublished, (publication) => {
          setTrackField(localState, publication?.source, null);
          syncLocalPreview();
          if (publication?.source === lk.Track.Source.ScreenShare) {
            onLocalScreenShareState?.(false);
          }
        })
        .on(lk.RoomEvent.Disconnected, () => {
          connected = false;
          onLocalScreenShareState?.(false);
        });
    }

    async function fetchToken() {
      const response = await fetch(tokenEndpoint, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          room_id: roomId,
          password: roomPassword,
          participant_sid: getParticipantSid(),
          name: getDisplayName(),
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data?.success || !data?.token) {
        throw new Error(data?.message || 'Failed to fetch LiveKit token');
      }
      return data;
    }

    async function connect({ autoEnableCamera = false, autoEnableMicrophone = false } = {}) {
      if (connected && room) return room;
      const tokenPayload = await fetchToken();
      room = new lk.Room({
        adaptiveStream: true,
        dynacast: true,
        stopLocalTrackOnUnpublish: true,
      });
      bindRoomEvents();
      await room.connect(url || tokenPayload.url, tokenPayload.token, {
        autoSubscribe: true,
      });
      connected = true;
      if (autoEnableMicrophone) {
        await room.localParticipant.setMicrophoneEnabled(true);
      }
      if (autoEnableCamera) {
        await room.localParticipant.setCameraEnabled(true);
      }
      syncLocalPreview();
      return room;
    }

    async function setMicrophoneEnabled(nextEnabled) {
      const activeRoom = requireRoom();
      const publication = activeRoom.localParticipant.getTrackPublication(lk.Track.Source.Microphone);
      const enabled = typeof nextEnabled === 'boolean'
        ? nextEnabled
        : !(publication?.isMuted === false && publication?.track);
      await activeRoom.localParticipant.setMicrophoneEnabled(enabled);
      return enabled;
    }

    async function setCameraEnabled(nextEnabled) {
      const activeRoom = requireRoom();
      const publication = activeRoom.localParticipant.getTrackPublication(lk.Track.Source.Camera);
      const enabled = typeof nextEnabled === 'boolean'
        ? nextEnabled
        : !(publication?.isMuted === false && publication?.track);
      await activeRoom.localParticipant.setCameraEnabled(enabled);
      return enabled;
    }

    async function setScreenShareEnabled(nextEnabled) {
      const activeRoom = requireRoom();
      const publication = activeRoom.localParticipant.getTrackPublication(lk.Track.Source.ScreenShare);
      const enabled = typeof nextEnabled === 'boolean'
        ? nextEnabled
        : !(publication?.isMuted === false && publication?.track);
      await activeRoom.localParticipant.setScreenShareEnabled(enabled);
      return enabled;
    }

    async function updateDisplayName(name) {
      if (!room?.localParticipant || !name) return;
      await room.localParticipant.setName(name);
    }

    function disconnect() {
      if (room) {
        try {
          room.disconnect();
        } catch (_) {}
      }
      connected = false;
      localState = createRemoteState();
      remoteStates.clear();
    }

    return {
      connect,
      disconnect,
      isConnected: () => connected,
      setMicrophoneEnabled,
      setCameraEnabled,
      setScreenShareEnabled,
      updateDisplayName,
    };
  }

  global.RoomPageLiveKit = {
    createController,
  };
})(window);
