(function (global) {
  function bumpCodeAttemptCounter(form) {
    const chip = form?.querySelector('.auth-code-attempt-chip');
    if (!chip) return;
    const match = String(chip.textContent || '').match(/^\s*(\d+)\s*\/\s*(\d+)\s*$/);
    if (!match) return;
    const current = Number.parseInt(match[1], 10);
    const limit = Number.parseInt(match[2], 10);
    if (!Number.isFinite(current) || !Number.isFinite(limit) || current >= limit) return;
    chip.textContent = `${current + 1}/${limit}`;
  }

  function bindIntentForm(options) {
    const {
      formId,
      intentInputId,
      sendSelector = '[data-code-submit="1"]',
      submitSelector = '[data-full-submit="1"]',
      sendIntent,
      submitIntent,
      sendingText = '',
    } = options || {};
    const form = document.getElementById(formId);
    const intentInput = document.getElementById(intentInputId);
    if (!form || !intentInput) return;

    form.querySelector(sendSelector)?.addEventListener('click', () => {
      intentInput.value = sendIntent;
      form.noValidate = true;
    });

    form.querySelector(submitSelector)?.addEventListener('click', () => {
      intentInput.value = submitIntent;
      form.noValidate = false;
    });

    form.addEventListener('submit', (event) => {
      const submitter = event.submitter;
      if (submitter?.dataset?.codeSubmit === '1') {
        intentInput.value = sendIntent;
      }
      if (submitter?.dataset?.fullSubmit === '1') {
        intentInput.value = submitIntent;
      }
      if (intentInput.value !== sendIntent || !submitter) return;
      bumpCodeAttemptCounter(form);
      submitter.disabled = true;
      if (sendingText) submitter.textContent = sendingText;
    });
  }

  global.AuthFlow = {
    bindIntentForm,
  };
})(window);
