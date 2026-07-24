# Tools are real (free/no-auth), not mocked stubs; argument correctness still not graded

The initial scaffold assumed no-op mock tools returning canned strings, since the benchmark's question is tool *selection*, not execution. That was rejected: mocked tools make this a synthetic exercise rather than "an actual test." Instead, all 8 tools do real work against free, no-auth resources — real API calls (Open-Meteo, a free FX API, DuckDuckGo) for the three tools that call external services, and real reads/writes against local files for the four that would otherwise need an authenticated account (email outbox, calendar, contacts, reminders) or would spam a real inbox (email). This keeps every call functionally real without pulling OAuth/credential plumbing into a ~1-2 hr day, and without a benchmark run emailing real people.

Argument correctness is still not graded, even though tools are now real — that decision didn't change with this one. All three strategies share the identical downstream argument-extraction path; grading arguments would measure prompt/parsing quality, which doesn't differ between the strategies under comparison and wouldn't move the result.

## Considered options

Live third-party integrations (Gmail API, Google Calendar API, real contacts) were considered and rejected: they'd blow the repo's per-day time budget on infrastructure unrelated to the actual question (tool-selection strategy), and would make the benchmark harder to rerun repeatably.
