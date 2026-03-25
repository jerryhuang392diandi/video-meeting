(function (global) {
  const lk = global.LivekitClient;
  const rtcHelpers = global.RoomPageRtc || {};

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

    function assignTrack(target, source, mediaTrack) {
      if (source === lk.Track.Source.Camera) {
        target.cameraVideo = mediaTrack;
        return;
      }
      if (source === lk.Track.Source.ScreenShare) {
        target.screenVideo = mediaTrack;
        return;
      }
      if (source === lk.Track.Source.ScreenShareAudio) {
        target.screenAudio = mediaTrack;
        return;
      }
      if (source === lk.Track.Source.Microphone) {
        target.microphone = mediaTrack;
      }
    }

    function clearTrack(target, source) {
      if (source === lk.Track.Source.Camera) {
        target.cameraVideo = null;
        return;
      }
      if (source === lk.Track.Source.ScreenShare) {
        target.screenVideo = null;
        return;
      }
      if (source === lk.Track.Source.ScreenShareAudio) {
        target.screenAudio = null;
        return;
      }
      if (source === lk.Track.Source.Microphone) {
        target.microphone = null;
      }
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

    function bindRoomEvents() {
      room
        .on(lk.RoomEvent.TrackSubscribed, (track, publication, participant) => {
          const mediaTrack = trackToMediaStreamTrack(track);
          if (!mediaTrack || !participant?.identity) return;
          const state = getRemoteState(participant.identity);
          assignTrack(state, publication?.source, mediaTrack);
          syncRemoteParticipant(participant.identity);
        })
        .on(lk.RoomEvent.TrackUnsubscribed, (track, publication, participant) => {
          if (!participant?.identity) return;
          const state = getRemoteState(participant.identity);
          clearTrack(state, publication?.source);
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
          assignTrack(localState, publication?.source, mediaTrack);
          syncLocalPreview();
        })
        .on(lk.RoomEvent.LocalTrackUnpublished, (publication) => {
          clearTrack(localState, publication?.source);
          syncLocalPreview();
        })
        .on(lk.RoomEvent.Disconnected, () => {
          connected = false;
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
      if (!room) throw new Error('LiveKit room is not connected');
      const publication = room.localParticipant.getTrackPublication(lk.Track.Source.Microphone);
      const enabled = typeof nextEnabled === 'boolean'
        ? nextEnabled
        : !(publication?.isMuted === false && publication?.track);
      await room.localParticipant.setMicrophoneEnabled(enabled);
      return enabled;
    }

    async function setCameraEnabled(nextEnabled) {
      if (!room) throw new Error('LiveKit room is not connected');
      const publication = room.localParticipant.getTrackPublication(lk.Track.Source.Camera);
      const enabled = typeof nextEnabled === 'boolean'
        ? nextEnabled
        : !(publication?.isMuted === false && publication?.track);
      await room.localParticipant.setCameraEnabled(enabled);
      return enabled;
    }

    async function setScreenShareEnabled(nextEnabled) {
      if (!room) throw new Error('LiveKit room is not connected');
      const publication = room.localParticipant.getTrackPublication(lk.Track.Source.ScreenShare);
      const enabled = typeof nextEnabled === 'boolean'
        ? nextEnabled
        : !(publication?.isMuted === false && publication?.track);
      await room.localParticipant.setScreenShareEnabled(enabled);
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
