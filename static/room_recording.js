(function (global) {
  function createController(ctx) {
    async function transcodeRecordingBlob(blob, filename = 'meeting-recording.webm') {
      const formData = new FormData();
      formData.append('recording', blob, filename);
      const response = await fetch('/api/remux-recording', {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
      });
      if (!response.ok) {
        let message = 'convert failed';
        try {
          const data = await response.json();
          message = data?.message || message;
        } catch (_) {}
        throw new Error(message);
      }
      return await response.blob();
    }

    function stopRecordingStream() {
      try { ctx.getRecorderStream()?.getTracks?.().forEach((track) => track.stop()); } catch (_) {}
      ctx.setRecorderStream(null);
    }

    function stopRecorderIfActive() {
      const recorder = ctx.getActiveRecorder();
      if (!recorder) return;
      try {
        if (recorder.state !== 'inactive') recorder.stop();
      } catch (_) {}
    }

    async function toggleScreenRecording() {
      if (ctx.getActiveRecorder()) {
        stopRecorderIfActive();
        stopRecordingStream();
        return;
      }

      if (!navigator.mediaDevices?.getDisplayMedia || typeof MediaRecorder === 'undefined') {
        ctx.setStatus(ctx.TEXT_RECORD_NOT_SUPPORTED, 'error');
        return;
      }

      try {
        let recorderStream = null;
        try {
          recorderStream = await navigator.mediaDevices.getDisplayMedia({
            video: true,
            audio: {
              echoCancellation: false,
              noiseSuppression: false,
              sampleRate: 48000,
            },
          });
        } catch (_) {
          recorderStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
        }
        ctx.setRecorderStream(recorderStream);
        const chunks = [];

        let mimeType = '';
        let outputExt = 'webm';
        if (MediaRecorder.isTypeSupported('video/mp4;codecs=avc1.42E01E,mp4a.40.2')) {
          mimeType = 'video/mp4;codecs=avc1.42E01E,mp4a.40.2';
          outputExt = 'mp4';
        } else if (MediaRecorder.isTypeSupported('video/mp4')) {
          mimeType = 'video/mp4';
          outputExt = 'mp4';
        } else if (MediaRecorder.isTypeSupported('video/webm;codecs=vp9,opus')) {
          mimeType = 'video/webm;codecs=vp9,opus';
        } else if (MediaRecorder.isTypeSupported('video/webm;codecs=vp8,opus')) {
          mimeType = 'video/webm;codecs=vp8,opus';
        } else if (MediaRecorder.isTypeSupported('video/webm')) {
          mimeType = 'video/webm';
        } else {
          ctx.setStatus(ctx.TEXT_RECORD_NOT_SUPPORTED, 'error');
          stopRecordingStream();
          return;
        }

        const recorder = new MediaRecorder(recorderStream, mimeType ? { mimeType } : undefined);
        ctx.setActiveRecorder(recorder);
        recorder.ondataavailable = (event) => {
          if (event.data && event.data.size > 0) chunks.push(event.data);
        };
        recorder.onstop = async () => {
          const recordedBlob = new Blob(chunks, { type: mimeType || 'video/webm' });
          ctx.recordingBtn.textContent = ctx.TEXT_RECORDING;
          ctx.setActiveRecorder(null);
          ctx.setRecorderStream(null);

          if (outputExt === 'mp4' || (recordedBlob.type || '').includes('mp4')) {
            ctx.downloadBlob(recordedBlob, `meeting-recording-${Date.now()}.mp4`);
            ctx.setStatus(ctx.TEXT_RECORD_DIRECT_MP4);
            return;
          }

          try {
            ctx.setStatus(ctx.TEXT_RECORD_CONVERTING, 'warning');
            const mp4Blob = await transcodeRecordingBlob(recordedBlob, 'meeting-recording.webm');
            ctx.downloadBlob(mp4Blob, `meeting-recording-${Date.now()}.mp4`);
            ctx.setStatus(ctx.TEXT_RECORD_SAVED);
          } catch (err) {
            console.error(err);
            ctx.downloadBlob(recordedBlob, `meeting-recording-${Date.now()}.webm`);
            const reason = err?.message
              ? `${ctx.TEXT_RECORD_MP4_SERVER_ERROR}: ${err.message}`
              : ctx.TEXT_RECORD_MP4_FAILED;
            ctx.setStatus(reason, 'warning');
          }
        };
        recorderStream.getVideoTracks()[0].onended = () => {
          const activeRecorder = ctx.getActiveRecorder();
          if (activeRecorder && activeRecorder.state !== 'inactive') activeRecorder.stop();
        };
        recorder.start(1000);
        ctx.recordingBtn.textContent = ctx.TEXT_RECORD_STOP;
        ctx.setStatus(ctx.TEXT_RECORD_STOP);
      } catch (err) {
        ctx.setActiveRecorder(null);
        stopRecordingStream();
        ctx.setStatus(err.message || ctx.TEXT_RECORD_NOT_SUPPORTED, 'error');
      }
    }

    function cleanup() {
      stopRecorderIfActive();
      stopRecordingStream();
    }

    return {
      transcodeRecordingBlob,
      toggleScreenRecording,
      cleanup,
    };
  }

  global.RoomPageRecording = {
    createController,
  };
})(window);
