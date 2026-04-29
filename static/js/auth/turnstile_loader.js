(function (global) {
  let loaderPromise = null;
  const mountedBlocks = new WeakMap();
  let retryTimer = null;
  const pendingBlocks = new WeakSet();

  function loadTurnstileScript() {
    if (global.turnstile?.render) return Promise.resolve(global.turnstile);
    if (loaderPromise) return loaderPromise;
    loaderPromise = new Promise((resolve, reject) => {
      const existing = document.querySelector('script[data-turnstile-loader="1"]');
      const script = existing || document.createElement('script');
      let settled = false;
      const finish = (fn, value) => {
        if (settled) return;
        settled = true;
        fn(value);
      };
      const timer = global.setTimeout(() => {
        finish(reject, new Error('turnstile_load_timeout'));
      }, 8000);
      const handleLoad = () => {
        global.clearTimeout(timer);
        if (global.turnstile?.render) {
          finish(resolve, global.turnstile);
        } else {
          finish(reject, new Error('turnstile_missing_api'));
        }
      };
      const handleError = () => {
        global.clearTimeout(timer);
        finish(reject, new Error('turnstile_load_error'));
      };
      script.addEventListener('load', handleLoad, { once: true });
      script.addEventListener('error', handleError, { once: true });
      if (!existing) {
        script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
        script.async = true;
        script.defer = true;
        script.dataset.turnstileLoader = '1';
        document.head.appendChild(script);
      }
    }).catch((error) => {
      loaderPromise = null;
      throw error;
    });
    return loaderPromise;
  }

  function isRenderable(block) {
    if (!block || !document.body.contains(block)) return false;
    const target = block.querySelector('.cf-turnstile');
    if (!target) return false;
    const style = global.getComputedStyle(block);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    const rect = target.getBoundingClientRect();
    return rect.width >= 200 && rect.height >= 40;
  }

  function ensureTokenField(form) {
    if (!form) return null;
    let tokenField = form.querySelector('input[name="cf-turnstile-response"]');
    if (tokenField) return tokenField;
    tokenField = document.createElement('input');
    tokenField.type = 'hidden';
    tokenField.name = 'cf-turnstile-response';
    form.appendChild(tokenField);
    return tokenField;
  }

  function setStatus(block, key) {
    const node = block?.querySelector('[data-turnstile-status]');
    if (!node) return;
    const text = block.dataset[key];
    if (text) node.textContent = text;
  }

  function requestPendingFormSubmit(block) {
    const form = block?.closest('form');
    if (!form || block.dataset.submitPending !== '1') return;
    block.dataset.submitPending = '0';
    const tokenField = ensureTokenField(form);
    if (!tokenField?.value) return;
    if (typeof form.requestSubmit === 'function') {
      form.requestSubmit();
    } else {
      form.submit();
    }
  }

  function mountBlock(block, api) {
    const target = block.querySelector('.cf-turnstile');
    const siteKey = target?.dataset?.sitekey || '';
    const form = block.closest('form');
    if (!target || !siteKey) return;
    if (mountedBlocks.has(block)) return mountedBlocks.get(block);
    const widgetId = api.render(target, {
      sitekey: siteKey,
      callback: function (token) {
        const tokenField = ensureTokenField(form);
        if (tokenField) tokenField.value = token || '';
        setStatus(block, 'helpText');
        requestPendingFormSubmit(block);
      },
      'expired-callback': function () {
        const tokenField = ensureTokenField(form);
        if (tokenField) tokenField.value = '';
        setStatus(block, 'expiredText');
        try { api.reset(widgetId); } catch (_) {}
      },
      'error-callback': function () {
        const tokenField = ensureTokenField(form);
        if (tokenField) tokenField.value = '';
        setStatus(block, 'failedText');
      },
    });
    mountedBlocks.set(block, widgetId);
    ensureTokenField(form);
    setStatus(block, 'helpText');
    return widgetId;
  }

  function initializeBlock(block) {
    if (!block || mountedBlocks.has(block)) return Promise.resolve();
    if (!isRenderable(block)) {
      pendingBlocks.add(block);
      return Promise.resolve();
    }
    setStatus(block, 'loadingText');
    return loadTurnstileScript()
      .then((api) => {
        mountBlock(block, api);
        pendingBlocks.delete(block);
      })
      .catch(() => {
        setStatus(block, 'failedText');
        throw new Error('turnstile_init_failed');
      });
  }

  function bindBlock(block) {
    const form = block.closest('form');
    if (!form || block.dataset.bound === '1') return;
    block.dataset.bound = '1';
    ensureTokenField(form);

    form.addEventListener('submit', function (event) {
      const tokenField = ensureTokenField(form);
      if (tokenField?.value) return;
      event.preventDefault();
      block.dataset.submitPending = '1';
      initializeBlock(block).catch(() => {});
    });
  }

  function retryVisibleBlocks() {
    const blocks = Array.from(document.querySelectorAll('[data-turnstile-block]'));
    blocks.forEach((block) => {
      const tokenField = ensureTokenField(block.closest('form'));
      if (tokenField?.value) return;
       if (!isRenderable(block)) {
        pendingBlocks.add(block);
        return;
      }
      initializeBlock(block).catch(() => {});
    });
  }

  function scheduleRetry() {
    if (retryTimer) global.clearTimeout(retryTimer);
    retryTimer = global.setTimeout(() => {
      retryTimer = null;
      retryVisibleBlocks();
    }, 1200);
  }

  function initialize() {
    const blocks = Array.from(document.querySelectorAll('[data-turnstile-block]'));
    if (!blocks.length) return;
    blocks.forEach((block) => {
      setStatus(block, 'helpText');
      bindBlock(block);
      initializeBlock(block).catch(() => {});
    });
    scheduleRetry();
  }

  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) scheduleRetry();
  });
  document.addEventListener('focusin', function (event) {
    if (event.target instanceof HTMLElement && event.target.closest('form')) {
      scheduleRetry();
    }
  });
  global.addEventListener('pageshow', scheduleRetry);
  global.addEventListener('load', scheduleRetry);
  global.addEventListener('resize', scheduleRetry);
  global.addEventListener('orientationchange', scheduleRetry);
  global.addEventListener('online', scheduleRetry);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize, { once: true });
  } else {
    initialize();
  }
})(window);
