"""
Northbound demo, end to end checks.

Run:  python3 tests/test_site.py
It serves the folder on a free port, drives Chromium and prints a PASS/FAIL
line per check. Exit code is non zero if anything failed.

What it proves, rather than assumes:
  * every page loads with no console or page errors
  * no element sticks out past the viewport at 390 / 768 / 1280
    (measured per element rect, because overflow-x:hidden makes a
     scrollWidth check a false pass)
  * every capture form rejects empty and malformed input and shows the
    success panel on a good address
  * the mobile drawer, the reading progress bar, the scrollspy, the
    slide-up bar and the demo strip all actually do something
  * every JSON-LD block is valid JSON with the expected @type
  * every internal link points at a file that exists
  * no em dash or en dash reaches the rendered page, including inside
    placeholders, aria-labels, titles and alt text
  * body and muted text clear WCAG AA against the paper background
"""

import http.server
import json
import os
import re
import socket
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
PAGES = ["index.html", "article.html", "landing.html"]

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS  " if ok else "FAIL  ") + name + ((" :: " + detail) if detail else ""))


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, *a):
        pass


def serve(port):
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


# --------------------------------------------------------------------------
# Static source checks
# --------------------------------------------------------------------------

def check_sources():
    bad_dash = []
    for dirpath, _dirs, files in os.walk(ROOT):
        if any(p in dirpath for p in (".git", "node_modules", "tests")):
            continue
        for fn in files:
            if not fn.endswith((".html", ".css", ".js", ".md")):
                continue
            path = os.path.join(dirpath, fn)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            for marker in ("—", "–", "&mdash;", "&ndash;"):
                if marker in text:
                    rel = os.path.relpath(path, ROOT)
                    bad_dash.append(rel + " contains " + repr(marker))
    check("source files contain no em or en dash", not bad_dash, "; ".join(bad_dash))


# --------------------------------------------------------------------------
# Per page checks
# --------------------------------------------------------------------------

OVERFLOW_JS = """() => {
  const vw = document.documentElement.clientWidth;
  const bad = [];
  document.querySelectorAll('body *').forEach(el => {
    if (el.closest('.skip-link') || el.classList.contains('skip-link')) return;
    const st = getComputedStyle(el);
    if (st.visibility === 'hidden' || st.display === 'none') return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;
    if (r.right > vw + 1.5 || r.left < -1.5) {
      bad.push(el.tagName.toLowerCase() + '.' +
        (typeof el.className === 'string' ? el.className.split(' ')[0] : '') +
        ' [' + Math.round(r.left) + ',' + Math.round(r.right) + '] vw=' + vw);
    }
  });
  return bad.slice(0, 8);
}"""

DASH_JS = r"""() => {
  const hits = [];
  const re = /[–—]/;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = walker.nextNode())) {
    if (re.test(n.nodeValue)) hits.push('text: ' + n.nodeValue.trim().slice(0, 60));
  }
  document.querySelectorAll('*').forEach(el => {
    ['placeholder', 'aria-label', 'title', 'alt', 'value', 'content'].forEach(a => {
      const v = el.getAttribute && el.getAttribute(a);
      if (v && re.test(v)) hits.push(a + '="' + v.slice(0, 60) + '"');
    });
  });
  return hits.slice(0, 8);
}"""


