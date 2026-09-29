# Fonts used in this build

Both families are licensed under the SIL Open Font License, Version 1.1, which
permits self-hosting and commercial use without a subscription or per-pageview
fee. The full licence text ships with each family at its source below.

| Family | Files here | Designer / foundry | Licence | Source |
| --- | --- | --- | --- | --- |
| Fraunces | `fraunces-latin.woff2`, `fraunces-latin-ext.woff2` | Undercase Type (Phaedra Charles, Flavia Zimbardi) | SIL OFL 1.1 | https://github.com/undercasetype/Fraunces |
| Instrument Sans | `instrumentsans-latin.woff2`, `instrumentsans-latin-ext.woff2` | Instrument | SIL OFL 1.1 | https://github.com/Instrument/instrument-sans |

The `.woff2` files here are the latin and latin-ext subsets of the variable
versions, taken from the Google Fonts distribution. They are served from this
repository rather than from a Google domain, which means:

- no external request on the critical path, so no extra DNS lookup, TLS
  handshake or third-party latency
- no visitor IP address is passed to a third party when the page loads, which
  keeps the font question out of your cookie and privacy policy

If either family is replaced with a licensed commercial face later, the swap is
two `@font-face` blocks and the `--font-display` / `--font-body` variables at
the top of `assets/css/site.css`.
