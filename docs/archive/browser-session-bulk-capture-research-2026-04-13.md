# Browser-Session Bulk Capture Research (2026-04-13)

> ⚠️ **ARCHIVED** — This document preserves an April 2026 research lane about extracting a large puzzle corpus from a browser-gated external source after direct HTTP fetching stopped working reliably.
> Current canonical documentation: [Tool Development Standards](../how-to/backend/tool-development-standards.md), [Puzzle Sources Catalog](../reference/puzzle-sources.md)
> Source-specific identifiers are intentionally normalized in this archive digest.
> Archived: 2026-05-08

**Last Updated**: 2026-05-08

## Scope

This digest replaces a single later-retired initiative research note about one external puzzle source whose pages remained human-viewable but challenged sustained scripted HTTP access.

The original research brief asked how to acquire a large backlog of puzzles while:

- staying on local hardware only
- keeping the process resumable on Windows
- reusing the existing parser, converter, storage, and checkpoint stack
- avoiding cloud CAPTCHA-solving services, proxy networks, and LLM-heavy browser control

## Historical Summary

### 1. The Downstream Toolchain Was Already Complete

The most important finding was architectural, not source-specific: the downstream extraction stack was already usable.

The only failing layer was page acquisition. Once the page payload was available, the existing model parsing, SGF conversion, storage, and checkpoint logic could remain unchanged.

### 2. Full Page Load Was Required

The research found that the useful puzzle payload was embedded directly in page HTML and exposed again as a browser-side JavaScript global after load.

That made two implications clear:

- a real page load was required
- XHR interception alone was insufficient because the important data did not arrive through a separate API call

### 3. Real-Browser Capture Beat LLM Automation

The recommended ranking was:

1. Browser-session capture inside a real user browser via userscript or extension.
2. A short Chrome DevTools Protocol attach probe to an already-manual browser session.
3. Avoid LLM-driven browser agents for deterministic next-page flows.

The reasoning was simple: when the navigation path is fixed and repetitive, LLM control adds latency, cost, and new failure modes without improving coverage.

### 4. Operational Discipline Mattered More Than Cleverness

The research emphasized that long bulk runs should prefer:

- randomized inter-page delays
- occasional longer reading pauses
- bounded session lengths with cooldowns
- manual recovery whenever a challenge page appears
- regular snapshot export from browser-side buffers or a local receiver

The conclusion was that bulk capture was still practical with a real browser session, but only if session discipline remained conservative.

## What Became Canonical Elsewhere

### 1. Browser-Session Fallback Guidance

The reusable operational lesson from this research is now documented generically in [Tool Development Standards](../how-to/backend/tool-development-standards.md): when a source becomes browser-gated, swap only the fetch layer and keep the parse-to-storage pipeline intact.

### 2. Source Identity Redaction

The broader documentation rule that source identities should not be enumerated in user-facing docs already lives in [Puzzle Sources Catalog](../reference/puzzle-sources.md).

## What Stayed Historical Instead of Becoming Canonical

The following items remain historical research detail rather than current documentation contract:

- exact corpus-size estimates from the investigated source
- the source-specific page variable name and page-layout details
- the framework comparison table across userscripts, extensions, CDP, macros, and LLM browser agents
- source-specific output-directory examples and checkpoint paths
- the original port number and local receiver sketch

## Retirement Note

The original initiative directory was removed after this digest was created. This archive file preserves the research lineage without keeping source-branded planning artifacts in `TODO/initiatives/`.
