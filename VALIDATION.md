# Verification — 2026-10-10

- Latest icon update: 13 standard-library unittest cases passed in the local
  virtual environment on Windows / Python 3.13. The added case verifies the
  favicon link on both pages and the served SVG response.
- Actual local dataset parsing, multi-token search, no-match/filter handling,
  stable product IDs, authentication, JSON validation, body size, security
  headers and loopback-only demo bypass covered.
- Offline engine tests forbid HTTP requests; model output is not fabricated.
- Browser check: source-search tab, `phone battery` query and returned local
  records observed. Layout inspected in the in-app browser.
- Repeated scraped product snapshots deduplicated by category/name; 127 catalog
  entries loaded. Names with + suffixes retain distinct stable hashed IDs.
  The numeric count is data-revision-specific.
- Earlier fresh virtual environment check installed requirements.txt; the then-current 12 tests passed
  there as well. No preinstalled embedding or vector-database package required.

Not verified: real OpenRouter request, answer factuality, Render deployment,
production hardening, cross-browser accessibility certification. Dataset
content is unverified example material and must not be used as safety guidance.

The lexical retrieval implementation is intentionally lightweight; semantic
embedding retrieval was removed because its dependencies were absent from the
published install and no retrieval-quality evaluation supported its claims.
