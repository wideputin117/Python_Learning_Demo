# 24 · Production basics

> This chapter is an **introduction**, not a milestone. The core track (M0–M8) runs locally. Here you learn
> what changes when TriageDesk serves real users, and you can do a few optional hardening tasks. The full
> production work (task queue, Postgres, tracing, CI/CD) is in `docs/ROADMAP.md` **R5, not implemented**.

## Concept

### What changes in production
| Locally | In production |
|---|---|
| `fastapi dev` with auto-reload | `fastapi run` (or uvicorn/gunicorn) with multiple worker processes |
| SQLite file, `chroma_data/` folder | Postgres (+ pgvector) or volumes that survive restarts |
| `.env` file | secrets injected by the platform (env vars, secret manager) |
| one user: you | many users, some malicious, some scripts |
| "the API call failed, I'll rerun it" | timeouts, retries, alerts, graceful fallbacks |
| cost = pocket change | cost = a line item someone will ask about |

AI features add three production concerns that normal CRUD doesn't have:
1. **Latency:** LLM calls take seconds, not milliseconds. Never block cheap endpoints on them.
2. **Cost:** every call costs money, and an abusive user or a retry loop can burn a budget.
3. **Non-determinism:** you need logs good enough to explain *why* a draft said what it said.

### The 12-factor basics (they apply to any backend)
- **Config from the environment.** You already do this with `Settings`. Different envs = different env vars, same code.
- **Stateless processes.** Anything stored in a Python dict disappears on restart and isn't shared between
  workers. (Our in-memory rate limiter below has this limitation.)
- **Logs as event streams.** Write to stdout. The platform collects them.
- **Dev/prod parity.** Use Docker so "works on my machine" means "works in the container".

### Timeouts and retries: a layered budget
```
client (browser)  ── 30s ──►  FastAPI route  ── 25s ──►  LLMClient  ── 20s × (1 + 2 retries) ──►  Claude API
```
Each layer's timeout should be *shorter* than the layer above it, or the user gives up while your server
keeps paying for work nobody will see. The SDK retries 408/409/429/5xx and connection errors (default
2 retries) with exponential backoff. Remember that the worst-case wall time is `timeout × (retries + 1)`.

### Rate limiting
Protects you from abuse and runaway clients. The expensive endpoint is `POST /tickets/{id}/draft`
(a Sonnet call). Limit it per user (e.g. 30/minute), and also limit ticket creation per customer, since every
ticket triggers a triage call.

### Cost guardrails
Even with rate limits, put a hard stop in the one place every call passes through, `LLMClient`:
- **cap input size** (truncate ticket bodies, cap retrieved chunks),
- **cap output** with `max_tokens`,
- **track spend** from `usage` on every call, and refuse new calls past a daily budget, falling back
  the way you already do for `LLMError`.

### Observability for LLM calls
For every call, log a structured line: `feature` (triage/draft/judge), `model`, `input_tokens`,
`output_tokens`, `latency_ms`, `stop_reason`, `request_id`, `ticket_id`, `estimated_cost_usd`. With these you
can answer "why did costs double on Tuesday?" and "which ticket produced this weird draft?".
Be careful with **PII**: ticket bodies contain names, emails and order numbers. Log ids, not content, unless
you have a retention policy.

## In Node you'd…
| Node | Python |
|---|---|
| `node:20-slim` base image, `npm ci --omit=dev` | `python:3.12-slim`, `uv sync --locked --no-dev` |
| `pm2` / cluster mode | `fastapi run --workers 4` (uvicorn worker processes) |
| `express-rate-limit` | `slowapi`, or a small dependency (below), or rate limiting at the gateway |
| `pino` JSON logs | `logging` with a JSON formatter (or `structlog`) |
| `helmet`, `cors` | `CORSMiddleware`; security headers usually set at the proxy |

## Examples

### 1. Dockerfile with uv
```dockerfile
# Dockerfile
FROM python:3.12-slim

# Copy the uv binary from its official image (pin the version you use locally).
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

# 1) Dependencies first: this layer is cached until pyproject.toml/uv.lock change
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

# 2) Then the code
COPY . .

EXPOSE 8000
CMD ["/app/.venv/bin/fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```
```bash
docker build -t triagedesk .
docker run --env-file .env -p 8000:8000 \
  -v "$PWD/chroma_data:/app/chroma_data" -v "$PWD/triagedesk.db:/app/triagedesk.db" \
  triagedesk
```
Add a `.dockerignore` (`.venv`, `.env`, `chroma_data`, `*.db`, `.git`, `reports`) so secrets and local state
never end up in the image. The Chroma embedding model downloads on first use, so pre-download it in the
image or mount a cache volume, otherwise the first request after every deploy is slow.

### 2. Environment-specific settings and fail-fast validation
```python
from pydantic import model_validator

class Settings(BaseSettings):
    ...
    environment: Literal["development", "test", "production"] = "development"
    llm_daily_budget_usd: float = 5.0

    @model_validator(mode="after")
    def check_production(self) -> "Settings":
        if self.environment == "production":
            if self.jwt_secret == "change-me":
                raise ValueError("JWT_SECRET must be set in production")
            if not self.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY must be set in production")
        return self
```
The app refuses to start with a dangerous config. That's much better than discovering it from a security report.

### 3. Timeouts at every layer
```python
# LLMClient: SDK timeout + retries
AsyncAnthropic(timeout=20.0, max_retries=2)

# route: an overall deadline for the whole draft operation
try:
    outcome = await asyncio.wait_for(draft_reply(...), timeout=60)
except TimeoutError:
    raise HTTPException(status_code=504, detail="Drafting took too long, try again")
```

