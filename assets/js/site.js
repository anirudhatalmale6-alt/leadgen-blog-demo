/* ==========================================================================
   Northbound - behaviour layer
   Demo build for Freelancer project 40739401

   Everything below is vanilla JS, no dependencies, no external requests.
   In the real build each of these maps to a small theme script or a plugin
   setting. The forms run in DEMO MODE: nothing is sent anywhere. See
   submitToEsp() for the single function that gets swapped for the live
   email platform call.
   ========================================================================== */

(function () {
  'use strict';

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ------------------------------------------------------------------
     Demo strip
     ------------------------------------------------------------------ */

  function initDemoStrip() {
    var strip = document.querySelector('[data-demo-strip]');
    if (!strip) return;

    try {
      if (window.sessionStorage.getItem('nb-demo-strip') === 'closed') {
        strip.hidden = true;
      }
    } catch (err) {
      /* storage blocked, leave the strip visible */
    }

    var close = strip.querySelector('[data-demo-close]');
    if (!close) return;

    close.addEventListener('click', function () {
      strip.hidden = true;
      measureHead();
      try {
        window.sessionStorage.setItem('nb-demo-strip', 'closed');
      } catch (err) {
        /* nothing to do */
      }
    });
  }

  /* ------------------------------------------------------------------
     Header: stuck state, mobile nav, offset measurement
     ------------------------------------------------------------------ */

  var head = document.querySelector('[data-head]');

  function measureHead() {
    if (!head) return;
    var rect = head.getBoundingClientRect();
    document.documentElement.style.setProperty(
      '--head-offset',
      Math.round(rect.bottom) + 'px'
    );
  }

  function initHeader() {
    if (!head) return;

    var toggle = head.querySelector('[data-nav-toggle]');
    var nav = head.querySelector('[data-nav]');

    var onScroll = function () {
      head.classList.toggle('is-stuck', window.scrollY > 8);
      measureHead();
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', measureHead);
    onScroll();

    if (!toggle || !nav) return;

    toggle.addEventListener('click', function () {
      var open = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!open));
      nav.classList.toggle('is-open', !open);
      measureHead();
    });

    nav.addEventListener('click', function (event) {
      if (event.target.closest('a')) {
        toggle.setAttribute('aria-expanded', 'false');
        nav.classList.remove('is-open');
      }
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && nav.classList.contains('is-open')) {
        toggle.setAttribute('aria-expanded', 'false');
        nav.classList.remove('is-open');
        toggle.focus();
      }
    });
  }

  /* ------------------------------------------------------------------
     Reveal on scroll
     ------------------------------------------------------------------ */

  function initReveal() {
    var items = document.querySelectorAll('.reveal');
    if (!items.length) return;

    if (reduceMotion || !('IntersectionObserver' in window)) {
      Array.prototype.forEach.call(items, function (el) {
        el.classList.add('is-in');
      });
      return;
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          var el = entry.target;
          var delay = parseInt(el.getAttribute('data-delay') || '0', 10);
          window.setTimeout(function () {
            el.classList.add('is-in');
          }, delay);
          observer.unobserve(el);
        });
      },
      { rootMargin: '0px 0px -8% 0px', threshold: 0.08 }
    );

    Array.prototype.forEach.call(items, function (el) {
      observer.observe(el);
    });
  }

  /* ------------------------------------------------------------------
     Reading progress
     ------------------------------------------------------------------ */

  function initProgress() {
    var bar = document.querySelector('[data-progress]');
    var article = document.querySelector('[data-article]');
    if (!bar || !article) return;

    var update = function () {
      var rect = article.getBoundingClientRect();
      var total = rect.height - window.innerHeight;
      var seen = -rect.top;
      var pct = total > 0 ? Math.min(Math.max(seen / total, 0), 1) : 0;
      bar.style.width = (pct * 100).toFixed(2) + '%';
    };

    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    update();
  }

  /* ------------------------------------------------------------------
     Table of contents scrollspy
     ------------------------------------------------------------------ */

  function initToc() {
    var toc = document.querySelector('[data-toc]');
    if (!toc || !('IntersectionObserver' in window)) return;

    var links = Array.prototype.slice.call(toc.querySelectorAll('a[href^="#"]'));
    if (!links.length) return;

    var targets = links
      .map(function (link) {
        return document.getElementById(link.getAttribute('href').slice(1));
      })
      .filter(Boolean);

    var setActive = function (id) {
      links.forEach(function (link) {
        link.classList.toggle(
          'is-active',
          link.getAttribute('href') === '#' + id
        );
      });
    };

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) setActive(entry.target.id);
        });
      },
      { rootMargin: '-15% 0px -70% 0px', threshold: 0 }
    );

    targets.forEach(function (el) {
      observer.observe(el);
    });
  }

  /* ------------------------------------------------------------------
     Slide-up CTA bar
     ------------------------------------------------------------------ */

  function initSlidebar() {
    var bar = document.querySelector('[data-slidebar]');
    if (!bar) return;

    var dismissed = false;
    try {
      dismissed = window.sessionStorage.getItem('nb-slidebar') === 'closed';
    } catch (err) {
      /* storage blocked */
    }
    if (dismissed) return;

    var trigger = parseInt(bar.getAttribute('data-trigger') || '40', 10) / 100;

    var update = function () {
      var max = document.documentElement.scrollHeight - window.innerHeight;
      var pct = max > 0 ? window.scrollY / max : 0;
      var nearBottom = pct > 0.93;
      bar.classList.toggle('is-up', pct > trigger && !nearBottom);
    };

    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    update();

    var close = bar.querySelector('[data-slidebar-close]');
    if (!close) return;

    close.addEventListener('click', function () {
      bar.classList.remove('is-up');
      window.removeEventListener('scroll', update);
      window.removeEventListener('resize', update);
      try {
        window.sessionStorage.setItem('nb-slidebar', 'closed');
      } catch (err) {
        /* nothing to do */
      }
    });
  }

  /* ------------------------------------------------------------------
     Lead capture forms
     ------------------------------------------------------------------ */

  /* This is the ONE place that talks to the email platform.
     In the live build the body of this function becomes either:
       a) a fetch() to the ESP endpoint (ConvertKit, Beehiiv, Brevo), or
       b) a submit to the form plugin (Fluent Forms, WPForms, Ghost members),
     and everything else on the page stays exactly as it is. */
  function submitToEsp(payload) {
    return new Promise(function (resolve) {
      if (window.console && window.console.info) {
        window.console.info('[demo mode] lead captured, not sent:', payload);
      }
      window.setTimeout(function () {
        resolve({ ok: true });
      }, 650);
    });
  }

  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

  function initForms() {
    var forms = document.querySelectorAll('[data-capture]');
    if (!forms.length) return;

    Array.prototype.forEach.call(forms, function (form) {
      var input = form.querySelector('input[type="email"]');
      var errorEl = form.querySelector('[data-error]');
      var button = form.querySelector('button[type="submit"]');
      var done = document.getElementById(form.getAttribute('data-done'));

      var showError = function (message) {
        if (errorEl) errorEl.textContent = message;
        if (input) input.setAttribute('aria-invalid', 'true');
      };

      var clearError = function () {
        if (errorEl) errorEl.textContent = '';
        if (input) input.removeAttribute('aria-invalid');
      };

      if (input) input.addEventListener('input', clearError);

      form.addEventListener('submit', function (event) {
        event.preventDefault();

        var value = input ? input.value.trim() : '';

        if (!value) {
          showError('Please enter your email address.');
          if (input) input.focus();
          return;
        }

        if (!EMAIL_RE.test(value)) {
          showError('That email address does not look right. Please check it.');
          if (input) input.focus();
          return;
        }

        clearError();

        var payload = {
          email: value,
          /* The tag is what makes attribution work: you can see which article
             or landing page produced each lead inside the email platform. */
          tag: form.getAttribute('data-tag') || 'general',
          source: window.location.pathname,
          referrer: document.referrer || 'direct'
        };

        var extra = form.querySelector('select[name="segment"]');
        if (extra) payload.segment = extra.value;

        var label = button ? button.innerHTML : '';
        if (button) {
          button.disabled = true;
          button.textContent = 'Sending';
        }

        submitToEsp(payload).then(function () {
          if (button) {
            button.disabled = false;
            button.innerHTML = label;
          }

          if (done) {
            form.hidden = true;
            done.hidden = false;
            var heading = done.querySelector('strong');
            if (heading) {
              done.setAttribute('tabindex', '-1');
              done.focus();
            }
          } else {
            form.reset();
          }
        });
      });
    });
  }

  /* ------------------------------------------------------------------
     Year stamp
     ------------------------------------------------------------------ */

  function initYear() {
    var nodes = document.querySelectorAll('[data-year]');
    Array.prototype.forEach.call(nodes, function (el) {
      el.textContent = String(new Date().getFullYear());
    });
  }

  /* ------------------------------------------------------------------
     Boot
     ------------------------------------------------------------------ */

  function boot() {
    initDemoStrip();
    initHeader();
    measureHead();
    initReveal();
    initProgress();
    initToc();
    initSlidebar();
    initForms();
    initYear();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
