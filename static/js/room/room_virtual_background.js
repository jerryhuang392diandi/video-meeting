(function (global) {
  let segmentationScriptPromise = null;

  function createController(ctx) {
    function loadSegmentationSdk({ timeoutMs = 18000 } = {}) {
      if (typeof global.SelfieSegmentation !== 'undefined') return Promise.resolve(global.SelfieSegmentation);
      if (segmentationScriptPromise) return segmentationScriptPromise;
      segmentationScriptPromise = new Promise((resolve, reject) => {
        const existing = document.querySelector('script[data-mediapipe-selfie-segmentation="1"]');
        const script = existing || document.createElement('script');
        let settled = false;
        const finish = (fn, value) => {
          if (settled) return;
          settled = true;
          fn(value);
        };
        const timer = global.setTimeout(() => {
          finish(reject, new Error(ctx.TEXT_VIRTUAL_BG_DEPENDENCY_UNAVAILABLE));
        }, timeoutMs);
        const handleLoad = () => {
          global.clearTimeout(timer);
          if (typeof global.SelfieSegmentation !== 'undefined') {
            finish(resolve, global.SelfieSegmentation);
          } else {
            finish(reject, new Error(ctx.TEXT_VIRTUAL_BG_DEPENDENCY_UNAVAILABLE));
          }
        };
        const handleError = () => {
          global.clearTimeout(timer);
          finish(reject, new Error(ctx.TEXT_VIRTUAL_BG_DEPENDENCY_UNAVAILABLE));
        };
        script.addEventListener('load', handleLoad, { once: true });
        script.addEventListener('error', handleError, { once: true });
        if (!existing) {
          script.src = 'https://cdn.jsdelivr.net/npm/@mediapipe/selfie_segmentation/selfie_segmentation.js';
          script.async = true;
          script.defer = true;
          script.dataset.mediapipeSelfieSegmentation = '1';
          document.head.appendChild(script);
        }
      }).catch((error) => {
        segmentationScriptPromise = null;
        throw error;
      });
      return segmentationScriptPromise;
    }

    function cleanupProcessedVideoStream({ stopCanvas = false } = {}) {
      const processedVideoStream = ctx.getProcessedVideoStream();
      if (processedVideoStream && processedVideoStream !== ctx.getRawCameraStream()) {
        processedVideoStream.getVideoTracks().forEach((track) => {
          try { track.stop(); } catch (_) {}
        });
      }
      ctx.setProcessedVideoStream(null);
      if (stopCanvas && ctx.getProcessedCanvasStream()) {
        ctx.stopStreamTracks(ctx.getProcessedCanvasStream());
        ctx.setProcessedCanvasStream(null);
      }
    }

    function cleanupVirtualBackgroundRawStream() {
      const virtualBgRawStream = ctx.getVirtualBgRawStream();
      if (!virtualBgRawStream) return;
      if (ctx.rawPreviewVideo.srcObject === virtualBgRawStream) {
        ctx.rawPreviewVideo.srcObject = null;
      }
      ctx.stopStreamTracks(virtualBgRawStream);
      ctx.setVirtualBgRawStream(null);
    }

    function disableVirtualBackgroundState({ stopCanvas = false, cleanupProcessed = true, stopRaw = false } = {}) {
      ctx.setVirtualBgEnabled(false);
      ctx.setVirtualBgLoopActive(false);
      ctx.setSegmentationSending(false);
      ctx.bumpVirtualBgActivationToken();
      ctx.setActiveVirtualBgToken(0);
      if (stopRaw) cleanupVirtualBackgroundRawStream();
      if (cleanupProcessed) {
        cleanupProcessedVideoStream({ stopCanvas });
      } else if (stopCanvas && ctx.getProcessedCanvasStream()) {
        ctx.stopStreamTracks(ctx.getProcessedCanvasStream());
        ctx.setProcessedCanvasStream(null);
      }
    }

    function getLiveVideoTrack(stream) {
      return stream?.getVideoTracks?.().find((track) => track && track.readyState === 'live' && track.enabled !== false) || null;
    }

    function hasLiveVideoTrack(stream) {
      return !!getLiveVideoTrack(stream);
    }

    function getVirtualBackgroundSourceStream() {
      if (hasLiveVideoTrack(ctx.getVirtualBgRawStream())) return ctx.getVirtualBgRawStream();
      if (hasLiveVideoTrack(ctx.getRawCameraStream())) return ctx.getRawCameraStream();
      if (ctx.IS_LIVEKIT_MODE && !ctx.getIsSharingScreen() && hasLiveVideoTrack(ctx.getLocalStream())) {
        return ctx.getLocalStream();
      }
      return null;
    }

    function ensureVirtualBackgroundRawStream() {
      if (hasLiveVideoTrack(ctx.getVirtualBgRawStream())) return ctx.getVirtualBgRawStream();
      cleanupVirtualBackgroundRawStream();
      const sourceStream = getVirtualBackgroundSourceStream();
      const sourceTrack = getLiveVideoTrack(sourceStream);
      if (!sourceTrack) return null;
      const rawTrack = sourceTrack.clone();
      ctx.setMediaTrackContentHint(rawTrack, 'motion');
      const nextStream = new MediaStream([rawTrack]);
      ctx.setVirtualBgRawStream(nextStream);
      return nextStream;
    }

    async function replaceLiveKitCameraTrackFromStream(stream) {
      if (!ctx.IS_LIVEKIT_MODE) return false;
      const controller = await ctx.ensureLiveKitConnected();
      if (!controller?.replaceCameraTrack) return false;
      const sourceTrack = getLiveVideoTrack(stream);
      if (!sourceTrack) return false;
      ctx.setMediaTrackContentHint(sourceTrack, 'motion');
      return await controller.replaceCameraTrack(sourceTrack.clone());
    }

    async function fallbackToRawCamera(message = null, { stopCanvas = false } = {}) {
      const rawSourceStream = getVirtualBackgroundSourceStream();
      disableVirtualBackgroundState({ stopCanvas, cleanupProcessed: false });
      if (rawSourceStream) {
        try {
          await replaceLiveKitCameraTrackFromStream(rawSourceStream);
        } catch (err) {
          console.error(err);
        }
      }
      cleanupProcessedVideoStream({ stopCanvas });
      ctx.updateVirtualBackgroundButtonState();
      if (message) ctx.setStatus(message, 'warning');
    }

    async function deactivateVirtualBackground(message = null, { stopCanvas = false } = {}) {
      await fallbackToRawCamera(message || ctx.TEXT_VIRTUAL_BG_OFF, { stopCanvas });
    }

    function getScaledSize(width, height) {
      if (!width || !height) return { width: 640, height: 360 };
      const scale = Math.min(ctx.MAX_VBG_WIDTH / width, ctx.MAX_VBG_HEIGHT / height, 1);
      const scaledWidth = Math.max(2, Math.round((width * scale) / 2) * 2);
      const scaledHeight = Math.max(2, Math.round((height * scale) / 2) * 2);
      return { width: scaledWidth, height: scaledHeight };
    }

    async function waitForVideoReady(videoEl, timeoutMs = 2000) {
      if (!videoEl?.srcObject || !hasLiveVideoTrack(videoEl.srcObject)) {
        throw new Error(ctx.TEXT_VIRTUAL_BG_CAMERA_UNAVAILABLE);
      }
      if (videoEl.readyState >= 2 && videoEl.videoWidth && videoEl.videoHeight) return true;
      await new Promise((resolve, reject) => {
        const timer = setTimeout(() => {
          cleanup();
          reject(new Error(ctx.TEXT_VIRTUAL_BG_CAMERA_UNAVAILABLE));
        }, timeoutMs);
        const onReady = () => {
          if (!videoEl.videoWidth || !videoEl.videoHeight) return;
          cleanup();
          resolve(true);
        };
        const cleanup = () => {
          clearTimeout(timer);
          videoEl.removeEventListener('loadedmetadata', onReady);
          videoEl.removeEventListener('canplay', onReady);
        };
        videoEl.addEventListener('loadedmetadata', onReady);
        videoEl.addEventListener('canplay', onReady);
      });
      return true;
    }

    async function ensureProcessedCanvasStream() {
      const processedCanvasStream = ctx.getProcessedCanvasStream();
      if (processedCanvasStream && processedCanvasStream.getVideoTracks()[0]?.readyState === 'live') {
        return processedCanvasStream;
      }
      if (processedCanvasStream) {
        ctx.stopStreamTracks(processedCanvasStream);
        ctx.setProcessedCanvasStream(null);
      }
      if (!ctx.processingCanvas.width || !ctx.processingCanvas.height) {
        throw new Error('Processed canvas is empty');
      }
      const nextStream = ctx.processingCanvas.captureStream(ctx.VBG_CAPTURE_FPS);
      ctx.applyMediaStreamContentHints(nextStream, { videoHint: 'motion' });
      ctx.setProcessedCanvasStream(nextStream);
      return nextStream;
    }

    async function loadSegmentationModel({ quiet = false } = {}) {
      if (ctx.getSegmentationModel()) return ctx.getSegmentationModel();
      if (!quiet) {
        ctx.setStatus(ctx.TEXT_VIRTUAL_BG_DEPENDENCY_LOADING, 'warning');
      }
      await loadSegmentationSdk();
      if (typeof SelfieSegmentation === 'undefined') {
        throw new Error(ctx.TEXT_VIRTUAL_BG_DEPENDENCY_UNAVAILABLE);
      }
      const segmentationModel = new SelfieSegmentation({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/selfie_segmentation/${file}`,
      });
      segmentationModel.setOptions({ modelSelection: 1 });
      segmentationModel.onResults(onSegmentationResults);
      ctx.setSegmentationModel(segmentationModel);
      return segmentationModel;
    }

    async function warmupSegmentationModel() {
      try {
        await loadSegmentationModel({ quiet: true });
        return true;
      } catch (_) {
        return false;
      }
    }

    function onSegmentationResults(results) {
      if (!ctx.getVirtualBgEnabled()) return;

      const sourceWidth = results.image.videoWidth || results.image.width || 1280;
      const sourceHeight = results.image.videoHeight || results.image.height || 720;
      const { width, height } = getScaledSize(sourceWidth, sourceHeight);
      if (ctx.processingCanvas.width !== width || ctx.processingCanvas.height !== height) {
        ctx.processingCanvas.width = width;
        ctx.processingCanvas.height = height;
      }

      ctx.processingCtx.save();
      ctx.processingCtx.clearRect(0, 0, width, height);
      ctx.processingCtx.drawImage(results.segmentationMask, 0, 0, width, height);
      ctx.processingCtx.globalCompositeOperation = 'source-in';
      ctx.processingCtx.drawImage(results.image, 0, 0, width, height);
      ctx.processingCtx.globalCompositeOperation = 'destination-over';
      ctx.processingCtx.filter = ctx.IS_MOBILE ? 'blur(10px)' : 'blur(18px)';
      ctx.processingCtx.drawImage(results.image, 0, 0, width, height);
      ctx.processingCtx.filter = 'none';
      ctx.processingCtx.restore();
      ctx.incrementProcessedFrameCount();
    }

    async function startSegmentationLoop() {
      if (ctx.getVirtualBgLoopActive()) return;
      ctx.setVirtualBgLoopActive(true);

      const scheduleNext = () => {
        if (!ctx.getVirtualBgEnabled()) return;
        if (typeof ctx.rawPreviewVideo.requestVideoFrameCallback === 'function') {
          ctx.rawPreviewVideo.requestVideoFrameCallback(() => {
            if (ctx.getVirtualBgEnabled()) loop();
          });
          return;
        }
        setTimeout(loop, Math.round(1000 / ctx.VBG_CAPTURE_FPS));
      };

      const loop = async () => {
        if (!ctx.getVirtualBgEnabled()) {
          ctx.setVirtualBgLoopActive(false);
          return;
        }
        if (ctx.getSegmentationSending() || !ctx.rawPreviewVideo.srcObject) {
          scheduleNext();
          return;
        }
        try {
          ctx.setSegmentationSending(true);
          await ctx.getSegmentationModel().send({ image: ctx.rawPreviewVideo });
        } catch (err) {
          console.error(err);
        } finally {
          ctx.setSegmentationSending(false);
          scheduleNext();
        }
      };

      scheduleNext();
    }

    async function activateVirtualBackground() {
      const sourceStream = ensureVirtualBackgroundRawStream();
      if (!sourceStream) {
        ctx.setStatus(ctx.TEXT_VIRTUAL_BG_NEEDS_CAMERA, 'warning');
        return false;
      }
      const activationToken = ctx.bumpVirtualBgActivationToken();
      ctx.setStatus(ctx.TEXT_VIRTUAL_BG_LOADING, 'warning');

      try {
        await loadSegmentationModel({ quiet: false });
        if (!hasLiveVideoTrack(sourceStream)) {
          throw new Error(ctx.TEXT_VIRTUAL_BG_CAMERA_UNAVAILABLE);
        }
        if (ctx.rawPreviewVideo.srcObject !== sourceStream) {
          ctx.rawPreviewVideo.srcObject = sourceStream;
        }
        await ctx.rawPreviewVideo.play().catch(() => {});
        await waitForVideoReady(ctx.rawPreviewVideo, 6000);

        const startCount = ctx.getProcessedFrameCount();

        ctx.setVirtualBgEnabled(true);
        ctx.updateVirtualBackgroundButtonState();
        await startSegmentationLoop();

        const deadline = Date.now() + 8000;
        while (ctx.getProcessedFrameCount() < startCount + 1) {
          if (activationToken !== ctx.getVirtualBgActivationToken()) return false;
          if (Date.now() > deadline) throw new Error(ctx.TEXT_VIRTUAL_BG_PROCESSING_TIMEOUT);
          await new Promise((resolve) => setTimeout(resolve, 60));
        }

        const processedCanvasStream = await ensureProcessedCanvasStream();
        const processedTrack = processedCanvasStream.getVideoTracks()[0];
        if (!processedTrack) throw new Error('Processed video track unavailable');

        const nextOutputStream = new MediaStream();
        nextOutputStream.addTrack(processedTrack.clone());
        sourceStream.getAudioTracks().forEach((track) => nextOutputStream.addTrack(track));

        if (activationToken !== ctx.getVirtualBgActivationToken()) {
          ctx.stopStreamTracks(nextOutputStream);
          return false;
        }

        if (ctx.IS_LIVEKIT_MODE) {
          const replaced = await replaceLiveKitCameraTrackFromStream(nextOutputStream);
          if (!replaced) throw new Error('LiveKit camera replacement unavailable');
        }

        cleanupProcessedVideoStream();
        ctx.setProcessedVideoStream(nextOutputStream);
        ctx.setActiveVirtualBgToken(activationToken);
        ctx.updateVirtualBackgroundButtonState();
        ctx.setStatus(ctx.TEXT_VIRTUAL_BG_READY);
        return true;
      } catch (err) {
        console.error(err);
        await fallbackToRawCamera(`${ctx.TEXT_VIRTUAL_BG_FAILED}: ${err.message || 'unknown error'}`, { stopCanvas: true });
        return false;
      }
    }

    function cleanup() {
      disableVirtualBackgroundState({ stopCanvas: true, stopRaw: true });
      ctx.rawPreviewVideo.srcObject = null;
      cleanupVirtualBackgroundRawStream();
      cleanupProcessedVideoStream({ stopCanvas: true });
    }

    return {
      cleanupProcessedVideoStream,
      cleanupVirtualBackgroundRawStream,
      disableVirtualBackgroundState,
      getLiveVideoTrack,
      hasLiveVideoTrack,
      getVirtualBackgroundSourceStream,
      ensureVirtualBackgroundRawStream,
      replaceLiveKitCameraTrackFromStream,
      fallbackToRawCamera,
      deactivateVirtualBackground,
      getScaledSize,
      waitForVideoReady,
      ensureProcessedCanvasStream,
      loadSegmentationModel,
      warmupSegmentationModel,
      startSegmentationLoop,
      activateVirtualBackground,
      cleanup,
    };
  }

  global.RoomPageVirtualBackground = {
    createController,
  };
})(window);
