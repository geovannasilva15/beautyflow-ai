# BeautyFlow Platform Foundation

## API access guard

Development (default): with no `API_ACCESS_TOKEN`, local API requests continue to work.

For a private deployment, configure:

```bash
APP_ENV=production
API_ACCESS_TOKEN=your-long-random-token
```

The Streamlit frontend must use the same `API_ACCESS_TOKEN` in its server-side
environment or Streamlit secrets.

**Security boundary:** this is a service-level API key, not personal account
authentication. Do not expose the key in browsers, mobile clients or JavaScript.
Do not publish the prototype login with hardcoded credentials to the Internet.
Per-user permissions, session authentication, migrations, audit logging,
TLS, rate limiting and backups are mandatory before handling real customer data.

## CRM metrics

`GET /api/crm/summary?inactive_days=60`

Returns totals derived from real appointments. Only completed appointments count
as visits and revenue. Inactive flags apply to previously served clients with
no completed visit in the specified interval. They are *not* predictive churn.

## PostgreSQL

The Python dependency `psycopg` is available for a later PostgreSQL deployment.
The SQLModel database URL accepts `postgresql+psycopg://...`.
Automatic `create_all` is suitable for local demos, not schema migration in
production. Add Alembic and migration checks before rollout.
