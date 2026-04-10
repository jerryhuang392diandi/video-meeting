(function (global) {
  const lk = global.LivekitClient;
  const mediaUtils = global.RoomPageUtils || {};
  const setMediaTrackContentHint = mediaUtils.setMediaTrackContentHint || function () {};
  const VIDEO_QUALITY = lk?.VideoQuality || { HIGH: 'high', MEDIUM: 'medium', LOW: 'low' };
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

  function isMobileViewport() {
    return !!(global.matchMedia && global.matchMedia('(max-width: 768px)').matches)
      || /Android|iPhone|iPad|iPod/i.test(global.navigator?.userAgent || '');
  }

  function createVideoPreset(width, height, maxBitrate, maxFramerate, priority = 'medium') {
    if (lk?.VideoPreset) {
      return new lk.VideoPreset(width, height, maxBitrate, maxFramerate, priority);
    }
    return {
      resolution: { width, height },
      encoding: { maxBitrate, maxFramerate, priority },
    };
  }

  function normalizeShareProfile(input, mobile = isMobileViewport()) {
    const mode = input?.mode === 'detail' ? 'detail' : 'motion';
    const level = ['high', 'balanced', 'stable'].includes(input?.level) ? input.level : 'high';
    return { mode, level, mobile };
  }

  function getScreenShareProfileConfig(input) {
    const profile = normalizeShareProfile(input);
    const presets = profile.mobile
      ? {
          motion: {
            high: {
              resolution: { width: 960, height: 540 },
              encoding: { maxBitrate: 1_700_000, maxFramerate: 24, priority: 'high' },
              layers: [
                createVideoPreset(640, 360, 900_000, 20, 'medium'),
                createVideoPreset(426, 240, 420_000, 15, 'low'),
              ],
              contentHint: 'motion',
              degradationPreference: 'maintain-framerate',
              quality: VIDEO_QUALITY.HIGH,
            },
            balanced: {
              resolution: { width: 960, height: 540 },
              encoding: { maxBitrate: 1_200_000, maxFramerate: 20, priority: 'medium' },
              layers: [
                createVideoPreset(640, 360, 720_000, 18, 'medium'),
                createVideoPreset(426, 240, 360_000, 12, 'low'),
              ],
              contentHint: 'motion',
              degradationPreference: 'maintain-framerate',
              quality: VIDEO_QUALITY.MEDIUM,
            },
            stable: {
              resolution: { width: 854, height: 480 },
              encoding: { maxBitrate: 850_000, maxFramerate: 18, priority: 'medium' },
              layers: [
                createVideoPreset(640, 360, 520_000, 15, 'medium'),
                createVideoPreset(426, 240, 260_000, 10, 'low'),
              ],
              contentHint: 'motion',
              degradationPreference: 'maintain-framerate',
              quality: VIDEO_QUALITY.LOW,
            },
          },
          detail: {
            high: {
              resolution: { width: 1280, height: 720 },
              encoding: { maxBitrate: 2_000_000, maxFramerate: 15, priority: 'high' },
              layers: [
                createVideoPreset(1024, 576, 1_000_000, 12, 'medium'),
                createVideoPreset(640, 360, 420_000, 10, 'low'),
              ],
              contentHint: 'text',
              degradationPreference: 'maintain-resolution',
              quality: VIDEO_QUALITY.HIGH,
            },
            balanced: {
              resolution: { width: 1024, height: 576 },
              encoding: { maxBitrate: 1_300_000, maxFramerate: 12, priority: 'medium' },
              layers: [
                createVideoPreset(854, 480, 760_000, 10, 'medium'),
                createVideoPreset(640, 360, 340_000, 8, 'low'),
              ],
              contentHint: 'text',
              degradationPreference: 'maintain-resolution',
              quality: VIDEO_QUALITY.MEDIUM,
            },
            stable: {
              resolution: { width: 960, height: 540 },
              encoding: { maxBitrate: 900_000, maxFramerate: 10, priority: 'medium' },
              layers: [
                createVideoPreset(640, 360, 480_000, 8, 'medium'),
                createVideoPreset(426, 240, 220_000, 6, 'low'),
              ],
              contentHint: 'text',
              degradationPreference: 'maintain-resolution',
              quality: VIDEO_QUALITY.LOW,
            },
          },
        }
      : {
          motion: {
            high: {
              resolution: { width: 1280, height: 720 },
              encoding: { maxBitrate: 3_000_000, maxFramerate: 30, priority: 'high' },
              layers: [
                createVideoPreset(960, 540, 1_600_000, 24, 'medium'),
                createVideoPreset(640, 360, 750_000, 18, 'low'),
              ],
              contentHint: 'motion',
              degradationPreference: 'maintain-framerate',
              quality: VIDEO_QUALITY.HIGH,
            },
            balanced: {
              resolution: { width: 1280, height: 720 },
              encoding: { maxBitrate: 2_200_000, maxFramerate: 24, priority: 'high' },
              layers: [
                createVideoPreset(960, 540, 1_200_000, 20, 'medium'),
                createVideoPreset(640, 360, 580_000, 15, 'low'),
              ],
              contentHint: 'motion',
              degradationPreference: 'maintain-framerate',
              quality: VIDEO_QUALITY.MEDIUM,
            },
            stable: {
              resolution: { width: 960, height: 540 },
              encoding: { maxBitrate: 1_450_000, maxFramerate: 20, priority: 'medium' },
              layers: [
                createVideoPreset(640, 360, 800_000, 18, 'medium'),
                createVideoPreset(426, 240, 360_000, 12, 'low'),
              ],
              contentHint: 'motion',
              degradationPreference: 'maintain-framerate',
              quality: VIDEO_QUALITY.LOW,
            },
          },
          detail: {
            high: {
              resolution: { width: 1920, height: 1080 },
              encoding: { maxBitrate: 4_400_000, maxFramerate: 18, priority: 'high' },
              layers: [
                createVideoPreset(1280, 720, 2_100_000, 15, 'medium'),
                createVideoPreset(960, 540, 900_000, 10, 'low'),
              ],
              contentHint: 'text',
              degradationPreference: 'maintain-resolution',
              quality: VIDEO_QUALITY.HIGH,
            },
            balanced: {
              resolution: { width: 1600, height: 900 },
              encoding: { maxBitrate: 2_700_000, maxFramerate: 15, priority: 'high' },
              layers: [
                createVideoPreset(1280, 720, 1_450_000, 12, 'medium'),
                createVideoPreset(960, 540, 720_000, 10, 'low'),
              ],
              contentHint: 'text',
              degradationPreference: 'maintain-resolution',
              quality: VIDEO_QUALITY.MEDIUM,
            },
            stable: {
              resolution: { width: 1280, height: 720 },
              encoding: { maxBitrate: 1_500_000, maxFramerate: 12, priority: 'medium' },
              layers: [
                createVideoPreset(960, 540, 900_000, 10, 'medium'),
                createVideoPreset(640, 360, 420_000, 8, 'low'),
              ],
              contentHint: 'text',
              degradationPreference: 'maintain-resolution',
              quality: VIDEO_QUALITY.LOW,
            },
          },
        };
    return {
      ...profile,
      ...presets[profile.mode][profile.level],
    };
  }

  function getFallbackShareProfile(profile) {
    const normalized = normalizeShareProfile(profile);
    if (normalized.level === 'high') return { mode: normalized.mode, level: 'balanced' };
    if (normalized.level === 'balanced') return { mode: normalized.mode, level: 'stable' };
    if (normalized.mode === 'motion') return { mode: 'detail', level: 'balanced' };
    return null;
  }

  function buildRoomOptions({ facingMode = 'user' } = {}) {
    const mobile = isMobileViewport();
    const cameraPrimary = mobile
      ? createVideoPreset(640, 360, 700_000, 24, 'medium')
      : createVideoPreset(1280, 720, 1_800_000, 30, 'medium');
    const cameraLayer = mobile
      ? createVideoPreset(320, 180, 180_000, 18, 'low')
      : createVideoPreset(640, 360, 700_000, 20, 'low');
    const defaultShare = getScreenShareProfileConfig({ mode: 'motion', level: 'high', mobile });
    return {
      adaptiveStream: true,
      dynacast: true,
      stopLocalTrackOnUnpublish: true,
      videoCaptureDefaults: {
        facingMode,
        resolution: cameraPrimary.resolution,
        frameRate: cameraPrimary.encoding.maxFramerate,
      },
      audioCaptureDefaults: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        channelCount: 1,
        sampleRate: 48000,
        latency: mobile ? 0.08 : 0.04,
      },
      publishDefaults: {
        videoCodec: 'vp8',
        simulcast: true,
        dtx: true,
        red: true,
        degradationPreference: 'maintain-framerate',
        videoEncoding: cameraPrimary.encoding,
        videoSimulcastLayers: [cameraLayer],
        screenShareEncoding: defaultShare.encoding,
        screenShareSimulcastLayers: defaultShare.layers,
      },
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
      roomOptions,
      initialShareProfile,
    } = options;

    let room = null;
    let connected = false;
    let connectPromise = null;
    let localState = createRemoteState();
    let shareProfile = normalizeShareProfile(initialShareProfile);
    let senderStatsCache = { bytesSent: null, timestamp: null };
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

    function getActiveShareConfig() {
      return getScreenShareProfileConfig(shareProfile);
    }

    function getScreenShareTrackPublication() {
      return room?.localParticipant?.getTrackPublication(lk.Track.Source.ScreenShare) || null;
    }

    function getScreenShareTrack() {
      return getScreenShareTrackPublication()?.track || null;
    }

    function applyTrackContentHint(publication) {
      const mediaTrack = trackToMediaStreamTrack(publication?.track);
      if (!mediaTrack) return;
      switch (publication?.source) {
        case lk.Track.Source.Camera:
          setMediaTrackContentHint(mediaTrack, 'motion');
          break;
        case lk.Track.Source.ScreenShare:
          setMediaTrackContentHint(mediaTrack, getActiveShareConfig().contentHint);
          break;
        case lk.Track.Source.Microphone:
        case lk.Track.Source.ScreenShareAudio:
          setMediaTrackContentHint(mediaTrack, 'speech');
          break;
        default:
          break;
      }
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

    async function applyActiveScreenShareProfile() {
      const track = getScreenShareTrack();
      const publication = getScreenShareTrackPublication();
      if (!track || !publication) return false;
      const profile = getActiveShareConfig();
      const mediaTrack = trackToMediaStreamTrack(track);
      if (mediaTrack) {
        setMediaTrackContentHint(mediaTrack, profile.contentHint);
      }
      if (typeof track.setDegradationPreference === 'function') {
        try {
          await track.setDegradationPreference(profile.degradationPreference);
        } catch (_) {}
      }
      if (typeof track.setPublishingQuality === 'function') {
        try {
          await track.setPublishingQuality(profile.quality);
        } catch (_) {}
      }
      return true;
    }

    function pickPrimaryVideoSenderStat(stats = []) {
      return [...stats]
        .filter((report) => report && (report.kind === 'video' || report.type === 'video'))
        .sort((a, b) => {
          const aScore = (Number(a.frameWidth || 0) * Number(a.frameHeight || 0)) || Number(a.targetBitrate || 0);
          const bScore = (Number(b.frameWidth || 0) * Number(b.frameHeight || 0)) || Number(b.targetBitrate || 0);
          return bScore - aScore;
        })[0] || null;
    }

    function summarizeScreenShareSenderStat(report) {
      if (!report) return null;
      let outboundKbps = null;
      if (
        Number.isFinite(report.bytesSent)
        && Number.isFinite(senderStatsCache.bytesSent)
        && Number.isFinite(report.timestamp)
        && Number.isFinite(senderStatsCache.timestamp)
        && report.timestamp > senderStatsCache.timestamp
      ) {
        outboundKbps = Math.round(((report.bytesSent - senderStatsCache.bytesSent) * 8) / (report.timestamp - senderStatsCache.timestamp));
      }
      senderStatsCache = {
        bytesSent: Number.isFinite(report.bytesSent) ? report.bytesSent : senderStatsCache.bytesSent,
        timestamp: Number.isFinite(report.timestamp) ? report.timestamp : senderStatsCache.timestamp,
      };
      return {
        fps: Number.isFinite(report.framesPerSecond) ? Math.round(report.framesPerSecond) : null,
        rttMs: Number.isFinite(report.roundTripTime) ? Math.round(report.roundTripTime * 1000) : null,
        packetsLost: Number.isFinite(report.packetsLost) ? Math.round(report.packetsLost) : 0,
        qualityLimitationReason: report.qualityLimitationReason || '',
        targetBitrateKbps: Number.isFinite(report.targetBitrate) ? Math.round(report.targetBitrate / 1000) : null,
        outboundKbps,
        frameWidth: Number.isFinite(report.frameWidth) ? report.frameWidth : null,
        frameHeight: Number.isFinite(report.frameHeight) ? report.frameHeight : null,
      };
    }

    async function getScreenShareSenderSnapshot() {
      const track = getScreenShareTrack();
      if (!track || typeof track.getSenderStats !== 'function') return null;
      try {
        const stats = await track.getSenderStats();
        const primary = pickPrimaryVideoSenderStat(Array.isArray(stats) ? stats : []);
        return summarizeScreenShareSenderStat(primary);
      } catch (_) {
        return null;
      }
    }

    function resetScreenShareStatsCache() {
      senderStatsCache = { bytesSent: null, timestamp: null };
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
          applyTrackContentHint(publication);
          const mediaTrack = trackToMediaStreamTrack(publication?.track);
          setTrackField(localState, publication?.source, mediaTrack);
          syncLocalStateFromPublications();
          syncLocalPreview();
          if (publication?.source === lk.Track.Source.ScreenShare) {
            resetScreenShareStatsCache();
            applyActiveScreenShareProfile().catch(() => {});
            onLocalScreenShareState?.(true);
          }
        })
        .on(lk.RoomEvent.LocalTrackUnpublished, (publication) => {
          setTrackField(localState, publication?.source, null);
          syncLocalStateFromPublications();
          syncLocalPreview();
          if (publication?.source === lk.Track.Source.ScreenShare) {
            resetScreenShareStatsCache();
            onLocalScreenShareState?.(false);
          }
        })
        .on(lk.RoomEvent.Disconnected, () => {
          connected = false;
          resetScreenShareStatsCache();
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

    async function connect() {
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
      setMediaTrackContentHint(mediaTrack, 'motion');
      await localTrack.replaceTrack(mediaTrack);
      syncLocalStateFromPublications();
      syncLocalPreview();
      return true;
    }

    async function setScreenShareEnabled(nextEnabled, { includeAudio, profile } = {}) {
      const activeRoom = requireRoom();
      const publication = activeRoom.localParticipant.getTrackPublication(lk.Track.Source.ScreenShare);
      const enabled = typeof nextEnabled === 'boolean'
        ? nextEnabled
        : !(publication?.isMuted === false && publication?.track);
      if (profile) {
        shareProfile = normalizeShareProfile(profile);
      }
      const shareAudio = typeof includeAudio === 'boolean' ? includeAudio : true;
      const config = getActiveShareConfig();
      await activeRoom.localParticipant.setScreenShareEnabled(
        enabled,
        enabled ? {
          audio: shareAudio,
          contentHint: config.contentHint,
          resolution: config.resolution,
        } : undefined,
        enabled ? {
          degradationPreference: config.degradationPreference,
          simulcast: true,
          videoCodec: 'vp8',
        } : undefined,
      );
      if (enabled) {
        await applyActiveScreenShareProfile();
      } else {
        resetScreenShareStatsCache();
      }
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
      resetScreenShareStatsCache();
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

    async function getDiagnosticsEntries() {
      if (!room) {
        return [{ label: 'LiveKit', lines: ['status: disconnected'] }];
      }
      const entries = [];
      const activeShareConfig = getActiveShareConfig();
      const shareSender = await getScreenShareSenderSnapshot();
      entries.push({
        label: 'LiveKit local',
        lines: [
          `connected: ${connected}`,
          `camera: ${localState.cameraVideo ? 'on' : 'off'}`,
          `microphone: ${localState.microphone ? 'on' : 'off'}`,
          `screen_video: ${localState.screenVideo ? 'on' : 'off'}`,
          `screen_audio: ${localState.screenAudio ? 'on' : 'off'}`,
          `share_profile: ${shareProfile.mode}/${shareProfile.level}`,
          `share_target: ${activeShareConfig.resolution.width}x${activeShareConfig.resolution.height} @ ${activeShareConfig.encoding.maxFramerate}fps`,
          shareSender
            ? `share_sender: out=${shareSender.outboundKbps ?? '-'} kbps | target=${shareSender.targetBitrateKbps ?? '-'} kbps | fps=${shareSender.fps ?? '-'} | rtt=${shareSender.rttMs ?? '-'} ms | reason=${shareSender.qualityLimitationReason || '-'}`
            : 'share_sender: inactive',
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
      getScreenShareSenderSnapshot,
      getScreenShareProfile: () => ({ ...shareProfile }),
      getFallbackScreenShareProfile: () => getFallbackShareProfile(shareProfile),
      setScreenShareProfile: async (profile, { applyToActiveShare = false } = {}) => {
        shareProfile = normalizeShareProfile(profile);
        if (applyToActiveShare) {
          return await applyActiveScreenShareProfile();
        }
        return true;
      },
      setMicrophoneEnabled,
      setCameraEnabled,
      replaceCameraTrack,
      setScreenShareEnabled,
      updateDisplayName,
    };
  }

  global.RoomPageLiveKit = {
    createController,
    buildRoomOptions,
    getScreenShareProfileConfig,
  };
})(window);
