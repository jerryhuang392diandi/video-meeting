(function (global) {
  function createRenderScheduler(render, { requestFrame = global.requestAnimationFrame?.bind(global), onDeferred = null } = {}) {
    let frameId = 0;
    let forcePending = false;
    let deferRender = false;

    function queue(force = false) {
      forcePending = forcePending || !!force;
      if (frameId || typeof requestFrame !== 'function') {
        if (!frameId && typeof requestFrame !== 'function') {
          const shouldForce = forcePending;
          forcePending = false;
          render(shouldForce);
        }
        return;
      }
      frameId = requestFrame(() => {
        const shouldForce = forcePending;
        frameId = 0;
        forcePending = false;
        if (deferRender) {
          onDeferred?.();
          return;
        }
        render(shouldForce);
      });
    }

    return {
      queue,
      defer() {
        deferRender = true;
      },
      flush(force = false) {
        deferRender = false;
        queue(force);
      },
      isDeferred() {
        return deferRender;
      },
    };
  }

  function createTaskQueue({ onError = (err) => console.error(err), onStart = null, onFinish = null } = {}) {
    let chain = Promise.resolve();
    return function runTask(label, task) {
      const execute = async () => {
        onStart?.(label);
        try {
          return await task();
        } finally {
          onFinish?.(label);
        }
      };
      const pending = chain.then(execute, execute);
      chain = pending.catch((err) => {
        onError(err, label);
      });
      return pending;
    };
  }

  global.RoomPageUi = {
    createRenderScheduler,
    createTaskQueue,
  };
})(window);
