(function (global) {
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
      submitter.disabled = true;
      if (sendingText) submitter.textContent = sendingText;
    });
  }

  global.AuthFlow = {
    bindIntentForm,
  };
})(window);
