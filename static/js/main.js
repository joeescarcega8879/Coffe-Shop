/* ============================================================
   Coffee Shop — Shared site scripts
   Handles: active nav link, mobile menu, scroll reveal animations.
   Loaded on: home.html, menu.html, detail.html, contact.html
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  /* ---------- Active nav link (based on current page) ---------- */
  const currentPage = document.body.dataset.page || 'home';

  document.querySelectorAll('[data-nav-link]').forEach(link => {

    const href = (link.getAttribute('href') || '').split('/').filter(Boolean)[0] || '';
    if (href === currentPage || (currentPage === 'menu' && href === 'menu')) {
      link.classList.add('nav-active');
      link.setAttribute('aria-current', 'page');
    }
  });

  // Sub-pages that belong to a main section (e.g. product detail -> Menu)
  const sectionOf = { 'detail.html': 'menu.html' };
  const activePage = sectionOf[currentPage] || currentPage;

  document.querySelectorAll('[data-nav-link]').forEach(link => {
    const href = (link.getAttribute('href') || '').split('#')[0];
    if (href === activePage) {
      link.classList.add('nav-active');
      link.setAttribute('aria-current', 'page');
    }
  });

  /* ---------- Mobile menu toggle ---------- */
  const mobileBtn = document.getElementById('mobile-menu-btn');
  const mobileMenu = document.getElementById('mobile-menu');

  if (mobileBtn && mobileMenu) {
    const icon = mobileBtn.querySelector('.material-symbols-outlined');
    const setMenu = (open) => {
      mobileMenu.classList.toggle('is-open', open);
      mobileBtn.setAttribute('aria-expanded', String(open));
      mobileBtn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
      mobileMenu.inert = !open;           // closed links can't be tabbed to
      if (icon) icon.textContent = open ? 'close' : 'menu';
    };
    setMenu(false);
    mobileBtn.addEventListener('click', () => setMenu(!mobileMenu.classList.contains('is-open')));
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && mobileMenu.classList.contains('is-open')) { setMenu(false); mobileBtn.focus(); }
    });
    // leaving the mobile layout while open: reset
    window.matchMedia('(min-width: 768px)').addEventListener('change', (e) => { if (e.matches) setMenu(false); });
  }

  /* ---------- Scroll reveal animations ---------- */
  const observerOptions = {
    root: null,
    rootMargin: '0px',
    threshold: 0.1
  };

  // Stagger delay for detail-page related cards
  document.querySelectorAll('.scroll-reveal').forEach((el, index) => {
    el.style.transitionDelay = `${index * 150}ms`;
  });

  const revealObserver = new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el = entry.target;

      if (el.classList.contains('animate-on-scroll')) {
        // Menu page: elements carry data-animation + data-delay
        const animation = el.getAttribute('data-animation');
        const delay = parseInt(el.getAttribute('data-delay') || '0', 10);
        const reveal = () => {
          if (animation) {
            el.classList.remove('invisible-initial');
            el.classList.add(animation);
          } else {
            el.classList.add('is-visible');
          }
        };
        if (delay > 0) {
          setTimeout(reveal, delay);
        } else {
          reveal();
        }
      } else if (el.classList.contains('observer-element')) {
        // Contact page
        el.classList.add('is-revealed');
      } else if (el.classList.contains('scroll-reveal')) {
        // Detail page
        el.classList.add('is-visible');
      }

      obs.unobserve(el);
    });
  }, observerOptions);

  document.querySelectorAll('.animate-on-scroll, .observer-element, .scroll-reveal')
    .forEach(el => revealObserver.observe(el));
});
