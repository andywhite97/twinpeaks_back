(() => {
  const form = document.querySelector('#campaign-send');
  if (!form) return;
  const resume = document.querySelector('#campaign-resume');
  const pause = document.querySelector('#campaign-pause');
  const progress = document.querySelector('#campaign-progress');
  let running = false;
  pause.addEventListener('click', () => { running = false; pause.disabled = true; });
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (running) return;
    running = true;
    resume.disabled = true;
    pause.hidden = false;
    pause.disabled = false;
    try {
      while (running) {
        const response = await fetch(form.dataset.url, {
          method: 'POST', credentials: 'same-origin',
          headers: { 'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value }
        });
        if (!response.ok) throw new Error('Sending paused. Reload this page to check delivery records before resuming.');
        const { counts: c, status } = await response.json();
        progress.textContent = `Accepted: ${c.accepted} · Pending: ${c.pending} · Rejected: ${c.failed} · Unknown: ${c.unknown} · Unverified: ${c.sending} · Skipped: ${c.skipped}`;
        if (status === 'complete' || !c.pending) {
          running = false;
          // One final call lets the server finish the campaign after the final recipient.
          if (status !== 'complete') await fetch(form.dataset.url, {method:'POST', credentials:'same-origin', headers:{'X-CSRFToken':form.querySelector('[name=csrfmiddlewaretoken]').value}});
          location.reload();
          return;
        }
        if (c.failed || c.unknown) {
          running = false;
          progress.textContent += ' — Paused: review the provider issue before continuing.';
        }
      }
    } catch (error) {
      progress.textContent += ' — Sending paused. Reload to check delivery records before resuming.';
    } finally {
      running = false;
      resume.disabled = false;
      pause.hidden = true;
    }
  });
  if (form.dataset.autoStart === 'yes') form.requestSubmit();
})();
