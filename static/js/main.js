// static/js/main.js
(() => {
  'use strict';

  // Keep default behavior for normal links (no hijacking)
  document.addEventListener('click', (e) => {
    const a = e.target.closest('a.btn');
    if (!a) return;
    // Only handle custom in-page behaviors if added.
  });

  let __sd_lastScrollY = 0; // remember scroll when locking

  const initDrawer = () => {
    const drawer   = document.getElementById('sdDrawer');
    const overlay  = document.getElementById('sdDrawerOverlay');
    const toggle   = document.querySelector('.sd-mobile-toggle');
    const closeBtn = drawer ? drawer.querySelector('.sd-drawer__close') : null;

    if (!drawer || !overlay || !toggle) return;
    if (drawer.dataset.bound === '1') return;
    drawer.dataset.bound = '1';

    const openDrawer = () => {
      __sd_lastScrollY = window.scrollY || window.pageYOffset || 0;
      document.body.style.top = `-${__sd_lastScrollY}px`;
      document.body.classList.add('drawer-open');

      drawer.classList.add('open');
      overlay.classList.add('show');
      overlay.hidden = false;
      toggle.setAttribute('aria-expanded', 'true');
      drawer.setAttribute('aria-hidden', 'false');
    };

    const closeDrawer = () => {
      drawer.classList.remove('open');
      overlay.classList.remove('show');
      overlay.hidden = true;

      document.body.classList.remove('drawer-open');
      document.body.style.top = '';
      window.scrollTo(0, __sd_lastScrollY);

      toggle.setAttribute('aria-expanded', 'false');
      drawer.setAttribute('aria-hidden', 'true');
    };

    // Toggle on burger click
    toggle.addEventListener('click', () => {
      if (drawer.classList.contains('open')) closeDrawer();
      else openDrawer();
    });

    overlay.addEventListener('click', closeDrawer);
    if (closeBtn) closeBtn.addEventListener('click', closeDrawer);

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && drawer.classList.contains('open')) closeDrawer();
    });

    drawer.addEventListener('click', (e) => {
      const link = e.target.closest('a.sd-drawer__link');
      if (link) closeDrawer();
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDrawer);
  } else {
    initDrawer();
  }
})();
