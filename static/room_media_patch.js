(function (global) {
  function getActiveOutboundAudioTracks() {
    const screenAudioTracks = isSharingScreen ? (localVideo?.srcObject?.getAudioTracks?.() || []) : [];
    if (screenAudioTracks.length) return screenAudioTracks;
    return localStream?.getAudioTracks?.() || [];
  }

  const originalRequestMedia = global.requestMedia;

  async function patchedRequestMedia(forceFacingMode = null, manualRequest = false, preferredKinds = null) {
    if (!isSharingScreen || typeof originalRequestMedia !== 'function') {
      return await originalRequestMedia(forceFacingMode, manualRequest, preferredKinds);
    }

    const originalUseLocalOutputStream = global.useLocalOutputStream;
    global.useLocalOutputStream = function preserveScreenSharePreview(stream) {
      localStream = stream;
      syncPeerMedia().catch((err) => console.error(err));
    };

    try {
      return await originalRequestMedia(forceFacingMode, manualRequest, preferredKinds);
    } finally {
      global.useLocalOutputStream = originalUseLocalOutputStream;
    }
  }

  async function patchedSyncPeerMedia(targetSid = null) {
    const entries = targetSid
      ? (peerConnections[targetSid] ? [[targetSid, peerConnections[targetSid]]] : [])
      : Object.entries(peerConnections);
    const tracks = [];
    const activeSourceStream = (isSharingScreen ? localVideo?.srcObject : null) || localStream;
    const activeVideoTrack = (isSharingScreen ? getCurrentScreenTrack() : null) || localStream?.getVideoTracks?.()[0] || null;
    if (activeVideoTrack) tracks.push(activeVideoTrack);
    getActiveOutboundAudioTracks().forEach((track) => tracks.push(track));
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
            pc.addTrack(track, activeSourceStream || localStream);
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

  function patchedEnsurePeer(targetSid) {
    if (peerConnections[targetSid]) return peerConnections[targetSid];
    const pc = new RTCPeerConnection(rtcConfig);
    peerConnections[targetSid] = pc;

    const activeSourceStream = (isSharingScreen ? localVideo?.srcObject : null) || localStream;
    const outboundVideoTrack = (isSharingScreen ? getCurrentScreenTrack() : null) || localStream?.getVideoTracks?.()[0] || null;
    if (outboundVideoTrack) pc.addTrack(outboundVideoTrack, activeSourceStream || localStream);
    getActiveOutboundAudioTracks().forEach((track) => pc.addTrack(track, activeSourceStream || localStream));

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

  global.getActiveOutboundAudioTracks = getActiveOutboundAudioTracks;
  global.requestMedia = patchedRequestMedia;
  global.syncPeerMedia = patchedSyncPeerMedia;
  global.ensurePeer = patchedEnsurePeer;
})(window);
