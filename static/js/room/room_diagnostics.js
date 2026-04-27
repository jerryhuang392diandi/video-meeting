(function (global) {
  function createRtcDiagnosticsController({
    getPeerConnections,
    getDiagnosticEntries,
    getPeerLabel,
    getHeaderLines,
    outputEl,
    intervalMs = 4000,
  }) {
    let timer = null;
    let statsCacheBySid = new Map();

    function calcKbpsWithCache(sid, reportId, direction, byteValue, timestamp, byteField) {
      let sidCache = statsCacheBySid.get(sid);
      if (!sidCache) {
        sidCache = new Map();
        statsCacheBySid.set(sid, sidCache);
      }
      const metricKey = `${direction}:${reportId}`;
      const cached = sidCache.get(metricKey) || {};
      let kbps = null;
      if (Number.isFinite(byteValue) && Number.isFinite(cached[byteField]) && Number.isFinite(timestamp) && Number.isFinite(cached.lastTimestamp) && timestamp > cached.lastTimestamp) {
        kbps = Math.round(((byteValue - cached[byteField]) * 8) / (timestamp - cached.lastTimestamp));
      }
      cached[byteField] = byteValue;
      cached.lastTimestamp = timestamp;
      sidCache.set(metricKey, cached);
      return kbps;
    }

    function updateOutboundVideoMetrics(report, sid, metrics) {
      const kbps = calcKbpsWithCache(sid, report.id, 'out', report.bytesSent, report.timestamp, 'lastBytesSent');
      if (Number.isFinite(kbps)) metrics.outboundVideoKbps = kbps;
      if (Number.isFinite(report.framesPerSecond)) metrics.fps = Math.round(report.framesPerSecond);
    }

    function updateInboundVideoMetrics(report, sid, metrics) {
      const kbps = calcKbpsWithCache(sid, report.id, 'in', report.bytesReceived, report.timestamp, 'lastBytesReceived');
      if (Number.isFinite(kbps)) metrics.inboundVideoKbps = kbps;
      if (Number.isFinite(report.framesDecoded)) metrics.framesDecoded = report.framesDecoded;
      metrics.packetsLost += Number(report.packetsLost || 0);
    }

    function formatKbps(value) {
      return Number.isFinite(value) ? `${value} kbps` : '-';
    }

    function formatMs(value) {
      return Number.isFinite(value) ? `${value} ms` : '-';
    }

    async function collectPeerConnectionSummaries() {
      const peerConnections = getPeerConnections?.() || {};
      const summaries = [];
      for (const [sid, pc] of Object.entries(peerConnections)) {
        if (!pc?.getStats) continue;
        const metrics = {
          outboundVideoKbps: null,
          inboundVideoKbps: null,
          fps: null,
          framesDecoded: null,
          packetsLost: 0,
          rttMs: null,
        };
        try {
          const stats = await pc.getStats();
          stats.forEach((report) => {
            if (report.type === 'outbound-rtp' && report.kind === 'video' && !report.isRemote) {
              updateOutboundVideoMetrics(report, sid, metrics);
            }
            if (report.type === 'inbound-rtp' && report.kind === 'video' && !report.isRemote) {
              updateInboundVideoMetrics(report, sid, metrics);
            }
            if (report.type === 'candidate-pair' && report.state === 'succeeded' && report.nominated && Number.isFinite(report.currentRoundTripTime)) {
              metrics.rttMs = Math.round(report.currentRoundTripTime * 1000);
            }
          });
        } catch (err) {
          summaries.push(`${getPeerLabel?.(sid) || sid}\n  error: ${err?.message || String(err)}`);
          continue;
        }
        summaries.push(`${getPeerLabel?.(sid) || sid}\n  state: ${pc.connectionState || '-'} / ${pc.iceConnectionState || '-'}\n  out: ${formatKbps(metrics.outboundVideoKbps)}\n  in : ${formatKbps(metrics.inboundVideoKbps)}\n  rtt: ${formatMs(metrics.rttMs)}\n  fps: ${metrics.fps || '-'}\n  decoded: ${metrics.framesDecoded || '-'}\n  lost: ${metrics.packetsLost || 0}`);
      }
      return summaries;
    }

    async function collectDiagnosticEntries() {
      const entries = await Promise.resolve(getDiagnosticEntries?.() || []);
      return entries
        .filter((entry) => entry && entry.label)
        .map((entry) => `${entry.label}\n  ${(entry.lines || ['no details']).join('\n  ')}`);
    }

    async function refresh() {
      if (!outputEl) return;
      const peerConnections = getPeerConnections?.() || {};
      const peerCount = Object.keys(peerConnections).length;
      const header = (getHeaderLines?.() || []).join(' | ');
      outputEl.textContent = `${header}\n\nCollecting...`;
      const peerSummaries = peerCount ? await collectPeerConnectionSummaries() : [];
      const diagnosticEntries = await collectDiagnosticEntries();
      const summaries = [...peerSummaries, ...diagnosticEntries].filter(Boolean);
      outputEl.textContent = summaries.length
        ? `${header}\n\n${summaries.join('\n\n')}`
        : `${header}\n\nNo active RTC diagnostics.`;
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
        statsCacheBySid.delete(sid);
      },
      reset() {
        statsCacheBySid = new Map();
      },
    };
  }

  global.RoomPageDiagnostics = {
    createRtcDiagnosticsController,
  };
})(window);
