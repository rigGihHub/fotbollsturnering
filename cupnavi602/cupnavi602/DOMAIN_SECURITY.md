# CupNavi domain security

Canonical public URL: `https://cup-navi.com`

## HTTPS / DNS requirements

`cup-navi.com` must have a valid TLS certificate.

`www.cup-navi.com` must either:
- have valid TLS coverage for `www.cup-navi.com` and permanently redirect (301/308) to `https://cup-navi.com`, or
- not be published as an entry point.

An application redirect cannot repair a broken certificate on `www`, because TLS validation
happens before Streamlit receives the request.

## Corporate security filters

If HTTPS is valid but a work computer still blocks the site, the likely cause is enterprise
URL reputation/category filtering. Then:
- record the exact warning/provider name;
- verify Google Safe Browsing and Microsoft SmartScreen reputation;
- request reclassification/allow-listing from the company's web-security provider;
- keep all public links on the canonical HTTPS apex domain;
- avoid mixed HTTP resources.

CupNavi source already uses `https://cup-navi.com` as its canonical public base URL.
