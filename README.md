# User Registration API

A user registration service built for the Dailymotion technical test. Users create an account and verify ownership of their email address via a time-limited 4-digit code before the account becomes active.

---

## Table of contents

1. [Application overview](#application-overview)
2. [Technical stack](#technical-stack)
3. [Codebase structure](#codebase-structure)
4. [Architecture diagrams](#architecture-diagrams)
5. [Running the application](#running-the-application)
6. [Running the tests](#running-the-tests)
7. [API endpoints](#api-endpoints)
8. [Applied trade-offs](#applied-trade-offs)
9. [Potential improvements](#potential-improvements)

---

## Application overview

The registration flow has two steps:

```
1. POST /api/v1/users
   ├── Creates an inactive user account
   ├── Generates a cryptographically-secure 4-digit code (TTL: 60 s)
   ├── Persists the code in the database
   └── Delivers the code by email (MailPit in local dev)

2. POST /api/v1/users/activate  [Basic Auth]
   ├── Authenticates the user via Basic Auth (email + password)
   ├── Verifies the 4-digit code is still active (not used, not expired)
   ├── Marks the code as used
   └── Activates the account
```

---

## Technical stack

| Concern | Choice |
|---|---|
| Language | Python 3.14 |
| Framework | FastAPI |
| Database | PostgreSQL 18 (raw SQL via asyncpg) |
| Password hashing | bcrypt  |
| Email delivery | aiosmtplib → MailPit (local dev) |
| Dependency management | Poetry |
| Testing | pytest + pytest-asyncio + httpx |
| Containerisation | Docker + Docker Compose |

---

## Codebase structure

Business logic is isolated in services and depends only on abstract interfaces (ports), not on concrete infrastructure.

```
app/
├── api/
│   ├── exception_handlers.py   # Maps domain exceptions → HTTP responses
│   └── v1/
│       └── users.py            # Registration and activation endpoints
├── core/
│   ├── exceptions.py           # Domain exception types
│   └── security.py             # bcrypt password hashing
├── db/
│   └── pool.py                 # asyncpg connection pool (lifespan-managed)
├── models/
│   ├── user.py                 # Internal DB row model (includes password hash)
│   └── verification_code.py   # Internal DB row model for codes
├── ports/
│   ├── email_service.py        # EmailServicePort (Protocol)
│   ├── user_repository.py      # UserRepositoryPort (Protocol)
│   └── verification_code_repository.py
├── repositories/
│   ├── user_repository.py      # Raw SQL adapter for users table
│   └── verification_code_repository.py
├── schemas/
│   └── users.py                # Pydantic request/response models (API boundary)
├── services/
│   ├── email_service.py        # MailPit SMTP adapter
│   └── user_service.py         # Registration & activation business logic
├── dependencies.py             # FastAPI Depends wiring
└── main.py                     # App factory, lifespan, router registration

sql/
└── init.sql                    # Schema (users + verification_codes tables)

tests/
├── api/
│   └── test_users.py           # Integration tests (HTTP layer, real FastAPI app)
└── services/
    ├── test_email_service.py   # Unit tests (MailPit adapter)
    └── test_user_service.py    # Unit tests (business logic)
```

**Layer responsibilities:**

- **Ports** — abstract interfaces. Services depend on these, not on concrete classes.
- **Repositories** — infrastructure adapters that execute raw SQL. They satisfy the port protocols structurally, without importing them.
- **Services** — pure business logic. No framework imports, no SQL, no HTTP.
- **Schemas** — Pydantic models used exclusively at the API boundary. Internal models (`app/models/`) are never serialised directly to responses.

---

## Architecture diagrams

C4 model diagrams (System Context, Container, Component, and Deployment views) are located in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Running the application

The only prerequisite is Docker and Docker Compose.

```bash
# Clone the repository and start all services
docker compose up --build
```

This starts three containers:

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| Interactive API docs | http://localhost:8000/docs |
| MailPit web UI (inspect emails) | http://localhost:8025 |
| PostgreSQL | localhost:5432 |

The database schema is applied automatically on first boot via `sql/init.sql`.

### Local development (without Docker)

Requires Python 3.14, Poetry, and a running PostgreSQL 18 instance.

```bash
# Install dependencies
poetry install

# Apply the schema
psql -d your_db < sql/init.sql

# Start the API
DATABASE_URL=postgresql://user:password@localhost:5432/your_db \
SMTP_HOST=localhost SMTP_PORT=1025 EMAIL_FROM=no-reply@example.com \
poetry run uvicorn app.main:app --reload
```

---

## Running the tests

Tests require no running infrastructure — the DB pool and SMTP client are patched in the test suite.

```bash
# Inside Docker
docker compose --profile test run --rm test

# Locally
poetry run pytest
```

The test suite has three layers:

| Layer | Location | What it covers |
|---|---|---|
| Unit — service | `tests/services/test_user_service.py` | Business logic, edge cases, domain exceptions |
| Unit — email | `tests/services/test_email_service.py` | SMTP adapter, error propagation |
| Integration — API | `tests/api/test_users.py` | HTTP status codes, request validation, auth, response shape |

---

## API endpoints

### `POST /api/v1/users` — Register a user

**Request**
```json
{ "email": "user@example.com", "password": "secret" }
```

**Response `201 Created`**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "is_active": false,
  "created_at": "2025-01-01T00:00:00Z"
}
```

| Status | Condition |
|---|---|
| `201` | User created, verification email sent |
| `409` | Email already registered |
| `422` | Invalid or missing fields |

---

### `POST /api/v1/users/activate` — Activate an account

Authentication: **HTTP Basic Auth** (email as username, password as password)

**Request**
```json
{ "code": "4242" }
```

**Response `200 OK`**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2025-01-01T00:00:00Z"
}
```

| Status | Condition |
|---|---|
| `200` | Account activated |
| `400` | Code is wrong or has expired (after 60 s) |
| `401` | Missing, or invalid Basic Auth credentials |
| `422` | Code is not exactly 4 digits |

---

## Applied trade-offs

**Expiry enforced in SQL.** `get_active_by_user` filters `expires_at > NOW()` at the database level. This avoids clock skew between the application server and the database, and removes the need for a background job to reap expired codes.

**No background workers.** Verification codes expire passively (SQL filter). This keeps the infrastructure footprint minimal for the scope of this test.

---

## Potential improvements

### Rate limiting

Production mitigations:

- Limit activation attempts per user (e.g. lock the account after 5 consecutive failures).
- Limit registration attempts per IP to slow down account creation abuse.

### Redis for code storage and expiry

Storing verification codes in PostgreSQL works but comes with trade-offs:

- Expiry requires a `WHERE expires_at > NOW()` filter on every lookup - there is no automatic row removal.
- Redis TTL handles expiry natively: the key ceases to exist after 60 seconds, so there is nothing to query or clean up.

### Idempotency on registration

The current `POST /api/v1/users` is not idempotent. A client that retries after a network timeout will receive `409` even though the original request succeeded. Solutions:

- Accept a client-generated `Idempotency-Key` header and store request outcomes (keyed by idempotency key) in Redis with a short TTL.
- Return the existing user instead of `409` when the email is already registered but not yet active, provided the caller can prove ownership (e.g. re-send the code).

### Resend endpoint

There is currently no way to request a new code if the first one expires. A `POST /api/v1/users/resend` endpoint would improve usability without weakening security, as long as resend requests are rate-limited.

### Observability

Basic plain-text logging is in place, but production use would require structured JSON logging to make fields queryable in log aggregators. Per-request correlation IDs are also missing, making it hard to trace a single request under concurrent load. Finally, no metrics are exposed.

### Async email delivery

Email delivery is currently synchronous in the request path. If the SMTP server is slow or temporarily unavailable, the registration response blocks. Moving the send to a background task decouples the HTTP response time from email latency and allows retries.

### HTTPS and secure headers

The API currently serves plain HTTP. In production it should sit behind a TLS-terminating reverse proxy and return security headers.

### Database migrations

The schema is applied from a single `init.sql` file on first boot. This is fine for initial setup but does not support schema evolution. A migration tool such as Alembic would allow incremental, reversible schema changes in production.
