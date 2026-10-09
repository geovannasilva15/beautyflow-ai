# Agent tools V1

The endpoint `POST /api/agent/tools` provides deterministic tools for a future
LLM-driven orchestrator: `list_services`, `find_client`, `availability`,
`book`, and `cancel`.

Booking and cancellation require a matching single-use `confirmation_token` issued
by a prior preview call. The token expires in ten minutes and is bound to the
exact request parameters. The client must send both `confirm=true` and the token.
The first call returns `confirmation_required` without altering appointments.

This is an **API tool layer**, not yet an LLM agent, WhatsApp integration or
security boundary for end-user authorization. The caller is still responsible for obtaining human confirmation. A token
proves an earlier preview was requested, **not** that a real person approved.

Before production usage, add individual identity, authorization checks,
short-lived confirmation tokens tied to exact actions, persistent audit logs,
idempotency keys, and concurrency-safe booking transactions.
