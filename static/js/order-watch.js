/* Tells the customer, on whatever page of the site they are, when their order is ready.
   The tracking/success pages register the order in localStorage; every other page
   polls its status endpoint and shows an alert once it changes to ready/completed. */
(() => {
  const KEY = 'coffee.activeOrder';
  const MAX_AGE = 12 * 60 * 60 * 1000;
  const read = () => { try { return JSON.parse(localStorage.getItem(KEY)); } catch { return null; } };
  const write = (v) => { try { v ? localStorage.setItem(KEY, JSON.stringify(v)) : localStorage.removeItem(KEY); } catch { /* storage blocked */ } };
  const isFinal = (s) => s === 'completed' || s === 'cancelled';

  // success / tracking page: remember the order (or forget it when it is over)
  const src = document.querySelector('[data-watch-order]');
  if (src) {
    const d = src.dataset;
    if (isFinal(d.status)) write(null);
    else {
      const prev = read();
      const same = prev && prev.statusUrl === d.statusUrl;
      write({ id: d.orderId, statusUrl: d.statusUrl, trackUrl: d.trackUrl, status: d.status,
              notified: (same && prev.notified) || d.status === 'ready', ts: same ? prev.ts : Date.now() });
    }
  }
  // the tracking page has its own live view; it keeps storage in sync itself
  if (document.querySelector('[data-track]')) return;

  let order = read();
  if (!order || Date.now() - order.ts > MAX_AGE || !String(order.statusUrl).startsWith('/track/')) {
    if (order) write(null);
    return;
  }

  const PILL_TEXT = { pending: 'Order received', preparing: 'Preparing your order', ready: 'Your order is ready!' };

  // floating button so the customer can get back to their order from any page
  let pill = null;
  function renderPill() {
    if (src) return;                       // success/track pages already link to the order
    if (!pill) {
      pill = document.createElement('a');
      pill.className = 'order-pill';
      pill.setAttribute('aria-live', 'polite');
      pill.innerHTML = '<span class="order-pill-dot" aria-hidden="true"></span>' +
        '<span class="order-pill-text"></span>' +
        '<span class="order-pill-go">View</span>';
      pill.href = order.trackUrl;
      document.body.appendChild(pill);
      document.body.classList.add('has-order-pill');
      requestAnimationFrame(() => requestAnimationFrame(() => pill.classList.add('is-in')));
    }
    pill.dataset.status = order.status;
    pill.querySelector('.order-pill-text').textContent = (PILL_TEXT[order.status] || 'Track your order') + ' · #' + order.id;
    pill.setAttribute('aria-label', (PILL_TEXT[order.status] || 'Track your order') + ', order number ' + order.id + '. View order');
  }
  function removePill() {
    pill?.remove(); pill = null;
    document.body.classList.remove('has-order-pill');
  }
  renderPill();

  const MESSAGES = {
    ready: ['Your order is ready!', 'Come and pick it up.'],
    completed: ['Your order is complete', 'Enjoy! Thanks for visiting.'],
    cancelled: ['Your order was cancelled', 'Please contact us if this is a mistake.'],
  };

  function showAlert(status) {
    const [title, text] = MESSAGES[status] || MESSAGES.ready;
    document.querySelector('.order-alert')?.remove();
    const el = document.createElement('div');
    el.className = 'order-alert';
    el.setAttribute('role', 'alert');
    el.innerHTML = '<span aria-hidden="true" class="material-symbols-outlined order-alert-icon">notifications_active</span>' +
      '<div class="order-alert-body"><strong></strong><span></span></div>' +
      '<a class="order-alert-link">View</a>' +
      '<button type="button" class="order-alert-close" aria-label="Dismiss"><span aria-hidden="true" class="material-symbols-outlined">close</span></button>';
    el.querySelector('strong').textContent = title;
    el.querySelector('.order-alert-body span').textContent = text;
    el.querySelector('.order-alert-link').href = order.trackUrl;
    el.querySelector('.order-alert-close').addEventListener('click', () => el.classList.remove('is-in'));
    document.body.appendChild(el);
    requestAnimationFrame(() => requestAnimationFrame(() => el.classList.add('is-in')));
    navigator.vibrate?.([200, 100, 200]);
    if (document.hidden) document.title = '✅ ' + title + ' · ' + document.title;
  }

  let timer;
  async function poll() {
    if (document.hidden) return;           // resumes on visibilitychange
    try {
      const res = await fetch(order.statusUrl, { headers: { Accept: 'application/json' } });
      if (res.status === 404) { removePill(); return write(null); }
      if (res.ok) {
        const data = await res.json();
        if (data.status !== order.status || (isFinal(data.status) && !order.notified)) {
          if (!order.notified && (data.status === 'ready' || isFinal(data.status))) {
            showAlert(data.status);
            order.notified = true;
          }
          order.status = data.status;
          write(isFinal(data.status) ? null : order);
          if (isFinal(data.status)) removePill(); else renderPill();
        }
        if (isFinal(data.status)) return;
      }
    } catch { /* offline: retry */ }
    timer = setTimeout(poll, 8000);
  }
  poll();
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) { clearTimeout(timer); poll(); }
  });
})();
