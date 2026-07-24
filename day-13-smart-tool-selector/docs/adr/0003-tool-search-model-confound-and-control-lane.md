# `tool_search` forces a second model, so the naive baseline is re-run on it as a control

The spec pinned `gpt-4.1-mini` across all three strategies and named `ToolSearchTool`'s
model compatibility as an implementation-time verification item. It resolved negatively:
the Responses API rejects `tool_search` on `gpt-4.1-mini`, on `gpt-4.1`, `gpt-4o-mini`,
`gpt-5`, `gpt-5.1`, and `gpt-5.4-nano`. It is served from `gpt-5.2` upward. The native
lane therefore runs on `gpt-5.4-mini` (the cheapest supported tier) while naive and
router stay on `gpt-4.1-mini`.

The spec's fallback was to document this as a confound. Documenting it alone would leave
the native lane's numbers uninterpretable — any difference could be the strategy or the
model. Instead the harness adds a fourth lane, `naive-ts`: the naive baseline re-run on
`gpt-5.4-mini`. It is a control, not a strategy. `native` is read against `naive-ts`;
`router` is read against `naive`.

A second `tool_search` requirement surfaced at the same time: `tool_namespace()` metadata
alone is not sufficient — the API also demands at least one tool marked `defer_loading`.
The native lane sets it on the namespace copies, which is why it does not leak into the
shared `CATALOG` the other lanes bind.

## Consequences

The report carries four lanes instead of three, and any cost comparison involving `native`
is a cross-model comparison with a same-model control beside it rather than a clean
single-model number. Retiring the control lane requires OpenAI to serve `tool_search` on a
`gpt-4.1`-tier model, which is not on offer. The eighth query set and grading are unchanged
by this, so the confound is contained to the model column.
