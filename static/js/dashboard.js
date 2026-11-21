/* Owner dashboard: detects new orders and refreshes the board. */
(() => {
  const root = document.querySelector('[data-dashboard]');
  if (!root) return;
  const ids = [...root.querySelectorAll('[data-order-id]')].map((c) => +c.dataset.orderId);
  let latest = ids.length ? Math.max(...ids) : 0;
  const baseTitle = document.title;

  function beep() {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination);
      o.frequency.value = 880; g.gain.value = 0.08;
      o.start(); o.stop(ctx.currentTime + 0.18);
    } catch { /* audio blocked until user interacts: fine */ }
  }

  async function check() {
    try {
      const res = await fetch(root.dataset.feedUrl, { headers: { Accept: 'application/json' } });
      if (res.ok) {
        const data = await res.json();
        document.title = (data.pending ? `(${data.pending}) ` : '') + baseTitle;
        if (data.latest_id > latest) {
          latest = data.latest_id;
          beep();
          setTimeout(() => location.reload(), 600);
          return;
        }
      }
    } catch { /* offline: retry */ }
    setTimeout(check, 8000);
  }
  setTimeout(check, 8000);
})();
