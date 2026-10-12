# CLAUDE.md: TriageDesk (Python learning project)

This file is the **source of truth** for what the project is and what exists right now. Keep the
milestone tracker accurate. If a feature isn't marked ✅ below, it does not exist in the code yet.

## Who this is for
The developer has ~2 years of Node.js backend experience and is **learning Python** with this repo.
- Explain Python concepts by mapping them to Node/Express/TypeScript where it helps.
- Hands-on first: for a new milestone, let the developer try it themselves, then review or pair.
  Don't silently generate whole milestones.
- The learning docs live in `docs/` (start at `docs/00-index.md`). Code should match what the docs
  teach. If you change a pattern in code, update the related chapter.

## The project
**TriageDesk** is a REST API for support-ticket triage with AI features:
1. Customers submit support tickets.
2. AI **classifies** each ticket (category, priority, sentiment) using Claude structured output.
3. AI **drafts a reply** using **RAG** over a knowledge base (FAQ/help-center markdown), with
   citations to the KB chunks it used.
4. Support agents review, edit and approve the draft. Similar past tickets can be searched semantically.

## Stack
| Concern | Choice | Node equivalent |
|---|---|---|
| Package/env manager | uv (`pyproject.toml`, `uv.lock`, `.venv/`) | npm + package.json + node_modules |
| Web framework | FastAPI | Express / Fastify |
| Validation & settings | Pydantic v2, pydantic-settings | Zod, dotenv |
| ORM & migrations | SQLAlchemy 2.0 (async) + Alembic, SQLite (aiosqlite) | Prisma / TypeORM |
| Auth | PyJWT + pwdlib[argon2] | jsonwebtoken + bcrypt |
| LLM | `anthropic` SDK: `claude-haiku-5-5` (classification), `claude-sonnet-5-5` (drafting) | @anthropic-ai/sdk |
| Vector DB / embeddings | ChromaDB (embedded, persisted to `chroma_data/`), default local embedding model | — |
| Tests / lint / format | pytest (+ FastAPI TestClient), ruff | jest + supertest, eslint + prettier |

Dependencies are added **per milestone** (`uv add <pkg>`), not up front. Check `pyproject.toml`
for what's actually installed. Before writing or changing AI code, load the `claude-api` skill so
model IDs and SDK usage are current.

## Commands
```bash
uv sync                              # install deps (like npm install)
uv run fastapi dev app/main.py       # dev server with reload → http://localhost:8000/docs
uv run pytest                        # tests
uv run ruff check . --fix            # lint (+ autofix)
uv run ruff format .                 # format
uv add <pkg> / uv add --dev <pkg>    # add a dependency
uv run python exercises/solutions/ch02_collections.py   # run an exercise solution
```
`uv` is installed at `~/.local/bin/uv`. If `uv` isn't found, run `source ~/.local/bin/env`.

## Layout (planned; ✅ = exists)
```
app/
  main.py                 ✅ app factory create_app(), mounts routers
  core/config.py          ✅ Settings (pydantic-settings), get_settings() cached
  core/                   security.py (M4), errors.py (M3), logging.py (M3)
  api/routes/health.py    ✅ GET /health
  api/routes/             tickets.py (M1), auth.py (M4), kb.py (M5)
  schemas/                Pydantic request/response models (M1)
  models/                 SQLAlchemy models (M2)
  db/                     engine/session (M2)
  services/               business logic; routes stay thin (M3)
  ai/                     llm.py, triage.py, vector_store.py, rag.py, prompts/ (M5–M8)
alembic/                  migrations (M2)
data/                     sample_kb/*.md, sample_tickets.json (M5/M8)
scripts/                  seed_kb.py, eval_triage.py (M5/M8)
tests/                    ✅ test_health.py
docs/                     ✅ learning chapters 00–24 + ROADMAP.md
exercises/                ✅ Part 1 exercise starters + solutions/
```

## Conventions
- Python 3.12. Type hints on every function signature. Use modern syntax (`list[str]`, `X | None`).
- Routes are thin: they parse input and call a service, and services hold the logic (from M3).
- Pydantic schemas (`app/schemas`) are separate from SQLAlchemy models (`app/models`). Never return
  ORM objects directly without a response model.
- DB access is async (`AsyncSession`), injected via `Depends(get_session)`.
- Config only via `get_settings()`. Never read `os.environ` scattered around the code.
- Prompts live as module-level constants or files under `app/ai/prompts/`, not inline in services.
- AI calls are wrapped in `app/ai/llm.py` so tests can mock them. **Tests never call the real API.**
- Every new endpoint gets at least one test.
- ruff config is in `pyproject.toml` (rules E, F, I, UP, B; line length 100).

## Milestone tracker
| M | Feature | Chapters | Status |
|---|---|---|---|
| M0 | Scaffold: uv project, FastAPI app, `/health`, settings, ruff, first test | 00–04, 13 | ✅ done |
| M1 | Tickets CRUD (in-memory store) with Pydantic schemas | 06, 13, 14 | ⬜ todo |
| M2 | Persist to SQLite with SQLAlchemy + Alembic | 15 | ⬜ todo |
| M3 | Routes/services layering, DI, error handling, logging, more tests | 05, 12, 16 | ⬜ todo |
| M4 | Users, JWT auth, roles (customer / agent / admin) | 17 | ⬜ todo |
| M5 | Knowledge base upload → chunk → embed → Chroma (background task) | 18, 21 | ⬜ todo |
| M6 | AI triage on ticket create (category / priority / sentiment) | 19, 20 | ⬜ todo |
| M7 | RAG draft reply with KB citations; agent approve/edit flow | 22 | ⬜ todo |
| M8 | Similar-ticket search + `scripts/eval_triage.py` eval report | 21, 23 | ⬜ todo |

When a milestone is finished, flip its status, update the ✅ marks in **Layout**, and note any
deviation from the plan here.

## NOT implemented: future direction (see `docs/ROADMAP.md`)
These are **plans only**. None of them exist in the code. Don't import, reference or assume them
until they're moved into the milestone tracker above:
- LangChain / LangGraph (chains, agents, tool-calling workflows)
- Fine-tuning (e.g. a small ticket classifier trained on triaged tickets)
- Hybrid search (BM25 + vectors), reranking, pgvector / Postgres migration
- Real task queue (arq / Celery), streaming chat UI, Docker deploy, observability/tracing