def relative_luminance(hexstr):
    hexstr = hexstr.strip().lstrip("#")
    if len(hexstr) == 3:
        hexstr = "".join(c * 2 for c in hexstr)
    parts = [int(hexstr[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in parts]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(fg, bg):
    a, b = relative_luminance(fg), relative_luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def check_contrast():
    pairs = [
        ("body text", "#383029", "#f7f3ec", 4.5),
        ("muted text", "#635a50", "#f7f3ec", 4.5),
        ("link and label accent", "#b32e15", "#f7f3ec", 4.5),
        ("button label on signal", "#ffffff", "#b32e15", 4.5),
        ("dark block body", "#c2b8a9", "#14110f", 4.5),
        ("dark block muted label", "#a79c8d", "#14110f", 4.5),
        ("footer link", "#a79c8d", "#14110f", 4.5),
    ]
    for label, fg, bg, need in pairs:
        ratio = contrast(fg, bg)
        check(
            "contrast, " + label,
            ratio >= need,
            "%.2f:1 (needs %.1f)" % (ratio, need),
        )


def check_links(page, name):
    hrefs = page.eval_on_selector_all(
        "a[href]", "els => els.map(e => e.getAttribute('href'))"
    )
    missing = []
    for href in hrefs:
        if not href or href.startswith(("#", "http", "mailto:", "tel:", "data:")):
            continue
        target = href.split("#")[0].split("?")[0]
        if target and not os.path.exists(os.path.join(ROOT, target)):
            missing.append(href)
    check(name + ": every internal link resolves to a file", not missing, ", ".join(sorted(set(missing))))


def check_schema(page, name, expected):
    blocks = page.eval_on_selector_all(
        'script[type="application/ld+json"]', "els => els.map(e => e.textContent)"
    )
    check(name + ": has JSON-LD", len(blocks) > 0)
    types = set()
    for raw in blocks:
        try:
            data = json.loads(raw)
        except Exception as err:
            check(name + ": JSON-LD parses", False, str(err))
            return
        nodes = data.get("@graph", [data]) if isinstance(data, dict) else data
        for node in nodes:
            if isinstance(node, dict) and "@type" in node:
                types.add(node["@type"])
    check(name + ": JSON-LD parses", True)
    for want in expected:
        check(name + ": schema includes " + want, want in types, "found " + ", ".join(sorted(types)))


def check_forms(page, name):
    forms = page.query_selector_all("[data-capture]")
    check(name + ": has at least one capture form", len(forms) > 0)

    for idx in range(len(forms)):
        form = page.query_selector_all("[data-capture]")[idx]
        tag = form.get_attribute("data-tag")
        email = form.query_selector('input[type="email"]')
        err = form.query_selector("[data-error]")
        submit = form.query_selector('button[type="submit"]')

        # 1. empty submit is rejected
        email.fill("")
        submit.click()
        page.wait_for_timeout(120)
        check(
            name + " form " + tag + ": empty input is rejected",
            bool(err.inner_text().strip()),
            err.inner_text().strip(),
        )

        # 2. malformed address is rejected
        email.fill("not-an-email")
        submit.click()
        page.wait_for_timeout(120)
        check(
            name + " form " + tag + ": malformed address is rejected",
            bool(err.inner_text().strip()),
            err.inner_text().strip(),
        )

        # 3. a good address reaches the success panel
        email.fill("rosa@example.com")
        submit.click()
        page.wait_for_timeout(1100)
        done_id = form.get_attribute("data-done")
        done = page.query_selector("#" + done_id)
        form_hidden = page.evaluate(
            "id => { const f = document.querySelector('[data-done=\"' + id + '\"]');"
            " return f ? f.hidden : null; }",
            done_id,
        )
        check(
            name + " form " + tag + ": good address shows the success panel",
            done is not None and done.is_visible() and form_hidden is True,
        )


def check_page(browser, base, page_name):
    label = page_name.replace(".html", "")
    errors = []
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base + "/" + page_name, wait_until="networkidle")
    page.wait_for_timeout(600)

    check(label + ": loads with no console or page errors", not errors, "; ".join(errors[:3]))

    dashes = page.evaluate(DASH_JS)
    check(label + ": no em or en dash in rendered page", not dashes, "; ".join(dashes))

    check_links(page, label)

    expected = {
        "index.html": ["Organization", "WebSite", "Blog"],
        "article.html": ["BlogPosting", "BreadcrumbList"],
        "landing.html": ["WebPage", "FAQPage"],
    }[page_name]
    check_schema(page, label, expected)

    # fonts actually loaded from our own files
    font_ok = page.evaluate(
        "() => document.fonts.check('1rem Fraunces') "
        "&& document.fonts.check('1rem \"Instrument Sans\"')"
    )
    check(label + ": both self-hosted fonts loaded", font_ok)

    externals = page.evaluate(
        """() => performance.getEntriesByType('resource')
             .map(r => r.name)
             .filter(n => !n.startsWith(location.origin) && !n.startsWith('data:'))"""
    )
    check(label + ": zero external requests", not externals, ", ".join(externals[:3]))

    # responsive sweep
    for w, h in ((390, 844), (768, 1024), (1280, 900)):
        page.set_viewport_size({"width": w, "height": h})
        page.wait_for_timeout(450)
        bad = page.evaluate(OVERFLOW_JS)
        check(label + ": nothing overflows at " + str(w) + "px", not bad, "; ".join(bad))

    page.set_viewport_size({"width": 1280, "height": 900})
    page.wait_for_timeout(300)

    # demo strip dismiss
    strip = page.query_selector("[data-demo-strip]")
    if strip:
        page.click("[data-demo-close]")
        page.wait_for_timeout(200)
        check(label + ": demo strip dismisses", not strip.is_visible())

    check_forms(page, label)

    page.close()


def check_mobile_nav(browser, base):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.goto(base + "/index.html", wait_until="networkidle")
    page.wait_for_timeout(400)

    nav = page.query_selector("[data-nav]")
    check("mobile: drawer starts closed", not nav.is_visible())

    page.click("[data-nav-toggle]")
    page.wait_for_timeout(450)
    check("mobile: drawer opens on tap", nav.is_visible())
    check(
        "mobile: toggle reports expanded state",
        page.get_attribute("[data-nav-toggle]", "aria-expanded") == "true",
    )

    page.keyboard.press("Escape")
    page.wait_for_timeout(450)
    check("mobile: Escape closes the drawer", not nav.is_visible())
    page.close()


def check_article_behaviour(browser, base):
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(base + "/article.html", wait_until="networkidle")
    page.wait_for_timeout(500)

    start = page.evaluate("() => document.querySelector('[data-progress]').style.width")
    page.evaluate("() => window.scrollTo(0, document.body.scrollHeight * 0.55)")
    page.wait_for_timeout(600)
    mid = page.evaluate("() => document.querySelector('[data-progress]').style.width")

    def pct(v):
        return float(v.replace("%", "")) if v and v.endswith("%") else 0.0

    check(
        "article: reading progress advances on scroll",
        pct(mid) > pct(start) + 5,
        (start or "0%") + " to " + (mid or "0%"),
    )

    active = page.query_selector_all(".toc a.is-active")
    check("article: table of contents highlights the current section", len(active) == 1,
          active[0].inner_text() if active else "nothing active")

    bar = page.query_selector("[data-slidebar]")
    check("article: slide-up bar is up past the trigger point",
          "is-up" in (bar.get_attribute("class") or ""))

    page.click("[data-slidebar-close]")
    page.wait_for_timeout(600)
    check("article: slide-up bar dismisses",
          "is-up" not in (page.query_selector("[data-slidebar]").get_attribute("class") or ""))

    page.evaluate("() => window.scrollTo(0, 0)")
    page.wait_for_timeout(400)
    page.close()


def check_faq(browser, base):
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(base + "/landing.html", wait_until="networkidle")
    page.wait_for_timeout(400)

    second = page.query_selector_all(".faq details")[1]
    check("landing: second FAQ item starts closed", second.get_attribute("open") is None)
    second.query_selector("summary").click()
    page.wait_for_timeout(300)
    check("landing: FAQ item opens on click", second.get_attribute("open") is not None)

    # every FAQ answer on the page must also exist in the FAQPage schema
    raw = page.eval_on_selector_all(
        'script[type="application/ld+json"]', "els => els.map(e => e.textContent)"
    )
    questions = set()
    for block in raw:
        data = json.loads(block)
        for node in data.get("@graph", [data]):
            if isinstance(node, dict) and node.get("@type") == "FAQPage":
                for item in node.get("mainEntity", []):
                    questions.add(item["name"].strip())

    visible = set(
        re.sub(r"\s+", " ", s.inner_text()).strip()
        for s in page.query_selector_all(".faq summary")
    )
    check(
        "landing: every visible FAQ question is in the FAQPage schema",
        visible <= questions,
        "not in schema: " + ", ".join(sorted(visible - questions)),
    )
    page.close()


def main():
    # Pass a base URL to run the same checks against a deployed site:
    #   python3 tests/test_site.py https://user.github.io/leadgen-blog-demo
    override = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else None

    httpd = None
    if override:
        base = override
        print("testing the deployed site at " + base + "\n")
    else:
        port = free_port()
        httpd = serve(port)
        base = "http://127.0.0.1:" + str(port)
        print("serving " + ROOT + " on " + base + "\n")

    check_sources()
    check_contrast()

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--no-proxy-server"])
        for page_name in PAGES:
            print("\n--- " + page_name + " ---")
            check_page(browser, base, page_name)
        print("\n--- behaviour ---")
        check_mobile_nav(browser, base)
        check_article_behaviour(browser, base)
        check_faq(browser, base)
        browser.close()

    if httpd:
        httpd.shutdown()

    failed = [r for r in results if not r[1]]
    print("\n" + "=" * 62)
    print("%d checks, %d passed, %d failed" % (len(results), len(results) - len(failed), len(failed)))
    if failed:
        print("\nFailures:")
        for name, _ok, detail in failed:
            print("  - " + name + ((" :: " + detail) if detail else ""))
    print("=" * 62)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
