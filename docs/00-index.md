# Python for Node developers: learning path

You'll learn Python by reading one chapter at a time and then applying it to **TriageDesk**, a real
backend with AI features (ticket classification + RAG). Project overview and current status: [`CLAUDE.md`](../CLAUDE.md).
Future plans (LangChain, agents, fine-tuning): [`ROADMAP.md`](ROADMAP.md). Those are **not implemented yet**.

## How to use these docs
1. Read the chapter. Type the examples into the REPL (`uv run python`) instead of copy-pasting.
2. Do the **Exercises**. Starter files are in `exercises/` (Part 1). Check yourself against the
   `<details>` solutions or `exercises/solutions/`.
3. When a chapter ends with **Apply to TriageDesk**, build that milestone yourself first. Then ask
   Claude to review it or pair on it, and flip the milestone to ✅ in `CLAUDE.md`.

Every chapter has the same shape:
**Concept → In Node you'd… → Examples → Gotchas → Exercises → Apply to TriageDesk**

## Chapters

### Part 1: Python foundations
| # | Chapter | Milestone |
|---|---|---|
| 00 | [Setup: uv, venv, editor, Node→Python cheat sheet](part1-python/00-setup.md) | M0 |
| 01 | [Syntax & built-in types](part1-python/01-syntax-and-types.md) | — |
| 02 | [Collections & comprehensions](part1-python/02-collections.md) | — |
| 03 | [Functions, args, closures, scope](part1-python/03-functions.md) | — |
| 04 | [Modules & packages](part1-python/04-modules-and-packages.md) | M0 |
| 05 | [Errors & exceptions](part1-python/05-errors.md) | M3 |
| 06 | [Classes, dataclasses, enums](part1-python/06-oop.md) | M1 |
| 07 | [Iterators, generators, context managers](part1-python/07-iterators-generators-context-managers.md) | M2 |
| 08 | [Decorators](part1-python/08-decorators.md) | — |
| 09 | [Type hints](part1-python/09-type-hints.md) | all |
| 10 | [Standard library essentials](part1-python/10-standard-library.md) | M3 |
| 11 | [Async Python vs the Node event loop](part1-python/11-async.md) | M2 |
| 12 | [Testing with pytest](part1-python/12-testing.md) | M3 |

### Part 2: Backend with FastAPI
| # | Chapter | Milestone |
|---|---|---|
| 13 | [FastAPI basics](part2-backend/13-fastapi-basics.md) | M0, M1 |
| 14 | [Pydantic deep dive & settings](part2-backend/14-pydantic.md) | M1 |
| 15 | [Databases: SQLAlchemy 2.0 + Alembic](part2-backend/15-databases-sqlalchemy.md) | M2 |
| 16 | [Architecture: DI, services, errors, middleware](part2-backend/16-architecture-di.md) | M3 |
| 17 | [Auth: hashing, JWT, roles](part2-backend/17-auth.md) | M4 |
| 18 | [Background tasks & file uploads](part2-backend/18-background-tasks-uploads.md) | M5 |

### Part 3: AI features
| # | Chapter | Milestone |
|---|---|---|
| 19 | [LLM fundamentals & the Claude API](part3-ai/19-llm-fundamentals-claude.md) | M6 |
| 20 | [Structured output & classification](part3-ai/20-structured-output.md) | M6 |
| 21 | [Embeddings & vector search](part3-ai/21-embeddings-vector-search.md) | M5, M8 |
| 22 | [RAG: retrieval-augmented generation](part3-ai/22-rag.md) | M7 |
| 23 | [Evaluating AI features](part3-ai/23-evaluating-ai.md) | M8 |
| 24 | [Production basics](part3-ai/24-production-basics.md) | — |

## Milestones at a glance
| M | What you build |
|---|---|
| M0 | Scaffold: FastAPI app, `/health`, settings, first test ✅ (done for you as a reference) |
| M1 | Tickets CRUD, in memory |
| M2 | SQLite persistence with SQLAlchemy + Alembic |
| M3 | Services layer, dependency injection, error handling, logging |
| M4 | Users, JWT auth, roles |
| M5 | Knowledge base ingestion into a vector DB |
| M6 | AI triage: category / priority / sentiment |
| M7 | RAG reply drafts with citations |
| M8 | Similar-ticket search + an eval script |

## Suggested pace
About 1 chapter per day in Part 1 (you already know programming, so it's mostly syntax and idioms), and
2–3 days per chapter in Parts 2–3, where the milestones are.
