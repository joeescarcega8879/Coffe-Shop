/* ============================================================
   Cart experience: drawer, quick-add, steppers, toasts, fly-to-cart.
   Progressive enhancement: forms/links still work without JS.
   Server contract: POSTs with header X-Requested-With: fetch get JSON
   {count, total, items:[{pk,name,price,image,quantity,subtotal,update_url,remove_url}]}
   ============================================================ */
(() => {
  'use strict';

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const csrf = $('meta[name="csrf-token"]')?.content || '';
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const money = (n) => '$' + Number(n).toFixed(2);
  const esc = (s) =>
    String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const drawer = $('[data-cart-drawer]');
  const overlay = $('[data-cart-overlay]');
  const summaryUrl = drawer?.dataset.summaryUrl;
  const menuUrl = drawer?.dataset.menuUrl || '/menu/';

  /* ---------- Network ---------- */
  async function api(url, body) {
    const init = {
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'fetch', Accept: 'application/json' },
    };
    if (body) {
      init.method = 'POST';
      init.headers['X-CSRFToken'] = csrf;
      init.body = new URLSearchParams(body);
    }
    const res = await fetch(url, init);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return res.json();
  }

  /* ---------- Animated numbers ---------- */
  function setNow(el, value) {
    if (!el) return;
    cancelAnimationFrame(el._raf);
    el.dataset.v = value;
    el.textContent = money(value);
  }

  function tween(el, to) {
    if (!el) return;
    const from = parseFloat(el.dataset.v ?? to);
    if (reduce || from === to) return setNow(el, to);
    cancelAnimationFrame(el._raf);
    el.dataset.v = to;
    const t0 = performance.now();
    const dur = 450;
    const step = (t) => {
      const p = Math.min((t - t0) / dur, 1);
      el.textContent = money(from + (to - from) * (1 - Math.pow(1 - p, 3)));
      if (p < 1) el._raf = requestAnimationFrame(step);
    };
    el._raf = requestAnimationFrame(step);
    flash(el);
  }

  function flash(el) {
    el.classList.remove('num-flash');
    void el.offsetWidth; // restart the animation
    el.classList.add('num-flash');
  }

  /* ---------- Badge ---------- */
  function setBadges(count, bump = false) {
    $$('[data-cart-badge]').forEach((b) => {
      b.textContent = count;
      b.classList.toggle('has-items', count > 0);
      if (bump) {
        b.classList.remove('bump');
        void b.offsetWidth;
        b.classList.add('bump');
      }
    });
  }

  /* ---------- Rows (drawer + cart page share the same markup contract) ---------- */
  function toggleEmpty(empty) {
    $$('[data-when-filled]').forEach((el) => (el.hidden = empty));
    $$('[data-when-empty]').forEach((el) => (el.hidden = !empty));
  }

  function removeRow(row) {
    if (row.classList.contains('is-removing')) return;
    row.classList.add('is-removing');
    const done = () => {
      if (!row.isConnected) return;
      row.remove();
      toggleEmpty(!$('[data-row]'));
    };
    if (reduce) return done();
    row.addEventListener('transitionend', (e) => {
      if (e.target === row && e.propertyName === 'grid-template-rows') done();
    });
    setTimeout(done, 700); // safety net
  }

  function syncRows(p) {
    const byPk = new Map(p.items.map((i) => [String(i.pk), i]));
    let leaving = 0;
    $$('[data-row]').forEach((row) => {
      const it = byPk.get(row.dataset.pk);
      if (!it) {
        leaving++;
        return removeRow(row);
      }
      if (row._pending) return; // a newer request is in flight; it will sync later
      const q = $('[data-qty]', row);
      if (q && q.textContent !== String(it.quantity)) {
        q.textContent = it.quantity;
        flash(q);
      }
      row.dataset.qty = it.quantity;
      tween($('[data-row-subtotal]', row), parseFloat(it.subtotal));
    });
    $$('[data-cart-total]').forEach((el) => tween(el, parseFloat(p.total)));
    if (!leaving && !$('.is-removing')) toggleEmpty(p.items.length === 0);
  }

  function apply(p, bump = false) {
    setBadges(p.count, bump);
    $$('[data-cart-mobile-count]').forEach((el) => (el.textContent = p.count ? ` (${p.count})` : ''));
    syncRows(p);
  }

  /* ---------- Drawer ---------- */
  function rowHtml(it, i) {
    const thumb = it.image
      ? `<img class="w-full h-full object-cover" src="${esc(it.image)}" alt="" />`
      : `<span class="font-headline-sm text-on-surface-variant/40">${esc(it.name.slice(0, 1))}</span>`;
    return `
    <li class="collapse-row" data-row data-pk="${it.pk}" data-qty="${it.quantity}"
        data-update-url="${esc(it.update_url)}" data-remove-url="${esc(it.remove_url)}">
      <div class="collapse-inner">
        <div class="drawer-item flex gap-md py-md border-b border-outline-variant/20" style="--i:${i}">
          <div class="w-16 h-16 rounded-lg overflow-hidden bg-surface-variant grid place-items-center shrink-0">${thumb}</div>
          <div class="flex-1 min-w-0">
            <p class="font-label-bold text-label-bold text-primary truncate">${esc(it.name)}</p>
            <p class="text-sm text-on-surface-variant">${money(it.price)}</p>
            <div class="stepper mt-sm">
              <button type="button" data-qty-step="-1" aria-label="Decrease quantity of ${esc(it.name)}"><span class="material-symbols-outlined text-[18px]">remove</span></button>
              <span class="qty" data-qty aria-live="polite">${it.quantity}</span>
              <button type="button" data-qty-step="1" aria-label="Increase quantity of ${esc(it.name)}"><span class="material-symbols-outlined text-[18px]">add</span></button>
            </div>
          </div>
          <div class="flex flex-col items-end justify-between">
            <button type="button" data-cart-remove aria-label="Remove ${esc(it.name)}" class="text-on-surface-variant hover:text-error transition-colors"><span class="material-symbols-outlined text-[20px]">close</span></button>
            <span class="font-label-bold text-label-bold" data-row-subtotal data-v="${it.subtotal}">${money(it.subtotal)}</span>
          </div>
        </div>
      </div>
    </li>`;
  }

  function renderDrawer(p) {
    const list = $('[data-drawer-list]');
    if (!list) return;
    list.innerHTML = p.items.map(rowHtml).join('');
    $$('[data-cart-total]', drawer).forEach((el) => setNow(el, parseFloat(p.total)));
    toggleEmpty(p.items.length === 0);
  }

  let lastFocus = null;

  function openDrawer() {
    if (!drawer) return;
    lastFocus = document.activeElement;
    document.body.classList.add('cart-locked');
    drawer.classList.add('is-open');
    overlay.classList.add('is-open');
    $('[data-drawer-close]').focus({ preventScroll: true });
    api(summaryUrl)
      .then((p) => {
        setBadges(p.count);
        renderDrawer(p);
      })
      .catch(() => toast('Could not load your order.'));
  }

  function closeDrawer() {
    if (!drawer?.classList.contains('is-open')) return;
    drawer.classList.remove('is-open');
    overlay.classList.remove('is-open');
    document.body.classList.remove('cart-locked');
    lastFocus?.focus?.({ preventScroll: true });
  }

  /* ---------- Toast ---------- */
  function toast(message, actionLabel, onAction) {
    const stack = $('[data-toast-stack]');
    if (!stack) return;
    while (stack.children.length >= 3) stack.firstChild.remove();
    const t = document.createElement('div');
    t.className = 'toast';
    t.innerHTML = `<span class="material-symbols-outlined text-tertiary-fixed-dim">check_circle</span><span>${esc(message)}</span>`;
    const dismiss = () => {
      t.classList.add('is-leaving');
      setTimeout(() => t.remove(), 300);
    };
    if (actionLabel) {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = actionLabel;
      b.addEventListener('click', () => {
        onAction?.();
        dismiss();
      });
      t.append(b);
    }
    stack.append(t);
    setTimeout(dismiss, 3400);
  }

  /* ---------- Fly to cart ---------- */
  function fly(from) {
    const target = $$('[data-cart-target]').find((el) => el.offsetParent !== null);
    if (reduce || !from || !target) return;
    const a = from.getBoundingClientRect();
    const b = target.getBoundingClientRect();
    const sx = a.left + a.width / 2;
    const sy = a.top + a.height / 2;
    const ex = b.left + b.width / 2;
    const ey = b.top + b.height / 2;
    const dx = ex - sx;
    const dy = ey - sy;
    const dist = Math.hypot(dx, dy) || 1;

    // Quadratic bezier: the control point bows the path sideways/upwards so it arcs
    let nx = -dy / dist;
    let ny = dx / dist;
    if (ny > 0 || (Math.abs(ny) < 0.2 && nx > 0)) { nx = -nx; ny = -ny; }
    const lift = Math.min(dist * 0.28, 240);
    const cx = (sx + ex) / 2 + nx * lift;
    const cy = (sy + ey) / 2 + ny * lift;

    // Dense samples keep the dot visible along the WHOLE path (no mid-flight fade)
    const STEPS = 40;
    const frames = (size, peak) => Array.from({ length: STEPS + 1 }, (_, k) => {
      const lin = k / STEPS;
      const t = 0.5 - Math.cos(Math.PI * lin) / 2; // ease-in-out
      const u = 1 - t;
      const x = u * u * sx + 2 * u * t * cx + t * t * ex;
      const y = u * u * sy + 2 * u * t * cy + t * t * ey;
      const scale = 1 - 0.55 * t;
      const fade = lin > 0.88 ? (1 - lin) / 0.12 : 1; // only fades as it lands in the cart
      return {
        transform: `translate(${x - size / 2}px, ${y - size / 2}px) scale(${scale})`,
        opacity: peak * fade,
        offset: lin,
      };
    });

    const duration = Math.round(Math.min(Math.max(600 + dist * 0.5, 800), 1500));
    // head + trailing ghosts that follow the same curve
    const parts = [
      { size: 18, delay: 0, peak: 1 },
      { size: 14, delay: 45, peak: 0.55 },
      { size: 10, delay: 90, peak: 0.35 },
      { size: 7, delay: 135, peak: 0.2 },
    ];
    const anims = parts.map(({ size, delay, peak }) => {
      const dot = document.createElement('div');
      dot.className = 'fly-dot';
      dot.style.width = dot.style.height = size + 'px';
      document.body.append(dot);
      const anim = dot.animate(frames(size, peak), { duration, delay, easing: 'linear', fill: 'both' });
      anim.finished.then(() => dot.remove(), () => dot.remove());
      return anim.finished;
    });

    Promise.all(anims)
      .then(() => {
        target.classList.remove('cart-shake');
        void target.offsetWidth;
        target.classList.add('cart-shake');
      })
      .catch(() => {});
  }

  /* ---------- Actions ---------- */
  async function addToCart(url, quantity, name, origin) {
    try {
      const p = await api(url, { quantity });
      fly(origin);
      apply(p, true);
      toast(`${name} added to your order`, 'View', openDrawer);
      return true;
    } catch {
      toast('Could not add the item. Please try again.');
      return false;
    }
  }

  function queue(row, fn) {
    // serialize requests per row so rapid taps cannot arrive out of order
    row._pending = (row._pending || 0) + 1;
    const settle = () => { row._pending -= 1; };
    row._q = (row._q || Promise.resolve()).then(fn).then(settle, settle);
    return row._q;
  }

  async function refreshFromServer() {
    try {
      const p = await api(summaryUrl);
      if ($('[data-cart-page]')) return location.reload();
      renderDrawer(p);
      apply(p);
    } catch {
      location.reload();
    }
  }

  function changeQty(row, delta) {
    const next = (parseInt(row.dataset.qty, 10) || 1) + delta;
    if (next < 1) return removeItem(row);
    if (next > 20) return;
    row.dataset.qty = next; // optimistic
    $('[data-qty]', row).textContent = next;
    queue(row, () => api(row.dataset.updateUrl, { quantity: next }).then((p) => apply(p)).catch(refreshFromServer));
  }

  function removeItem(row) {
    removeRow(row);
    queue(row, () => api(row.dataset.removeUrl, {}).then((p) => apply(p)).catch(refreshFromServer));
  }

  /* ---------- Events ---------- */
  document.addEventListener('click', async (e) => {
    const quick = e.target.closest('[data-add-to-cart]');
    if (quick) {
      e.preventDefault();
      e.stopPropagation();
      if (quick.disabled) return;
      quick.disabled = true;
      const ok = await addToCart(quick.dataset.url, 1, quick.dataset.name, quick);
      quick.disabled = false;
      if (ok) {
        const icon = $('.material-symbols-outlined', quick);
        quick.classList.add('is-done');
        if (icon) icon.textContent = 'check';
        setTimeout(() => {
          quick.classList.remove('is-done');
          if (icon) icon.textContent = 'add';
        }, 1400);
      }
      return;
    }

    const step = e.target.closest('[data-qty-step]');
    if (step) return changeQty(step.closest('[data-row]'), parseInt(step.dataset.qtyStep, 10));

    const rm = e.target.closest('[data-cart-remove]');
    if (rm) return removeItem(rm.closest('[data-row]'));

    const opener = e.target.closest('[data-open-cart]');
    if (opener && drawer && !$('[data-cart-page]') && !(e.metaKey || e.ctrlKey || e.shiftKey || e.button)) {
      e.preventDefault();
      return openDrawer();
    }

    if (e.target.closest('[data-drawer-close]') || e.target === overlay) closeDrawer();
  });

  // Detail page: real form (works without JS), enhanced here.
  document.addEventListener('submit', async (e) => {
    const form = e.target.closest('form[data-add-form]');
    if (!form) return;
    e.preventDefault();
    const btn = $('[type="submit"]', form);
    const qty = parseInt($('[name="quantity"]', form).value, 10) || 1;
    btn.disabled = true;
    const ok = await addToCart(form.action, qty, form.dataset.name, btn);
    btn.disabled = false;
    if (ok) {
      const label = $('[data-label]', btn);
      const icon = $('.material-symbols-outlined', btn);
      const prevLabel = label?.textContent;
      if (label) label.textContent = 'Added!';
      if (icon) icon.textContent = 'check';
      setTimeout(() => {
        if (label) label.textContent = prevLabel;
        if (icon) icon.textContent = 'shopping_bag';
      }, 1400);
    }
  });

  document.addEventListener('keydown', (e) => {
    if (!drawer?.classList.contains('is-open')) return;
    if (e.key === 'Escape') return closeDrawer();
    if (e.key !== 'Tab') return;
    const f = $$('a[href], button:not([disabled])', drawer).filter((el) => el.offsetParent !== null);
    if (!f.length) return;
    const first = f[0];
    const last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  });

  // Back/forward cache: the badge may be stale
  window.addEventListener('pageshow', (e) => {
    if (e.persisted && summaryUrl) api(summaryUrl).then((p) => setBadges(p.count)).catch(() => {});
  });
})();