### 4. A tiny per-user rate limiter (single process only)
```python
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException

class RateLimiter:
    def __init__(self, max_calls: int, per_seconds: float) -> None:
        self.max_calls, self.per = max_calls, per_seconds
        self.calls: dict[int, deque[float]] = defaultdict(deque)

    def __call__(self, user: User = Depends(get_current_user)) -> None:
        now, window = time.monotonic(), self.calls[user.id]
        while window and now - window[0] > self.per:
            window.popleft()                       # forget calls outside the window
        if len(window) >= self.max_calls:
            raise HTTPException(status_code=429, detail="Too many requests")
        window.append(now)

draft_limiter = RateLimiter(max_calls=30, per_seconds=60)

@router.post("/tickets/{ticket_id}/draft", dependencies=[Depends(draft_limiter)])
async def create_draft(...): ...
```
An instance with `__call__` works as a dependency (chapter 16). Limitation: each worker process has its own
dict, so with 4 workers the real limit is 4×. A production limiter keeps counts in Redis (ROADMAP R5).

### 5. A daily budget guard in `LLMClient`
```python
class BudgetExceeded(LLMError):
    pass

class LLMClient:
    def __init__(self, ...):
        ...
        self._spent_today = 0.0
        self._day = date.today()

    def _check_budget(self) -> None:
        if date.today() != self._day:
            self._day, self._spent_today = date.today(), 0.0
        if self._spent_today >= self.settings.llm_daily_budget_usd:
            raise BudgetExceeded("daily LLM budget reached")

    def _record(self, usage: LLMUsage) -> None:
        self._spent_today += cost_usd(usage.model, usage.input_tokens, usage.output_tokens)
```
Because `BudgetExceeded` *is an* `LLMError`, triage falls back and drafting returns 502 with no extra code.
That's the payoff of the wrapper and the exception hierarchy (chapter 05).

### 6. Structured JSON logs
```python
import json
import logging

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"level": record.levelname, "logger": record.name, "msg": record.getMessage()}
        payload.update(getattr(record, "fields", {}))
        return json.dumps(payload)

logger.info("llm_call", extra={"fields": {"feature": "triage", "model": usage.model,
                                          "input_tokens": usage.input_tokens, "ticket_id": ticket_id}})
```

### 7. Health vs readiness
- `/health` (liveness): "the process is up". It already exists from M0.
- `/ready` (readiness): "I can serve traffic". It checks the DB connection and that the Chroma collection opens.
  Don't call the LLM here: health checks run every few seconds and would cost money.

## Gotchas
- **`fastapi dev` in production** enables reload and debug behaviour. Use `fastapi run`.
- **SQLite + multiple workers** works for reads, but concurrent writes lock. Fine for learning, not for real traffic (Postgres: ROADMAP R3/R5).
- **Embedded Chroma + multiple workers:** each process opens the same folder. Fine for reads. For heavy
  concurrent writes, use a Chroma server or pgvector.
- **`BackgroundTasks` die with the process.** If the server restarts mid-triage, that ticket stays `pending`.
  Add a startup job or admin endpoint to re-triage stale `pending` tickets. A real queue (arq/Celery ≈ BullMQ) fixes this properly (ROADMAP R5).
- **Secrets in images:** never `COPY .env`. Check with `docker history`.
- **Logging prompts:** convenient for debugging, but it's PII. Log ids and metadata by default, and full prompts only behind a debug flag with short retention.
- **Retries multiply cost and latency.** Three layers that each retry 3 times can mean 27 calls.

## Exercises
1. Build and run the Docker image. Hit `/health` and `/docs` from your host.
2. Set `ENVIRONMENT=production` with the default `JWT_SECRET`. Does the app refuse to start?
3. Write a test for `RateLimiter`: 3 allowed calls, the 4th gets a 429. (Hint: override `get_current_user`.)
4. Estimate monthly LLM cost for 300 tickets/day, all triaged (Haiku, ~700 in / ~200 out tokens) and 40% drafted
   (Sonnet, ~3,000 in / ~500 out). Use the prices from chapter 19.

<details><summary>Answers</summary>

2. It should fail at startup with your `ValueError`, raised when `Settings()` is created.
4. Triage per ticket: `700×0.10/1e6 + 200×0.50/1e6 = $0.00017`, × 9,000/month ≈ **$1.53**.
   Draft per ticket: `3000×2/1e6 + 500×10/1e6 = $0.011`, × 3,600/month ≈ **$39.60**. Total ≈ **$41/month**.
   Drafting dominates, so that's where caching, fewer chunks or cheaper settings would pay off.
</details>

## Apply to TriageDesk: optional hardening tasks
None of these are required for M0–M8. Do them in any order once M8 is done, and record what you did in `CLAUDE.md`:
- [ ] `Dockerfile` + `.dockerignore`. The image builds, runs and serves `/docs`.
- [ ] production `Settings` validation (example 2) with a test.
- [ ] `/ready` endpoint checking DB + vector store.
- [ ] `RateLimiter` on `POST /tickets` (per customer) and `POST /tickets/{id}/draft` (per agent), with tests.
- [ ] `BudgetExceeded` in `LLMClient`, plus a test where a fake usage pushes spend over the limit.
- [ ] structured JSON logs for every LLM call, with `feature`, tokens, latency, cost and `ticket_id` (no ticket text).
- [ ] an admin endpoint `POST /admin/retriage-stale` that re-queues tickets stuck in `pending` for > 10 minutes.
- [ ] `asyncio.wait_for` deadline on the draft route → 504.

**What's next:** open `docs/ROADMAP.md` and pick a direction: LangChain (R1) to compare with your hand-built
RAG, agents with tools (R2), better retrieval (R3), fine-tuning on your corrected triage labels (R4), or full
production hardening (R5). **None of these are implemented yet.** Move an item into the `CLAUDE.md` milestone
tracker before building it.
