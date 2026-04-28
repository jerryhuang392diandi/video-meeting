(function (global) {
  let loaderPromise = null;

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

  function mountBlock(block, api) {
    const target = block.querySelector('.cf-turnstile');
    const siteKey = target?.dataset?.sitekey || '';
    if (!target || !siteKey || target.dataset.rendered === '1') return;
    api.render(target, {
      sitekey: siteKey,
      callback: function () {
        setStatus(block, 'helpText');
      },
      'expired-callback': function () {
        setStatus(block, 'expiredText');
        try { api.reset(target); } catch (_) {}
      },
      'error-callback': function () {
        setStatus(block, 'failedText');
      },
    });
    target.dataset.rendered = '1';
    setStatus(block, 'helpText');
  }

  function initialize() {
    const blocks = Array.from(document.querySelectorAll('[data-turnstile-block]'));
    if (!blocks.length) return;
    blocks.forEach((block) => setStatus(block, 'loadingText'));
    loadTurnstileScript()
      .then((api) => {
        blocks.forEach((block) => mountBlock(block, api));
      })
      .catch(() => {
        blocks.forEach((block) => setStatus(block, 'failedText'));
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize, { once: true });
  } else {
    initialize();
  }
})(window);
