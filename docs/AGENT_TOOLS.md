# Agent tools V1

The endpoint `POST /api/agent/tools` provides deterministic tools for a future
LLM-driven orchestrator: `list_services`, `find_client`, `availability`,
`book`, and `cancel`.

Booking and cancellation require an explicit `confirm=true` value. The
first call returns `confirmation_required` without writing appointments.

This is an **API tool layer**, not yet an LLM agent, WhatsApp integration or
security boundary for end-user authorization. The caller is responsible for
obtaining human confirmation; `confirm=true` is not cryptographic proof.

Before production usage, add individual identity, authorization checks,
short-lived confirmation tokens tied to exact actions, persistent audit logs,
idempotency keys, and concurrency-safe booking transactions.
