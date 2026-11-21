/* Order tracking: polls the status endpoint and updates the stepper live. */
(() => {
  const root = document.querySelector('[data-track]');
  if (!root) return;

  const HINTS = {
    pending: 'We got your order and will start it shortly.',
    preparing: 'Your order is being prepared.',
    ready: 'Your order is ready — come and get it!',
    completed: 'Enjoy! Thanks for visiting.',
    cancelled: 'This order was cancelled. Please contact us if this is a mistake.',
  };
  const label = root.querySelector('[data-track-label]');
  const hint = root.querySelector('[data-track-hint]');
  const tracker = root.querySelector('[data-tracker]');
  const cancelled = root.querySelector('[data-track-cancelled]');
  const banner = root.querySelector('[data-track-ready]');
  const steps = [...root.querySelectorAll('[data-step-index]')];
  let status = root.dataset.status;
  let timer;

  function render(data) {
    label.textContent = data.label;
    hint.textContent = HINTS[data.status] || '';
    const isCancelled = data.status === 'cancelled';
    tracker.hidden = isCancelled;
    cancelled.hidden = !isCancelled;
    steps.forEach((el, i) => {
      el.classList.toggle('is-done', i < data.step);
      el.classList.toggle('is-current', i === data.step);
    });
    if (data.status === 'ready' && status !== 'ready') {
      document.title = '✅ Ready! ' + document.title;
      banner.hidden = false;
      navigator.vibrate?.([200, 100, 200]);
    }
    if (data.status !== 'ready') banner.hidden = true;
    syncStorage(data.status);
  }

  // the order-watch script (other pages) reads this: don't alert again for what this page already showed
  function syncStorage(s) {
    try {
      const raw = localStorage.getItem('coffee.activeOrder');
      const o = raw && JSON.parse(raw);
      if (!o || o.statusUrl !== root.dataset.statusUrl) return;
      if (s === 'completed' || s === 'cancelled') localStorage.removeItem('coffee.activeOrder');
      else { o.status = s; o.notified = s === 'ready'; localStorage.setItem('coffee.activeOrder', JSON.stringify(o)); }
    } catch { /* storage blocked */ }
  }

  const finished = (s) => s === 'completed' || s === 'cancelled';

  async function poll() {
    try {
      const res = await fetch(root.dataset.statusUrl, { headers: { Accept: 'application/json' } });
      if (res.ok) {
        const data = await res.json();
        if (data.status !== status) { render(data); status = data.status; }
        if (data.done) return;
      }
    } catch { /* offline: just retry */ }
    timer = setTimeout(poll, 5000);
  }

  if (!finished(status)) timer = setTimeout(poll, 5000);
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && !finished(status)) { clearTimeout(timer); poll(); }
  });
})();
