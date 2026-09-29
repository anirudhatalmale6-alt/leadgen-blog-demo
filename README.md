# Northbound, a conversion-focused blog design

A working demo built for Freelancer project 40739401 (Modern Lead-Generating
Blog Design). Three page types, one design system, no external requests.

**Live:** https://anirudhatalmale6-alt.github.io/leadgen-blog-demo/

| Page | File | What it demonstrates |
| --- | --- | --- |
| Homepage | `index.html` | Above-the-fold capture, credibility strip, featured post, numbered archive, dark offer block, topic rail |
| Article template | `article.html` | Reading progress, sticky offer rail with scrollspy, inline mid-article CTA, end-of-post capture, slide-up bar |
| Landing variant | `landing.html` | Stripped navigation, hero form with segmentation, proof strip, FAQ wired to schema, closing capture |

The brand, copy and numbers are placeholders. The point is the structure and
the conversion mechanics, not the words.

---

## Where the conversions happen

A blog that generates leads is not a blog with a form in the footer. There are
five capture points in this build, each tagged separately so you can tell which
one earned the lead:

| Tag | Where |
| --- | --- |
| `home-hero` | Homepage, first screen, inline with the headline |
| `home-midpage-teardown` | Homepage, dark offer block |
| `article-inline-teardown` | Article, at roughly 40% depth |
| `article-footer-newsletter` | Article, end of post |
| `lp-teardown` / `lp-footer-teardown` | Landing page, hero and closing block |

Plus two non-form prompts: the sticky sidebar offer card and the slide-up bar
that appears once a reader passes 40% of an article and hides again near the
end so it never covers the footer CTA.

Every submission carries `tag`, `source` (the path) and `referrer`, which is
what makes "this article produced eleven leads last month" a question you can
actually answer.

## Wiring it to a real email platform

Forms currently run in demo mode. Everything routes through one function:

```
assets/js/site.js  ->  submitToEsp(payload)
```

That is the only thing that changes when the site goes live. It becomes either
a `fetch()` to your platform's endpoint (ConvertKit, Beehiiv, Brevo, Mailchimp)
or a submit handled by the form plugin (Fluent Forms, WPForms, Ghost members).
Nothing else on any page needs to be touched.

The landing page also sends a `segment` field, which shows the pattern for
writing an answer to a custom field so you can segment the list later.

## Speed and SEO

- Two self-hosted variable fonts, woff2, subset to latin and latin-ext. **Zero
  external requests**, so no third-party connection is on the critical path and
  there is no cookie-consent question about Google Fonts.
- No framework, no jQuery, no icon font. One stylesheet, one deferred script.
- All artwork is CSS or inline SVG, so there are no image files in this demo.
  Real photography drops into the same slots.
- Schema: `Organization`, `WebSite` and `Blog` on the homepage; `BlogPosting`
  and `BreadcrumbList` on the article; `WebPage` and `FAQPage` on the landing
  page. The FAQ schema is checked against the visible questions by the test
  suite, so the two cannot drift apart.
- Open Graph and Twitter card tags, canonical URLs, sensible heading order.

## Accessibility

Skip link, visible focus rings, `aria-expanded` on the menu, Escape closes the
drawer, live-region form errors, and `prefers-reduced-motion` honoured
throughout. All body, muted, link and button colour pairs clear WCAG AA, which
the test suite asserts rather than assumes.

---

## Tests

```
python3 tests/test_site.py
```

80 checks across the three pages. It serves the folder, drives Chromium and
verifies, among other things:

- every page loads with no console or page errors
- nothing overflows the viewport at 390, 768 and 1280, measured per element
  rect rather than by `scrollWidth`, which `overflow-x: hidden` would mask
- every capture form rejects empty and malformed input, and reaches the success
  panel on a valid address
- mobile drawer, reading progress, scrollspy, slide-up bar and demo strip all
  actually do something
- every JSON-LD block is valid JSON and carries the expected types
- every internal link points at a file that exists
- both self-hosted fonts loaded and zero external requests were made
- no em dash or en dash reaches the page, including inside placeholders,
  aria-labels, titles and alt text

## Moving this onto a CMS

The build is deliberately block-shaped so it ports cleanly:

- **WordPress**: a block theme with `theme.json` carrying the tokens below.
  Each section here becomes a reusable block pattern, so adding a landing page
  is inserting patterns, not writing code.
- **Ghost**: a handlebars theme. The capture blocks become members signup
  forms and the sticky rail is a partial.

Design tokens live at the top of `assets/css/site.css` under `:root`. Changing
the brand is changing that block:

```
--paper   #f7f3ec   page background
--ink     #14110f   headings and dark sections
--signal  #d43a1f   the single accent, used only for actions
```

Type is Fraunces for display and Instrument Sans for everything else. Both are
open-licence (SIL Open Font License), so they can be self-hosted commercially
without a subscription.

## Running locally

```
python3 -m http.server 8000
```

Then open http://127.0.0.1:8000. No build step, no dependencies.
