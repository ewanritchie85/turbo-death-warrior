## Context log

This project maintains `LLM_CONTEXT_LOG.md` at the repo root — a rolling,
high-signal summary of architecture, priorities, and recent changes, meant
to give any coding assistant (Copilot, opencode, etc.) immediate context
without re-discovering the codebase from scratch each session.

After any meaningful code change, append a new entry to
`LLM_CONTEXT_LOG.md` under "Change Log Entries" following the format
already defined in that file's "Update Protocol" section (Date, Scope,
Summary, Why, Impact, Validation, Follow-ups). Keep entries factual and
short — prefer file paths over long prose.

If a change affects the "Current Snapshot", "Architecture", "Safety +
Auth Boundaries", or "Active Priorities" sections, update those sections
directly rather than only relying on the change log to convey it.

## Definition of done

Before considering any change finished, confirm all of the following:

- `make check` and `make test` both pass.
- `README.md` has been updated with any relevant changes.
- `LLM_CONTEXT_LOG.md` has a new entry for this change under "Change Log
  Entries". If you're about to say a task is complete without having
  added one, that's a sign you're not actually done yet.
- If anything you changed makes an existing "Active Priorities" or "Known
  drift / debt" item stale or resolved, update or remove that item rather
  than leaving it to go out of date.