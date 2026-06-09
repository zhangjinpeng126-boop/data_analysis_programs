/* ============================================================
   shared-report.js — 双项目共享交互功能
   在 </body> 前引入: <script src="../shared-report.js" defer></script>
   ============================================================ */

(function() {
  'use strict';

  // ===== 1. Scroll Progress Bar =====
  (function() {
    var bar = document.createElement('div');
    bar.className = 'scroll-progress';
    document.body.prepend(bar);

    function updateProgress() {
      var scrollH = document.documentElement.scrollHeight - window.innerHeight;
      bar.style.width = scrollH > 0 ? (window.scrollY / scrollH * 100) + '%' : '0%';
    }
    window.addEventListener('scroll', updateProgress, { passive: true });
    updateProgress();
  })();

  // ===== 2. Back to Top Button =====
  (function() {
    var btn = document.createElement('button');
    btn.className = 'back-to-top';
    btn.innerHTML = '↑';
    btn.setAttribute('aria-label', '返回顶部');
    document.body.appendChild(btn);

    function toggleBtn() {
      btn.classList.toggle('visible', window.scrollY > 400);
    }
    window.addEventListener('scroll', toggleBtn, { passive: true });
    btn.addEventListener('click', function() {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    toggleBtn();
  })();

  // ===== 3. Active Nav Highlighting =====
  (function() {
    var sections = document.querySelectorAll('section[id], header[id]');
    var navLinks = document.querySelectorAll('.navbar nav a[href^="#"]');
    if (!sections.length || !navLinks.length) return;

    var observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (!entry.isIntersecting) return;
        var id = entry.target.getAttribute('id');
        navLinks.forEach(function(link) {
          var isActive = link.getAttribute('href') === '#' + id;
          link.classList.toggle('active', isActive);
        });
      });
    }, { rootMargin: '-20% 0px -70% 0px' });

    sections.forEach(function(s) { observer.observe(s); });
  })();

  // ===== 4. Mobile Hamburger Menu =====
  (function() {
    var navbar = document.querySelector('.navbar .container');
    var nav = navbar ? navbar.querySelector('nav') : null;
    if (!navbar || !nav) return;

    var btn = document.createElement('button');
    btn.className = 'hamburger';
    btn.innerHTML = '☰';
    btn.setAttribute('aria-label', '菜单');
    btn.setAttribute('aria-expanded', 'false');
    navbar.insertBefore(btn, nav);

    btn.addEventListener('click', function() {
      var open = nav.classList.toggle('open');
      btn.innerHTML = open ? '✕' : '☰';
      btn.setAttribute('aria-expanded', String(open));
    });

    // Close when a link is clicked
    nav.querySelectorAll('a').forEach(function(a) {
      a.addEventListener('click', function() {
        nav.classList.remove('open');
        btn.innerHTML = '☰';
        btn.setAttribute('aria-expanded', 'false');
      });
    });
  })();

  // ===== 5. Image Lazy Loading & Error Fallback =====
  (function() {
    document.querySelectorAll('img[loading="lazy"]').forEach(function(img) {
      // Modern browsers handle loading="lazy" natively.
      // This adds error handling.
      img.addEventListener('error', function() {
        img.setAttribute('data-error', 'true');
        img.style.minHeight = '100px';
        img.alt = img.alt || '图片加载失败';
      });
    });

    // Also handle non-lazy images for error fallback
    document.querySelectorAll('img:not([loading])').forEach(function(img) {
      img.addEventListener('error', function() {
        img.setAttribute('data-error', 'true');
        img.style.minHeight = '100px';
      });
    });
  })();

})();
