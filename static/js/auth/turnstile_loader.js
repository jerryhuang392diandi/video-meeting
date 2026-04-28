(function (global) {
  let loaderPromise = null;
  const mountedBlocks = new WeakMap();

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
    const tokenField = form.querySelector('input[name="cf-turnstile-response"]');
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
    if (!target || !siteKey) return;
    if (mountedBlocks.has(block)) return mountedBlocks.get(block);
    const widgetId = api.render(target, {
      sitekey: siteKey,
      callback: function () {
        setStatus(block, 'helpText');
        requestPendingFormSubmit(block);
      },
      'expired-callback': function () {
        setStatus(block, 'expiredText');
        try { api.reset(target); } catch (_) {}
      },
      'error-callback': function () {
        setStatus(block, 'failedText');
      },
    });
    mountedBlocks.set(block, widgetId);
    setStatus(block, 'helpText');
    return widgetId;
  }

  function initializeBlock(block) {
    if (!block || mountedBlocks.has(block)) return Promise.resolve();
    setStatus(block, 'loadingText');
    return loadTurnstileScript()
      .then((api) => {
        mountBlock(block, api);
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

    const eagerInit = function () {
      initializeBlock(block).catch(() => {});
    };

    form.addEventListener('focusin', eagerInit, { once: true });
    form.addEventListener('pointerdown', eagerInit, { once: true });

    form.addEventListener('submit', function (event) {
      const tokenField = form.querySelector('input[name="cf-turnstile-response"]');
      if (tokenField?.value) return;
      event.preventDefault();
      block.dataset.submitPending = '1';
      initializeBlock(block).catch(() => {});
    });
  }

  function initialize() {
    const blocks = Array.from(document.querySelectorAll('[data-turnstile-block]'));
    if (!blocks.length) return;
    blocks.forEach((block) => {
      setStatus(block, 'helpText');
      bindBlock(block);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize, { once: true });
  } else {
    initialize();
  }
})(window);
