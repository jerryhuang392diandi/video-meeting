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
      roomOptions,
    } = options;

    let room = null;
    let connected = false;
    let connectPromise = null;
    let localState = createRemoteState();
    const remoteStates = new Map();

    function resolveRoomOptions() {
      return {
        adaptiveStream: true,
        dynacast: true,
        stopLocalTrackOnUnpublish: true,
        ...(roomOptions || {}),
      };
    }

    function createRoomInstance() {
      if (room) return room;
      room = new lk.Room(resolveRoomOptions());
      bindRoomEvents();
      return room;
    }

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
      const audioTracks = [target.screenAudio, target.microphone]
        .filter((track, index, list) => track && list.indexOf(track) === index && track.readyState === 'live');
      if (preferredVideo && preferredVideo.readyState === 'live') {
        stream.addTrack(preferredVideo);
      }
      audioTracks.forEach((track) => stream.addTrack(track));
      return stream;
    }

    function syncLocalPreview() {
      const stream = buildStream(localState);
      const hasVideo = stream.getVideoTracks().length > 0;
      const hasAudio = stream.getAudioTracks().length > 0;
      setLocalPreview(hasVideo || hasAudio ? stream : null, {
        hasVideo,
        hasAudio,
        isScreenShare: !!localState.screenVideo,
        cameraEnabled: !!localState.cameraVideo,
        microphoneEnabled: !!localState.microphone,
        screenAudioEnabled: !!localState.screenAudio,
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

    function getPublicationMediaTrack(publication) {
      if (!publication || publication.isMuted) return null;
      const mediaTrack = trackToMediaStreamTrack(publication.track);
      return mediaTrack?.readyState === 'live' ? mediaTrack : null;
    }

    function syncLocalStateFromPublications() {
      if (!room?.localParticipant) {
        localState = createRemoteState();
        return;
      }
      localState.cameraVideo = getPublicationMediaTrack(
        room.localParticipant.getTrackPublication(lk.Track.Source.Camera),
      );
      localState.microphone = getPublicationMediaTrack(
        room.localParticipant.getTrackPublication(lk.Track.Source.Microphone),
      );
      localState.screenVideo = getPublicationMediaTrack(
        room.localParticipant.getTrackPublication(lk.Track.Source.ScreenShare),
      );
      localState.screenAudio = getPublicationMediaTrack(
        room.localParticipant.getTrackPublication(lk.Track.Source.ScreenShareAudio),
      );
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
          syncLocalStateFromPublications();
          syncLocalPreview();
          if (publication?.source === lk.Track.Source.ScreenShare) {
            onLocalScreenShareState?.(true);
          }
        })
        .on(lk.RoomEvent.LocalTrackUnpublished, (publication) => {
          setTrackField(localState, publication?.source, null);
          syncLocalStateFromPublications();
          syncLocalPreview();
          if (publication?.source === lk.Track.Source.ScreenShare) {
            onLocalScreenShareState?.(false);
          }
        })
        .on(lk.RoomEvent.Disconnected, () => {
          connected = false;
          onLocalScreenShareState?.(false);
        });
      if (lk.RoomEvent.TrackMuted) {
        room.on(lk.RoomEvent.TrackMuted, (publication, participant) => {
          const identity = participant?.identity;
          if (!identity) return;
          if (room?.localParticipant?.identity === identity) {
            syncLocalStateFromPublications();
            syncLocalPreview();
            return;
          }
          const state = getRemoteState(identity);
          setTrackField(state, publication?.source, null);
          syncRemoteParticipant(identity);
        });
      }
      if (lk.RoomEvent.TrackUnmuted) {
        room.on(lk.RoomEvent.TrackUnmuted, (publication, participant) => {
          const identity = participant?.identity;
          if (!identity) return;
          if (room?.localParticipant?.identity === identity) {
            syncLocalStateFromPublications();
            syncLocalPreview();
            return;
          }
          const state = getRemoteState(identity);
          setTrackField(state, publication?.source, trackToMediaStreamTrack(publication?.track));
          syncRemoteParticipant(identity);
        });
      }
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
      if (connectPromise) return connectPromise;
      connectPromise = (async () => {
        const tokenPayload = await fetchToken();
        const activeRoom = createRoomInstance();
        if (typeof activeRoom.prepareConnection === 'function') {
          try {
            await activeRoom.prepareConnection(url || tokenPayload.url, tokenPayload.token);
          } catch (_) {}
        }
        await activeRoom.connect(url || tokenPayload.url, tokenPayload.token, {
          autoSubscribe: true,
        });
        connected = true;
        await Promise.allSettled([
          autoEnableMicrophone ? activeRoom.localParticipant.setMicrophoneEnabled(true) : Promise.resolve(),
          autoEnableCamera ? activeRoom.localParticipant.setCameraEnabled(true) : Promise.resolve(),
        ]);
        syncLocalStateFromPublications();
        syncLocalPreview();
        return activeRoom;
      })().finally(() => {
        connectPromise = null;
      });
      return connectPromise;
    }

    async function setMicrophoneEnabled(nextEnabled) {
      const activeRoom = requireRoom();
      const publication = activeRoom.localParticipant.getTrackPublication(lk.Track.Source.Microphone);
      const enabled = typeof nextEnabled === 'boolean'
        ? nextEnabled
        : !(publication?.isMuted === false && publication?.track);
      await activeRoom.localParticipant.setMicrophoneEnabled(enabled);
      syncLocalStateFromPublications();
      syncLocalPreview();
      return enabled;
    }

    async function setCameraEnabled(nextEnabled) {
      const activeRoom = requireRoom();
      const publication = activeRoom.localParticipant.getTrackPublication(lk.Track.Source.Camera);
      const enabled = typeof nextEnabled === 'boolean'
        ? nextEnabled
        : !(publication?.isMuted === false && publication?.track);
      await activeRoom.localParticipant.setCameraEnabled(enabled);
      syncLocalStateFromPublications();
      syncLocalPreview();
      return enabled;
    }

    async function replaceCameraTrack(mediaTrack) {
      const activeRoom = requireRoom();
      const publication = activeRoom.localParticipant.getTrackPublication(lk.Track.Source.Camera);
      const localTrack = publication?.track;
      if (!localTrack || typeof localTrack.replaceTrack !== 'function') return false;
      if (!mediaTrack) return false;
      await localTrack.replaceTrack(mediaTrack);
      syncLocalStateFromPublications();
      syncLocalPreview();
      return true;
    }

    async function setScreenShareEnabled(nextEnabled) {
      const activeRoom = requireRoom();
      const publication = activeRoom.localParticipant.getTrackPublication(lk.Track.Source.ScreenShare);
      const enabled = typeof nextEnabled === 'boolean'
        ? nextEnabled
        : !(publication?.isMuted === false && publication?.track);
      await activeRoom.localParticipant.setScreenShareEnabled(
        enabled,
        enabled ? { audio: true } : undefined,
      );
      syncLocalStateFromPublications();
      syncLocalPreview();
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
      room = null;
      connected = false;
      localState = createRemoteState();
      remoteStates.clear();
    }

    async function prepareConnection(targetUrl = url) {
      const activeRoom = createRoomInstance();
      if (typeof activeRoom.prepareConnection !== 'function' || !targetUrl) return;
      try {
        await activeRoom.prepareConnection(targetUrl);
      } catch (_) {}
    }

    function getLocalMediaState() {
      return {
        cameraEnabled: !!localState.cameraVideo,
        microphoneEnabled: !!localState.microphone,
        screenShareEnabled: !!localState.screenVideo,
        screenAudioEnabled: !!localState.screenAudio,
      };
    }

    function sourceLabel(source) {
      switch (source) {
        case lk.Track.Source.Camera: return 'camera';
        case lk.Track.Source.Microphone: return 'microphone';
        case lk.Track.Source.ScreenShare: return 'screen_share_video';
        case lk.Track.Source.ScreenShareAudio: return 'screen_share_audio';
        default: return String(source || 'unknown');
      }
    }

    function collectParticipantPublicationLines(participant) {
      const lines = [];
      participant?.trackPublications?.forEach?.((publication) => {
        lines.push(
          `${sourceLabel(publication?.source)} | subscribed=${publication?.isSubscribed !== false} | muted=${publication?.isMuted === true}`,
        );
      });
      return lines;
    }

    function getDiagnosticsEntries() {
      if (!room) {
        return [{ label: 'LiveKit', lines: ['status: disconnected'] }];
      }
      const entries = [];
      entries.push({
        label: 'LiveKit local',
        lines: [
          `connected: ${connected}`,
          `camera: ${localState.cameraVideo ? 'on' : 'off'}`,
          `microphone: ${localState.microphone ? 'on' : 'off'}`,
          `screen_video: ${localState.screenVideo ? 'on' : 'off'}`,
          `screen_audio: ${localState.screenAudio ? 'on' : 'off'}`,
        ],
      });
      room.remoteParticipants?.forEach?.((participant) => {
        entries.push({
          label: participant?.name || participant?.identity || 'remote',
          lines: collectParticipantPublicationLines(participant),
        });
      });
      return entries;
    }

    return {
      connect,
      disconnect,
      isConnected: () => connected,
      prepareConnection,
      getLocalMediaState,
      getDiagnosticsEntries,
      setMicrophoneEnabled,
      setCameraEnabled,
      replaceCameraTrack,
      setScreenShareEnabled,
      updateDisplayName,
    };
  }

  global.RoomPageLiveKit = {
    createController,
  };
})(window);
