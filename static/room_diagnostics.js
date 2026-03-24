(function (global) {
  function createRtcDiagnosticsController({
    getPeerConnections,
    getPeerLabel,
    getHeaderLines,
    outputEl,
    intervalMs = 4000,
  }) {
    let timer = null;
    let statsCache = {};

    function formatKbps(value) {
      return Number.isFinite(value) ? `${value} kbps` : '-';
    }

    function formatMs(value) {
      return Number.isFinite(value) ? `${value} ms` : '-';
    }

    async function collect() {
      const peerConnections = getPeerConnections?.() || {};
      const summaries = [];
      for (const [sid, pc] of Object.entries(peerConnections)) {
        if (!pc?.getStats) continue;
        let outboundVideoKbps = null;
        let inboundVideoKbps = null;
        let fps = null;
        let framesDecoded = null;
        let packetsLost = 0;
        let rttMs = null;
        try {
          const stats = await pc.getStats();
          stats.forEach((report) => {
            if (report.type === 'outbound-rtp' && report.kind === 'video' && !report.isRemote) {
              const cacheKey = `${sid}:out:${report.id}`;
              const cached = statsCache[cacheKey] || {};
              if (Number.isFinite(report.bytesSent) && Number.isFinite(cached.lastBytesSent) && Number.isFinite(report.timestamp) && Number.isFinite(cached.lastTimestamp) && report.timestamp > cached.lastTimestamp) {
                outboundVideoKbps = Math.round(((report.bytesSent - cached.lastBytesSent) * 8) / (report.timestamp - cached.lastTimestamp));
              }
              statsCache[cacheKey] = { ...cached, lastBytesSent: report.bytesSent, lastTimestamp: report.timestamp };
              if (Number.isFinite(report.framesPerSecond)) fps = Math.round(report.framesPerSecond);
            }
            if (report.type === 'inbound-rtp' && report.kind === 'video' && !report.isRemote) {
              const cacheKey = `${sid}:in:${report.id}`;
              const cached = statsCache[cacheKey] || {};
              if (Number.isFinite(report.bytesReceived) && Number.isFinite(cached.lastBytesReceived) && Number.isFinite(report.timestamp) && Number.isFinite(cached.lastTimestamp) && report.timestamp > cached.lastTimestamp) {
                inboundVideoKbps = Math.round(((report.bytesReceived - cached.lastBytesReceived) * 8) / (report.timestamp - cached.lastTimestamp));
              }
              statsCache[cacheKey] = { ...cached, lastBytesReceived: report.bytesReceived, lastTimestamp: report.timestamp };
              if (Number.isFinite(report.framesDecoded)) framesDecoded = report.framesDecoded;
              packetsLost += Number(report.packetsLost || 0);
            }
            if (report.type === 'candidate-pair' && report.state === 'succeeded' && report.nominated && Number.isFinite(report.currentRoundTripTime)) {
              rttMs = Math.round(report.currentRoundTripTime * 1000);
            }
          });
        } catch (err) {
          summaries.push(`${getPeerLabel?.(sid) || sid}\n  error: ${err?.message || String(err)}`);
          continue;
        }
        summaries.push(`${getPeerLabel?.(sid) || sid}\n  state: ${pc.connectionState || '-'} / ${pc.iceConnectionState || '-'}\n  out: ${formatKbps(outboundVideoKbps)}\n  in : ${formatKbps(inboundVideoKbps)}\n  rtt: ${formatMs(rttMs)}\n  fps: ${fps || '-'}\n  decoded: ${framesDecoded || '-'}\n  lost: ${packetsLost || 0}`);
      }
      return summaries;
    }

    async function refresh() {
      if (!outputEl) return;
      const peerConnections = getPeerConnections?.() || {};
      const peerCount = Object.keys(peerConnections).length;
      const header = (getHeaderLines?.() || []).join(' | ');
      if (!peerCount) {
        outputEl.textContent = `${header}\n\nNo active peer connections.`;
        return;
      }
      outputEl.textContent = `${header}\n\nCollecting...`;
      const summaries = await collect();
      outputEl.textContent = `${header}\n\n${summaries.join('\n\n')}`;
    }

    return {
      start() {
        if (timer) clearInterval(timer);
        refresh().catch(() => {});
        timer = setInterval(() => {
          refresh().catch(() => {});
        }, intervalMs);
      },
      stop() {
        if (timer) clearInterval(timer);
        timer = null;
      },
      refresh,
      pruneSid(sid) {
        Object.keys(statsCache).forEach((key) => {
          if (key.startsWith(`${sid}:`)) delete statsCache[key];
        });
      },
      reset() {
        statsCache = {};
      },
    };
  }

  global.RoomPageDiagnostics = {
    createRtcDiagnosticsController,
  };
})(window);
