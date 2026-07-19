<!-- Status: Completed 2026-07-19 -->
# Spec: Day-08 Section-Based Topic Filter

## Problem
The current topic filter in `get-docs-content` (`src/index.ts:138-147`) does:
```ts
lines.filter(line => line.toLowerCase().includes(topicLower))
```
This returns orphaned lines with no surrounding context, broken code blocks, and no headers. Output is unusable.

## Goal
Replace the line filter with a section-aware filter: find Markdown sections whose heading or body contains the topic keyword, return those sections intact.

## Logic
```
Split content on /^#{1,3} /m  → array of sections
For each section: if heading OR any line contains topicLower → keep whole section
Join kept sections with "\n\n---\n\n"
If no sections match → fall back to full content (don't return empty)
```

## File changes
- `src/index.ts` — replace the filter block (lines ~138-147) with the section split logic above

## Success criterion
`get-docs-content` with `topic: "installation"` on a typical README returns the Installation section with its full text and code blocks intact, not a list of lines containing the word "installation".

## Out of scope
- Fuzzy / semantic matching
- Nested section hierarchy (treat all `#`, `##`, `###` as section boundaries)
