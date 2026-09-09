# v601 – Kit search accuracy + speed

- Fast first-pass multi-source web search instead of three narrow sequential searches.
- A second web roundtrip is only used for weak or incomplete evidence.
- Home and away kits now require kit-specific source URLs before they are marked verified.
- Evidence text is shown separately for home and away.
- High confidence is automatically capped when source support is too thin.
- Repeated identical searches use a 12-hour in-process cache.
- Whole-tournament scanning runs up to four network-bound searches in parallel.
- Search context still includes tournament location, country, age class and optional organiser hint.
- Nothing is persisted until the organiser explicitly approves.
