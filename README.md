# TriageDesk: learn Python by building an AI support-ticket backend

A hands-on Python learning track for Node.js developers. You read a chapter in `docs/`, do the
exercises, then build the matching milestone of **TriageDesk**, a FastAPI backend that classifies
support tickets with Claude and drafts replies using RAG over a knowledge base.

- **Start here:** [`docs/00-index.md`](docs/00-index.md)
- **Project overview & current status:** [`CLAUDE.md`](CLAUDE.md)
- **Future plans (not implemented):** [`docs/ROADMAP.md`](docs/ROADMAP.md)

## Quick start
```bash
source ~/.local/bin/env          # puts uv on PATH (once per shell, or add to ~/.bashrc)
uv sync                          # install dependencies into .venv
cp .env.example .env
uv run pytest                    # run tests
uv run fastapi dev app/main.py   # → http://localhost:8000/docs
```
