(function (global) {
  function getSenderByKind(pc, kind) {
    const senders = pc?.getSenders?.() || [];
    const direct = senders.find((sender) => sender.track?.kind === kind);
    if (direct) return direct;
    const transceivers = pc?.getTransceivers?.() || [];
    const fromTransceiver = transceivers.find((transceiver) => {
      if (transceiver?.stopped) return false;
      if (transceiver?.mid == null && !transceiver?.sender) return false;
      const transceiverKind = transceiver.sender?.track?.kind || transceiver.receiver?.track?.kind || null;
      return transceiverKind === kind;
    });
    return fromTransceiver?.sender || null;
  }

  function getVideoSender(pc) {
    return getSenderByKind(pc, 'video');
  }

  function getAudioSender(pc) {
    return getSenderByKind(pc, 'audio');
  }

  function getVideoSenderProfile({ isScreenShare = false, peerCount = 1, profiles = {} } = {}) {
    const shareProfiles = profiles.screenShare || {};
    const cameraProfiles = profiles.camera || {};
    if (isScreenShare) {
      if (peerCount <= 2) return shareProfiles.small || shareProfiles.medium || shareProfiles.large || {};
      if (peerCount <= 4) return shareProfiles.medium || shareProfiles.small || shareProfiles.large || {};
      if (peerCount <= 6) return shareProfiles.large || shareProfiles.medium || shareProfiles.small || {};
      return shareProfiles.xlarge || shareProfiles.large || shareProfiles.medium || shareProfiles.small || {};
    }
    if (peerCount <= 2) return cameraProfiles.small || cameraProfiles.medium || cameraProfiles.large || {};
    if (peerCount <= 4) return cameraProfiles.medium || cameraProfiles.small || cameraProfiles.large || {};
    return cameraProfiles.large || cameraProfiles.medium || cameraProfiles.small || {};
  }

  function applyTrackContentHint(track, { isScreenShare = false } = {}) {
    if (!track) return;
    try {
      track.contentHint = isScreenShare ? 'detail' : 'motion';
    } catch (_) {}
  }

  async function applySenderOptimization(sender, { isScreenShare = false, peerCount = 1, profiles = {}, totalUplinkBudget = null } = {}) {
    if (!sender?.track || typeof sender.getParameters !== 'function' || typeof sender.setParameters !== 'function') return;
    const params = sender.getParameters() || {};
    const encodings = Array.isArray(params.encodings) && params.encodings.length ? params.encodings : [{}];
    const profile = getVideoSenderProfile({ isScreenShare, peerCount, profiles });
    applyTrackContentHint(sender.track, { isScreenShare });
    params.degradationPreference = profile.degradationPreference || (isScreenShare ? 'maintain-resolution' : 'balanced');
    const profileBitrate = Number(profile.maxBitrate) || null;
    const budgetBitrate = (Number.isFinite(totalUplinkBudget) && totalUplinkBudget > 0)
      ? Math.max(250_000, Math.floor(totalUplinkBudget / Math.max(1, peerCount)))
      : null;
    const targetBitrate = profileBitrate && budgetBitrate ? Math.min(profileBitrate, budgetBitrate) : (profileBitrate || budgetBitrate || null);
    params.encodings = encodings.map((encoding) => ({
      ...encoding,
      maxBitrate: targetBitrate || encoding.maxBitrate,
      maxFramerate: profile.maxFramerate || encoding.maxFramerate,
      scaleResolutionDownBy: profile.scaleResolutionDownBy || encoding.scaleResolutionDownBy,
      priority: profile.priority || encoding.priority,
      networkPriority: profile.networkPriority || encoding.networkPriority,
    }));
    await sender.setParameters(params);
  }

  function replaceTracksByKind(stream, track) {
    if (!stream || !track) return;
    stream.getTracks()
      .filter((existing) => existing.kind === track.kind && existing.id !== track.id)
      .forEach((existing) => {
        try { stream.removeTrack(existing); } catch (_) {}
      });
    if (!stream.getTracks().some((existing) => existing.id === track.id)) {
      stream.addTrack(track);
    }
  }

  async function replaceSenderTrack(pc, kind, track, stream = null, options = {}) {
    const sender = kind === 'video' ? getVideoSender(pc) : getAudioSender(pc);
    if (sender) {
      const previousTrackId = sender.track?.id || null;
      const nextTrackId = track?.id || null;
      await sender.replaceTrack(track || null);
      if (kind === 'video' && track) await applySenderOptimization(sender, options);
      return { sender, added: false, changed: previousTrackId !== nextTrackId };
    }
    if (!track) return { sender: null, added: false, changed: false };
    const nextStream = stream || new MediaStream([track]);
    const nextSender = pc.addTrack(track, nextStream);
    if (kind === 'video') await applySenderOptimization(nextSender, options);
    return { sender: nextSender, added: true, changed: true };
  }

  function mergeIncomingTrackIntoStream(remoteMediaStreams, sid, event, onReady) {
    const incomingStream = event.streams?.[0] || new MediaStream(event.track ? [event.track] : []);
    const mergedStream = remoteMediaStreams[sid] || new MediaStream();
    remoteMediaStreams[sid] = mergedStream;
    incomingStream.getTracks().forEach((track) => {
      replaceTracksByKind(mergedStream, track);
      track.onended = () => {
        try { mergedStream.removeTrack(track); } catch (_) {}
        onReady?.(mergedStream);
      };
    });
    onReady?.(mergedStream);
    return mergedStream;
  }

  global.RoomPageRtc = {
    getVideoSender,
    getAudioSender,
    getVideoSenderProfile,
    applyTrackContentHint,
    applySenderOptimization,
    replaceSenderTrack,
    mergeIncomingTrackIntoStream,
  };
})(window);
